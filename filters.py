import re

import config

_INTERN_RE = re.compile(r"\b(intern(ship)?s?|co-?ops?)\b")

# ---------------------------------------------------------------- seniority
# Titles matching any of these are treated as senior and dropped.
SENIOR_PATTERNS = [
    r"\bsenior\b", r"\bsr\b", r"\bstaff\b", r"\bprincipal\b", r"\blead\b",
    r"\bmanager\b", r"\bmgr\b", r"\bdirector\b", r"\bhead of\b", r"\bvp\b",
    r"\bvice president\b", r"\bchief\b", r"\barchitect\b", r"\bdistinguished\b",
    r"\bfellow\b", r"\bexpert\b",
    r"\b[3-9]\+?\s*(years|yrs)\b",          # "5+ years"
]
# Mid-level markers such as "Software Engineer II", "Software Engineer 3", "SDE 2".
MID_LEVEL_PATTERNS = [r"\b(ii|iii|iv|v|vi)\b", r"\b[2-9]\b"]
ALLOW_MID_LEVEL = False   # set True to keep "II"/"2" style roles


# Entry-level experience ranges ("0-2 years", "1-3 yrs") shouldn't trip the senior/mid-level checks.
_ENTRY_RANGE_RE = re.compile(r"\b[01]\s*(?:-|to)\s*[1-3]\+?\s*(?:years?|yrs?)\b")


def is_entry_level(title: str) -> bool:
    """True unless the title looks senior or mid-level."""
    t = title.lower().replace("member of technical staff", "mts")  # "staff" there isn't a level
    t = _ENTRY_RANGE_RE.sub(" ", t)
    if any(re.search(p, t) for p in SENIOR_PATTERNS):
        return False
    if not ALLOW_MID_LEVEL and any(re.search(p, t) for p in MID_LEVEL_PATTERNS):
        return False
    return True


# ---------------------------------------------------------------- software roles
def _matches(keywords, text):
    return any(re.search(rf"\b{re.escape(k)}", text) for k in keywords)


def software_eng_role(title: str) -> bool:
    t = title.lower()
    if _INTERN_RE.search(t):
        return False
    if _matches(config.TITLE_EXCLUDED_KEYWORDS, t):
        return False
    if not _matches(config.TITLE_INCLUDED_KEYWORDS, t):
        return False
    return is_entry_level(title)


# ---------------------------------------------------------------- entry-level roles in ANY field
# A title must contain one of these signals to count as entry-level/junior.
ENTRY_SIGNALS = [
    r"\bentry[\s-]?level\b", r"\bjunior\b", r"\bjr\b",
    r"\bgrad(uate)?s?\b",                                   # new grad, college grad, graduate
    r"\bearly[\s-]?(career|talent)\b", r"\bearly in career\b", r"\bcampus\b",
    r"\b(university|college)\s+(hire|grad|graduate|recruit|program)",
    r"\bassociate\b", r"\btrainee\b", r"\bapprentice(ship)?\b", r"\brotational\b",
    r"\bdevelopment program\b",
    r"\b(analyst|engineer|specialist|technician|developer|scientist|coordinator|representative|consultant|accountant|auditor)\s+(i|1)\b",
    r"\b(0|1)\s*(-|to)\s*[1-3]\+?\s*(years|yrs)\b",         # "0-2 years"
]
# Obvious frontline/hourly roles you probably don't want from big retail/food employers.
FRONTLINE_PATTERNS = [
    r"\b(cashier|barista|cook|driver|warehouse|stocker|janitor|custodian|housekeeper|dishwasher|"
    r"forklift|packer|picker)\b",
    r"\b(crew|team) member\b", r"\b(store|sales|retail|customer service) associate\b",
    r"\bshift (lead|supervisor)\b",
]
# If a career SITE's name contains one of these, every (non-senior) job on it counts as entry-level.
EARLY_CAREER_SITE_HINTS = (
    "campus", "university", "college", "graduate", "student", "earlycareer", "early_career",
    "early-career", "earlytalent", "early_talent", "newgrad", "new_grad", "entrylevel",
    "entry_level", "junior", "apprentice",
)


def is_early_career_site(site_name: str) -> bool:
    s = (site_name or "").lower()
    return any(h in s for h in EARLY_CAREER_SITE_HINTS)


def is_entry_level_posting(title: str, early_career_site: bool = False) -> bool:
    """Entry-level/junior role in any field. Never internships; never senior or mid-level."""
    t = title.lower()
    if _INTERN_RE.search(t):
        return False
    if not is_entry_level(title):
        return False
    if any(re.search(p, t) for p in FRONTLINE_PATTERNS):
        return False
    if early_career_site:
        return True
    return any(re.search(p, t) for p in ENTRY_SIGNALS)

# ---------------------------------------------------------------- SWE / developer / analyst roles
# On top of config.TITLE_INCLUDED_KEYWORDS (software engineer, backend engineer, ...), these count too.
EXTRA_TECH_PATTERNS = [
    r"\bdeveloper\b", r"\bprogrammer\b", r"\bswe\b", r"\bsde\b", r"\banalyst\b",
    r"\bdata engineer", r"\bmachine learning engineer", r"\bml engineer", r"\bai engineer",
    r"\bcloud engineer", r"\bdevops", r"\bsoftware (test|quality|development|dev)\b",
]


def is_tech_role(title: str) -> bool:
    """Entry-level SWE / developer / analyst role (never internships, never senior or mid-level)."""
    t = title.lower()
    if _INTERN_RE.search(t):
        return False
    if _matches(config.TITLE_EXCLUDED_KEYWORDS, t):
        return False
    if not (_matches(config.TITLE_INCLUDED_KEYWORDS, t) or any(re.search(p, t) for p in EXTRA_TECH_PATTERNS)):
        return False
    return is_entry_level(title)