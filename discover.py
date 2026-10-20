"""
Find which job board (Greenhouse / Lever / Ashby) each company uses, and its slug.

  python discover.py                          check every name in NAMES below
  python discover.py "Some Company" "Other"   check only these names

Working boards are saved to discovered_companies.json, which config.py loads
automatically. Re-running is safe: new finds are merged into the existing file.
"""
import asyncio
import json
import re
import sys
from pathlib import Path

import aiohttp

OUT_FILE = Path(__file__).parent / "discovered_companies.json"
CONCURRENCY = 8

ENDPOINTS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
}

# Add any company you like here (plain names, no slugs needed).
NAMES = [
    "Stripe", "Airbnb", "Databricks", "Figma", "Coinbase", "Robinhood", "Instacart", "Lyft",
    "Pinterest", "Reddit", "Discord", "Dropbox", "Twilio", "Cloudflare", "Datadog", "MongoDB",
    "Anthropic", "Scale AI", "Brex", "Affirm", "DoorDash", "Vercel", "Palantir", "Spotify",
    "Plaid", "OpenAI", "Ramp", "Notion", "Linear", "PostHog", "Deel", "Supabase",
    "GitLab", "Okta", "Asana", "PagerDuty", "Elastic", "Roblox", "Samsara", "Duolingo",
    "Squarespace", "Airtable", "Flexport", "Gusto", "Checkr", "Carta", "Webflow", "Grammarly",
    "Mixpanel", "Amplitude", "Sentry", "Intercom", "HashiCorp", "DigitalOcean", "Fastly",
    "Lattice", "Faire", "Opendoor", "Peloton", "Etsy", "NerdWallet", "Betterment", "Wealthfront",
    "Ripple", "Kraken", "Chainalysis", "Anduril", "SpaceX", "Cruise", "Nuro", "Epic Games",
    "Riot Games", "Unity", "Verkada", "Fivetran", "dbt Labs", "Retool", "Benchling", "Mercury",
    "Rippling", "Chime", "SoFi", "Toast", "Zapier", "Miro", "Airbyte", "Confluent",
    "Cockroach Labs", "Temporal", "Netlify", "Render", "Fly.io", "Railway", "PlanetScale",
    "Neon", "ClickHouse", "Cohere", "Mistral AI", "Perplexity", "Anysphere", "Hugging Face",
    "Replit", "Glean", "Harvey", "Sierra", "Decagon", "Abridge", "Applied Intuition", "Rivian",
    "Lucid Motors", "Relativity Space", "Rocket Lab", "Planet Labs", "Shield AI", "Saronic",
    "Hadrian", "Ironclad", "Loom", "Calendly", "Gong", "Clari", "Outreach", "Heap",
    "LaunchDarkly", "Postman", "Snyk", "1Password", "Tailscale", "Wiz", "SentinelOne", "Vanta",
    "Drata", "Alchemy", "Consensys", "Uniswap Labs", "Paxos", "Anchorage Digital", "Gemini",
    "BitGo", "Jane Street", "Hudson River Trading", "DRW", "Jump Trading", "Two Sigma",
    "IMC Trading", "Optiver", "Tower Research Capital", "Attentive", "Klaviyo", "Braze",
    "Iterable", "Veeva", "Circle", "Navan", "Zocdoc", "Oscar Health", "Hims & Hers", "Ro",
    "Cerebras", "Groq", "Lambda", "CoreWeave", "Together AI", "Modal", "Anyscale",
    "Weights & Biases", "Pinecone", "Weaviate", "LangChain", "Snorkel AI", "Labelbox",
    "Character.AI", "Runway", "ElevenLabs", "Stability AI", "xAI", "Cognition", "Poolside",
    "Luma AI", "Honeycomb", "Grafana Labs", "New Relic", "Sumo Logic", "Dynatrace", "Zendesk",
    "Freshworks", "Sourcegraph", "Marqeta", "Wise", "Monzo", "Mux", "Segment", "Clerk",
    "Resend", "Sanity", "Contentful", "Algolia", "Typeform", "Lucid Software", "Podium",
    "Blend", "Ripple Labs", "Thumbtack", "Yelp", "Quora", "Medium", "Patreon", "Substack",
    "Strava", "Whoop", "Oura", "Sonos", "GoPro", "Bumble", "Match Group", "Zynga",
    "Niantic", "Scopely", "Supercell", "Wizards of the Coast", "Blizzard",
]


def slug_variants(name: str) -> list[str]:
    base = re.sub(r"\(.*?\)", "", name).lower().strip()
    squashed = re.sub(r"[^a-z0-9]", "", base)
    hyphenated = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    out = []
    for v in (squashed, hyphenated):
        if v and v not in out:
            out.append(v)
    return out


OTHER_ERRORS = 0


async def probe(session, ats: str, slug: str):
    """Number of open jobs if this board exists, otherwise None."""
    global OTHER_ERRORS
    url = ENDPOINTS[ats].format(slug=slug)
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            if resp.status == 404:
                return None
            if resp.status != 200:
                OTHER_ERRORS += 1
                return None
            data = await resp.json(content_type=None)
    except Exception:
        OTHER_ERRORS += 1
        return None
    jobs = data.get("jobs") if isinstance(data, dict) else data
    return len(jobs) if isinstance(jobs, list) else None


async def discover_one(session, sem, name: str):
    candidates = []
    for slug in slug_variants(name):
        for ats in ENDPOINTS:
            async with sem:
                count = await probe(session, ats, slug)
            if count:  # a board with 0 open jobs is useless (or abandoned), so skip it
                candidates.append((count, ats, slug))
    if not candidates:
        return None
    count, ats, slug = max(candidates, key=lambda c: c[0])
    return {"name": name, "ats": ats, "slug": slug, "jobs": count}


async def main(names: list[str]):
    seen, unique = set(), []
    for n in names:
        if n.lower() not in seen:
            seen.add(n.lower())
            unique.append(n)

    existing = {}
    if OUT_FILE.exists():
        for c in json.loads(OUT_FILE.read_text(encoding="utf-8")):
            existing[c["name"].lower()] = c

    sem = asyncio.Semaphore(CONCURRENCY)
    async with aiohttp.ClientSession(headers={"User-Agent": "jobbot-discovery/1.0"}) as session:
        results = await asyncio.gather(*(discover_one(session, sem, n) for n in unique))

    found = 0
    for name, r in zip(unique, results):
        if r is None:
            print(f"none   {name}")
            continue
        found += 1
        print(f"FOUND  {name:<26} {r['ats']}:{r['slug']:<24} {r['jobs']:>4} open jobs")
        existing[name.lower()] = {"name": r["name"], "ats": r["ats"], "slug": r["slug"]}

    entries = sorted(existing.values(), key=lambda c: c["name"].lower())
    OUT_FILE.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    print(f"\nFound boards for {found} of {len(unique)} names. {len(entries)} companies saved to {OUT_FILE.name}.")
    if OTHER_ERRORS:
        print(f"{OTHER_ERRORS} requests failed with timeouts or rate limits - re-run to retry those.")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:] or NAMES))