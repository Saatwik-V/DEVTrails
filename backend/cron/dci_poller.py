"""
cron/dci_poller.py — DCI Engine Poller
────────────────────────────────────────────────────
Runs every 5 minutes driven by APScheduler.
Iterates over active zones (pin codes), fetches their Weather, AQI, and Heat scores,
computes the final Disruption Composite Index (DCI), and stores it in Redis and Supabase.
"""

import logging
import asyncio
import datetime
from typing import List

from services.weather_service import get_weather_score
from services.aqi_service import get_aqi_score
from services.heat_service import get_heat_score
from services.social_service import get_social_score
from services.platform_service import get_platform_score
from utils.redis_client import set_dci_cache
from utils.supabase_client import get_supabase
from config.settings import settings

logger = logging.getLogger("gigkavach.dci_poller")

async def get_active_zones() -> List[str]:
    """Returns a list of active pin codes to poll."""
    return ["560001", "560037", "560034", "560038", "560068"]

def get_severity_tier(score: int) -> str:
    """Returns the tier string string for the database."""
    if score >= 85:
        return "catastrophic"
    elif score >= 65:
        return "moderate"
    return "none"

def _insert_log_to_db(payload: dict):
    """Synchronous function to execute the Supabase insert"""
    sb = get_supabase()
    # If the setup fails due to missing keys, it returns a stub or raises.
    if sb and settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        try:
            sb.table("dci_logs").insert(payload).execute()
        except Exception as e:
            logger.error(f"Failed to insert DCI log into Supabase: {e}")

async def process_zone(pincode: str) -> dict:
    """Fetches components and calculates DCI for a single zone."""
    logger.debug(f"Processing DCI for zone {pincode}")
    
    # 1. Fetch live components concurrently
    weather_task = get_weather_score(pincode)
    aqi_task = get_aqi_score(pincode)
    social_task = get_social_score(pincode)
    platform_task = get_platform_score(pincode)
    
    # heat_service reads from weather_service's cache.
    # To ensure it grabs the freshest weather data, we await weather first.
    weather_result = await weather_task
    heat_result = await get_heat_score(pincode)
    aqi_result = await aqi_task
    social_result = await social_task
    platform_result = await platform_task
    
    w_score = weather_result.get("score", 0)
    a_score = aqi_result.get("score", 0)
    h_score = heat_result.get("score", 0)
    s_score = social_result.get("score", 0)
    p_score = platform_result.get("score", 0)
    
    # 2. Compute Composite DCI Score (Weighted aggregation)
    # Rainfall*0.3 + AQI*0.2 + Heat*0.2 + Social*0.2 + Platform*0.1
    final_dci_float = (w_score * 0.3) + (a_score * 0.2) + (h_score * 0.2) + (s_score * 0.2) + (p_score * 0.1)
    final_dci = int(round(final_dci_float))
    severity = get_severity_tier(final_dci)
    
    dci_data = {
        "pincode": pincode,
        "dci_score": final_dci,
        "severity_tier": severity,
        "components": {
            "rainfall": weather_result,
            "aqi": aqi_result,
            "heat": heat_result,
            "social": social_result,
            "platform": platform_result,
        },
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    # 3. Cache the full composite payload in Redis for APIs / Payout tracking
    await set_dci_cache(pincode, dci_data, settings.DCI_CACHE_TTL_SECONDS)
    
    # 4. Insert historical log into Supabase
    db_payload = {
        "pincode": pincode,
        "total_score": final_dci,
        "rainfall_score": w_score,
        "aqi_score": a_score,
        "heat_score": h_score,
        "social_score": s_score,
        "platform_score": p_score,
        "severity_tier": severity
    }
    
    # Run the synchronous Supabase insert in a background thread to prevent blocking
    await asyncio.to_thread(_insert_log_to_db, db_payload)
    
    return dci_data

async def run_dci_cycle():
    """Main job triggered by APScheduler every 5 minutes."""
    logger.info("Starting DCI polling cycle...")
    start_time = datetime.datetime.now()
    
    active_zones = await get_active_zones()
    semaphore = asyncio.Semaphore(5)
    
    async def _process_with_semaphore(pincode: str):
        async with semaphore:
            return await process_zone(pincode)
            
    tasks = [_process_with_semaphore(pin) for pin in active_zones]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = sum(1 for r in results if not isinstance(r, Exception))
    elapsed = (datetime.datetime.now() - start_time).total_seconds()
    
    logger.info(f"DCI cycle completed. Processed {success_count}/{len(active_zones)} zones in {elapsed:.2f}s")
