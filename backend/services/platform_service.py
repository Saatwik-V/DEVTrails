"""
services/platform_service.py — 4-Layer Platform Redundancy
────────────────────────────────────────────────────────
Implements the 100% resilient fallback cascade for internal Platform Metrics.
Layer 1: Custom Mock FastAPI Endpoint 1
Layer 2: Custom Mock FastAPI Endpoint 2
Layer 3: Stale Redis Cache (Max 30m old)
Layer 4: Baseline Safety Default (Return 0)
"""

import logging
import httpx
import json
from utils.redis_client import get_redis
from api.payouts import trigger_sla_breach

logger = logging.getLogger("gigkavach.platform")

async def fetch_mock_endpoint(url: str) -> dict | None:
    try:
        # In a real environment, Zomato/Swiggy mock APIs hosted on different ports
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=3.0)
            if r.status_code == 200:
                data = r.json()
                return {"platform_congestion": float(data.get("congestion", 0))}
    except Exception as e:
        logger.error(f"Platform Mock {url} failed: {e}")
    return None

async def fetch_baseline() -> dict | None:
    """Layer 4: Absolute baseline fallback so the algorithm doesn't crash."""
    return {"platform_congestion": 0.0, "note": "Assumed nominal platform load"}

async def get_platform_score(pincode: str) -> dict:
    """Follows strict 4-Layer Cascade."""
    cache_key = f"platform_data:{pincode}"
    rc = await get_redis()
    
    platform_data = None
    
    # For testing, you would aim this at an actual locally hosted mock server
    mock_url_1 = f"http://127.0.0.1:8001/mock/platform/congestion/{pincode}"
    mock_url_2 = f"http://127.0.0.1:8002/mock/platform/congestion/{pincode}"
    
    # LAYER 1: Mock Server 1
    platform_data = await fetch_mock_endpoint(mock_url_1)
    if platform_data is not None:
        platform_data["source"] = "Layer_1_Mock_API_1"
        logger.info(f"Platform Layer 1 Success for {pincode}")

    # LAYER 2: Mock Server 2
    if platform_data is None:
        logger.warning(f"Platform Layer 1 failed. Attempting Layer 2 (Mock API 2) for {pincode}.")
        platform_data = await fetch_mock_endpoint(mock_url_2)
        if platform_data is not None:
            platform_data["source"] = "Layer_2_Mock_API_2"
            logger.info(f"Platform Layer 2 Success for {pincode}")

    # LAYER 3: Stale Redis Cache
    if platform_data is None:
        logger.warning(f"Platform Layer 2 failed. Attempting Layer 3 (Redis Cache) for {pincode}.")
        cached = await rc.get(cache_key)
        if cached:
            platform_data = json.loads(cached)
            platform_data["source"] = "Layer_3_Redis_Stale"
            logger.info(f"Platform Layer 3 Success for {pincode}")

    # LAYER 4: Baseline
    if platform_data is None:
        logger.warning(f"Platform Layer 3 failed. Attempting Layer 4 (Baseline Zero) for {pincode}.")
        platform_data = await fetch_baseline()
        if platform_data is not None:
            platform_data["source"] = "Layer_4_Baseline_0"
            logger.info(f"Platform Layer 4 Success for {pincode}")

    # SLA BREACH FAIL-OUT
    if platform_data is None:
        logger.critical(f"ALL 4 PLATFORM DATA LAYERS FAILED for {pincode}. Data complete blackout.")
        await trigger_sla_breach(pincode, "Complete Platform Data Outage")
        return {"score": 0, "error": "All 4 layers crashed - SLA Breach Triggered"}

    # Assign score based on pure 0-100 logic
    score = int(platform_data.get("platform_congestion", 0))
    platform_data["score"] = score

    if platform_data["source"] != "Layer_3_Redis_Stale":
        await rc.set(cache_key, json.dumps(platform_data), ex=1800)

    return platform_data
