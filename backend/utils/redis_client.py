"""
utils/redis_client.py — Redis Cache Client
─────────────────────────────────────────────
Uses redis.asyncio to connect to a Redis server for caching DCI scores
and managing payout locks across multiple workers.

Usage:
    from utils.redis_client import set_dci_cache, get_dci_cache, acquire_payout_lock
"""

import logging
import json
import time
from typing import Optional
from redis.asyncio import Redis, from_url
from config.settings import settings

logger = logging.getLogger("gigkavach.cache")

# Redis Client singleton
redis_client: Optional[Redis] = None

async def get_redis() -> Redis:
    """Returns the Redis connection, initializing it if necessary."""
    global redis_client
    if not redis_client:
        redis_client = from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        logger.info(f"Connected to Redis at {settings.REDIS_URL}")
    return redis_client

async def close_redis():
    """Closes the Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.aclose()
        redis_client = None

# DCI cache TTL (seconds)
DCI_CACHE_TTL_SECONDS = settings.DCI_CACHE_TTL_SECONDS

# ─── DCI Score Cache ──────────────────────────────────────────────────────────

def _dci_key(pin_code: str) -> str:
    return f"dci:score:{pin_code}"

async def set_dci_cache(pin_code: str, dci_data: dict, ttl_seconds: int = DCI_CACHE_TTL_SECONDS) -> None:
    """Stores a DCI result for a zone. TTL = 30 min (default)."""
    rc = await get_redis()
    await rc.set(_dci_key(pin_code), json.dumps(dci_data), ex=ttl_seconds)
    logger.debug(f"DCI cached for pin {pin_code} | TTL {ttl_seconds}s")

async def get_dci_cache(pin_code: str) -> Optional[dict]:
    """Returns cached DCI data for a zone, or None if expired / not set."""
    rc = await get_redis()
    raw = await rc.get(_dci_key(pin_code))
    if raw is None:
        logger.debug(f"DCI cache miss for pin {pin_code}")
        return None
    return json.loads(raw)

# ─── Payout Deduplication Lock ───────────────────────────────────────────────

def _lock_key(worker_id: str, dci_event_id: str) -> str:
    return f"payout:lock:{worker_id}:{dci_event_id}"

async def acquire_payout_lock(worker_id: str, dci_event_id: str, ttl_seconds: int = 86400) -> bool:
    """
    Tries to acquire a payout lock for this worker + DCI event.
    Returns True if acquired (first call), False if already locked.
    TTL = 24 hours.
    """
    rc = await get_redis()
    acquired = await rc.set(_lock_key(worker_id, dci_event_id), "locked", ex=ttl_seconds, nx=True)
    if acquired:
        logger.info(f"Payout lock acquired: worker={worker_id} event={dci_event_id}")
        return True
    else:
        logger.warning(f"Payout lock exists — preventing duplicate: worker={worker_id} event={dci_event_id}")
        return False

async def release_payout_lock(worker_id: str, dci_event_id: str) -> None:
    """Release a payout lock (used when a payout fails and must be retried)."""
    rc = await get_redis()
    await rc.delete(_lock_key(worker_id, dci_event_id))
    logger.info(f"Payout lock released: worker={worker_id} event={dci_event_id}")

# ─── API Health Tracking ──────────────────────────────────────────────────────

async def record_api_failure(api_name: str) -> None:
    """Mark when an API first went down. Used for SLA breach detection."""
    rc = await get_redis()
    key = f"api:failure_start:{api_name}"
    await rc.set(key, str(time.time()), ex=DCI_CACHE_TTL_SECONDS * 2, nx=True)

async def record_api_success(api_name: str) -> None:
    """Clear failure record when an API recovers."""
    rc = await get_redis()
    await rc.delete(f"api:failure_start:{api_name}")
