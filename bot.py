import os
import ssl
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import aiohttp
import discord
from discord.ext import tasks, commands
from dotenv import load_dotenv

import config
import filters
import locations
import storage
from sources import greenhouse, lever, ashby, workday, successfactors, phenom, amazon, simplify

try:
    import truststore   # pip install truststore: uses the Windows certificate store (fixes SSL errors)
except ImportError:
    truststore = None

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))
POLL_MINUTES = float(os.getenv("POLL_INTERVAL_MINUTES", "10"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("jobbot")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Filled in on_ready: "tech_ca", "tech_us", "other"
channels: dict[str, discord.TextChannel] = {}

FETCHERS = {
    "greenhouse": greenhouse.fetch_jobs,
    "lever": lever.fetch_jobs,
    "ashby": ashby.fetch_jobs,
    "workday": workday.fetch_jobs,
    "successfactors": successfactors.fetch_jobs,
    "phenom": phenom.fetch_jobs,
    "amazon": amazon.fetch_jobs,
}

# Big employers post every kind of job, so for these the bot also looks for entry-level
# roles in any field (those go to the "other" channel). The rest only post tech roles.
ANY_FIELD_ATS = {"workday", "successfactors", "phenom"}

SOURCE_LABELS = {"ca": "🇨🇦", "us": "🇺🇸"}


async def get_or_create_category(guild, name):
    category = discord.utils.get(guild.categories, name=name)
    if category is None:
        category = await guild.create_category(name)
        log.info("Created category: %s", name)
    return category


async def get_or_create_channel(guild, category, name):
    safe_name = name.lower().replace(" ", "-")
    channel = discord.utils.get(category.text_channels, name=safe_name)
    if channel is None:
        channel = await guild.create_text_channel(safe_name, category=category)
        log.info("Created channel: #%s", safe_name)
    return channel


@bot.event
async def on_ready():
    log.info("Logged in as %s", bot.user)
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        log.error("Could not find guild %s - check DISCORD_GUILD_ID and that the bot is invited.", GUILD_ID)
        return

    tech_cat = await get_or_create_category(guild, config.TECH_CATEGORY_NAME)
    other_cat = await get_or_create_category(guild, config.OTHER_CATEGORY_NAME)
    channels["tech_ca"] = await get_or_create_channel(guild, tech_cat, config.TECH_CANADA_CHANNEL)
    channels["tech_us"] = await get_or_create_channel(guild, tech_cat, config.TECH_US_CHANNEL)
    channels["other"] = await get_or_create_channel(guild, other_cat, config.OTHER_CHANNEL)

    it_cat = await get_or_create_category(guild, config.INTERN_TECH_CATEGORY_NAME)
    channels["int_tech_ca"] = await get_or_create_channel(guild, it_cat, config.INTERN_TECH_CANADA_CHANNEL)
    channels["int_tech_us"] = await get_or_create_channel(guild, it_cat, config.INTERN_TECH_US_CHANNEL)
    if_cat = await get_or_create_category(guild, config.INTERN_FIN_CATEGORY_NAME)
    channels["int_fin_ca"] = await get_or_create_channel(guild, if_cat, config.INTERN_FIN_CANADA_CHANNEL)
    channels["int_fin_us"] = await get_or_create_channel(guild, if_cat, config.INTERN_FIN_US_CHANNEL)
    fin_cat = await get_or_create_category(guild, config.FIN_CATEGORY_NAME)
    channels["fin_ca"] = await get_or_create_channel(guild, fin_cat, config.FIN_CANADA_CHANNEL)
    channels["fin_us"] = await get_or_create_channel(guild, fin_cat, config.FIN_US_CHANNEL)

    poll_jobs.change_interval(minutes=POLL_MINUTES)
    if not poll_jobs.is_running():
        poll_jobs.start()


def make_embed(title, url, location, company=None, source=None, color=None):
    embed = discord.Embed(title=title, url=url, color=color or discord.Color.blurple())
    if company:
        embed.add_field(name="Company", value=company, inline=True)
    embed.add_field(name="Location", value=(location or "Unknown")[:1000], inline=True)
    if source:
        embed.set_footer(text=source)
    return embed


# kind -> (Canada channel key, US channel key)
KIND_CHANNELS = {
    "tech": ("tech_ca", "tech_us"),
    "tech_intern": ("int_tech_ca", "int_tech_us"),
    "fin_intern": ("int_fin_ca", "int_fin_us"),
    "fin_ft": ("fin_ca", "fin_us"),
}
KIND_COLORS = {
    "tech": discord.Color.green(), "tech_intern": discord.Color.teal(),
    "fin_intern": discord.Color.gold(), "fin_ft": discord.Color.dark_gold(),
    "other": discord.Color.orange(),
}
# Kinds that existed before internships/finance were added keep their old dedup key, so an
# upgrade doesn't re-announce them. The newer kinds get their own key (and their own silent
# first pass for sources without dates).
LEGACY_KINDS = {"tech", "other"}


def role_kind(title: str, ats: str, early_career_site: bool = False, force_intern: bool = False):
    """tech | tech_intern | fin_intern | fin_ft | other | None (skip). See filters.classify_role."""
    return filters.classify_role(title, any_field=ats in ANY_FIELD_ATS,
                                 early_career_site=early_career_site, force_intern=force_intern)


def target_channels(kind: str, countries) -> list[str]:
    """Which channel keys a role goes to. Non Canada/US locations return []."""
    countries = set(countries)
    if not countries & {"CA", "US"}:
        return []
    if kind == "other":
        return ["other"]
    ca, us = KIND_CHANNELS[kind]
    return ([ca] if "CA" in countries else []) + ([us] if "US" in countries else [])


async def post_job(keys, job, company, source, kind):
    color = KIND_COLORS.get(kind, discord.Color.blurple())
    for key in keys:
        channel = channels.get(key)
        if channel is None:
            continue
        await channel.send(
            embed=make_embed(job["title"], job["url"], locations.display_location(job),
                             company=company, source=source, color=color)
        )


def _site_name(company: dict) -> str:
    """Part of the careers URL that may say 'campus' / 'university' / 'new grad' etc."""
    if company["ats"] == "workday":
        try:
            return workday.parse_careers_url(company["slug"])[2]
        except ValueError:
            return ""
    if company["ats"] in ("successfactors", "phenom"):
        return urlparse(company["slug"]).path
    return ""


def _new_session():
    kwargs = {"headers": {"User-Agent": "Mozilla/5.0 (jobbot)"}}
    if truststore is not None:
        kwargs["connector"] = aiohttp.TCPConnector(ssl=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT))
    return aiohttp.ClientSession(**kwargs)


async def poll_companies(session, cutoff):
    # ---------- Company career pages ----------
    for company in config.COMPANIES:
        fetch = FETCHERS.get(company["ats"])
        if fetch is None:
            continue
        try:
            jobs = await fetch(session, company["slug"])
        except Exception:
            log.exception("Failed to fetch jobs for %s", company["name"])
            continue

        n_read = len(jobs)
        early_site = filters.is_early_career_site(_site_name(company))

        # role type + location
        routed = []
        n_role = 0
        for j in jobs:
            kind = role_kind(j["title"], company["ats"], early_site)
            if kind is None:
                continue
            n_role += 1
            keys = target_channels(kind, locations.classify_job(j).countries)
            if keys:
                routed.append((j, kind, keys))
        n_loc = len(routed)

        # Sources that report a date: only the last MAX_POSTING_AGE_DAYS. Undated: silent first sight.
        has_dates = bool(jobs) and all(j.get("date_posted") for j in jobs)
        if has_dates:
            routed = [
                r for r in routed
                if datetime.fromtimestamp(r[0]["date_posted"], tz=timezone.utc) >= cutoff
            ]
        n_recent = len(routed)

        base_key = f"company:{company['name']}:{company['ats']}:{company['slug']}"
        posted = 0
        for suffix, legacy in (("", True), (":v2", False)):
            items = [r for r in routed if (r[1] in LEGACY_KINDS) == legacy]
            new_ids = set(storage.filter_new(base_key + suffix, [r[0]["id"] for r in items], seed=not has_dates))
            for job, kind, keys in items:
                if job["id"] in new_ids:
                    await post_job(keys, job, company["name"], company["ats"].title(), kind)
                    posted += 1

        log.info("%s (%s): read %d | role match %d | in Canada/US %d | recent %d | NEW %d",
                 company["name"], company["ats"], n_read, n_role, n_loc, n_recent, posted)


async def poll_simplify(session, cutoff):
    # ---------- Simplify lists (new-grad + internships) ----------
    for key, repo in config.SIMPLIFY_REPOS.items():
        try:
            jobs = await simplify.fetch_jobs(session, repo)
        except Exception:
            log.exception("Failed to fetch Simplify jobs for %s", repo)
            continue

        is_intern_list = key in config.SIMPLIFY_INTERN_KEYS
        routed = []
        for j in jobs:
            if not j.get("date_posted"):
                continue
            if datetime.fromtimestamp(j["date_posted"], tz=timezone.utc) < cutoff:
                continue
            cat = j.get("category")
            title_kind = role_kind(j["title"], "simplify", False, force_intern=is_intern_list)
            if is_intern_list or filters.is_intern_title(j["title"]):
                # internship: tech category -> tech internship, Quant -> finance internship
                if cat in config.SIMPLIFY_TECH_CATEGORIES:
                    kind = "fin_intern" if title_kind == "fin_intern" else "tech_intern"
                elif cat in config.SIMPLIFY_FINANCE_CATEGORIES or title_kind == "fin_intern":
                    kind = "fin_intern"
                else:
                    continue
            else:
                if not filters.is_entry_level(j["title"]):
                    continue
                if title_kind == "fin_ft" or cat in config.SIMPLIFY_FINANCE_CATEGORIES:
                    kind = "fin_ft"
                elif cat in config.SIMPLIFY_TECH_CATEGORIES:
                    kind = "tech"
                elif config.SIMPLIFY_POST_OTHER:
                    kind = "other"
                else:
                    continue
            keys = target_channels(kind, locations.classify_job(j).countries)
            if keys:
                routed.append((j, kind, keys))

        posted = 0
        for suffix, legacy in (("", True), (":v2", False)):
            items = [r for r in routed if (r[1] in LEGACY_KINDS) == legacy]
            new_ids = set(storage.filter_new(f"simplify:{key}{suffix}", [r[0]["id"] for r in items]))
            for job, kind, keys in items:
                if job["id"] in new_ids:
                    await post_job(keys, job, job.get("company"), "Simplify", kind)
                    posted += 1
        log.info("Simplify (%s): %d routed, NEW %d", key, len(routed), posted)


@tasks.loop(minutes=10)  # actual interval is set from .env in on_ready
async def poll_jobs():
    if not channels:
        return
    cutoff = datetime.now(timezone.utc) - timedelta(days=config.MAX_POSTING_AGE_DAYS)
    async with _new_session() as session:
        await poll_simplify(session, cutoff)     # Simplify first: one quick request
        await poll_companies(session, cutoff)    # then the slower company career pages


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("DISCORD_BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")
    if not GUILD_ID:
        raise SystemExit("DISCORD_GUILD_ID is not set. Copy .env.example to .env and fill it in.")
    bot.run(TOKEN)