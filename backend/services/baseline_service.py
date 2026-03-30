"""
services/baseline_service.py — Earnings Baseline Calculation (Earnings Fingerprint)
────────────────────────────────────────────────────────────────────────────────────

The Earnings Baseline (Fingerprint) is the expected daily earnings for a worker.
It's used by the payout formula:

  Payout = Baseline × (Disruption Duration / 480 min) × XGBoost Multiplier

Calculation Logic:
  1. Fetch worker's 4-week activity log (disruption days excluded)
  2. Group by day-of-week (Monday earnings ≠ Friday earnings)
  3. Compute rolling 4-week median per day-of-week (robust to outliers)
  4. Filter out festival/holiday weeks
  5. For NEW workers: Blend city-average baseline with personal 4-week history
     - Week 1-2: 100% city average
     - Week 3: 30% personal + 70% city
     - Week 4: 60% personal + 40% city
     - Week 5+: 100% personal baseline
  6. Persist to workers table for quick payout calculation

Design Principles:
  - Use MEDIAN not MEAN: Robust to outlier weeks (sick day, injury, off-day)
  - Per-DAY-OF-WEEK: Workers have different earning patterns by day
  - 4-week window: Captures weekly cycles; yearly seasonality handled separately
  - Festival exclusion: Prevent festival week anomalies from inflating baseline

Usage:
    from services.baseline_service import calculate_baseline, get_baseline
    
    # Calculate fresh baseline for worker
    baseline = await calculate_baseline(worker_id="w_123")
    # Returns: {"monday": 750, "tuesday": 780, ..., "overall_daily_avg": 760}
    
    # Get cached baseline from workers table
    baseline = await get_baseline(worker_id="w_123")
    # Returns same structure (no recalculation)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import pandas as pd
import numpy as np

from config.settings import settings
from utils.supabase_client import get_supabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("gigkavach.baseline_service")


# ─── Constants ────────────────────────────────────────────────────────────────

DAYS_OF_WEEK = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
LOOKBACK_DAYS = 28  # 4-week window for median calculation
FESTIVAL_WEEKS = [
    # (month, week_of_month) tuples for major Indian festivals/holidays
    (1, 1),   # New Year
    (3, 2),   # Holi
    (4, 2),   # Ugadi/Gudi Padwa
    (8, 2),   # Independence Day + monsoon peak
    (10, 4),  # Diwali season
    (12, 4),  # Christmas/New Year holidays
]

# New worker blending schedule (week since registration → (personal%, city_avg%))
NEW_WORKER_BLEND_SCHEDULE = {
    1: (0.0, 1.0),    # Week 1: Pure city average
    2: (0.0, 1.0),    # Week 2: Pure city average
    3: (0.3, 0.7),    # Week 3: 30% personal, 70% city
    4: (0.6, 0.4),    # Week 4: 60% personal, 40% city
    5: (1.0, 0.0),    # Week 5+: Pure personal baseline
}

# City-level baseline earnings (INR per day) — used for new workers
CITY_BASELINE_EARNINGS = {
    "Mumbai": 850,
    "Delhi": 780,
    "Chennai": 720,
    "Bengaluru": 780,
    "Pune": 750,
    "Hyderabad": 720,
}

# DCI threshold — days with DCI > 65 are excluded from baseline calculation
DCI_DISRUPTION_THRESHOLD = settings.DCI_TRIGGER_THRESHOLD  # 65

# Minimum data points required for baseline calculation
MIN_DATA_POINTS_FOR_BASELINE = 7  # At least 1 week of data


class BaselineCalculationError(Exception):
    """Raised when baseline calculation fails."""
    pass


async def calculate_baseline(
    worker_id: str,
    supabase_client=None,
    force_recalculate: bool = False,
) -> Dict[str, float]:
    """
    Calculate or update a worker's earnings baseline.
    
    This function:
    1. Fetches 4-week activity log from activity_log table
    2. Filters out disruption days (DCI > 65) and festival weeks
    3. Groups by day-of-week and computes rolling 4-week median
    4. Blends with city average for workers with < 4 weeks data
    5. Computes overall daily average
    6. Persists to workers table for payout engine
    
    Args:
        worker_id (str): Unique worker ID
        supabase_client: Optional Supabase client (for testing)
        force_recalculate (bool): Recalculate even if cached (default False)
        
    Returns:
        Dict with structure:
        {
            "monday": 750,
            "tuesday": 780,
            ...
            "sunday": 650,
            "overall_daily_avg": 760,
            "data_days": 18,  # Number of days used in calculation
            "weeks_active": 3.2,  # Weeks of data
            "blending_applied": False,  # True if city average blended
            "blending_pct_personal": 0.0,  # Percentage personal vs city
            "timestamp": "2026-03-30T18:45:00Z",
        }
        
    Raises:
        BaselineCalculationError: If calculation fails or insufficient data
    """
    
    try:
        logger.info(f"Calculating baseline for worker {worker_id}")
        
        # ─── STEP 1: Check if baseline already cached in workers table ────────
        # (unless force_recalculate is True)
        
        if not force_recalculate:
            cached = await get_baseline(worker_id, supabase_client)
            if cached:
                logger.info(f"Baseline cache HIT for {worker_id}")
                cached["from_cache"] = True
                return cached
        
        sb = supabase_client or get_supabase()
        
        # ─── STEP 2: Fetch worker metadata ────────────────────────────────────
        
        worker_response = sb.table("workers").select("*").eq("id", worker_id).execute()
        if not worker_response.data:
            raise BaselineCalculationError(f"Worker {worker_id} not found")
        
        worker = worker_response.data[0]
        worker_created_at = datetime.fromisoformat(worker["created_at"])
        weeks_since_registration = (
            (datetime.now(timezone.utc) - worker_created_at).days / 7.0
        )
        
        logger.debug(f"Worker registered {weeks_since_registration:.1f} weeks ago")
        
        # ─── STEP 3: Fetch Activity Log (4 weeks) ────────────────────────────
        
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).date()
        
        activity_response = sb.table("activity_log").select(
            "log_date, estimated_earnings"
        ).eq(
            "worker_id", worker_id
        ).gte(
            "log_date", cutoff_date.isoformat()
        ).order(
            "log_date", desc=False
        ).execute()
        
        if not activity_response.data:
            logger.warning(f"No activity data for {worker_id} — using city average baseline")
            return _get_city_average_baseline(
                worker.get("created_at", ""),
                worker.get("shift", "morning"),
            )
        
        # ─── STEP 4: Prepare DataFrame ───────────────────────────────────────
        
        df = pd.DataFrame(activity_response.data)
        df["log_date"] = pd.to_datetime(df["log_date"])
        df["earnings"] = df["estimated_earnings"].astype(float)
        df["day_of_week"] = df["log_date"].dt.day_name().str.lower()
        df["date_only"] = df["log_date"].dt.date
        
        logger.debug(f"Loaded {len(df)} activity records for {worker_id}")
        
        # ─── STEP 5: Filter Out Disruption Days (DCI > 65) ───────────────────
        
        # Fetch DCI logs for the same period
        dci_response = sb.table("dci_logs").select(
            "created_at, total_score"
        ).gte(
            "created_at", cutoff_date.isoformat()
        ).execute()
        
        dci_data = pd.DataFrame(dci_response.data) if dci_response.data else pd.DataFrame()
        
        if not dci_data.empty:
            dci_data["created_at"] = pd.to_datetime(dci_data["created_at"])
            dci_data["date_only"] = dci_data["created_at"].dt.date
            
            # Mark disruption days (max DCI per day >= THRESHOLD)
            disruption_dates = dci_data[
                dci_data["total_score"] >= DCI_DISRUPTION_THRESHOLD
            ]["date_only"].unique()
            
            initial_count = len(df)
            df = df[~df["date_only"].isin(disruption_dates)]
            filtered_out = initial_count - len(df)
            
            logger.debug(f"Filtered out {filtered_out} disruption days (DCI >= {DCI_DISRUPTION_THRESHOLD})")
        
        # ─── STEP 6: Filter Out Festival Weeks ────────────────────────────────
        
        def is_festival_week(date: datetime) -> bool:
            """Check if date falls in a festival week."""
            month = date.month
            week_of_month = (date.day - 1) // 7 + 1
            return (month, week_of_month) in FESTIVAL_WEEKS
        
        initial_count = len(df)
        df = df[~df["log_date"].apply(is_festival_week)]
        filtered_out = initial_count - len(df)
        logger.debug(f"Filtered out {filtered_out} festival week records")
        
        # ─── STEP 7: Check Minimum Data Requirement ──────────────────────────
        
        if len(df) < MIN_DATA_POINTS_FOR_BASELINE:
            logger.warning(
                f"Insufficient data ({len(df)} days) for {worker_id} — "
                f"using blended city average"
            )
            return _get_blended_baseline(
                worker_id,
                weeks_since_registration,
                df,  # Use partial data for blending
                worker.get("shift", "morning"),
            )
        
        # ─── STEP 8: Compute Median Per Day-of-Week ──────────────────────────
        
        day_baselines = {}
        for day in DAYS_OF_WEEK:
            day_data = df[df["day_of_week"] == day]["earnings"]
            
            if len(day_data) > 0:
                # Use median for robustness (immune to outliers)
                median_earning = day_data.median()
                day_baselines[day] = float(median_earning)
                logger.debug(f"  {day.title()}: ₹{median_earning:.0f} (n={len(day_data)} records)")
            else:
                # If no data for this day, use overall median as fallback
                day_baselines[day] = float(df["earnings"].median())
        
        # ─── STEP 9: Compute Overall Daily Average ───────────────────────────
        
        overall_avg = np.mean(list(day_baselines.values()))
        
        # ─── STEP 10: Blending for New Workers ───────────────────────────────
        
        blending_applied = False
        blending_pct_personal = 1.0
        
        if weeks_since_registration < 5:  # Blend if less than 5 weeks active
            personal_pct, city_pct = NEW_WORKER_BLEND_SCHEDULE.get(
                int(weeks_since_registration), (1.0, 0.0)
            )
            
            if city_pct > 0:
                blending_applied = True
                blending_pct_personal = personal_pct
                
                # Get city average baseline
                city_avg = CITY_BASELINE_EARNINGS.get(
                    worker.get("city", "Bengaluru"), 750
                )
                
                # Blend personal baseline with city average
                for day in DAYS_OF_WEEK:
                    day_baselines[day] = (
                        day_baselines[day] * personal_pct +
                        city_avg * city_pct
                    )
                
                overall_avg = np.mean(list(day_baselines.values()))
                
                logger.info(
                    f"Blending applied for {worker_id} (week {weeks_since_registration:.1f}): "
                    f"{personal_pct:.0%} personal + {city_pct:.0%} city average"
                )
        
        # ─── STEP 11: Round to nearest ₹10 ──────────────────────────────────
        
        for day in day_baselines:
            day_baselines[day] = round(day_baselines[day] / 10) * 10
        
        overall_avg = round(overall_avg / 10) * 10
        
        # ─── STEP 12: Build Result ──────────────────────────────────────────
        
        result = {
            **day_baselines,
            "overall_daily_avg": float(overall_avg),
            "data_days": len(df),
            "weeks_active": len(df) / 7.0,
            "blending_applied": blending_applied,
            "blending_pct_personal": blending_pct_personal,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "from_cache": False,
        }
        
        # ─── STEP 13: Persist to workers Table ───────────────────────────────
        
        try:
            # Store as JSON string
            baseline_json = {k: v for k, v in result.items() if k not in ["timestamp", "from_cache"]}
            
            sb.table("workers").update({
                "earnings_baseline": baseline_json,
                "baseline_updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", worker_id).execute()
            
            logger.info(f"✅ Baseline persisted for {worker_id}: ₹{overall_avg:.0f}/day")
        
        except Exception as e:
            logger.warning(f"Failed to persist baseline for {worker_id}: {e}")
            # Don't fail entirely — still return result
        
        return result
    
    except Exception as e:
        logger.error(f"❌ Baseline calculation failed for {worker_id}: {str(e)}")
        raise BaselineCalculationError(f"Baseline calculation failed: {str(e)}")


async def get_baseline(
    worker_id: str,
    supabase_client=None,
) -> Optional[Dict[str, float]]:
    """
    Retrieve cached baseline from workers table (no recalculation).
    
    Args:
        worker_id (str): Worker ID
        supabase_client: Optional Supabase client
        
    Returns:
        Dict with baseline structure, or None if not found/invalid
    """
    try:
        sb = supabase_client or get_supabase()
        
        response = sb.table("workers").select(
            "earnings_baseline, baseline_updated_at"
        ).eq(
            "id", worker_id
        ).execute()
        
        if not response.data:
            logger.debug(f"No cached baseline for {worker_id}")
            return None
        
        baseline = response.data[0].get("earnings_baseline")
        if not baseline:
            logger.debug(f"Baseline is null for {worker_id}")
            return None
        
        # Add metadata
        baseline_dict = baseline if isinstance(baseline, dict) else {}
        baseline_dict["timestamp"] = response.data[0].get("baseline_updated_at", "")
        baseline_dict["from_cache"] = True
        
        logger.debug(f"Baseline cache HIT for {worker_id}")
        return baseline_dict
    
    except Exception as e:
        logger.warning(f"Failed to fetch cached baseline for {worker_id}: {e}")
        return None


def _get_city_average_baseline(
    created_at_str: str,
    shift: str,
    city: str = "Bengaluru",
) -> Dict[str, float]:
    """
    Return city-level average baseline for new workers with no activity data.
    
    Args:
        created_at_str: Worker creation timestamp
        shift: Worker shift (for future shift-specific baselines)
        city: City name
        
    Returns:
        Dict with baseline structure
    """
    city_avg = CITY_BASELINE_EARNINGS.get(city, 750)
    
    return {
        **{day: city_avg for day in DAYS_OF_WEEK},
        "overall_daily_avg": float(city_avg),
        "data_days": 0,
        "weeks_active": 0.0,
        "blending_applied": True,  # Entire baseline is city average
        "blending_pct_personal": 0.0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "from_cache": False,
        "note": "City average baseline (no personal data)",
    }


def _get_blended_baseline(
    worker_id: str,
    weeks_since_registration: float,
    partial_df: pd.DataFrame,
    shift: str,
    city: str = "Bengaluru",
) -> Dict[str, float]:
    """
    Create baseline with city average blended with partial personal data.
    
    Args:
        worker_id: Worker ID (for logging)
        weeks_since_registration: Weeks active
        partial_df: Partial activity dataframe
        shift: Worker shift
        city: City name
        
    Returns:
        Dict with blended baseline
    """
    city_avg = CITY_BASELINE_EARNINGS.get(city, 750)
    personal_pct, city_pct = NEW_WORKER_BLEND_SCHEDULE.get(
        int(weeks_since_registration), (0.0, 1.0)
    )
    
    # Compute personal baseline from partial data
    day_baselines = {}
    for day in DAYS_OF_WEEK:
        if not partial_df.empty:
            day_data = partial_df[partial_df["day_of_week"] == day]["earnings"]
            personal_baseline = float(day_data.median()) if len(day_data) > 0 else city_avg
        else:
            personal_baseline = city_avg
        
        # Blend
        day_baselines[day] = personal_baseline * personal_pct + city_avg * city_pct
    
    overall_avg = np.mean(list(day_baselines.values()))
    
    # Round to nearest ₹10
    for day in day_baselines:
        day_baselines[day] = round(day_baselines[day] / 10) * 10
    
    overall_avg = round(overall_avg / 10) * 10
    
    return {
        **day_baselines,
        "overall_daily_avg": float(overall_avg),
        "data_days": len(partial_df),
        "weeks_active": weeks_since_registration,
        "blending_applied": True,
        "blending_pct_personal": personal_pct,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "from_cache": False,
        "note": f"Blended baseline (week {weeks_since_registration:.1f})",
    }


# ─── Example Usage & Testing ───────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio
    
    async def main():
        print("\n" + "="*60)
        print("  Earnings Baseline Service Test")
        print("="*60)
        
        # Example worker ID (would need to exist in database)
        worker_id = "test_worker_001"
        
        try:
            # Calculate baseline
            baseline = await calculate_baseline(worker_id)
            
            print(f"\n✅ Baseline Calculated:")
            print(f"   Monday: ₹{baseline['monday']}")
            print(f"   Tuesday: ₹{baseline['tuesday']}")
            print(f"   Wednesday: ₹{baseline['wednesday']}")
            print(f"   Thursday: ₹{baseline['thursday']}")
            print(f"   Friday: ₹{baseline['friday']}")
            print(f"   Saturday: ₹{baseline['saturday']}")
            print(f"   Sunday: ₹{baseline['sunday']}")
            print(f"   ---")
            print(f"   Overall Daily Average: ₹{baseline['overall_daily_avg']}")
            print(f"   Data Days: {baseline['data_days']}")
            print(f"   Weeks Active: {baseline['weeks_active']:.1f}")
            print(f"   Blending Applied: {baseline['blending_applied']}")
            if baseline['blending_applied']:
                print(f"   Blending %: {baseline['blending_pct_personal']:.0%} personal + {(1-baseline['blending_pct_personal']):.0%} city")
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
        
        print("\n" + "="*60)
    
    asyncio.run(main())
