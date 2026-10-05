import aiohttp

API_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"


async def fetch_jobs(session: aiohttp.ClientSession, slug: str) -> list[dict]:
    url = API_URL.format(slug=slug)
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
        if resp.status != 200:
            return []
        data = await resp.json()

    jobs = []
    for job in data.get("jobs", []):
        jobs.append(
            {
                "id": str(job["id"]),
                "title": job.get("title", "Untitled role"),
                "url": job.get("absolute_url", ""),
                "location": (job.get("location") or {}).get("name", "Unknown location"),
            }
        )
    return jobs