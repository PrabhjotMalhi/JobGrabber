"""
Workday career sites (https://<tenant>.wd<N>.myworkdayjobs.com/<site>).

Workday has no documented public API. Every career site's own web page loads its
job list from an unauthenticated JSON endpoint, and this connector reads that same
endpoint. It is unofficial, so Workday can change it without notice.
"""
import asyncio
import logging
import re
import time
from urllib.parse import urlparse

import aiohttp

import config

log = logging.getLogger("jobbot")

SEARCH_TEXT = ""      # empty = Workday returns the NEWEST jobs first
MAX_PAGES = 10
PAGE_SIZE = 20        # Workday rejects anything larger with HTTP 400
PAGE_DELAY = 1.0

RETRY_WAITS = (5, 15, 45)
MAX_RETRY_AFTER = 120
COOLDOWN_SECONDS = 15 * 60

_LOCALE_RE = re.compile(r"^[a-z]{2}([-_][A-Za-z]{2})?$")

_frontier: dict[str, set] = {}
_cooldown_until: dict[str, float] = {}


async def _sleep(seconds: float):
    await asyncio.sleep(seconds)


def parse_careers_url(url: str):
    """'https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite' -> (host, tenant, site)"""
    p = urlparse(url.strip())
    host = (p.hostname or "").lower()
    if p.scheme != "https" or not host.endswith(".myworkdayjobs.com"):
        raise ValueError("must be an https://<company>.wd<N>.myworkdayjobs.com/<site> URL")
    parts = [s for s in p.path.split("/") if s]
    if parts and _LOCALE_RE.match(parts[0]):
        parts = parts[1:]
    if not parts:
        raise ValueError("URL is missing the site name after myworkdayjobs.com/")
    return host, host.split(".")[0], parts[0]


def _posted_to_epoch(text, now):
    if not text:
        return None
    t = text.lower()
    if any(w in t for w in ("today", "just now", "hour", "minute")):
        days = 0
    elif "yesterday" in t:
        days = 1
    else:
        m = re.search(r"(\d+)\+?\s*day", t)
        if not m:
            return None
        days = int(m.group(1))
    return now - days * 86400


def _retry_after_seconds(value):
    try:
        return max(0, int(str(value).strip()))
    except (TypeError, ValueError):
        return None


async def _post_json(session, api, payload, key):
    for attempt in range(len(RETRY_WAITS) + 1):
        status, retry_after, data = None, None, None
        try:
            async with session.post(
                api, json=payload, headers={"Accept": "application/json"},
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                status = resp.status
                retry_after = resp.headers.get("Retry-After")
                if status == 200:
                    data = await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
            log.warning("Workday request failed for %s: %s", key, e)
            return None

        if status == 200:
            return data
        if status == 429:
            if attempt >= len(RETRY_WAITS):
                _cooldown_until[key] = time.time() + COOLDOWN_SECONDS
                log.warning("Workday %s keeps returning HTTP 429 (rate limited); resting it for %d minutes",
                            key, COOLDOWN_SECONDS // 60)
                return None
            wait = min(_retry_after_seconds(retry_after) or RETRY_WAITS[attempt], MAX_RETRY_AFTER)
            log.info("Workday %s: HTTP 429, waiting %ds before retry %d", key, wait, attempt + 1)
            await _sleep(wait)
            continue
        log.warning("Workday returned HTTP %s for %s - check the careers URL in config.py", status, key)
        return None
    return None


async def fetch_jobs(session: aiohttp.ClientSession, careers_url: str) -> list[dict]:
    try:
        host, tenant, site = parse_careers_url(careers_url)
    except ValueError as e:
        log.warning("Workday: bad careers URL %r (%s)", careers_url, e)
        return []

    key = f"{tenant}/{site}"
    if time.time() < _cooldown_until.get(key, 0):
        log.info("Workday %s: resting after rate limiting, skipping this check", key)
        return []

    api = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
    now = time.time()
    newest_first = not SEARCH_TEXT
    window_days = getattr(config, "MAX_POSTING_AGE_DAYS", 2)
    stop_before = now - (window_days + 1) * 86400
    previous = _frontier.get(key)
    jobs, seen_ids, total, pages, complete = [], set(), 0, 0, True

    for page in range(MAX_PAGES):
        offset = page * PAGE_SIZE
        payload = {"appliedFacets": {}, "limit": PAGE_SIZE, "offset": offset, "searchText": SEARCH_TEXT}
        data = await _post_json(session, api, payload, key)
        if data is None:
            complete = False
            break
        if not isinstance(data, dict) or "jobPostings" not in data:
            keys = list(data.keys()) if isinstance(data, dict) else type(data).__name__
            log.warning("Workday %s: unexpected response shape (keys: %s)", key, keys)
            complete = False
            break
        pages += 1
        if page == 0:
            total = data.get("total") or 0
        postings = data.get("jobPostings") or []

        page_dates, page_ids = [], []
        for p in postings:
            date_posted = _posted_to_epoch(p.get("postedOn"), now)
            page_dates.append(date_posted)
            path = p.get("externalPath") or ""
            if path and not path.startswith("/job/"):
                path = "/job" + path
            job_id = path or p.get("title", "")
            page_ids.append(job_id)
            slug = re.match(r"^/job/([^/]+)/", path)
            location_hint = re.sub(r"[-_]+", " ", slug.group(1)).strip() if slug else ""
            if not job_id or job_id in seen_ids:
                continue
            seen_ids.add(job_id)
            jobs.append(
                {
                    "id": job_id,
                    "title": p.get("title", "Untitled role"),
                    "url": f"https://{host}/{site}{path}",
                    "location": p.get("locationsText") or "Unknown location",
                    "location_hint": location_hint,
                    "date_posted": date_posted,
                }
            )

        if len(postings) < PAGE_SIZE or (total and offset + PAGE_SIZE >= total):
            break
        if newest_first and previous and page_ids and page_ids[-1] in previous:
            break
        if newest_first and page_dates and all(d is not None and d < stop_before for d in page_dates):
            break
        await _sleep(PAGE_DELAY)

    if complete and jobs:
        _frontier[key] = {j["id"] for j in jobs}
    log.info("Workday %s: read %d postings from %d page(s)", key, len(jobs), pages)
    return jobs