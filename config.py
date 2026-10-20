# ---------- Where jobs get posted ----------
JOBS_CATEGORY_NAME = "💼 Job Postings"
JOBS_CHANNEL_NAME = "new-jobs"

# ---------- Companies to watch ----------
# ats must be "greenhouse", "lever", or "ashby"
# slug = the part of the company's job board URL after the site name, e.g.
#   boards.greenhouse.io/<slug>   jobs.lever.co/<slug>   jobs.ashbyhq.com/<slug>
COMPANIES = [
    # Greenhouse
    {"name": "Stripe", "ats": "greenhouse", "slug": "stripe"},
    {"name": "Airbnb", "ats": "greenhouse", "slug": "airbnb"},
    {"name": "Databricks", "ats": "greenhouse", "slug": "databricks"},
    {"name": "Figma", "ats": "greenhouse", "slug": "figma"},
    {"name": "Coinbase", "ats": "greenhouse", "slug": "coinbase"},
    {"name": "Robinhood", "ats": "greenhouse", "slug": "robinhood"},
    {"name": "Instacart", "ats": "greenhouse", "slug": "instacart"},
    {"name": "Lyft", "ats": "greenhouse", "slug": "lyft"},
    {"name": "Pinterest", "ats": "greenhouse", "slug": "pinterest"},
    {"name": "Reddit", "ats": "greenhouse", "slug": "reddit"},
    {"name": "Discord", "ats": "greenhouse", "slug": "discord"},
    {"name": "Dropbox", "ats": "greenhouse", "slug": "dropbox"},
    {"name": "Twilio", "ats": "greenhouse", "slug": "twilio"},
    {"name": "Cloudflare", "ats": "greenhouse", "slug": "cloudflare"},
    {"name": "Datadog", "ats": "greenhouse", "slug": "datadog"},
    {"name": "MongoDB", "ats": "greenhouse", "slug": "mongodb"},
    {"name": "Anthropic", "ats": "greenhouse", "slug": "anthropic"},
    {"name": "Scale AI", "ats": "greenhouse", "slug": "scaleai"},
    {"name": "Brex", "ats": "greenhouse", "slug": "brex"},
    {"name": "Affirm", "ats": "greenhouse", "slug": "affirm"},
    {"name": "DoorDash", "ats": "greenhouse", "slug": "doordash"},
    {"name": "Vercel", "ats": "greenhouse", "slug": "vercel"},
    # Lever
    {"name": "Palantir", "ats": "lever", "slug": "palantir"},
    {"name": "Spotify", "ats": "lever", "slug": "spotify"},
    {"name": "Plaid", "ats": "lever", "slug": "plaid"},
    # Ashby
    {"name": "OpenAI", "ats": "ashby", "slug": "openai"},
    {"name": "Ramp", "ats": "ashby", "slug": "ramp"},
    {"name": "Notion", "ats": "ashby", "slug": "notion"},
    {"name": "Linear", "ats": "ashby", "slug": "linear"},
    {"name": "PostHog", "ats": "ashby", "slug": "posthog"},
    {"name": "Deel", "ats": "ashby", "slug": "deel"},
    {"name": "Supabase", "ats": "ashby", "slug": "supabase"},
]

# ---------- Simplify (new-grad only) ----------
SIMPLIFY_REPOS = {
    "new-grad": "SimplifyJobs/New-Grad-Positions",
}
SIMPLIFY_CATEGORIES = {"Software", "Software Engineering"}
MAX_POSTING_AGE_DAYS = 2

# ---------- Title filter for company career pages ----------
TITLE_INCLUDED_KEYWORDS = [
    "software engineer", "software developer", "backend engineer", "back-end engineer",
    "frontend engineer", "front-end engineer", "full stack engineer", "fullstack engineer",
    "full-stack engineer", "platform engineer", "infrastructure engineer", "systems engineer",
    "site reliability", "mobile engineer", "ios engineer", "android engineer", "devops engineer", "software development engineer",
    "sde",
]
TITLE_EXCLUDED_KEYWORDS = [
    "sales engineer", "solutions engineer", "support engineer", "field engineer",
    "hardware engineer", "mechanical engineer", "electrical engineer", "civil engineer",
]


# ---------- Auto-discovered companies (created by discover.py) ----------
import json
from pathlib import Path

_discovered_file = Path(__file__).parent / "discovered_companies.json"
if _discovered_file.exists():
    _have_names = {c["name"].lower() for c in COMPANIES}
    _have_boards = {(c["ats"], c["slug"]) for c in COMPANIES}
    for _c in json.loads(_discovered_file.read_text(encoding="utf-8")):
        if _c["name"].lower() not in _have_names and (_c["ats"], _c["slug"]) not in _have_boards:
            COMPANIES.append(_c)
            
# ---------- Workday companies: name -> careers-page URL (copy it from your browser) ----------
WORKDAY_SITES = {
    "Nvidia": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
    "Salesforce": "https://salesforce.wd12.myworkdayjobs.com/External_Career_Site",
    "Adobe": "https://adobe.wd5.myworkdayjobs.com/external_experienced",
    "Workday": "https://workday.wd5.myworkdayjobs.com/Workday",
    "Nike": "https://nike.wd1.myworkdayjobs.com/NikeCareers",
    "Accenture": "https://accenture.wd103.myworkdayjobs.com/AccentureCareers",
}
_have_names = {c["name"].lower() for c in COMPANIES}
for _name, _url in WORKDAY_SITES.items():
    if _name.lower() not in _have_names:
        COMPANIES.append({"name": _name, "ats": "workday", "slug": _url})