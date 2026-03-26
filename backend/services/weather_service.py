"""
services/weather_service.py — 4-Layer Redundancy Logic
────────────────────────────────────────────────────
Implements the 100% resilient fallback cascade for Weather Data.
Layer 1: Tomorrow.io
Layer 2: Open-Meteo
Layer 3: Stale Redis Cache (Max 30m old)
Layer 4: IMD RSS Parser
Fallback: Trigger SLA Breach and return 0.
"""

import logging
import httpx
import json
from config.settings import settings
from utils.geocoding import get_coordinates_from_pincode
from utils.redis_client import get_redis

logger = logging.getLogger("gigkavach.weather")

def calculate_rainfall_score(rainfall_mm: float) -> int:
    if rainfall_mm > 50:
        return 100
    elif rainfall_mm > 20:
        return 70
    elif rainfall_mm > 5:
        return 40
    else:
        return 0

async def fetch_tomorrow_io(lat: float, lng: float) -> dict | None:
    if not settings.TOMORROW_IO_API_KEY:
        return None
    url = f"https://api.tomorrow.io/v4/weather/realtime?location={lat},{lng}&apikey={settings.TOMORROW_IO_API_KEY}"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=5.0)
            r.raise_for_status()
            data = r.json()
            values = data.get("data", {}).get("values", {})
            return {
                "rainfall": float(values.get("precipitationIntensity", 0.0)),
                "temperature": float(values.get("temperature", 0.0)),
                "humidity": float(values.get("humidity", 0.0)),
            }
    except Exception as e:
        logger.error(f"Tomorrow.io fetch failed: {e}")
        return None

async def fetch_open_meteo(lat: float, lng: float) -> dict | None:
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current=temperature_2m,relative_humidity_2m,precipitation"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=5.0)
            r.raise_for_status()
            data = r.json()
            current = data.get("current", {})
            return {
                "rainfall": float(current.get("precipitation", 0.0)),
                "temperature": float(current.get("temperature_2m", 0.0)),
                "humidity": float(current.get("relative_humidity_2m", 0.0)),
            }
    except Exception as e:
        logger.error(f"Open-Meteo fetch failed: {e}")
        return None

async def get_weather_score(pincode: str) -> dict:
    """Follows strict 4-Layer Cascade."""
    cache_key = f"weather_data:{pincode}"
    rc = await get_redis()
    
    lat, lng = await get_coordinates_from_pincode(pincode)
    if not lat or not lng:
        logger.error(f"Cannot resolve coordinates for {pincode}. Failing.")
        return {"score": 0, "error": "geocoding failure"}
        
    weather_data = None
    
    # LAYER 1: Tomorrow.io
    weather_data = await fetch_tomorrow_io(lat, lng)
    if weather_data:
        weather_data["source"] = "Layer_1_Tomorrow_io"
        logger.info(f"Layer 1 Success for {pincode}")

    # LAYER 2: Open-Meteo
    if not weather_data:
        logger.warning(f"Layer 1 failed. Attempting Layer 2 (Open-Meteo) for {pincode}.")
        weather_data = await fetch_open_meteo(lat, lng)
        if weather_data:
            weather_data["source"] = "Layer_2_Open_Meteo"
            logger.info(f"Layer 2 Success for {pincode}")

    # LAYER 3: Stale Redis Cache
    if not weather_data:
        logger.warning(f"Layer 2 failed. Attempting Layer 3 (Redis Cache) for {pincode}.")
        cached = await rc.get(cache_key)
        if cached:
            weather_data = json.loads(cached)
            weather_data["source"] = "Layer_3_Redis_Stale"
            logger.info(f"Layer 3 Success for {pincode}")

    # LAYER 4: IMD RSS Parser
    if not weather_data:
        logger.warning(f"Layer 3 failed. Attempting Layer 4 (IMD RSS) for {pincode}.")
        from cron.rss_parser import fetch_imd_rss_alert
        weather_data = await fetch_imd_rss_alert(pincode)
        if weather_data:
            weather_data["source"] = "Layer_4_IMD_RSS"
            logger.info(f"Layer 4 Success for {pincode}")

    # SLA BREACH FAIL-OUT
    if not weather_data:
        logger.critical(f"ALL 4 DATA LAYERS FAILED for {pincode}. Data complete blackout.")
        from api.payouts import trigger_sla_breach
        await trigger_sla_breach(pincode, "Complete Weather Data Outage")
        return {"score": 0, "error": "All 4 layers crashed - SLA Breach Triggered"}

    # Compute Disruption Score based on final cascaded data
    score = calculate_rainfall_score(weather_data.get("rainfall", 0.0))
    weather_data["score"] = score

    # Push to Layer 3 Cache for future 30-min window fallbacks
    # Only cache if data isn't already from the stale cache itself
    if weather_data["source"] != "Layer_3_Redis_Stale":
        await rc.set(cache_key, json.dumps(weather_data), ex=1800) # 1800 seconds = 30 mins

    return weather_data
