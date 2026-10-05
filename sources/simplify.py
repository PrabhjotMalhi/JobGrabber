import aiohttp

RAW_URL = "https://raw.githubusercontent.com/{repo}/dev/.github/scripts/listings.json"


async def fetch_jobs(session: aiohttp.ClientSession, repo: str) -> list[dict]:
    url = RAW_URL.format(repo=repo)
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
        if resp.status != 200:
            return []
        data = await resp.json(content_type=None)

    jobs = []
    for entry in data:
        if not entry.get("active", True):
            continue
        locations = entry.get("locations") or ["Unknown location"]
        jobs.append(
            {
                "id": str(entry.get("id") or entry.get("url") or entry.get("title")),
                "title": entry.get("title", "Untitled role"),
                "url": entry.get("url", ""),
                "location": ", ".join(locations),
                "company": entry.get("company_name", "Unknown company"),
                "category": entry.get("category", ""),
                "date_posted": entry.get("date_posted"),
            }
        )
    return jobs