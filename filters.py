import config

def software_eng_role(title: str) -> bool:
    t = title.lower()
    if any(bad in t for bad in config.TITLE_EXCLUDED_KEYWORDS):
        return False
    return any(good in t for good in config.TITLE_INCLUDED_KEYWORDS)