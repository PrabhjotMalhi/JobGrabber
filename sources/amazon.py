"""
Amazon (amazon.jobs). The careers site loads its search results from a JSON endpoint; this reads
the same one, newest first, limited to the United States and Canada.

In config.py the 'slug' is the search keyword, e.g. "software development engineer".
Unofficial endpoint: Amazon can change it without notice.
"""
import asyncio
import logging
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

import config
from . import _http

log = logging.getLogger("jobbot")

SEARCH_URL = "https://www.amazon.jobs/en/search.json"
COUNTRIES = ("USA", "CAN")
MAX_PAGES = 4
PAGE_SIZE = 100
PAGE_DELAY = 1.0

_frontier: dict[str, set] = {}


async def _sleep(seconds: float):
    await asyncio.sleep(seconds)


def _parse_date(value):
    if not value or not isinstance(value, str):
        return None
    v = re.sub(r"\s+", " ", value.strip())
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(v, fmt).replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            continue
    return None


async def fetch_jobs(session, query: str) -> list[dict]:
    key = f"amazon '{query}'"
    if _http.cooling_down(key):
        log.info("%s: resting after rate limiting, skipping this check", key)
        return []

    now = time.time()
    window_days = getattr(config, "MAX_POSTING_AGE_DAYS", 2)
    stop_before = now - (window_days + 1) * 86400
    previous = _frontier.get(query)
    jobs, seen_ids, offset, hits, pages, complete = [], set(), 0, 0, 0, True
    newest_first = None

    for page in range(MAX_PAGES):
        params = [("base_query", query)] + [("normalized_country_code[]", c) for c in COUNTRIES] + [
            ("sort", "recent"), ("offset", offset), ("result_limit", PAGE_SIZE)]
        data = await _http.request(session, "GET", f"{SEARCH_URL}?{urlencode(params)}", key, as_json=True)
        if data is None:
            complete = False
            break
        raw = data.get("jobs") if isinstance(data, dict) else None
        if raw is None:
            keys = list(data.keys()) if isinstance(data, dict) else type(data).__name__
            log.warning("%s: unexpected response shape (keys: %s)", key, keys)
            complete = False
            break
        pages += 1
        if page == 0:
            hits = data.get("hits") or 0

        rows = []
        for j in raw:
            jid = str(j.get("id_icims") or j.get("id") or "")
            if not jid:
                continue
            path = j.get("job_path") or f"/en/jobs/{jid}"
            rows.append({
                "id": jid,
                "title": j.get("title") or "Untitled role",
                "url": f"https://www.amazon.jobs{path}",
                "location": j.get("location") or j.get("normalized_location") or "Unknown location",
                "date_posted": _parse_date(j.get("posted_date")),
            })
        for r in rows:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                jobs.append(r)
        offset += len(raw)

        if page == 0:
            dates = [r["date_posted"] for r in rows if r["date_posted"] is not None]
            newest_first = all(a >= b for a, b in zip(dates, dates[1:])) if len(dates) > 1 else None
        if not raw or len(raw) < PAGE_SIZE or (hits and offset >= hits):
            break
        if newest_first and previous and rows and rows[-1]["id"] in previous:
            break
        if newest_first and rows and all(r["date_posted"] is not None and r["date_posted"] < stop_before for r in rows):
            break
        await _sleep(PAGE_DELAY)

    if complete and jobs and newest_first:
        _frontier[query] = {j["id"] for j in jobs}
    log.info("%s: read %d postings from %d page(s)", key, len(jobs), pages)
    return jobs