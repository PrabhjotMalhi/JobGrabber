# JobGrabber

JobGrabber is a Discord bot that watches company career pages and the [Simplify new-grad list](https://github.com/SimplifyJobs/New-Grad-Positions), filters for recent entry-level roles in Canada and the United States, and posts new opportunities to organized Discord channels.

## Features

- Monitors Greenhouse, Lever, Ashby, and Workday career sites
- Includes new-grad software roles from Simplify
- Filters out internships, senior roles, mid-level roles, and unrelated job titles
- Separates technical roles by country
- Supports entry-level non-technical roles from selected sources
- Creates the required Discord categories and channels automatically
- Stores seen posting IDs in SQLite so jobs are not posted twice
- Seeds undated sources on their first scan to avoid flooding a new server with old listings
- Handles Workday pagination and rate limits

## Discord layout

When the bot starts, it creates these categories and channels if they do not already exist:

- **💻 SWE-Dev-Analyst Roles**
  - `#tech-canada`
  - `#tech-united-states`
- **📋 Other Entry-Level Roles**
  - `#other-roles-canada-us`

The names can be overridden in `config.py`.

## Requirements

- Python 3.10 or newer
- A Discord server where you can invite and configure a bot
- Internet access to the supported job-board endpoints

## Installation

Clone the repository and enter the project directory:

```bash
git clone https://github.com/PrabhjotMalhi/JobGrabber.git
cd JobGrabber
```

Create and activate a virtual environment:

```bash
python -m venv .venv
```

On Windows:

```powershell
.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install aiohttp discord.py python-dotenv
```

## Discord bot setup

1. Open the [Discord Developer Portal](https://discord.com/developers/applications).
2. Create an application and add a bot.
3. Copy the bot token.
4. Invite the bot to your server.
5. Give it permission to view channels, manage channels, send messages, and embed links.
6. In Discord, enable Developer Mode, right-click your server, and copy its server ID.

Keep the bot token private. Never commit it to the repository.

## Environment variables

Create a `.env` file in the project root:

```dotenv
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_GUILD_ID=your_server_id
POLL_INTERVAL_MINUTES=10
```

- `DISCORD_BOT_TOKEN` is the token from the Discord Developer Portal.
- `DISCORD_GUILD_ID` is the ID of the server where jobs should be posted.
- `POLL_INTERVAL_MINUTES` is optional and defaults to `10`.

## Running the bot

```bash
python bot.py
```

On a successful startup, the bot logs into Discord, creates any missing categories and channels, and begins polling configured sources.

## Configuration

Most behavior is controlled in `config.py`.

### Add a Greenhouse, Lever, or Ashby company

Add an entry to `COMPANIES`:

```python
{"name": "Example", "ats": "greenhouse", "slug": "example"}
```

The slug is the company-specific part of its job-board URL:

- `boards.greenhouse.io/<slug>`
- `jobs.lever.co/<slug>`
- `jobs.ashbyhq.com/<slug>`

### Add a Workday company

Add the public careers-page URL to `WORKDAY_SITES`:

```python
WORKDAY_SITES = {
    "Example": "https://example.wd5.myworkdayjobs.com/ExampleCareers",
}
```

Workday does not provide a documented public jobs API. Its connector uses the unauthenticated endpoint used by public Workday career pages, so upstream changes may require maintenance.

### Discover career boards

To look for Greenhouse, Lever, or Ashby boards:

```bash
python discover.py "Company Name"
```

To look for Workday sites:

```bash
python discover_workday.py "Company Name"
```

Successful discoveries are merged into `discovered_companies.json` and loaded automatically.

### Change role filters

Edit these settings in `config.py` and `filters.py`:

- `TITLE_INCLUDED_KEYWORDS`
- `TITLE_EXCLUDED_KEYWORDS`
- `MAX_POSTING_AGE_DAYS`
- `SIMPLIFY_CATEGORIES`
- `ANY_FIELD_ATS`
- `ALLOW_MID_LEVEL`

Location matching is implemented in `locations.py`. Jobs with recognized Canadian or US locations are routed to the matching channels; jobs outside those countries or with unreadable locations are skipped.

## How duplicate protection works

JobGrabber records posting IDs in `seen_postings.db`.

- Ashby and Workday provide posting dates, so recent matching jobs can be announced immediately.
- Greenhouse and Lever do not reliably provide dates. On the first scan of one of these sources, existing jobs are recorded without being posted. Later scans announce only newly discovered jobs.
- Simplify listings are limited to active, recent entries.

To preserve duplicate history, keep `seen_postings.db` when moving or redeploying the bot.

## Useful checks

Check every configured company and print the number of available and matching jobs:

```bash
python check_companies.py
```

Run the basic Greenhouse fetch check:

```bash
python test_fetch.py
```

## Troubleshooting

### The bot cannot find the Discord server

Verify that `DISCORD_GUILD_ID` is correct and that the bot has been invited to that server.

### Channels are not created

Ensure the bot has the **Manage Channels** permission.

### No jobs appear after the first run

This can be expected for undated Greenhouse and Lever sources. Their initial scan seeds the duplicate database; only jobs found on later scans are posted. Also check the logs for location or role-filter exclusions.

### A company returns no jobs

The company may have changed ATS providers or board slugs. Run the relevant discovery script or update its entry in `config.py`.

### Workday reports HTTP 429

Workday is rate-limiting requests. The connector retries automatically and temporarily pauses the affected site after repeated failures.

## Project structure

```text
bot.py                    Discord bot and polling loop
config.py                 Sources, company lists, and filter settings
filters.py                Role and seniority filters
locations.py              Canada/US location classification
storage.py                SQLite duplicate tracking
sources/                  ATS and Simplify connectors
discover.py               Greenhouse/Lever/Ashby discovery
discover_workday.py       Workday site discovery
check_companies.py        Source and filter health check
discovered_companies.json Auto-discovered sources
seen_postings.db          Previously seen posting IDs
```

## Responsible use

JobGrabber reads public job-board endpoints. Use reasonable polling intervals, respect provider terms and rate limits, and review the supported sources periodically for upstream changes.
