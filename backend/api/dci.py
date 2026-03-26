"""
api/dci.py — DCI Engine Endpoints
────────────────────────────────────────────────────
Exposes the Disruption Composite Index (DCI) for external systems (like frontend dashboards).
Includes current breakdown and historical trends fetched from Redis and Supabase.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import datetime
import json
import asyncio

from utils.redis_client import get_redis
from utils.supabase_client import get_supabase
from config.settings import settings
import logging

logger = logging.getLogger("gigkavach.api.dci")

router = APIRouter(tags=["DCI Engine"])

def fetch_history_sync(pincode: str) -> list:
    """Helper to fetch from Supabase synchronously so it can be threaded."""
    sb = get_supabase()
    if not sb or not settings.SUPABASE_URL:
        return []
    
    # Get last 24 hours of data
    time_threshold = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)).isoformat()
    
    try:
        response = sb.table("dci_logs")\
            .select("*")\
            .eq("pincode", pincode)\
            .gte("created_at", time_threshold)\
            .order("created_at", desc=True)\
            .execute()
        return response.data
    except Exception as e:
        logger.error(f"Failed fetching history: {e}")
        return []

@router.get("/dci/{pincode}", response_model=Dict[str, Any])
async def get_dci_status(pincode: str):
    """
    Returns the current DCI score breakdown and historical 24-hr data for a given pin code.
    If no cached realtime data exists, it returns a 404 suggesting the poller hasn't run.
    """
    rc = await get_redis()
    
    # 1. Fetch CURRENT status from Redis
    cache_key = f"dci:score:{pincode}"  # This is the key set by `set_dci_cache`
    current_raw = await rc.get(cache_key)
    
    if not current_raw:
        # Check if we have raw weather/aqi but no composite
        raise HTTPException(
            status_code=404, 
            detail=f"No active DCI data for pin code {pincode}. Ensure the cron poller is tracking this zone."
        )
        
    current_data = json.loads(current_raw)
    
    # 2. Fetch HISTORICAL data from Supabase
    history_data = await asyncio.to_thread(fetch_history_sync, pincode)
    
    # We can format the history to just standard points (time vs total_score) to save bandwidth
    condensed_history = [
        {
            "timestamp": row["created_at"],
            "score": row["total_score"],
            "severity": row["severity_tier"]
        }
        for row in history_data
    ]
    
    return {
        "pincode": pincode,
        "current": current_data,
        "history_24h": condensed_history
    }
