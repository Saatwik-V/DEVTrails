"""
utils/geocoding.py — Lat/Lng Resolver
─────────────────────────────────────────────────
Uses Nominatim (OpenStreetMap) to convert Indian pin codes to latitude and longitude.
"""

import httpx
import logging
from typing import Tuple, Optional

logger = logging.getLogger("gigkavach.geocoding")

# We can cache these mappings so we don't spam Nominatim
from utils.redis_client import get_redis

async def get_coordinates_from_pincode(pincode: str) -> Optional[Tuple[float, float]]:
    """
    Given an Indian pin code (e.g., '560001'), returns (latitude, longitude).
    Uses a Redis cache to avoid rate limits, falls back to Nominatim API.
    """
    # 1. Check Cache
    rc = await get_redis()
        
    cache_key = f"geocode:pincode:{pincode}"
    cached = await rc.get(cache_key)
    if cached:
        lat, lng = cached.split(",")
        return float(lat), float(lng)

    # 2. Fetch from Nominatim API
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "postalcode": pincode,
        "country": "India",
        "format": "json",
        "limit": 1
    }
    headers = {
        "User-Agent": "GigKavach-Hackathon-App/1.0 (contact@gigkavach.com)"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers, timeout=5.0)
            response.raise_for_status()
            data = response.json()
            
            if data and len(data) > 0:
                lat = float(data[0]["lat"])
                lng = float(data[0]["lon"])
                
                # Cache indefinitely (pin codes rarely move)
                await rc.set(cache_key, f"{lat},{lng}")
                return lat, lng
            else:
                logger.warning(f"Nominatim returned no results for pincode {pincode}")
                return None
                
    except Exception as e:
        logger.error(f"Geocoding failed for {pincode}: {e}")
        return None
