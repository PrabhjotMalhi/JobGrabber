import os
import logging
from datetime import datetime, timedelta, timezone

import aiohttp
import discord
from discord.ext import tasks, commands
from dotenv import load_dotenv
import filters

import config
import storage
from sources import greenhouse, lever, simplify

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))
POLL_MINUTES = float(os.getenv("POLL_INTERVAL_MINUTES", "10"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("jobbot")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

channels: dict[str, discord.TextChannel] = {}


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
        log.error("Could not find guild %s — check DISCORD_GUILD_ID and that the bot is invited.", GUILD_ID)
        return

    company_category = await get_or_create_category(guild, config.CATEGORY_COMPANIES)
    for company in config.COMPANIES:
        ch = await get_or_create_channel(guild, company_category, company["name"])
        channels[f"company:{company['name']}"] = ch

    simplify_category = await get_or_create_category(guild, config.CATEGORY_SIMPLIFY)
    for key in config.SIMPLIFY_REPOS:
        ch = await get_or_create_channel(guild, simplify_category, key)
        channels[f"simplify:{key}"] = ch

    other_category = await get_or_create_category(guild, config.CATEGORY_OTHER)
    for key in config.PLACEHOLDER_CHANNELS:
        ch = await get_or_create_channel(guild, other_category, key)
        channels[f"placeholder:{key}"] = ch
        await maybe_post_placeholder_notice(ch, key)

    poll_jobs.change_interval(minutes=POLL_MINUTES)
    if not poll_jobs.is_running():
        poll_jobs.start()


async def maybe_post_placeholder_notice(channel, key):
    history = [msg async for msg in channel.history(limit=1)]
    if history:
        return
    text = (
        f"ℹ️ **{key.title()} isn't connected to a live feed yet.**\n"
        f"{key.title()} doesn't offer a free public jobs-search API, so this channel "
        "is a placeholder. See the README for legitimate options you can plug in here."
    )
    await channel.send(text)


def make_embed(title, url, location, company=None):
    embed = discord.Embed(title=title, url=url, color=discord.Color.blurple())
    if company:
        embed.add_field(name="Company", value=company, inline=True)
    embed.add_field(name="Location", value=location or "Unknown", inline=True)
    return embed


@tasks.loop(minutes=10)
async def poll_jobs():
    async with aiohttp.ClientSession() as session:
        for company in config.COMPANIES:
            try:
                if company["ats"] == "greenhouse":
                    jobs = await greenhouse.fetch_jobs(session, company["slug"])
                    jobs = [j for j in jobs if filters.software_eng_role(j["title"])]
                elif company["ats"] == "lever":
                    jobs = await lever.fetch_jobs(session, company["slug"])
                    jobs = [j for j in jobs if filters.software_eng_role(j["title"])]
                else:
                    continue
            except Exception:
                log.exception("Failed to fetch jobs for %s", company["name"])
                continue

            source_key = f"company:{company['name']}"
            new_ids = storage.filter_new(source_key, [j["id"] for j in jobs])
            channel = channels.get(source_key)
            if not channel:
                continue
            for job in jobs:
                if job["id"] in new_ids:
                    await channel.send(embed=make_embed(job["title"], job["url"], job["location"]))

        cutoff = datetime.now(timezone.utc) - timedelta(days=config.MAX_POSTING_AGE_DAYS)
        for key, repo in config.SIMPLIFY_REPOS.items():
            try:
                jobs = await simplify.fetch_jobs(session, repo)
                jobs = [j for j in jobs if filters.software_eng_role(j["title"])]
            except Exception:
                log.exception("Failed to fetch Simplify jobs for %s", repo)
                continue
            
            jobs = [
                j for j in jobs
                if j.get("category") in config.SIMPLIFY_CATEGORIES
                and j.get("date_posted")
                and datetime.fromtimestamp(j["date_posted"], tz=timezone.utc) >= cutoff
            ]

            source_key = f"simplify:{key}"
            new_ids = storage.filter_new(source_key, [j["id"] for j in jobs])
            channel = channels.get(source_key)
            if not channel:
                continue
            for job in jobs:
                if job["id"] in new_ids:
                    await channel.send(
                        embed=make_embed(job["title"], job["url"], job["location"], job.get("company"))
                    )


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("DISCORD_BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")
    if not GUILD_ID:
        raise SystemExit("DISCORD_GUILD_ID is not set. Copy .env.example to .env and fill it in.")
    bot.run(TOKEN)