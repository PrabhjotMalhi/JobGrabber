"""
SAP SuccessFactors career sites, e.g. https://jobs.scotiabank.com

These sites show job lists as plain HTML tables (title, date, location). This reads those
public list pages, newest first. In config.py use a list-page URL: a category page such as
https://jobs.scotiabank.com/go/IT-&-Digital-Banking-Jobs/2298017/ or a search page.
It is not an official API, so a site redesign can break it.
"""
import asyncio
import html as htmllib
import logging
import re
import time
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import config
from . import _http

log = logging.getLogger("jobbot")

MAX_PAGES = 6
PAGE_DELAY = 1.0
DEFAULT_PAGE_SIZE = 25     # used only if the page doesn't say "Results 1 - 25 of 300"

_JOB_LINK_RE = re.compile(r'<a\b[^>]*?\bhref="([^"]*?/job/[^"]*?/(\d+)/?(?:\?[^"]*)?)"[^>]*>(.*?)</a>', re.S | re.I)
_TAG_RE = re.compile(r"<[^>]+>")
_DATE_RE = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),\s+(\d{4})\b")
_LOC_SPAN_RE = re.compile(r'class="[^"]*\bjobLocation\b[^"]*"[^>]*>(.*?)</', re.S | re.I)
_LOC_FALLBACK_RE = re.compile(r"([A-Za-zÀ-ÿ.'() \-]{2,40},\s*[A-Za-z0-9]{1,3},\s*[A-Z]{2})\b")
_TOTAL_RE = re.compile(r"Results\s+(\d+)\s*[–—-]\s*(\d+)\s+of\s+(\d+)")
_MONTHS = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}

_frontier: dict[str, set] = {}


async def _sleep(seconds: float):
    await asyncio.sleep(seconds)


def _clean(fragment: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(_TAG_RE.sub(" ", fragment))).strip()


def _page_url(base_url: str, startrow: int) -> str:
    p = urlparse(base_url)
    q = dict(parse_qsl(p.query, keep_blank_values=True))
    q.setdefault("q", "")
    q.setdefault("sortColumn", "referencedate")
    q.setdefault("sortDirection", "desc")
    q.setdefault("locale", "en_US")
    if startrow:
        q["startrow"] = str(startrow)
    else:
        q.pop("startrow", None)
    return urlunparse(p._replace(query=urlencode(q)))


def parse_listing(page_html: str, base_url: str):
    """Returns ([job dicts in page order], (shown_to, total) or None)."""
    matches = list(_JOB_LINK_RE.finditer(page_html))
    groups = []
    for m in matches:
        if groups and groups[-1]["id"] == m.group(2):
            groups[-1]["links"].append(m)
        else:
            groups.append({"id": m.group(2), "links": [m], "start": m.start()})
    jobs, seen = [], set()
    for i, g in enumerate(groups):
        if g["id"] in seen:
            continue
        seen.add(g["id"])
        end = groups[i + 1]["start"] if i + 1 < len(groups) else g["start"] + 3000
        chunk = page_html[g["start"]:end]
        title = next((t for t in (_clean(m.group(3)) for m in g["links"]) if t), "Untitled role")
        d = _DATE_RE.search(_clean(chunk))
        date_posted = None
        if d:
            try:
                date_posted = datetime(int(d.group(3)), _MONTHS[d.group(1)], int(d.group(2)),
                                       tzinfo=timezone.utc).timestamp()
            except ValueError:
                pass
        loc_m = _LOC_SPAN_RE.search(chunk)
        location = _clean(loc_m.group(1)) if loc_m else ""
        if not location:
            fb = _LOC_FALLBACK_RE.search(_clean(chunk))
            location = fb.group(1).strip() if fb else "Unknown location"
        jobs.append({
            "id": g["id"],
            "title": title,
            "url": urljoin(base_url, htmllib.unescape(g["links"][0].group(1))),
            "location": location,
            "date_posted": date_posted,
        })
    total = _TOTAL_RE.search(_clean(page_html))
    return jobs, ((int(total.group(2)), int(total.group(3))) if total else None)


async def fetch_jobs(session, list_url: str) -> list[dict]:
    p = urlparse(list_url)
    if p.scheme != "https" or not p.hostname:
        log.warning("SuccessFactors: bad list URL %r", list_url)
        return []
    key = f"successfactors {p.hostname}{p.path}"
    if _http.cooling_down(key):
        log.info("%s: resting after rate limiting, skipping this check", key)
        return []

    now = time.time()
    window_days = getattr(config, "MAX_POSTING_AGE_DAYS", 2)
    stop_before = now - (window_days + 1) * 86400
    previous = _frontier.get(key)
    jobs, seen_ids, consumed, pages, complete = [], set(), 0, 0, True

    for page in range(MAX_PAGES):
        page_html = await _http.request(session, "GET", _page_url(list_url, consumed), key)
        if page_html is None:
            complete = False
            break
        rows, totals = parse_listing(page_html, list_url)
        if not rows:
            if page == 0:
                log.warning("%s: no job rows found on the page (layout changed, or the page is blocked)", key)
                complete = False
            break
        pages += 1
        consumed += len(rows)
        for j in rows:
            if j["id"] not in seen_ids:
                seen_ids.add(j["id"])
                jobs.append(j)

        if totals and totals[0] >= totals[1]:
            break
        if not totals and len(rows) < DEFAULT_PAGE_SIZE:
            break
        if previous and rows[-1]["id"] in previous:
            break
        if all(r["date_posted"] is not None and r["date_posted"] < stop_before for r in rows):
            break
        await _sleep(PAGE_DELAY)

    if complete and jobs:
        _frontier[key] = {j["id"] for j in jobs}
    log.info("%s: read %d postings from %d page(s)", key, len(jobs), pages)
    return jobs