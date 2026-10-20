import asyncio 
import aiohttp

import config 
import filters
from bot import FETCHERS

async def main():
    async with aiohttp.ClientSession() as session:
        for c in config.COMPANIES:
            try:
                jobs = await FETCHERS[c["ats"]](session, c["slug"])
            except Exception as e:
                print(f"ERROR {c['name']:<14}{e}")
                continue
            swe = [j for j in jobs if filters.software_eng_role(j["title"])]
            flag = "OK " if jobs else "EMPTY"
            print(f"{flag} {c['name']:<14} {len(jobs):>4} total, {len(swe):>3} SWE")
            
asyncio.run(main())