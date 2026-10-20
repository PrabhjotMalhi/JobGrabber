"""
Find the Workday career-site URL for each company name.

  python discover_workday.py                         check every name in NAMES below
  python discover_workday.py "Capital One" "Wells Fargo|wf"   check only these

"Name|tenant" lets you give the Workday tenant yourself when it differs from the name
(the tenant is the first part of the company's careers URL: https://TENANT.wd5.myworkdayjobs.com/...).

How it works: for each company it tries the Workday servers (wd1, wd5, ...), reads the
tenant's robots.txt to learn its career-site names, then confirms each one by asking
for its job count. Working sites are merged into discovered_companies.json, which
config.py already loads. Re-running is safe.
"""
import asyncio
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import aiohttp

OUT_FILE = Path(__file__).parent / "discovered_companies.json"
PODS = ["wd5", "wd1", "wd3", "wd12", "wd2", "wd103", "wd108", "wd501"]
CONCURRENCY = 6
MAX_SITES_PER_COMPANY = 3     # e.g. a main site plus a university/early-career site
_LOCALE_RE = re.compile(r"^[a-z]{2}([-_][A-Za-z]{2})?$")

# Plain names are tried as the tenant name; "Name|tenant" sets it explicitly.
# These are guesses to test, so many will come back "none".
NAMES = [
    "Nvidia", "Salesforce", "Adobe", "Workday", "Intel", "AMD", "Qualcomm", "Dell", "HP",
    "Hewlett Packard Enterprise|hpe", "Broadcom", "Micron", "Texas Instruments|ti",
    "Analog Devices|analogdevices", "Applied Materials|amat", "Lam Research|lamresearch", "KLA",
    "Western Digital|wdc", "Seagate", "NetApp", "Pure Storage|purestorage", "Nutanix", "Autodesk",
    "Zoom", "Snowflake", "Juniper Networks|juniper", "Arista Networks|arista",
    "Motorola Solutions|motorolasolutions", "Zebra Technologies|zebra", "Logitech", "Synopsys",
    "Cadence", "Ansys", "PTC", "Teradyne", "Keysight", "Marvell", "ON Semiconductor|onsemi",
    "Microchip", "Skyworks", "Qorvo", "Lumentum", "Coherent", "Ciena", "Intuit", "Box",
    "DocuSign", "Splunk", "VMware", "Akamai", "Palo Alto Networks|paloaltonetworks", "Fortinet",
    "Dynatrace", "Zillow", "Expedia", "eBay", "Yahoo", "Warner Bros Discovery|wbd", "Comcast",
    "Verizon", "T-Mobile|tmobile", "Charter Communications|charter", "AT&T|att",
    "Mastercard", "PayPal", "Capital One|capitalone", "Citi", "Wells Fargo|wf", "Morgan Stanley|ms",
    "BlackRock", "State Street|statestreet", "American Express|aexp", "Discover", "Synchrony",
    "Ally", "PNC", "Truist", "Fifth Third|fifththird", "KeyBank|key", "Northern Trust|northerntrust",
    "T. Rowe Price|troweprice", "Franklin Templeton|franklintempleton", "Invesco", "Nasdaq",
    "Intercontinental Exchange|ice", "CME Group|cmegroup", "S&P Global|spgi", "Moody's|moodys",
    "MSCI", "FactSet", "Morningstar", "Fiserv", "FIS|fis", "Broadridge", "Equifax",
    "TransUnion|transunion", "Charles Schwab|schwab", "Fidelity|fmr", "Vanguard", "Prudential",
    "MetLife", "Aflac", "Allstate", "Progressive", "Travelers", "Liberty Mutual|libertymutual",
    "Nationwide", "Principal", "Lincoln Financial|lfg", "Guardian", "MassMutual|massmutual",
    "Accenture", "Booz Allen Hamilton|bah", "Leidos", "SAIC", "CACI", "MITRE",
    "Lockheed Martin|lmco", "Northrop Grumman|ngc", "Boeing", "General Dynamics|gd",
    "L3Harris|l3harris", "BAE Systems|baesystems", "Honeywell", "GE Aerospace|geaerospace",
    "Raytheon", "Textron", "3M", "Cummins", "Caterpillar", "General Motors|gm", "Rivian", "Lucid",
    "Johnson Controls|jci", "Emerson", "Rockwell Automation|rockwellautomation",
    "Schneider Electric|schneider", "Eaton", "Parker Hannifin|parker", "Walmart", "Target",
    "Best Buy|bestbuy", "Nike", "Starbucks", "Lowe's|lowes", "Kroger", "Albertsons", "Gap Inc|gap",
    "Macy's|macys", "Under Armour|underarmour", "Lululemon", "Pfizer", "Merck|msd", "Amgen",
    "Gilead", "Moderna|modernatx", "Regeneron", "Vertex", "Illumina", "Thermo Fisher|thermofisher",
    "Danaher", "Abbott", "Medtronic", "Boston Scientific|bostonscientific", "Stryker",
    "Becton Dickinson|bd", "Cigna", "Elevance Health|elevancehealth", "CVS Health|cvshealth",
    "Humana", "Centene", "HCA Healthcare|hca", "Bristol Myers Squibb|bms", "AstraZeneca",
    "Sanofi", "Expedia Group|expedia", "CIBC", "BMO", "RBC"
]

OTHER_ERRORS = 0


async def _sleep(seconds):
    await asyncio.sleep(seconds)


def tenant_variants(display: str) -> list[str]:
    base = re.sub(r"\(.*?\)", "", display).lower().strip()
    squashed = re.sub(r"[^a-z0-9]", "", base)
    hyphenated = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    out = []
    for v in (squashed, hyphenated):
        if v and v not in out:
            out.append(v)
    return out


def sites_from_robots(text: str, host: str) -> list[str]:
    """Career-site names from the 'Sitemap:' lines of a tenant's robots.txt."""
    slugs = []
    for m in re.finditer(r"(?im)^\s*sitemap:\s*(\S+)", text):
        p = urlparse(m.group(1))
        if (p.hostname or "").lower() != host:
            continue
        parts = [s for s in p.path.split("/") if s]
        if parts and _LOCALE_RE.match(parts[0]):
            parts = parts[1:]
        if len(parts) >= 2 and not parts[0].lower().startswith("sitemap"):
            if parts[0] not in slugs:
                slugs.append(parts[0])
    return slugs


async def _request(session, method, url, **kw):
    """One request; waits and retries on HTTP 429. Returns (status, text) or (None, '') on failure."""
    global OTHER_ERRORS
    for attempt in range(3):
        try:
            async with session.request(method, url, timeout=aiohttp.ClientTimeout(total=20), **kw) as resp:
                if resp.status == 429 and attempt < 2:
                    retry_after = str(resp.headers.get("Retry-After", ""))
                    wait = int(retry_after) if retry_after.isdigit() else 0
                    await _sleep(min(wait or 5 * (attempt + 1), 60))
                    continue
                if resp.status in (429,) or resp.status >= 500:
                    OTHER_ERRORS += 1
                return resp.status, (await resp.text() if resp.status == 200 else "")
        except aiohttp.ClientConnectorError:
            return None, ""                      # that host doesn't exist: simply "not found"
        except (aiohttp.ClientError, asyncio.TimeoutError):
            OTHER_ERRORS += 1
            return None, ""
    return None, ""


async def job_count(session, host: str, tenant: str, site: str):
    api = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
    payload = {"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""}
    status, body = await _request(session, "POST", api, json=payload, headers={"Accept": "application/json"})
    if status != 200:
        return None
    try:
        data = json.loads(body)
    except ValueError:
        return None
    total = data.get("total") if isinstance(data, dict) else None
    return total if isinstance(total, int) else None


async def discover_one(session, sem, entry: str):
    display, _, explicit = entry.partition("|")
    display = display.strip()
    tenants = [explicit.strip().lower()] if explicit.strip() else tenant_variants(display)
    for tenant in tenants:
        for pod in PODS:
            host = f"{tenant}.{pod}.myworkdayjobs.com"
            async with sem:
                status, body = await _request(session, "GET", f"https://{host}/robots.txt")
            if status != 200:
                continue
            slugs = sites_from_robots(body, host)
            if not slugs:
                continue
            found = []
            for slug in slugs:
                async with sem:
                    total = await job_count(session, host, tenant, slug)
                if total:
                    found.append((total, slug))
            if found:
                found.sort(reverse=True)
                return {"display": display, "host": host, "sites": found[:MAX_SITES_PER_COMPANY]}
    return None


async def main(entries: list[str]):
    seen, unique = set(), []
    for e in entries:
        if e.lower() not in seen:
            seen.add(e.lower())
            unique.append(e)

    existing = {}
    if OUT_FILE.exists():
        for c in json.loads(OUT_FILE.read_text(encoding="utf-8")):
            existing[c["name"].lower()] = c

    sem = asyncio.Semaphore(CONCURRENCY)
    async with aiohttp.ClientSession(headers={"User-Agent": "jobbot-discovery/1.0"}) as session:
        results = await asyncio.gather(*(discover_one(session, sem, e) for e in unique))

    found = 0
    for entry, r in zip(unique, results):
        if r is None:
            print(f"none   {entry.split('|')[0]}")
            continue
        found += 1
        for i, (total, slug) in enumerate(r["sites"]):
            name = r["display"] if i == 0 else f"{r['display']} ({slug})"
            url = f"https://{r['host']}/{slug}"
            existing[name.lower()] = {"name": name, "ats": "workday", "slug": url}
            print(f"FOUND  {name:<34} {r['host'].split('.')[0]}.{r['host'].split('.')[1]}/{slug:<30} {total:>5} jobs")

    entries_out = sorted(existing.values(), key=lambda c: c["name"].lower())
    OUT_FILE.write_text(json.dumps(entries_out, indent=2), encoding="utf-8")
    print(f"\nFound Workday sites for {found} of {len(unique)} names. {len(entries_out)} companies now in {OUT_FILE.name}.")
    if OTHER_ERRORS:
        print(f"{OTHER_ERRORS} requests hit rate limits or timeouts - wait a few minutes and re-run to fill gaps.")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:] or NAMES))