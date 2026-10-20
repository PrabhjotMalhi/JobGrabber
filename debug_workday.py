"""
Show exactly what a Workday career site returns, and what the bot would do with it.

  python debug_workday.py "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"
"""
import asyncio
import json
import sys
import time

import aiohttp

import config
import filters
from sources import workday


async def main(url, session=None):
    own = session is None
    if own:
        session = aiohttp.ClientSession()
    try:
        host, tenant, site = workday.parse_careers_url(url)
        api = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
        payload = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}
        print("POST", api)
        async with session.post(api, json=payload, headers={"Accept": "application/json"}) as resp:
            print("HTTP status:", resp.status)
            print("Content-Type:", resp.headers.get("Content-Type"))
            body = await resp.text()
        try:
            data = json.loads(body)
        except ValueError:
            print("Response is NOT JSON. First 300 characters:\n", body[:300])
            return
        print("Top-level keys:", list(data.keys()) if isinstance(data, dict) else type(data).__name__)
        postings = (data.get("jobPostings") or []) if isinstance(data, dict) else []
        print("total reported:", data.get("total") if isinstance(data, dict) else "?", "| postings on page 1:", len(postings))
        print("\nFirst 10 postings exactly as Workday sends them:")
        for p in postings[:10]:
            print(f"  {str(p.get('postedOn')):<22} | {p.get('title')} | {p.get('locationsText')}")

        print("\n--- what the bot's connector makes of it ---")
        jobs = await workday.fetch_jobs(session, url)
        cutoff = time.time() - config.MAX_POSTING_AGE_DAYS * 86400
        swe = [j for j in jobs if filters.software_eng_role(j["title"])]
        recent = [j for j in swe if j["date_posted"] and j["date_posted"] >= cutoff]
        undated = [j for j in jobs if not j["date_posted"]]
        print(f"jobs read: {len(jobs)} | pass title filter: {len(swe)} | "
              f"also posted in last {config.MAX_POSTING_AGE_DAYS} days: {len(recent)} | missing a date: {len(undated)}")
        for j in recent[:10]:
            print("  WOULD POST:", j["title"], "|", j["location"])
        if not recent and swe:
            print("  (software jobs exist but none are recent - normal if the company posted nothing new)")
        if not swe and jobs:
            print("  Titles seen (none matched the filter):", [j["title"] for j in jobs[:5]])
    finally:
        if own:
            await session.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit('Usage: python debug_workday.py "<careers page URL>"')
    asyncio.run(main(sys.argv[1]))