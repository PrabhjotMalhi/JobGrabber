import re

import config

_INTERN_RE = re.compile(r"\b(intern(ship)?s?|co-?ops?)\b")

# ---------------------------------------------------------------- seniority
SENIOR_PATTERNS = [
    r"\bsenior\b", r"\bsr\b", r"\bstaff\b", r"\bprincipal\b", r"\blead\b",
    r"\bmanager\b", r"\bmgr\b", r"\bdirector\b", r"\bhead of\b", r"\bvp\b",
    r"\bvice president\b", r"\bchief\b", r"\barchitect\b", r"\bdistinguished\b",
    r"\bfellow\b", r"\bexpert\b",
    r"\b[3-9]\+?\s*(years|yrs)\b",
]
MID_LEVEL_PATTERNS = [r"\b(ii|iii|iv|v|vi)\b", r"\b[2-9]\b"]
ALLOW_MID_LEVEL = False   # set True to keep "II"/"2" style roles

_ENTRY_RANGE_RE = re.compile(r"\b[01]\s*(?:-|to)\s*[1-3]\+?\s*(?:years?|yrs?)\b")


def is_entry_level(title: str) -> bool:
    """True unless the title looks senior or mid-level."""
    t = title.lower().replace("member of technical staff", "mts")
    t = _ENTRY_RANGE_RE.sub(" ", t)
    if any(re.search(p, t) for p in SENIOR_PATTERNS):
        return False
    if not ALLOW_MID_LEVEL and any(re.search(p, t) for p in MID_LEVEL_PATTERNS):
        return False
    return True


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


# ---------------------------------------------------------------- SWE / developer / analyst roles
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


# ---------------------------------------------------------------- entry-level roles in ANY field
ENTRY_SIGNALS = [
    r"\bentry[\s-]?level\b", r"\bjunior\b", r"\bjr\b",
    r"\bgrad(uate)?s?\b",
    r"\bearly[\s-]?(career|talent)\b", r"\bearly in career\b", r"\bcampus\b",
    r"\b(university|college)\s+(hire|grad|graduate|recruit|program)",
    r"\bassociate\b", r"\btrainee\b", r"\bapprentice(ship)?\b", r"\brotational\b",
    r"\bdevelopment program\b",
    r"\b(analyst|engineer|specialist|technician|developer|scientist|coordinator|representative|consultant|accountant|auditor)\s+(i|1)\b",
    r"\b(0|1)\s*(-|to)\s*[1-3]\+?\s*(years|yrs)\b",
]
FRONTLINE_PATTERNS = [
    r"\b(cashier|barista|cook|driver|warehouse|stocker|janitor|custodian|housekeeper|dishwasher|"
    r"forklift|packer|picker)\b",
    r"\b(crew|team) member\b", r"\b(store|sales|retail|customer service) associate\b",
    r"\bshift (lead|supervisor)\b",
]
EARLY_CAREER_SITE_HINTS = (
    "campus", "university", "college", "graduate", "student", "earlycareer", "early_career",
    "early-career", "earlytalent", "early_talent", "newgrad", "new_grad", "entrylevel",
    "entry_level", "junior", "apprentice", "new-grad", "new grad",
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


def is_intern_title(title: str) -> bool:
    return bool(_INTERN_RE.search(title.lower()))


# ---------------------------------------------------------------- internships + finance/accounting
STRONG_TECH_PATTERNS = [
    r"\bsoftware\b", r"\bdeveloper\b", r"\bprogrammer\b", r"\bswe\b", r"\bsde\b",
    r"\bdata (engineer|scientist)", r"\bmachine learning\b", r"\bml engineer", r"\bai engineer",
    r"\bcloud engineer", r"\bdevops", r"\b(back|front)[\s-]?end\b", r"\bfull[\s-]?stack\b",
    r"\bsite reliability\b", r"\b(ios|android|mobile) engineer", r"\bplatform engineer",
    r"\binfrastructure engineer", r"\bmember of technical staff\b",
]
FINANCE_PATTERNS = [
    r"\bfinanc", r"\baccounting\b", r"\baccountant\b", r"\baccounts (payable|receivable)\b",
    r"\baudit", r"\btax\b", r"\btreasury\b", r"\bcontroller\b", r"\bfp\s?&\s?a\b", r"\bfp and a\b",
    r"\bactuar", r"\bunderwrit", r"\bcapital markets\b", r"\binvestment", r"\bbanking\b", r"\bbanker\b",
    r"\bequity research\b", r"\bcredit\b", r"\bwealth\b", r"\basset management\b", r"\bprivate equity\b",
    r"\bcorporate development\b", r"\bquantitative (analyst|research|finance|trad)", r"\bquant\b",
    r"\bpayroll\b", r"\bbookkeep", r"\bcpa\b", r"\bcfa\b", r"\bportfolio (analyst|manager|assistant)",
    r"\bmarkets (analyst|associate)\b", r"\btrading (analyst|associate|assistant)\b", r"\bfund (accounting|admin)",
    r"\bassurance\b", r"\bvaluations?\b",
]


_STAFF_ENTRY_RE = re.compile(r"\bstaff (accountant|auditor|associate|analyst)\b")


def _tech_title(t: str, allow_analyst: bool) -> bool:
    if _matches(config.TITLE_EXCLUDED_KEYWORDS, t):
        return False
    if _matches(config.TITLE_INCLUDED_KEYWORDS, t) or any(re.search(p, t) for p in STRONG_TECH_PATTERNS):
        return True
    return allow_analyst and bool(re.search(r"\banalyst\b", t))


def is_finance_title(title: str) -> bool:
    t = title.lower()
    return any(re.search(p, t) for p in FINANCE_PATTERNS)


def classify_role(title: str, any_field: bool = False, early_career_site: bool = False,
                  force_intern: bool = False):
    """Returns one of:
        'tech'         full-time entry-level SWE / developer / analyst
        'tech_intern'  internship / co-op in SWE / developer / analyst
        'fin_intern'   internship / co-op in finance / accounting (analyst roles included)
        'fin_ft'       full-time entry-level finance / accounting
        'other'        any other entry-level role (only when any_field=True)
        None           skip
    Order matters: software titles are tested first, so 'Software Engineer, Payments' stays tech, and
    finance is tested before the generic 'analyst' rule, so 'Financial Analyst' is finance, not tech.
    """
    t = title.lower()
    if force_intern or _INTERN_RE.search(t):
        if _tech_title(t, allow_analyst=False):
            return "tech_intern"
        if is_finance_title(title):
            return "fin_intern"
        if _tech_title(t, allow_analyst=True):
            return "tech_intern"
        return None

    if _tech_title(t, allow_analyst=False):
        return "tech" if is_entry_level(title) else None
    if is_finance_title(title):
        # In accounting "Staff Accountant / Staff Auditor" is a first-job title (unlike "Staff Engineer")
        staff = _STAFF_ENTRY_RE.search(t)
        if staff:
            plain = _STAFF_ENTRY_RE.sub(lambda m: m.group(1), t)
            return "fin_ft" if is_entry_level(plain) and not any(re.search(p, t) for p in FRONTLINE_PATTERNS) else None
        return "fin_ft" if is_entry_level_posting(title, early_career_site) else None
    if _tech_title(t, allow_analyst=True):
        return "tech" if is_entry_level(title) else None
    if any_field and is_entry_level_posting(title, early_career_site):
        return "other"
    return None