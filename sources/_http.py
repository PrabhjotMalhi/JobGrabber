"""Small shared helper: one request with polite handling of HTTP 429 (rate limiting)."""
import asyncio
import logging
import time

import aiohttp

log = logging.getLogger("jobbot")

RETRY_WAITS = (5, 15, 45)     # seconds before retry 1, 2, 3 (a Retry-After header overrides these)
MAX_RETRY_AFTER = 120
COOLDOWN_SECONDS = 15 * 60

_cooldown_until: dict[str, float] = {}


async def _sleep(seconds: float):
    await asyncio.sleep(seconds)


def cooling_down(key: str) -> bool:
    return time.time() < _cooldown_until.get(key, 0)


def _retry_after_seconds(value):
    try:
        return max(0, int(str(value).strip()))
    except (TypeError, ValueError):
        return None


async def request(session, method, url, key, *, as_json=False, **kwargs):
    """Returns parsed JSON (as_json=True) or text, or None on any failure."""
    for attempt in range(len(RETRY_WAITS) + 1):
        status, retry_after, data = None, None, None
        try:
            async with session.request(method, url, timeout=aiohttp.ClientTimeout(total=25), **kwargs) as resp:
                status = resp.status
                retry_after = resp.headers.get("Retry-After")
                if status == 200:
                    data = await (resp.json(content_type=None) if as_json else resp.text())
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
            log.warning("%s: request failed (%s)", key, e)
            return None

        if status == 200:
            return data
        if status == 429:
            if attempt >= len(RETRY_WAITS):
                _cooldown_until[key] = time.time() + COOLDOWN_SECONDS
                log.warning("%s keeps returning HTTP 429 (rate limited); resting it for %d minutes",
                            key, COOLDOWN_SECONDS // 60)
                return None
            wait = min(_retry_after_seconds(retry_after) or RETRY_WAITS[attempt], MAX_RETRY_AFTER)
            log.info("%s: HTTP 429, waiting %ds before retry %d", key, wait, attempt + 1)
            await _sleep(wait)
            continue
        log.warning("%s returned HTTP %s - check the URL in config.py", key, status)
        return None
    return None