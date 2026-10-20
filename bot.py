import os
import logging
from datetime import datetime, timedelta, timezone

import aiohttp
import discord
from discord.ext import tasks, commands
from dotenv import load_dotenv

import config
import filters
import storage
from sources import greenhouse, lever, ashby, simplify, workday

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))
POLL_MINUTES = float(os.getenv("POLL_INTERVAL_MINUTES", "10"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("jobbot")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# The one channel every job gets posted to (set in on_ready)
jobs_channel: discord.TextChannel | None = None

FETCHERS = {
    "greenhouse": greenhouse.fetch_jobs,
    "lever": lever.fetch_jobs,
    "ashby": ashby.fetch_jobs,
    "workday": workday.fetch_jobs,
}


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
    global jobs_channel
    log.info("Logged in as %s", bot.user)
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        log.error("Could not find guild %s - check DISCORD_GUILD_ID and that the bot is invited.", GUILD_ID)
        return

    category = await get_or_create_category(guild, config.JOBS_CATEGORY_NAME)
    jobs_channel = await get_or_create_channel(guild, category, config.JOBS_CHANNEL_NAME)

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


@tasks.loop(minutes=10)  # actual interval is set from .env in on_ready
async def poll_jobs():
    if jobs_channel is None:
        return

    async with aiohttp.ClientSession() as session:
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

            jobs = [j for j in jobs if filters.software_eng_role(j["title"])]

            source_key = f"company:{company['name']}"
            new_ids = storage.filter_new(source_key, [j["id"] for j in jobs], seed=True)
            for job in jobs:
                if job["id"] in new_ids:
                    await jobs_channel.send(
                        embed=make_embed(
                            job["title"], job["url"], job["location"],
                            company=company["name"], source=company["ats"].title(),
                        )
                    )

        # ---------- Simplify (new-grad only, software, recent) ----------
        cutoff = datetime.now(timezone.utc) - timedelta(days=config.MAX_POSTING_AGE_DAYS)
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

            source_key = f"simplify:{key}"
            new_ids = storage.filter_new(source_key, [j["id"] for j in jobs])
            for job in jobs:
                if job["id"] in new_ids:
                    await jobs_channel.send(
                        embed=make_embed(
                            job["title"], job["url"], job["location"],
                            company=job.get("company"), source="Simplify",
                        )
                    )


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("DISCORD_BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")
    if not GUILD_ID:
        raise SystemExit("DISCORD_GUILD_ID is not set. Copy .env.example to .env and fill it in.")
    bot.run(TOKEN)