"""
cron/dci_poller.py — DCI Engine Poller
────────────────────────────────────────────────────
Runs every 5 minutes driven by APScheduler.
Iterates over active zones (pin codes), fetches their Weather and AQI scores,
computes the final Disruption Composite Index (DCI), and stores it in Redis.
"""

import logging
import asyncio
import datetime
from typing import List

from services.weather_service import get_weather_score
from services.aqi_service import get_aqi_score
from utils.redis_client import set_dci_cache
from config.settings import settings

logger = logging.getLogger("gigkavach.dci_poller")

async def get_active_zones() -> List[str]:
    """
    Returns a list of active pin codes to poll.
    For this hackathon, we simulate fetching these from the database.
    Focus on primary Bangalore delivery zones.
    """
    # TODO: Fetch dynamically from database `zones` table
    return [
        "560001", # MG Road / Central
        "560037", # Marathahalli
        "560034", # Koramangala
        "560038", # Indiranagar
        "560068", # HSR Layout
    ]

async def process_zone(pincode: str) -> dict:
    """Fetches components and calculates DCI for a single zone."""
    logger.debug(f"Processing DCI for zone {pincode}")
    
    # Run fetchers concurrently to save time
    weather_task = get_weather_score(pincode)
    aqi_task = get_aqi_score(pincode)
    
    weather_result, aqi_result = await asyncio.gather(weather_task, aqi_task)
    
    w_score = weather_result.get("score", 0)
    a_score = aqi_result.get("score", 0)
    
    # DCI is a composite logic. In parametric insurance, often the worst disruption 
    # dictates the payout. We use the maximum score among all components.
    final_dci = max(w_score, a_score)
    
    dci_data = {
        "pincode": pincode,
        "dci_score": final_dci,
        "components": {
            "weather": weather_result,
            "aqi": aqi_result,
        },
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    # Cache it in Redis for rapid access by payout/pricing systems
    await set_dci_cache(pincode, dci_data, settings.DCI_CACHE_TTL_SECONDS)
    
    return dci_data

async def run_dci_cycle():
    """
    Main job triggered by APScheduler every 5 minutes.
    """
    logger.info("Starting DCI polling cycle...")
    start_time = datetime.datetime.now()
    
    active_zones = await get_active_zones()
    
    # Limit concurrency so we don't overwhelm external APIs
    # Tomorrow.io and AQICN might have rate limits per second.
    semaphore = asyncio.Semaphore(5)
    
    async def _process_with_semaphore(pincode: str):
        async with semaphore:
            return await process_zone(pincode)
            
    tasks = [_process_with_semaphore(pin) for pin in active_zones]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = sum(1 for r in results if not isinstance(r, Exception))
    elapsed = (datetime.datetime.now() - start_time).total_seconds()
    
    logger.info(f"DCI cycle completed. Processed {success_count}/{len(active_zones)} zones in {elapsed:.2f}s")
