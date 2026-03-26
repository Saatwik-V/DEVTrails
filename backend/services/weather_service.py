"""
services/weather_service.py — Weather Integrations
────────────────────────────────────────────────────
Fetches weather details (rainfall, temp, humidity) via Tomorrow.io,
falling back to Open-Meteo. Calculates the normalized rainfall score (0-100).
Caches results in Redis.
"""

import httpx
import logging
import datetime
from typing import Optional, Dict

from config.settings import settings
from utils.redis_client import get_dci_cache, set_dci_cache, record_api_failure, record_api_success
from utils.geocoding import get_coordinates_from_pincode

logger = logging.getLogger("gigkavach.weather")

def calculate_rainfall_score(rainfall_mm: float) -> int:
    """
    Converts rainfall in mm to a 0-100 disruption score.
    Based on typical thresholds:
      - 0-2mm: 0
      - >2-10mm (Light-Mod): scales to ~30
      - >10-50mm (Heavy): scales to ~70
      - >50mm (Violent): scales 70-100
      - >100mm: 100
    """
    if rainfall_mm <= 0:
        return 0
    elif rainfall_mm <= 10:
        return int((rainfall_mm / 10.0) * 30)
    elif rainfall_mm <= 50:
        return 30 + int(((rainfall_mm - 10) / 40.0) * 40)
    elif rainfall_mm <= 100:
        return 70 + int(((rainfall_mm - 50) / 50.0) * 30)
    else:
        return 100

async def fetch_tomorrow_io(lat: float, lng: float) -> Optional[Dict]:
    """Fetch realtime weather data from Tomorrow.io API."""
    if not settings.TOMORROW_IO_API_KEY:
        logger.warning("TOMORROW_IO_API_KEY is missing, skipping Tomorrow.io")
        return None
        
    url = "https://api.tomorrow.io/v4/weather/realtime"
    params = {
        "location": f"{lat},{lng}",
        "units": "metric",
        "apikey": settings.TOMORROW_IO_API_KEY
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            
            values = data.get("data", {}).get("values", {})
            return {
                "rainfall": float(values.get("precipitationIntensity", 0.0)),
                "temperature": float(values.get("temperature", 0.0)),
                "humidity": float(values.get("humidity", 0.0)),
                "source": "tomorrow.io"
            }
    except Exception as e:
        logger.error(f"Tomorrow.io fetching error: {e}")
        await record_api_failure("tomorrow.io")
        return None

async def fetch_open_meteo(lat: float, lng: float) -> Optional[Dict]:
    """Fetch realtime weather data from Open-Meteo (Fallback API)."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lng,
        "current": ["temperature_2m", "relative_humidity_2m", "precipitation"],
        "timezone": "auto"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            
            current = data.get("current", {})
            return {
                "rainfall": float(current.get("precipitation", 0.0)),
                "temperature": float(current.get("temperature_2m", 0.0)),
                "humidity": float(current.get("relative_humidity_2m", 0.0)),
                "source": "open-meteo"
            }
    except Exception as e:
        logger.error(f"Open-meteo fetching error: {e}")
        await record_api_failure("open-meteo")
        return None

async def get_weather_score(pincode: str) -> Dict:
    """
    Main entry point.
    Returns {"score": 0-100, "rainfall": ..., "temp": ..., "humidity": ..., "source": ...}
    1. Checks Redis cache.
    2. Geocodes pincode -> lat, lng
    3. Tries Tomorrow.io -> Open-Meteo.
    4. Caches and returns results.
    """
    cache_key = f"weather_data:{pincode}"
    cache_ttl = settings.DCI_CACHE_TTL_SECONDS
    
    # 1. Check specific weather cache 
    from utils.redis_client import get_redis
    rc = await get_redis()
    
    cached = await rc.get(cache_key)
    if cached:
        logger.debug(f"Weather cache hit for {pincode}")
        import json
        return json.loads(cached)
        
    # 2. Geocoding
    coords = await get_coordinates_from_pincode(pincode)
    if not coords:
        logger.error(f"Cannot resolve coordinates for {pincode}. Returning 0 score.")
        return {"score": 0, "error": "Geocoding failed"}
        
    lat, lng = coords
    
    # 3. Call Tomorrow.io
    weather_data = await fetch_tomorrow_io(lat, lng)
    if weather_data is not None:
        await record_api_success("tomorrow.io")
    else:
        # 4. Fallback to Open-Meteo
        logger.info("Falling back to Open-Meteo for weather")
        weather_data = await fetch_open_meteo(lat, lng)
        if weather_data is not None:
            await record_api_success("open-meteo")
            
    if not weather_data:
        logger.error(f"All weather APIs failed for pincode {pincode}")
        return {"score": 0, "error": "All APIs failed"}
        
    # 5. Calculate Score
    score = calculate_rainfall_score(weather_data["rainfall"])
    weather_data["score"] = score
    weather_data["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # 6. Cache
    import json
    await rc.set(cache_key, json.dumps(weather_data), ex=cache_ttl)
    
    return weather_data
