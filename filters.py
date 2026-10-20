import re

import config

_INTERN_RE = re.compile(r"\bintern(ship)?s?\b")

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


def is_entry_level(title: str) -> bool:
    t = title.lower().replace("member of technical staff", "mts")  # "staff" there isn't a level
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