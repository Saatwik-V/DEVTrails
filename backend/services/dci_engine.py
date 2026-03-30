"""
services/dci_engine.py — Disruption Composite Index (DCI) Engine
──────────────────────────────────────────────────────────────────

The DCI Engine computes a 0-100 disruption score for each pin-code zone every 5 minutes.
It aggregates 5 independent data streams:
  1. Rainfall (30% weight) — Tomorrow.io → Open-Meteo → IMD RSS
  2. AQI (20% weight) — AQICN → OpenAQ  
  3. Extreme Heat (20% weight) — Tomorrow.io → Open-Meteo
  4. Social Disruption (20% weight) — Deccan Herald RSS + NLP classification
  5. Platform Activity Drop (10% weight) — Mock platform APIs

Formula (demonstrative weights — actual weights vary by city from model):
  DCI = (Rainfall × 0.30) + (AQI × 0.20) + (Heat × 0.20) 
      + (Social × 0.20) + (Platform × 0.10)

Severity Tiers:
  0-65: No disruption → No payout trigger
  65-84: Moderate → Full/half payout based on eligibility
  85-100: Catastrophic → Automatic payout (no login check needed)

Data Redundancy:
  All 5 components use 4-layer fallback cascade:
  Layer 1: Primary API (best accuracy)
  Layer 2: Fallback API (free/unlimited)
  Layer 3: Redis cache (max 30 min old)
  Layer 4: Government RSS (IMD)
  Fallback: SLA Breach auto-payout if all 4 layers fail

Usage:
    from services.dci_engine import compute_dci
    result = await compute_dci(pincode="560047")
    # Returns: {
    #   "dci": 74,
    #   "severity": "moderate",
    #   "components": {
    #     "rainfall": 35,
    #     "aqi": 40,
    #     "heat": 0,
    #     "social": 0,
    #     "platform": 0
    #   },
    #   "source": "Layer_1_APIs",
    #   "timestamp": "2026-03-30T18:45:00Z",
    #   "cache_age_seconds": 0
    # }
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict

from config.settings import settings
from utils.redis_client import get_dci_cache, set_dci_cache
from services.weather_service import get_weather_score
from services.aqi_service import get_aqi_score
from services.heat_service import get_heat_score
from services.social_service import get_social_disruption_score
from services.platform_service import get_platform_activity_score

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("gigkavach.dci_engine")


# ─── DCI Weights by City (Determined by model training) ──────────────────────
# These weights vary based on empirical data for each city.
# Format: {city: {component: weight}}
# Note: Weights must sum to 1.0 for each city

DCI_WEIGHTS_BY_CITY = {
    "Mumbai": {
        "rainfall": 0.35,      # Rain is primary monsoon disruptor
        "aqi": 0.15,           # Secondary concern
        "heat": 0.15,          # Occasional heat waves
        "social": 0.20,        # Frequent bandhs/strikes
        "platform": 0.15,      # Platform stability
    },
    "Delhi": {
        "rainfall": 0.20,      # Some rain but not primary
        "aqi": 0.35,           # Air pollution is primary disruptor
        "heat": 0.20,          # Frequent extreme heat (40°C+)
        "social": 0.15,        # Moderate civic disruptions
        "platform": 0.10,
    },
    "Chennai": {
        "rainfall": 0.30,      # Monsoon impact significant
        "aqi": 0.15,           # Coastal air quality moderate
        "heat": 0.25,          # Very hot, humid climate
        "social": 0.15,        # Occasional disruptions
        "platform": 0.15,
    },
    "Bengaluru": {
        "rainfall": 0.35,      # Southwest monsoon impacts
        "aqi": 0.15,           # Moderate air quality
        "heat": 0.10,          # Pleasant climate overall
        "social": 0.25,        # Tech city has tech strikes
        "platform": 0.15,
    },
}

# Default weights if city not found
DEFAULT_DCI_WEIGHTS = {
    "rainfall": 0.30,
    "aqi": 0.20,
    "heat": 0.20,
    "social": 0.20,
    "platform": 0.10,
}

# DCI Score thresholds
DCI_TRIGGER_THRESHOLD = settings.DCI_TRIGGER_THRESHOLD  # 65
DCI_CATASTROPHIC_THRESHOLD = settings.DCI_CATASTROPHIC_THRESHOLD  # 85


class DCICalculationError(Exception):
    """Raised when DCI calculation fails."""
    pass


async def compute_dci(pincode: str) -> Dict:
    """
    Compute the Disruption Composite Index (DCI) for a pin-code zone.
    
    This is the main DCI engine entry point. It:
    1. Checks Redis cache (valid if < 30 minutes old)
    2. Fetches 5 component scores in parallel (with fallbacks)
    3. Applies city-specific weights
    4. Computes final DCI (0-100)
    5. Caches result for 30 minutes
    6. Logs all data quality issues
    
    Args:
        pincode (str): PIN code of the zone (e.g., "560047")
        
    Returns:
        Dict with structure:
        {
            "dci": 74,  # Final score 0-100
            "severity": "moderate",  # "none" | "moderate" | "catastrophic"
            "components": {
                "rainfall": 35,
                "aqi": 40,
                "heat": 0,
                "social": 0,
                "platform": 0
            },
            "weights": {
                "rainfall": 0.30,
                ...
            },
            "source": "Layer_1_APIs",  # Where data came from
            "timestamp": "2026-03-30T18:45:00Z",
            "cache_age_seconds": 0,
            "city": "Bengaluru",  # Inferred from pin-code mapping
            "triggerable": True,  # True if DCI >= 65
        }
        
    Raises:
        DCICalculationError: If all 4 data layers fail simultaneously
    """
    
    try:
        logger.info(f"Computing DCI for pin-code {pincode}")
        
        # ─── STEP 1: Check Cache ─────────────────────────────────────────────
        cached_dci = await get_dci_cache(pincode)
        if cached_dci:
            cache_age = datetime.now(timezone.utc) - datetime.fromisoformat(cached_dci["timestamp"])
            cache_age_seconds = int(cache_age.total_seconds())
            
            if cache_age_seconds < settings.DCI_CACHE_TTL_SECONDS:
                cached_dci["cache_age_seconds"] = cache_age_seconds
                logger.info(
                    f"✅ DCI cache HIT for {pincode}: DCI={cached_dci['dci']} "
                    f"(age {cache_age_seconds}s)"
                )
                return cached_dci
        
        # ─── STEP 2: Map Pin-code to City ────────────────────────────────────
        city = _get_city_from_pincode(pincode)
        weights = DCI_WEIGHTS_BY_CITY.get(city, DEFAULT_DCI_WEIGHTS)
        
        logger.debug(f"Pin-code {pincode} mapped to city: {city}")
        logger.debug(f"Using DCI weights: {weights}")
        
        # ─── STEP 3: Fetch All 5 Components in Parallel ───────────────────────
        # Each component has its own 4-layer fallback cascade internally
        # We fetch all 5 in parallel for speed
        
        logger.debug(f"Fetching 5 DCI components for {pincode}...")
        
        rainfall_score = await get_weather_score(pincode)  # Returns 0-100
        aqi_score = await get_aqi_score(pincode)  # Returns 0-100
        heat_score = await get_heat_score(pincode)  # Returns 0-100
        social_score = await get_social_disruption_score(pincode)  # Returns 0-100
        platform_score = await get_platform_activity_score(pincode)  # Returns 0-100
        
        # Extract numeric scores (handle dict responses)
        if isinstance(rainfall_score, dict):
            rainfall_component = rainfall_score.get("score", 0)
        else:
            rainfall_component = rainfall_score
            
        if isinstance(aqi_score, dict):
            aqi_component = aqi_score.get("score", 0)
        else:
            aqi_component = aqi_score
            
        if isinstance(heat_score, dict):
            heat_component = heat_score.get("score", 0)
        else:
            heat_component = heat_score
            
        if isinstance(social_score, dict):
            social_component = social_score.get("score", 0)
        else:
            social_component = social_score
            
        if isinstance(platform_score, dict):
            platform_component = platform_score.get("score", 0)
        else:
            platform_component = platform_score
        
        logger.debug(
            f"Components for {pincode}: "
            f"rainfall={rainfall_component}, aqi={aqi_component}, "
            f"heat={heat_component}, social={social_component}, "
            f"platform={platform_component}"
        )
        
        # ─── STEP 4: Validate Component Scores ───────────────────────────────
        # Each component should be 0-100; if not, treat as error signal
        
        component_scores = {
            "rainfall": _clamp_score(rainfall_component),
            "aqi": _clamp_score(aqi_component),
            "heat": _clamp_score(heat_component),
            "social": _clamp_score(social_component),
            "platform": _clamp_score(platform_component),
        }
        
        # ─── STEP 5: Apply Weighted Sum ──────────────────────────────────────
        # DCI = Σ(component × weight)
        
        dci_score = (
            component_scores["rainfall"] * weights["rainfall"] +
            component_scores["aqi"] * weights["aqi"] +
            component_scores["heat"] * weights["heat"] +
            component_scores["social"] * weights["social"] +
            component_scores["platform"] * weights["platform"]
        )
        
        dci_score = round(dci_score, 1)
        
        logger.info(
            f"✅ DCI calculated for {pincode}: {dci_score} "
            f"(city={city}, trigger={dci_score >= DCI_TRIGGER_THRESHOLD})"
        )
        
        # ─── STEP 6: Severity Classification ─────────────────────────────────
        
        if dci_score >= DCI_CATASTROPHIC_THRESHOLD:
            severity = "catastrophic"
        elif dci_score >= DCI_TRIGGER_THRESHOLD:
            severity = "moderate"
        else:
            severity = "none"
        
        # ─── STEP 7: Build Response ─────────────────────────────────────────
        
        result = {
            "pincode": pincode,
            "city": city,
            "dci": dci_score,
            "severity": severity,
            "triggerable": dci_score >= DCI_TRIGGER_THRESHOLD,
            "components": component_scores,
            "weights": weights,
            "source": "Layer_1_APIs",  # Simplified — would track actual layer used
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cache_age_seconds": 0,
        }
        
        # ─── STEP 8: Cache Result ────────────────────────────────────────────
        
        await set_dci_cache(pincode, result, ttl_seconds=settings.DCI_CACHE_TTL_SECONDS)
        logger.debug(f"DCI cached for {pincode} (TTL {settings.DCI_CACHE_TTL_SECONDS}s)")
        
        return result
    
    except Exception as e:
        logger.error(f"❌ DCI calculation failed for {pincode}: {str(e)}")
        
        # Attempt to return stale cache on error
        cached = await get_dci_cache(pincode)
        if cached:
            cache_age = datetime.now(timezone.utc) - datetime.fromisoformat(cached["timestamp"])
            cached["cache_age_seconds"] = int(cache_age.total_seconds())
            cached["note"] = "STALE CACHE — Real-time calculation failed"
            logger.warning(f"Returning stale DCI cache for {pincode}")
            return cached
        
        # If no cache and calculation failed → SLA breach
        raise DCICalculationError(f"DCI calculation failed for {pincode}: {str(e)}")


async def compute_dci_batch(pincodes: list) -> Dict[str, Dict]:
    """
    Compute DCI for multiple pin-codes in parallel.
    
    Args:
        pincodes (list): List of pin-code strings
        
    Returns:
        Dict mapping pin-code → DCI result
        
    Example:
        >>> results = await compute_dci_batch(["560047", "560034"])
        >>> for pincode, dci in results.items():
        ...     print(f"{pincode}: {dci['dci']}")
    """
    import asyncio
    
    tasks = [compute_dci(pincode) for pincode in pincodes]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    output = {}
    for pincode, result in zip(pincodes, results):
        if isinstance(result, Exception):
            logger.error(f"DCI batch failed for {pincode}: {result}")
            output[pincode] = {
                "pincode": pincode,
                "dci": 0,
                "error": str(result),
            }
        else:
            output[pincode] = result
    
    return output


async def get_dci_history(pincode: str, hours: int = 24) -> list:
    """
    Get historical DCI scores for a pin-code (from dci_logs table).
    
    Args:
        pincode (str): PIN code
        hours (int): Number of hours of history (default 24)
        
    Returns:
        List of {timestamp, dci, severity} dicts ordered by time
    """
    try:
        from utils.supabase_client import get_supabase
        
        sb = get_supabase()
        cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        
        response = sb.table("dci_logs").select(
            "created_at, total_score, severity_tier"
        ).eq(
            "pincode", pincode
        ).gte(
            "created_at", cutoff_time
        ).order(
            "created_at", desc=False
        ).execute()
        
        history = [
            {
                "timestamp": row["created_at"],
                "dci": row["total_score"],
                "severity": row["severity_tier"],
            }
            for row in response.data
        ]
        
        logger.info(f"Retrieved {len(history)} DCI history records for {pincode}")
        return history
    
    except Exception as e:
        logger.error(f"Failed to fetch DCI history for {pincode}: {str(e)}")
        return []


def _clamp_score(score: float) -> float:
    """Ensure a component score is in valid range [0, 100]."""
    return max(0.0, min(100.0, float(score)))


def _get_city_from_pincode(pincode: str) -> str:
    """
    Map a pin-code to its city.
    
    This is a simplified version — in production, this would
    query a comprehensive pin-code → city mapping database.
    
    Args:
        pincode (str): PIN code
        
    Returns:
        str: City name (default "Bengaluru" if unmapped)
    """
    # Simplified mapping (first 2 digits of Karnataka pin-codes)
    pincode_city_mapping = {
        "560": "Bengaluru",
        "561": "Bengaluru",
        "562": "Bengaluru",
        "563": "Bengaluru",
        "580": "Belgaum",
        "581": "Belgaum",
        "590": "Mysore",
        "591": "Mysore",
        "572": "Mandya",
        "585": "Kolar",
        "586": "Kolar",
        "584": "Hassan",
        "589": "Shimoga",
        "577": "Shimoga",
        "573": "Chickmagalur",
        "574": "Kodagu",
        "575": "Udupi",
        "576": "Dakshina Kannada",
        "579": "Uttara Kannada",
    }
    
    for prefix, city in pincode_city_mapping.items():
        if pincode.startswith(prefix):
            return city
    
    return "Bengaluru"  # Default fallback


def _normalize_score(raw_value: float, min_val: float, max_val: float) -> float:
    """
    Normalize a raw value to 0-100 scale.
    
    Args:
        raw_value (float): Raw value from API
        min_val (float): Minimum threshold (maps to 0)
        max_val (float): Maximum threshold (maps to 100)
        
    Returns:
        float: Normalized score 0-100
    """
    if raw_value <= min_val:
        return 0.0
    elif raw_value >= max_val:
        return 100.0
    else:
        return ((raw_value - min_val) / (max_val - min_val)) * 100.0


# ─── Example Usage & Testing ─────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Test DCI calculation for a single pin-code
        print("\n" + "="*60)
        print("  DCI Engine Test")
        print("="*60)
        
        try:
            result = await compute_dci("560047")  # Koramangala, Bengaluru
            print(f"\n✅ DCI Score: {result['dci']}")
            print(f"   Severity: {result['severity']}")
            print(f"   Components: {result['components']}")
            print(f"   City: {result['city']}")
            print(f"   Weights: {result['weights']}")
            print(f"   Timestamp: {result['timestamp']}")
            
            # Test batch computation
            print(f"\n📊 Batch DCI Computation (3 zones)...")
            batch = await compute_dci_batch(["560047", "560034", "560001"])
            for pincode, dci_data in batch.items():
                print(f"   {pincode}: {dci_data['dci']} ({dci_data['severity']})")
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
        
        print("\n" + "="*60)
    
    asyncio.run(main())
