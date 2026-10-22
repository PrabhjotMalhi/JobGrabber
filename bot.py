import os
import logging
from datetime import datetime, timedelta, timezone

import aiohttp
import discord
from discord.ext import tasks, commands
from dotenv import load_dotenv

import config
import filters
import locations
import storage
from sources import greenhouse, lever, ashby, workday, simplify

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))
POLL_MINUTES = float(os.getenv("POLL_INTERVAL_MINUTES", "10"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("jobbot")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------------------------------------------------------ Discord layout
# Names can be overridden in config.py (e.g. TECH_CANADA_CHANNEL = "swe-canada").
TECH_CATEGORY = getattr(config, "TECH_CATEGORY_NAME", "💻 SWE-Dev-Analyst Roles")
OTHER_CATEGORY = getattr(config, "OTHER_CATEGORY_NAME", "📋 Other Entry-Level Roles")
TECH_CA_CHANNEL = getattr(config, "TECH_CANADA_CHANNEL", "tech-canada")
TECH_US_CHANNEL = getattr(config, "TECH_US_CHANNEL", "tech-united-states")
OTHER_CHANNEL = getattr(config, "OTHER_CHANNEL", "other-roles-canada-us")

channels: dict[str, discord.TextChannel] = {}   # filled in on_ready: tech_ca, tech_us, other

FETCHERS = {
    "greenhouse": greenhouse.fetch_jobs,
    "lever": lever.fetch_jobs,
    "ashby": ashby.fetch_jobs,
    "workday": workday.fetch_jobs,
}

# ATS types where ANY entry-level/junior role is posted (not just SWE/developer/analyst roles).
# Override in config.py with e.g. ENTRY_LEVEL_ANY_FIELD_ATS = {"workday", "greenhouse"}.
ANY_FIELD_ATS = getattr(config, "ENTRY_LEVEL_ANY_FIELD_ATS", {"workday"})


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

    tech_cat = await get_or_create_category(guild, TECH_CATEGORY)
    other_cat = await get_or_create_category(guild, OTHER_CATEGORY)
    channels["tech_ca"] = await get_or_create_channel(guild, tech_cat, TECH_CA_CHANNEL)
    channels["tech_us"] = await get_or_create_channel(guild, tech_cat, TECH_US_CHANNEL)
    channels["other"] = await get_or_create_channel(guild, other_cat, OTHER_CHANNEL)

    poll_jobs.change_interval(minutes=POLL_MINUTES)
    if not poll_jobs.is_running():
        poll_jobs.start()


def make_embed(title, url, location, company=None, source=None):
    embed = discord.Embed(title=title, url=url, color=discord.Color.blurple())
    if company:
        embed.add_field(name="Company", value=company, inline=True)
    embed.add_field(name="Location", value=location or "Unknown", inline=True)
    if source:
        embed.set_footer(text=source)
    return embed


def _site_name(company):
    """The career-site name for Workday companies (e.g. 'Campus'), else ''."""
    if company["ats"] == "workday":
        try:
            return workday.parse_careers_url(company["slug"])[2]
        except ValueError:
            return ""
    return ""


def role_kind(company, title, early_site):
    """'tech' (SWE / developer / analyst), 'other' (any other entry-level role), or None to skip."""
    if filters.is_tech_role(title):
        return "tech"
    if company["ats"] in ANY_FIELD_ATS and filters.is_entry_level_posting(title, early_career_site=early_site):
        return "other"
    return None


def target_channels(kind, countries):
    """Tech roles go to the Canada and/or US channel; everything else to the one combined channel."""
    if not countries:
        return []
    if kind == "tech":
        out = []
        if "CA" in countries:
            out.append(channels.get("tech_ca"))
        if "US" in countries:
            out.append(channels.get("tech_us"))
        return [c for c in out if c is not None]
    return [c for c in [channels.get("other")] if c is not None]


async def post_job(job, kind, countries, company, source):
    embed = make_embed(job["title"], job["url"], locations.display_location(job), company=company, source=source)
    for channel in target_channels(kind, countries):
        await channel.send(embed=embed)


@tasks.loop(minutes=10)  # actual interval is set from .env in on_ready
async def poll_jobs():
    if not channels:
        return

    cutoff = datetime.now(timezone.utc) - timedelta(days=config.MAX_POSTING_AGE_DAYS)

    async with aiohttp.ClientSession() as session:
        # ---------- Company career pages ----------
        for company in config.COMPANIES:
            fetch = FETCHERS.get(company["ats"])
            if fetch is None:
                continue
            try:
                all_jobs = await fetch(session, company["slug"])
            except Exception:
                log.exception("Failed to fetch jobs for %s", company["name"])
                continue

            early_site = filters.is_early_career_site(_site_name(company))
            meta, n_role, n_foreign, unknown = {}, 0, 0, []
            for j in all_jobs:
                kind = role_kind(company, j["title"], early_site)
                if kind is None:
                    continue
                n_role += 1
                loc = locations.classify_job(j)
                if not loc.countries:
                    if loc.recognized:
                        n_foreign += 1
                    else:
                        unknown.append(j.get("location") or "(blank)")
                    continue
                meta[j["id"]] = (kind, loc.countries)
            jobs = [j for j in all_jobs if j["id"] in meta]
            n_in_na = len(jobs)

            # Sources that report a posting date (Ashby, Workday): post anything from the last
            # MAX_POSTING_AGE_DAYS right away. Sources without dates (Greenhouse, Lever):
            # stay silent the first time we see a company, then announce only new jobs.
            has_dates = bool(jobs) and all(j.get("date_posted") for j in jobs)
            if has_dates:
                jobs = [
                    j for j in jobs
                    if datetime.fromtimestamp(j["date_posted"], tz=timezone.utc) >= cutoff
                ]

            source_key = f"company:{company['name']}"
            new_ids = storage.filter_new(source_key, [j["id"] for j in jobs], seed=not has_dates)

            if all_jobs:
                log.info("%s [%s]: read %d | role match %d | in Canada/US %d | recent %d | NEW %d%s",
                         company["name"], company["ats"], len(all_jobs), n_role, n_in_na, len(jobs),
                         len(new_ids),
                         "" if has_dates or not n_in_na else " | undated source: a company's first check is silent")
                if n_role == 0:
                    log.info("    no title matched the role filters, e.g. dropped: %s",
                             [j["title"] for j in all_jobs[:3]])
                elif n_in_na == 0:
                    log.info("    %d role match(es) but none in Canada/US (%d outside, %d unreadable) %s",
                             n_role, n_foreign, len(unknown), unknown[:3])

            for job in jobs:
                if job["id"] in new_ids:
                    kind, countries = meta[job["id"]]
                    await post_job(job, kind, countries, company=company["name"],
                                   source=company["ats"].title())

        # ---------- Simplify (new-grad software roles) ----------
        for key, repo in config.SIMPLIFY_REPOS.items():
            try:
                jobs = await simplify.fetch_jobs(session, repo)
            except Exception:
                log.exception("Failed to fetch Simplify jobs for %s", repo)
                continue

            jobs = [
                j for j in jobs
                if j.get("category") in config.SIMPLIFY_CATEGORIES
                and filters.is_entry_level(j["title"])
                and j.get("date_posted")
                and datetime.fromtimestamp(j["date_posted"], tz=timezone.utc) >= cutoff
            ]
            meta = {}
            for j in jobs:
                loc = locations.classify_job(j)
                if loc.countries:
                    meta[j["id"]] = loc.countries
            jobs = [j for j in jobs if j["id"] in meta]

            source_key = f"simplify:{key}"
            new_ids = storage.filter_new(source_key, [j["id"] for j in jobs])
            for job in jobs:
                if job["id"] in new_ids:
                    await post_job(job, "tech", meta[job["id"]], company=job.get("company"), source="Simplify")


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("DISCORD_BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")
    if not GUILD_ID:
        raise SystemExit("DISCORD_GUILD_ID is not set. Copy .env.example to .env and fill it in.")
    bot.run(TOKEN)