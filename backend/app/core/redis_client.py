"""Valfri Redis-integration för fler-replikskörning.

Utan REDIS_URL (enkelnod) är allt en no-op och funktionerna beter sig som
in-memory/enkelnod. Med REDIS_URL används Redis för att koordinera repliker.
"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis = None


def redis_enabled() -> bool:
    return bool(settings.REDIS_URL)


async def get_redis():
    """Lazy-initierad async Redis-klient, eller None om ej konfigurerad."""
    global _redis
    if not settings.REDIS_URL:
        return None
    if _redis is None:
        import redis.asyncio as aioredis
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def acquire_run_lock(name: str, ttl: int) -> bool:
    """Avgör om ett schemalagt jobb ska köras av denna replik.

    Enkelnod (ingen Redis): alltid True.
    Flera repliker: bara den som lyckas ta låset (SET NX EX) kör — övriga hoppar över.
    Vid Redis-fel körs jobbet ändå (hellre köra än att tappa det helt).
    """
    if not settings.REDIS_URL:
        return True
    try:
        r = await get_redis()
        got = await r.set(f"insight:joblock:{name}", "1", nx=True, ex=ttl)
        return bool(got)
    except Exception as e:
        logger.warning("Redis-lås otillgängligt (%s) — kör jobbet %s ändå", e, name)
        return True
