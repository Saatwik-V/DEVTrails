"""
services/aqi_service.py — AQI Integrations
────────────────────────────────────────────────────
Fetches AQI details via AQICN, falling back to CPCB.
Calculates the normalized AQI score (0-100).
Caches results in Redis.
"""

import httpx
import logging
import datetime
from typing import Optional, Dict

from config.settings import settings
from utils.redis_client import record_api_failure, record_api_success
from utils.geocoding import get_coordinates_from_pincode

logger = logging.getLogger("gigkavach.aqi")

def calculate_aqi_score(aqi: int) -> int:
    """
    Converts AQI to a 0-100 disruption score.
    Based on thresholds:
      - >300: 100
      - 200-300: 70
      - 100-200: 30
      - 50-100: 10
      - 0-50: 0
    """
    if aqi > 300:
        return 100
    elif aqi > 200:
        return 70
    elif aqi > 100:
        return 30
    elif aqi > 50:
        return 10
    else:
        return 0

async def fetch_aqicn(lat: float, lng: float) -> Optional[Dict]:
    """Fetch realtime AQI data from AQICN."""
    if not settings.AQICN_API_TOKEN:
        logger.warning("AQICN_API_TOKEN is missing, skipping AQICN")
        return None
        
    url = f"https://api.waqi.info/feed/geo:{lat};{lng}/"
    params = {
        "token": settings.AQICN_API_TOKEN
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("status") == "ok":
                aqi_value = data.get("data", {}).get("aqi", 0)
                try:
                    aqi_value = int(aqi_value)
                except ValueError:
                    aqi_value = 0
                    
                return {
                    "aqi": aqi_value,
                    "source": "aqicn"
                }
            return None
    except Exception as e:
        logger.error(f"AQICN fetching error: {e}")
        await record_api_failure("aqicn")
        return None

async def fetch_cpcb(lat: float, lng: float) -> Optional[Dict]:
    """
    Fetch realtime AQI data from CPCB (National Air Quality Index).
    NOTE: CPCB doesn't have a simple public REST API for lat/lng without an enterprise key.
    We will simulate a fallback response or use an open alternative for the hackathon.
    For this implementation, we will mock a reasonable fallback if AQICN goes down.
    """
    try:
        # Simulate an API call latency
        import asyncio
        await asyncio.sleep(0.5)
        # Hackathon mock logic: generate a somewhat realistic fallback AQI
        mock_aqi = 150 # Moderate to Poor fallback
        return {
            "aqi": mock_aqi,
            "source": "cpcb-mock"
        }
    except Exception as e:
        logger.error(f"CPCB fetching error: {e}")
        await record_api_failure("cpcb")
        return None

async def get_aqi_score(pincode: str) -> Dict:
    """
    Main entry point for AQI.
    Returns {"score": 0-100, "aqi": ..., "source": ...}
    1. Checks Redis cache.
    2. Geocodes pincode -> lat, lng
    3. Tries AQICN -> CPCB.
    4. Caches and returns results.
    """
    cache_key = f"aqi_data:{pincode}"
    cache_ttl = settings.DCI_CACHE_TTL_SECONDS
    
    # 1. Check specific AQI cache
    from utils.redis_client import get_redis
    rc = await get_redis()
    
    cached = await rc.get(cache_key)
    if cached:
        logger.debug(f"AQI cache hit for {pincode}")
        import json
        return json.loads(cached)
        
    # 2. Geocoding
    coords = await get_coordinates_from_pincode(pincode)
    if not coords:
        logger.error(f"Cannot resolve coordinates for {pincode}. Returning 0 score.")
        return {"score": 0, "error": "Geocoding failed"}
        
    lat, lng = coords
    
    # 3. Call AQICN
    aqi_data = await fetch_aqicn(lat, lng)
    if aqi_data is not None:
        await record_api_success("aqicn")
    else:
        # 4. Fallback to CPCB
        logger.info("Falling back to CPCB for AQI")
        aqi_data = await fetch_cpcb(lat, lng)
        if aqi_data is not None:
            await record_api_success("cpcb")
            
    if not aqi_data:
        logger.error(f"All AQI APIs failed for pincode {pincode}")
        return {"score": 0, "error": "All APIs failed"}
        
    # 5. Calculate Score
    score = calculate_aqi_score(aqi_data["aqi"])
    aqi_data["score"] = score
    aqi_data["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # 6. Cache
    import json
    await rc.set(cache_key, json.dumps(aqi_data), ex=cache_ttl)
    
    return aqi_data
