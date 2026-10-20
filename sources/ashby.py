import aiohttp

API_URL = "https://api.ashbyhq.com/posting-api/job-board/{slug}"


async def fetch_jobs(session: aiohttp.ClientSession, slug: str) -> list[dict]:
    url = API_URL.format(slug=slug)
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
        if resp.status != 200:
            return []
        data = await resp.json()

    jobs = []
    for job in data.get("jobs", []):
        if not job.get("isListed", True):
            continue
        job_url = job.get("jobUrl") or job.get("applyUrl") or ""
        location = job.get("location") or "Unknown location"
        if job.get("isRemote") and "remote" not in location.lower():
            location += " (Remote)"
        jobs.append(
            {
                "id": str(job.get("id") or job_url),
                "title": job.get("title", "Untitled role"),
                "url": job_url,
                "location": location,
            }
        )
    return jobs
