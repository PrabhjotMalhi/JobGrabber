import json
from pathlib import Path

# ---------- Discord layout (two categories, three channels) ----------
TECH_CATEGORY_NAME = "💻 SWE-Dev-Analyst Roles"
OTHER_CATEGORY_NAME = "📋 Other Entry-Level Roles"
TECH_CANADA_CHANNEL = "tech-canada"
TECH_US_CHANNEL = "tech-united-states"      # also receives remote roles
OTHER_CHANNEL = "other-roles-canada-us"

INTERN_TECH_CATEGORY_NAME = "🎓 Tech Internships"
INTERN_TECH_CANADA_CHANNEL = "intern-tech-canada"
INTERN_TECH_US_CHANNEL = "intern-tech-united-states"

INTERN_FIN_CATEGORY_NAME = "🏦 Finance Internships"
INTERN_FIN_CANADA_CHANNEL = "intern-finance-canada"
INTERN_FIN_US_CHANNEL = "intern-finance-united-states"

FIN_CATEGORY_NAME = "💰 Finance & Accounting Roles"
FIN_CANADA_CHANNEL = "finance-canada"
FIN_US_CHANNEL = "finance-united-states"

# Only postings from the last N days are announced (for sources that report a date)
MAX_POSTING_AGE_DAYS = 2

# ---------- Companies to watch ----------
# ats:  greenhouse | lever | ashby | workday | successfactors | phenom | amazon
# slug: greenhouse/lever/ashby -> the board name in the URL (boards.greenhouse.io/<slug>, jobs.lever.co/<slug>,
#                                 jobs.ashbyhq.com/<slug>)
#       workday / successfactors / phenom -> the full careers-page URL
#       amazon -> a search phrase
# Slugs/URLs I could not test from here: run `python check_companies.py` and delete or fix any it flags.
COMPANIES = [
    # ----- Greenhouse -----
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
    {"name": "GitLab", "ats": "greenhouse", "slug": "gitlab"},
    {"name": "Asana", "ats": "greenhouse", "slug": "asana"},
    {"name": "Okta", "ats": "greenhouse", "slug": "okta"},
    {"name": "Elastic", "ats": "greenhouse", "slug": "elastic"},
    {"name": "Samsara", "ats": "greenhouse", "slug": "samsara"},
    {"name": "Airtable", "ats": "greenhouse", "slug": "airtable"},
    {"name": "Duolingo", "ats": "greenhouse", "slug": "duolingo"},
    {"name": "Roblox", "ats": "greenhouse", "slug": "roblox"},
    {"name": "Squarespace", "ats": "greenhouse", "slug": "squarespace"},
    {"name": "Etsy", "ats": "greenhouse", "slug": "etsy"},
    {"name": "PagerDuty", "ats": "greenhouse", "slug": "pagerduty"},
    {"name": "Fastly", "ats": "greenhouse", "slug": "fastly"},
    {"name": "Mixpanel", "ats": "greenhouse", "slug": "mixpanel"},
    {"name": "Amplitude", "ats": "greenhouse", "slug": "amplitude"},
    {"name": "Carta", "ats": "greenhouse", "slug": "carta"},
    {"name": "Gusto", "ats": "greenhouse", "slug": "gusto"},
    {"name": "Chime", "ats": "greenhouse", "slug": "chime"},
    {"name": "SoFi", "ats": "greenhouse", "slug": "sofi"},
    {"name": "Toast", "ats": "greenhouse", "slug": "toast"},
    {"name": "Webflow", "ats": "greenhouse", "slug": "webflow"},
    {"name": "Grammarly", "ats": "greenhouse", "slug": "grammarly"},
    {"name": "HubSpot", "ats": "greenhouse", "slug": "hubspot"},
    {"name": "Intercom", "ats": "greenhouse", "slug": "intercom"},
    {"name": "Klaviyo", "ats": "greenhouse", "slug": "klaviyo"},
    {"name": "Faire", "ats": "greenhouse", "slug": "faire"},
    {"name": "Flexport", "ats": "greenhouse", "slug": "flexport"},
    {"name": "Unity", "ats": "greenhouse", "slug": "unity3d"},
    {"name": "Hudson River Trading", "ats": "greenhouse", "slug": "hudsonrivertrading"},
    {"name": "Clio", "ats": "greenhouse", "slug": "clio"},
    {"name": "Lightspeed", "ats": "greenhouse", "slug": "lightspeedhq"},
    {"name": "Wealthsimple", "ats": "ashby", "slug": "wealthsimple"},
    # ----- Lever -----
    {"name": "Palantir", "ats": "lever", "slug": "palantir"},
    {"name": "Spotify", "ats": "lever", "slug": "spotify"},
    {"name": "Plaid", "ats": "lever", "slug": "plaid"},
    {"name": "Mistral AI", "ats": "lever", "slug": "mistral"},
    {"name": "Zoox", "ats": "lever", "slug": "zoox"},
    # ----- Ashby -----
    {"name": "OpenAI", "ats": "ashby", "slug": "openai"},
    {"name": "Ramp", "ats": "ashby", "slug": "ramp"},
    {"name": "Notion", "ats": "ashby", "slug": "notion"},
    {"name": "Linear", "ats": "ashby", "slug": "linear"},
    {"name": "PostHog", "ats": "ashby", "slug": "posthog"},
    {"name": "Deel", "ats": "ashby", "slug": "deel"},
    {"name": "Supabase", "ats": "ashby", "slug": "supabase"},
    {"name": "Cohere", "ats": "ashby", "slug": "cohere"},
    {"name": "1Password", "ats": "ashby", "slug": "1password"},
    {"name": "Replit", "ats": "ashby", "slug": "replit"},
    {"name": "Retool", "ats": "ashby", "slug": "retool"},
    {"name": "Mercury", "ats": "ashby", "slug": "mercury"},
    {"name": "Modal", "ats": "ashby", "slug": "modal"},
    {"name": "ClickHouse", "ats": "ashby", "slug": "clickhouse"},
    {"name": "Vanta", "ats": "ashby", "slug": "vanta"},
    {"name": "Harvey", "ats": "ashby", "slug": "harvey"},
    {"name": "ElevenLabs", "ats": "ashby", "slug": "elevenlabs"},

    # ----- Accounting & finance firms -----
    # EY runs SAP SuccessFactors (one global site); these two list pages are filtered to Canada / US.
    {"name": "EY", "ats": "successfactors", "slug": "https://careers.ey.com/ey/search/?q=&locationsearch=Canada"},
    {"name": "EY", "ats": "successfactors", "slug": "https://careers.ey.com/ey/search/?q=&locationsearch=United+States"},
    {"name": "Baker Tilly", "ats": "workday", "slug": "https://bakertilly.wd5.myworkdayjobs.com/en-US/BTCareers"},
    {"name": "Raymond Chabot Grant Thornton", "ats": "workday", "slug": "https://rcgt.wd3.myworkdayjobs.com/en-US/External"},

    # ----- Startups / unicorns (slugs are from memory: check_companies.py flags any that are wrong) -----
    {"name": "Rippling", "ats": "ashby", "slug": "rippling"},
    {"name": "Perplexity", "ats": "ashby", "slug": "perplexity-ai"},
    {"name": "Cursor (Anysphere)", "ats": "ashby", "slug": "anysphere"},
    {"name": "Sierra", "ats": "ashby", "slug": "sierra"},
    {"name": "Decagon", "ats": "ashby", "slug": "decagon"},
    {"name": "Glean", "ats": "greenhouse", "slug": "gleanwork"},
    {"name": "Block", "ats": "greenhouse", "slug": "block"},
    {"name": "Marqeta", "ats": "greenhouse", "slug": "marqeta"},
    {"name": "Adyen", "ats": "greenhouse", "slug": "adyen"},
    {"name": "Upstart", "ats": "greenhouse", "slug": "upstart"},
    {"name": "Navan", "ats": "greenhouse", "slug": "navan"},
    {"name": "Ada", "ats": "greenhouse", "slug": "ada18"},
    {"name": "Rivian", "ats": "greenhouse", "slug": "rivian"},
    {"name": "Anduril", "ats": "greenhouse", "slug": "anduril"},
    {"name": "SpaceX", "ats": "greenhouse", "slug": "spacex"},
    {"name": "Waymo", "ats": "greenhouse", "slug": "waymo"},
    {"name": "Epic Games", "ats": "greenhouse", "slug": "epicgames"},
    {"name": "Wiz", "ats": "greenhouse", "slug": "wizinc"},
    {"name": "Grafana Labs", "ats": "greenhouse", "slug": "grafanalabs"},
    {"name": "Canva", "ats": "greenhouse", "slug": "canva"},
    {"name": "Miro", "ats": "greenhouse", "slug": "miro"},
    {"name": "Monzo", "ats": "greenhouse", "slug": "monzo"},
    {"name": "Wise", "ats": "greenhouse", "slug": "wise"},
    {"name": "Checkout.com", "ats": "greenhouse", "slug": "checkoutcom"},
    {"name": "Zip", "ats": "ashby", "slug": "zip"},
    {"name": "Lovable", "ats": "ashby", "slug": "lovable"},
    {"name": "Ironclad", "ats": "ashby", "slug": "ironclad"},
    {"name": "Hightouch", "ats": "ashby", "slug": "hightouch"},
    {"name": "Statsig", "ats": "ashby", "slug": "statsig"},

    # ----- Amazon (FAANG) - amazon.jobs, US + Canada; the slug is the search phrase -----
    {"name": "Amazon", "ats": "amazon", "slug": "software development engineer"},
    {"name": "Amazon", "ats": "amazon", "slug": "new grad software engineer"},
    {"name": "Amazon", "ats": "amazon", "slug": "data engineer"},
    {"name": "Amazon", "ats": "amazon", "slug": "business analyst"},

    # ----- Canadian banks -----
    # Scotiabank runs its own SAP SuccessFactors site: use list pages from jobs.scotiabank.com.
    {"name": "Scotiabank", "ats": "successfactors", "slug": "https://jobs.scotiabank.com/go/Student-&-New-Grad-Jobs/2298417/"},
    {"name": "Scotiabank", "ats": "successfactors", "slug": "https://jobs.scotiabank.com/go/IT-&-Digital-Banking-Jobs/2298017/"},
    # RBC runs a Phenom site (unofficial, untested from here - see debug_source.py)
    {"name": "RBC", "ats": "phenom", "slug": "https://jobs.rbc.com/ca/en/search-results"},

    # ----- Workday career sites (any field; entry-level filter applies) -----
    {"name": "NVIDIA", "ats": "workday", "slug": "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"},
    {"name": "Salesforce", "ats": "workday", "slug": "https://salesforce.wd12.myworkdayjobs.com/en-US/External_Career_Site"},
    {"name": "Adobe", "ats": "workday", "slug": "https://adobe.wd5.myworkdayjobs.com/en-US/external_experienced"},
    {"name": "Workday", "ats": "workday", "slug": "https://workday.wd5.myworkdayjobs.com/en-US/Workday"},
    {"name": "Nike", "ats": "workday", "slug": "https://nike.wd1.myworkdayjobs.com/en-US/nke"},
    {"name": "Accenture", "ats": "workday", "slug": "https://accenture.wd103.myworkdayjobs.com/en-US/AccentureCareers"},
    {"name": "Intel", "ats": "workday", "slug": "https://intel.wd1.myworkdayjobs.com/en-US/External"},
    {"name": "Dell", "ats": "workday", "slug": "https://dell.wd1.myworkdayjobs.com/en-US/External"},
    {"name": "HP", "ats": "workday", "slug": "https://hp.wd5.myworkdayjobs.com/en-US/ExternalCareerSite"},
    {"name": "AMD", "ats": "workday", "slug": "https://amd.wd1.myworkdayjobs.com/en-US/External"},
    {"name": "Qualcomm", "ats": "workday", "slug": "https://qualcomm.wd5.myworkdayjobs.com/en-US/External"},
    {"name": "Broadcom", "ats": "workday", "slug": "https://broadcom.wd1.myworkdayjobs.com/en-US/External_Career"},
    {"name": "Autodesk", "ats": "workday", "slug": "https://autodesk.wd1.myworkdayjobs.com/en-US/Ext"},
    {"name": "Snowflake", "ats": "workday", "slug": "https://snowflake.wd1.myworkdayjobs.com/en-US/Snowflake"},
    {"name": "Zoom", "ats": "workday", "slug": "https://zoom.wd5.myworkdayjobs.com/en-US/Zoom"},
    {"name": "Red Hat", "ats": "workday", "slug": "https://redhat.wd5.myworkdayjobs.com/en-US/Jobs"},
    {"name": "PayPal", "ats": "workday", "slug": "https://paypal.wd1.myworkdayjobs.com/en-US/jobs"},
    {"name": "Mastercard", "ats": "workday", "slug": "https://mastercard.wd1.myworkdayjobs.com/en-US/CorporateCareers"},
    {"name": "Capital One", "ats": "workday", "slug": "https://capitalone.wd12.myworkdayjobs.com/en-US/Capital_One"},
    {"name": "Walmart", "ats": "workday", "slug": "https://walmart.wd5.myworkdayjobs.com/en-US/WalmartExternal"},
    {"name": "Target", "ats": "workday", "slug": "https://target.wd5.myworkdayjobs.com/en-US/targetcareers"},
    {"name": "Citi", "ats": "workday", "slug": "https://citi.wd5.myworkdayjobs.com/en-US/2"},
    {"name": "Wells Fargo", "ats": "workday", "slug": "https://wellsfargo.wd1.myworkdayjobs.com/en-US/WellsFargoJobs"},
    {"name": "BMO", "ats": "workday", "slug": "https://bmo.wd3.myworkdayjobs.com/en-US/External"},
    {"name": "CIBC", "ats": "workday", "slug": "https://cibc.wd3.myworkdayjobs.com/en-US/search"},
    {"name": "Manulife", "ats": "workday", "slug": "https://manulife.wd3.myworkdayjobs.com/en-US/MFCJH_Jobs"},
    {"name": "Sun Life", "ats": "workday", "slug": "https://sunlife.wd3.myworkdayjobs.com/en-US/Experienced-Jobs"},
    {"name": "Rogers", "ats": "workday", "slug": "https://rogers.wd3.myworkdayjobs.com/en-US/Rogers"},
]

# Extra companies found by discover.py are merged in automatically
_discovered = Path(__file__).parent / "discovered_companies.json"
if _discovered.exists():
    try:
        _known = {(c["ats"], c["slug"]) for c in COMPANIES}
        _names = {c["name"].lower() for c in COMPANIES}
        for _c in json.loads(_discovered.read_text(encoding="utf-8")):
            if (_c.get("ats"), _c.get("slug")) not in _known and _c.get("name", "").lower() not in _names:
                COMPANIES.append(_c)
    except (ValueError, KeyError, TypeError):
        pass

# ---------- Simplify (new-grad list) ----------
# The key "internships" is special: everything in that list is treated as an internship.
SIMPLIFY_REPOS = {
    "new-grad": "SimplifyJobs/New-Grad-Positions",
    "internships": "SimplifyJobs/Summer2027-Internships",   # next summer's list; change the year when it rolls over
}
SIMPLIFY_INTERN_KEYS = {"internships"}
SIMPLIFY_TECH_CATEGORIES = {"Software", "Software Engineering", "AI/ML/Data", "Data Science, AI & Machine Learning"}
SIMPLIFY_FINANCE_CATEGORIES = {"Quant"}
SIMPLIFY_POST_OTHER = True      # non-tech, non-finance new-grad categories (Hardware, Product) -> "other" channel

# ---------- Title keywords for SWE roles ----------
TITLE_INCLUDED_KEYWORDS = [
    "software engineer", "software developer", "backend engineer", "back-end engineer",
    "frontend engineer", "front-end engineer", "full stack engineer", "fullstack engineer",
    "full-stack engineer", "platform engineer", "infrastructure engineer", "systems engineer",
    "site reliability", "mobile engineer", "ios engineer", "android engineer", "devops engineer",
    "product engineer", "founding engineer", "member of technical staff",
    "software development engineer", "sde",
]
TITLE_EXCLUDED_KEYWORDS = [
    "sales engineer", "solutions engineer", "support engineer", "field engineer",
    "hardware engineer", "mechanical engineer", "electrical engineer", "civil engineer",
]