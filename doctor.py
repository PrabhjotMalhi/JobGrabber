"""Run `python doctor.py` before starting the bot: checks packages, .env and that every module loads."""
import importlib
import os
import sys

REQUIRED = {"discord": "discord.py", "aiohttp": "aiohttp", "dotenv": "python-dotenv"}
MODULES = ["config", "filters", "locations", "storage", "bot",
           "sources.greenhouse", "sources.lever", "sources.ashby", "sources.workday",
           "sources.successfactors", "sources.phenom", "sources.amazon", "sources.simplify"]


def main() -> int:
    bad = 0
    for mod, pkg in REQUIRED.items():
        try:
            importlib.import_module(mod)
            print(f"ok    {pkg}")
        except ImportError:
            print(f"FAIL  {pkg} is not installed -> pip install {pkg}")
            bad += 1
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    for name in MODULES:
        try:
            importlib.import_module(name)
            print(f"ok    {name}")
        except Exception as e:
            print(f"FAIL  {name}: {type(e).__name__}: {e}")
            bad += 1
    try:
        import config
        import filters
        import locations
        for attr in ("COMPANIES", "SIMPLIFY_REPOS", "MAX_POSTING_AGE_DAYS", "TECH_CATEGORY_NAME",
                     "OTHER_CATEGORY_NAME", "TECH_CANADA_CHANNEL", "TECH_US_CHANNEL", "OTHER_CHANNEL",
                     "INTERN_TECH_CATEGORY_NAME", "INTERN_TECH_CANADA_CHANNEL", "INTERN_TECH_US_CHANNEL",
                     "INTERN_FIN_CATEGORY_NAME", "INTERN_FIN_CANADA_CHANNEL", "INTERN_FIN_US_CHANNEL",
                     "FIN_CATEGORY_NAME", "FIN_CANADA_CHANNEL", "FIN_US_CHANNEL",
                     "SIMPLIFY_INTERN_KEYS", "SIMPLIFY_FINANCE_CATEGORIES", "SIMPLIFY_TECH_CATEGORIES"):
            if not hasattr(config, attr):
                print(f"FAIL  config.py is missing {attr}")
                bad += 1
        for fn in ("is_tech_role", "is_entry_level_posting", "is_entry_level", "is_intern_title", "classify_role"):
            if not hasattr(filters, fn):
                print(f"FAIL  filters.py is missing {fn}")
                bad += 1
        if not hasattr(locations, "classify_job"):
            print("FAIL  locations.py is missing classify_job")
            bad += 1
    except Exception:
        pass
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    for var in ("DISCORD_BOT_TOKEN", "DISCORD_GUILD_ID"):
        if os.getenv(var):
            print(f"ok    {var} is set")
        else:
            print(f"FAIL  {var} is not set in .env")
            bad += 1
    print("\nAll good." if not bad else f"\n{bad} problem(s) found - fix the FAIL lines above.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())