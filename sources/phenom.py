"""
Phenom-powered career sites, e.g. https://jobs.rbc.com/ca/en/search-results

Phenom has no public job API (its official one is for the employer only). The career page itself
loads jobs from the site's own /widgets search endpoint, which answers without a login. This
reads that, newest first. It is unofficial, so Phenom or the employer can change it any time.
"""
import asyncio
import logging
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import config
from . import _http

log = logging.getLogger("jobbot")

MAX_PAGES = 4
PAGE_SIZE = 50
PAGE_DELAY = 1.0

_frontier: dict[str, set] = {}
_site_cache: dict[str, tuple] = {}     # careers_url -> (refNum, country, lang)


async def _sleep(seconds: float):
    await asyncio.sleep(seconds)


def _parse_date(value):
    if not value or not isinstance(value, str):
        return None
    try:
        v = re.sub(r"\.\d+", "", value.strip()).replace("Z", "+00:00")
        v = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", v)
        dt = datetime.fromisoformat(v)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        return None


def _slug(title: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-") or "job"


def _location(job: dict) -> str:
    multi = job.get("multi_location") or job.get("multi_location_array")
    if isinstance(multi, list) and multi:
        parts = [m.get("location", "") if isinstance(m, dict) else str(m) for m in multi]
        parts = [p for p in parts if p]
        if parts:
            return "; ".join(parts)
    return job.get("location") or job.get("cityStateCountry") or "Unknown location"


async def _discover_site(session, careers_url, key):
    cached = _site_cache.get(careers_url)
    if cached:
        return cached
    page = await _http.request(session, "GET", careers_url, key)
    if page is None:
        return None
    ref = re.search(r'"refNum"\s*:\s*"([^"]+)"', page)
    if not ref:
        log.warning("%s: couldn't find the site's refNum on %s (not a Phenom page, or layout changed)", key, careers_url)
        return None
    parts = [s for s in urlparse(careers_url).path.split("/") if s]
    country, lang = (parts[0].lower(), parts[1].lower()) if len(parts) >= 2 and len(parts[0]) == 2 else ("us", "en")
    base = re.search(r'"baseUrl"\s*:\s*"https?://[^"/]+/([a-z]{2})/([a-z]{2})/?"', page)
    if base:
        country, lang = base.group(1), base.group(2)
    _site_cache[careers_url] = (ref.group(1), country, lang)
    return _site_cache[careers_url]


async def fetch_jobs(session, careers_url: str) -> list[dict]:
    p = urlparse(careers_url)
    if p.scheme != "https" or not p.hostname:
        log.warning("Phenom: bad careers URL %r", careers_url)
        return []
    host = p.hostname
    key = f"phenom {host}"
    if _http.cooling_down(key):
        log.info("%s: resting after rate limiting, skipping this check", key)
        return []

    site = await _discover_site(session, careers_url, key)
    if site is None:
        return []
    ref, country, lang = site

    now = time.time()
    window_days = getattr(config, "MAX_POSTING_AGE_DAYS", 2)
    stop_before = now - (window_days + 1) * 86400
    previous = _frontier.get(careers_url)
    jobs, seen_ids, offset, total, pages, complete = [], set(), 0, 0, 0, True
    newest_first = None

    for page in range(MAX_PAGES):
        payload = {
            "lang": f"{lang}_{country}", "deviceType": "desktop", "country": country,
            "pageName": "search-results", "ddoKey": "refineSearch", "sortBy": "Most recent",
            "subsearch": "", "from": offset, "jobs": True, "counts": True,
            "all_fields": ["category", "country", "state", "city", "type"], "size": PAGE_SIZE,
            "clearAll": False, "jdsource": "facets", "isSliderEnable": False, "pageId": "page11",
            "siteType": "external", "keywords": "", "global": True, "selected_fields": {},
            "locationData": {}, "refNum": ref,
        }
        data = await _http.request(session, "POST", f"https://{host}/widgets", key, as_json=True, json=payload)
        if data is None:
            _site_cache.pop(careers_url, None)
            complete = False
            break
        rs = data.get("refineSearch") if isinstance(data, dict) else None
        raw = ((rs or {}).get("data") or {}).get("jobs") if isinstance(rs, dict) else None
        if raw is None:
            keys = list(data.keys()) if isinstance(data, dict) else type(data).__name__
            log.warning("%s: unexpected response shape (keys: %s)", key, keys)
            _site_cache.pop(careers_url, None)
            complete = False
            break
        pages += 1
        if page == 0:
            total = (rs or {}).get("totalHits") or 0

        rows = []
        for j in raw:
            jid = str(j.get("jobSeqNo") or j.get("jobId") or j.get("reqId") or "")
            if not jid:
                continue
            title = j.get("title") or "Untitled role"
            rows.append({
                "id": jid,
                "title": title,
                "url": j.get("jobUrl") or f"https://{host}/{country}/{lang}/job/{jid}/{_slug(title)}",
                "location": _location(j),
                "date_posted": _parse_date(j.get("postedDate") or j.get("dateCreated")),
            })
        for r in rows:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                jobs.append(r)
        offset += len(raw)

        if page == 0:
            dates = [r["date_posted"] for r in rows if r["date_posted"] is not None]
            newest_first = all(a >= b for a, b in zip(dates, dates[1:])) if len(dates) > 1 else None
        if not raw or len(raw) < PAGE_SIZE or (total and offset >= total):
            break
        if newest_first and previous and rows and rows[-1]["id"] in previous:
            break
        if newest_first and rows and all(r["date_posted"] is not None and r["date_posted"] < stop_before for r in rows):
            break
        await _sleep(PAGE_DELAY)

    if complete and jobs and newest_first:
        _frontier[careers_url] = {j["id"] for j in jobs}
    log.info("%s: read %d postings from %d page(s)%s", key, len(jobs), pages,
             "" if newest_first is not False else " (list is not newest-first, scanning the first pages only)")
    return jobs