import asyncio, aiohttp

async def main():
    url = "https://boards-api.greenhouse.io/v1/boards/stripe/jobs?content=true"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
    for job in data["jobs"][:10]:
        print(job["title"], "-", job["absolute_url"])
        
asyncio.run(main())