import aiohttp

API_URL = "https://api.lever.co/v0/postings/{slug}?mode=json"


async def fetch_jobs(session: aiohttp.ClientSession, slug: str) -> list[dict]:
    url = API_URL.format(slug=slug)
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
        if resp.status != 200:
            return []
        data = await resp.json()

    jobs = []
    for job in data:
        categories = job.get("categories", {}) or {}
        jobs.append(
            {
                "id": str(job["id"]),
                "title": job.get("text", "Untitled role"),
                "url": job.get("hostedUrl", ""),
                "location": categories.get("location", "Unknown location"),
            }
        )
    return jobs