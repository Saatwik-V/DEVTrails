"""
services/heat_service.py — Heat Integrations
────────────────────────────────────────────────────
Reads the latest temperature for the zone (fetched by Tomorrow.io via weather_service cache),
and calculates the requested normalized Heat score. 
Applies gradient logic for 38-42°C.
"""

import logging
import datetime
from typing import Dict
from config.settings import settings
from utils.redis_client import get_redis

logger = logging.getLogger("gigkavach.heat")

def calculate_heat_score(temperature_celsius: float) -> int:
    """
    Converts temperature to a 0-100 disruption score.
    Based on thresholds:
      - >42°C: 100
      - 38-42°C: 50-100 gradient
      - <38°C: 0
    """
    if temperature_celsius > 42.0:
        return 100
    elif temperature_celsius >= 38.0:
        # Gradient: 38 -> 50, 42 -> 100
        # Formula: 50 + ((temp - 38) / (42 - 38)) * (100 - 50)
        return int(50 + ((temperature_celsius - 38.0) / 4.0) * 50)
    else:
        return 0

async def get_heat_score(pincode: str) -> Dict:
    """
    Main entry point for Heat.
    Returns {"score": 0-100, "temperature": ..., "source": ...}
    1. Checks if heat was already calculated in Redis.
    2. If not, reads the weather_data cache to get the latest temperature.
    3. Calculates score & caches.
    """
    cache_key = f"heat_data:{pincode}"
    weather_cache_key = f"weather_data:{pincode}"
    cache_ttl = settings.DCI_CACHE_TTL_SECONDS
    
    rc = await get_redis()
    
    # Check if heat score is already cached
    cached = await rc.get(cache_key)
    if cached:
        logger.debug(f"Heat cache hit for {pincode}")
        import json
        return json.loads(cached)
        
    # We need temperature data. We read it from the weather service's cache.
    # The cron poller executes weather_service first, so this should usually be populated.
    weather_cached = await rc.get(weather_cache_key)
    if not weather_cached:
        logger.warning(f"No weather data found for {pincode} to calculate heat. Defaulting to 0.")
        return {"score": 0, "error": "No temperature data available"}
        
    import json
    weather_data = json.loads(weather_cached)
    temperature = float(weather_data.get("temperature", 0.0))
    source = weather_data.get("source", "unknown")
    
    score = calculate_heat_score(temperature)
    
    # TODO: "Apply only during worker's declared shift window."
    # Since DCI is calculated universally per zone, we calculate the raw environmental hazard here.
    # In the payout/coverage engine that maps worker IDs to payout triggers, it should check
    # if the current DCI event timestamp overlaps with the worker's shift.
    # We add a flag indicating this score represents the raw hazard.
    
    heat_data = {
        "score": score,
        "temperature": temperature,
        "source": source,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "_shift_window_note": "Worker shift validation must be applied in the payout engine."
    }
    
    # Cache
    await rc.set(cache_key, json.dumps(heat_data), ex=cache_ttl)
    
    return heat_data
