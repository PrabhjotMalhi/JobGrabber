COMPANIES = [
    {"name": "Stripe", "ats": "greenhouse", "slug": "stripe"},
    {"name": "Airbnb", "ats": "greenhouse", "slug": "airbnb"},
    {"name": "Netflix", "ats": "lever", "slug": "netflix"},
]

SIMPLIFY_REPOS = {
    "new-grad": "SimplifyJobs/New-Grad-Positions",
}

# only the categories that specifically say software engineering/ developer will be pingedby the bot
SIMPLIFY_CATEGORIES = {"Software", "Software Engineering", "Software Developer"}

MAX_POSTING_AGE_DAYS = 2

TITLE_INCLUDED_KEYWORDS = [
    "software engineer", "software developer", "backend engineer", "back-end engineer",
    "frontend engineer", "front-end engineer", "full stack engineer", "fullstack engineer",
    "full-stack engineer", "platform engineer", "infrastructure engineer", "systems engineer",
    "site reliability engineer", "sre", "mobile engineer", "ios engineer", "android engineer",
    "devops engineer", "swe", "solutions engineer", "support engineer", "data engineer"
]

TITLE_EXCLUDED_KEYWORDS = [
    "sales engineer", "field engineer", "hardware engineer", "mechanical engineer", "electrical engineer", "civil engineer",
]

CATEGORY_COMPANIES = "🏢 Company Careers"
CATEGORY_SIMPLIFY = "🔎 Simplify"
CATEGORY_OTHER = "📋 Other Sources"
PLACEHOLDER_CHANNELS = ["linkedin", "indeed"]