"""
ml/earnings_fingerprint.py — Worker Baseline Earnings Calculation
──────────────────────────────────────────────────────────────────

The Earnings Fingerprint is GigKavach's model for computing a worker's expected
daily earnings baseline. It uses a rolling 4-week median per day-of-week, with:

  1. Disruption filtering (exclude days when DCI > 65)
  2. Festival week filtering (exclude known festival/holiday weeks)
  3. New worker blending (city-average → personal history over 4 weeks)
  4. Persistence to workers table for payout calculation

Key Design Principles:
  - Use MEDIAN not MEAN: Robust to outlier weeks (sick days, off-days)
  - Per-DAY-OF-WEEK median: Monday earnings ≠ Friday earnings
  - 4-week window: Yearly seasonal variations handled separately
  - Parametric nature preserved: Baselines inform payout fairness, not arbitrary

Usage:
    from ml.earnings_fingerprint import calculate_baseline
    baseline = calculate_baseline(worker_id="w_123")
    # Returns: {"monday": 750, "tuesday": 780, ..., "overall_daily_avg": 760}
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import numpy as np
import pandas as pd
from enum import Enum

# Local imports
try:
    from utils.supabase_client import get_supabase
except ImportError:
    # For testing purposes - allows unit tests to run without full env setup
    pass

logger = logging.getLogger("gigkavach.earnings_fingerprint")

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

DAYS_OF_WEEK = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
LOOKBACK_DAYS = 28  # 4 weeks
FESTIVAL_WEEKS = {
    # (month, week_number) of major Indian festivals/holidays
    # Week 1 = first 7 days of month, Week 4 = 22-28, etc.
    (1, 1),   # New Year
    (3, 2),   # Holi
    (4, 2),   # Ugadi (regional)
    (8, 2),   # Independence Day + monsoon peak
    (10, 4),  # Diwali season
    (12, 4),  # Christmas/New Year holidays
}

# New worker blending schedule
# Week N since registration → % of personal history vs city average
NEW_WORKER_BLEND_SCHEDULE = {
    1: (0.0, 1.0),    # Week 1: 0% personal, 100% city average
    2: (0.0, 1.0),    # Week 2: 0% personal, 100% city average
    3: (0.3, 0.7),    # Week 3: 30% personal, 70% city average
    4: (0.6, 0.4),    # Week 4: 60% personal, 40% city average
    5: (1.0, 0.0),    # Week 5+: 100% personal history
}

DCI_DISRUPTION_THRESHOLD = 65  # Exclude days when DCI > 65


# ─────────────────────────────────────────────────────────────────────────────
# Data Retrieval Functions
# ─────────────────────────────────────────────────────────────────────────────

def fetch_activity_log(
    worker_id: str,
    lookback_days: int = LOOKBACK_DAYS,
    supabase_client=None
) -> pd.DataFrame:
    """
    Fetch raw daily earnings activity for a worker from activity_log table.

    Args:
        worker_id: Unique worker identifier
        lookback_days: Number of days to look back (default 28 = 4 weeks)
        supabase_client: Optional Supabase client (for testing)

    Returns:
        DataFrame with columns:
            - date (YYYY-MM-DD)
            - daily_earnings (₹)
            - dci_score (0-100, from dci_events table)
            - platform (zomato/swiggy)
            - shift (morning/day/night/flexible)

    Returns empty DataFrame if worker has < 7 days of data.
    """
    try:
        sb = supabase_client or get_supabase()
        start_date = (datetime.utcnow() - timedelta(days=lookback_days)).date()

        # Fetch activity_log with joined DCI scores from dci_events
        response = sb.table("activity_log").select(
            "date, daily_earnings, dci_score, platform, shift"
        ).gte(
            "date", start_date.isoformat()
        ).eq(
            "worker_id", worker_id
        ).order(
            "date", desc=False
        ).execute()

        if not response.data:
            logger.warning(f"No activity data for worker {worker_id}")
            return pd.DataFrame()

        df = pd.DataFrame(response.data)
        df["date"] = pd.to_datetime(df["date"])
        return df

    except Exception as e:
        logger.error(f"Error fetching activity log for {worker_id}: {str(e)}")
        return pd.DataFrame()


def fetch_worker_metadata(
    worker_id: str,
    supabase_client=None
) -> Dict:
    """
    Fetch worker metadata needed for baseline calculation.

    Args:
        worker_id: Unique worker identifier
        supabase_client: Optional Supabase client (for testing)

    Returns:
        Dict with keys:
            - registration_date (ISO format string)
            - city (e.g., "Bengaluru")
            - segment (e.g., "food_delivery")
            - platform (zomato/swiggy)
            - shift (morning/day/night/flexible)
            - baseline_earnings (dict or None, if already calculated)

    Returns empty dict if worker not found.
    """
    try:
        sb = supabase_client or get_supabase()

        response = sb.table("workers").select(
            "id, registration_date, city, segment, platform, shift, baseline_earnings"
        ).eq(
            "id", worker_id
        ).single().execute()

        if not response.data:
            logger.warning(f"Worker {worker_id} not found")
            return {}

        return {
            "registration_date": response.data.get("registration_date"),
            "city": response.data.get("city"),
            "segment": response.data.get("segment"),
            "platform": response.data.get("platform"),
            "shift": response.data.get("shift"),
            "baseline_earnings": response.data.get("baseline_earnings"),
        }

    except Exception as e:
        logger.error(f"Error fetching worker metadata for {worker_id}: {str(e)}")
        return {}


def fetch_city_segment_average(
    city: str,
    segment: str = "food_delivery",
    supabase_client=None
) -> Dict:
    """
    Fetch the city-segment average baseline for new worker blending.

    Computes across all workers in the city who have 4+ weeks of unfiltered data.

    Args:
        city: City name (e.g., "Bengaluru")
        segment: Worker segment (default "food_delivery")
        supabase_client: Optional Supabase client (for testing)

    Returns:
        Dict with baseline per day-of-week:
            {"monday": 750, "tuesday": 780, ..., "overall_daily_avg": 765}

    Returns fallback average if no data available.
    """
    try:
        sb = supabase_client or get_supabase()

        # Fetch baseline_earnings for all workers in city (assumed pre-calculated)
        response = sb.table("workers").select(
            "baseline_earnings"
        ).eq(
            "city", city
        ).eq(
            "segment", segment
        ).execute()

        if not response.data:
            logger.warning(f"No baseline data available for {city}/{segment}")
            # Return fallback city average (based on platform analytics)
            return get_fallback_city_average(city)

        # Aggregate baselines across workers
        all_baselines = [w.get("baseline_earnings", {}) for w in response.data if w.get("baseline_earnings")]

        if not all_baselines:
            logger.warning(f"No valid baselines found for {city}/{segment}")
            return get_fallback_city_average(city)

        # Compute median baseline per day-of-week across all workers
        aggregated = {}
        for day in DAYS_OF_WEEK:
            values = [b.get(day, 0) for b in all_baselines if b.get(day)]
            if values:
                aggregated[day] = float(np.median(values))

        # Compute overall daily average
        all_values = [v for b in all_baselines for v in b.values() if isinstance(v, (int, float))]
        aggregated["overall_daily_avg"] = float(np.median(all_values)) if all_values else 0

        return aggregated

    except Exception as e:
        logger.error(f"Error fetching city segment average for {city}/{segment}: {str(e)}")
        return get_fallback_city_average(city)


def get_fallback_city_average(city: str) -> Dict:
    """
    Fallback city-level earnings averages (based on platform data).
    Used when insufficient baseline data exists.

    Returns:
        Dict with estimated daily earnings by day-of-week.
    """
    # These are reasonable estimates for Indian cities
    # In production, these would come from Zomato/Swiggy analytics
    city_averages = {
        "bengaluru": {"monday": 650, "tuesday": 680, "wednesday": 700, "thursday": 720,
                      "friday": 780, "saturday": 850, "sunday": 820, "overall_daily_avg": 743},
        "mumbai": {"monday": 700, "tuesday": 750, "wednesday": 780, "thursday": 800,
                   "friday": 850, "saturday": 900, "sunday": 880, "overall_daily_avg": 807},
        "delhi": {"monday": 600, "tuesday": 630, "wednesday": 660, "thursday": 690,
                  "friday": 750, "saturday": 820, "sunday": 790, "overall_daily_avg": 704},
        "chennai": {"monday": 550, "tuesday": 580, "wednesday": 610, "thursday": 640,
                    "friday": 700, "saturday": 770, "sunday": 740, "overall_daily_avg": 656},
        "default": {"monday": 650, "tuesday": 675, "wednesday": 700, "thursday": 725,
                    "friday": 775, "saturday": 825, "sunday": 800, "overall_daily_avg": 736},
    }
    return city_averages.get(city.lower(), city_averages["default"])


# ─────────────────────────────────────────────────────────────────────────────
# Processing Functions
# ─────────────────────────────────────────────────────────────────────────────

def is_festival_week(date_obj) -> bool:
    """
    Check if a date falls within a festival/holiday week.

    Festival weeks have elevated earnings (surge), so they're excluded from
    the baseline to avoid skewing the normal earnings expectation.

    Args:
        date_obj: datetime object or string (YYYY-MM-DD format)

    Returns:
        True if date is in a festival week, False otherwise
    """
    # Handle both datetime objects and strings
    if isinstance(date_obj, str):
        date_obj = pd.to_datetime(date_obj)
    elif not isinstance(date_obj, (datetime, pd.Timestamp)):
        return False

    month = date_obj.month
    day = date_obj.day
    week_of_month = (day - 1) // 7 + 1  # Week 1-4

    return (month, week_of_month) in FESTIVAL_WEEKS


def is_disruption_day(dci_score: Optional[float]) -> bool:
    """
    Check if a day should be excluded due to disruption.

    Disruption days (DCI > 65) reflect crisis earnings patterns, not normal
    baseline expectation. They're filtered out to maintain fairness.

    Args:
        dci_score: DCI score (0-100) or None

    Returns:
        True if day had significant disruption (DCI > 65), False otherwise
    """
    if dci_score is None:
        return False
    return dci_score > DCI_DISRUPTION_THRESHOLD


def filter_activity_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter activity data to exclude:
      1. Disruption days (DCI > 65)
      2. Festival weeks
      3. Days with zero or suspicious earnings

    Args:
        df: DataFrame with columns [date, daily_earnings, dci_score, ...]

    Returns:
        Filtered DataFrame ready for median calculation
    """
    if df.empty:
        return df

    # Create copy to avoid modifying original
    df = df.copy()

    # Ensure date column is datetime
    df["date"] = pd.to_datetime(df["date"])

    # Remove disruption days (DCI > 65)
    initial_count = len(df)
    df = df[~df["dci_score"].apply(is_disruption_day)]
    logger.debug(f"Removed {initial_count - len(df)} disruption days")

    # Remove festival weeks
    df["is_festival"] = df["date"].apply(is_festival_week)
    festival_count = df["is_festival"].sum()
    df = df[~df["is_festival"]]
    df = df.drop("is_festival", axis=1)
    logger.debug(f"Removed {festival_count} festival days")

    # Remove zero earnings (indicates off-day, not working that day)
    df = df[df["daily_earnings"] > 0]

    # Remove outliers (extremely high earnings on single unusual day)
    # Keep values within IQR * 1.5, but cap at 2x median
    if len(df) > 0:
        q1 = df["daily_earnings"].quantile(0.25)
        q3 = df["daily_earnings"].quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        df = df[(df["daily_earnings"] >= lower_bound) & (df["daily_earnings"] <= upper_bound)]

    logger.debug(f"Filtered activity data: {len(df)} days remaining")
    return df


def calculate_rolling_median_per_dow(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate the rolling 4-week median earnings for each day-of-week.

    Args:
        df: Filtered DataFrame with columns [date, daily_earnings]

    Returns:
        Dict mapping day-of-week → median earnings (₹)
        Example: {"monday": 750, "tuesday": 780, ..., "overall_daily_avg": 765}

    Returns dict with 0 values if insufficient data.
    """
    if df.empty:
        logger.warning("Cannot calculate median: empty activity data")
        return {day: 0 for day in DAYS_OF_WEEK} | {"overall_daily_avg": 0}

    # Create working copy
    df_work = df.copy()

    # Ensure date column is datetime
    df_work["date"] = pd.to_datetime(df_work["date"])
    # day_name() returns full name (Monday, Tuesday, etc.)
    df_work["day_of_week"] = df_work["date"].dt.day_name().str.lower()

    baseline = {}

    # Calculate median per day-of-week
    for day in DAYS_OF_WEEK:
        day_data = df_work[df_work["day_of_week"] == day]["daily_earnings"]

        if len(day_data) == 0:
            baseline[day] = 0  # No data for this day
        else:
            baseline[day] = float(np.median(day_data.values))

    # Calculate overall daily average (median across all days)
    if len(df_work) > 0:
        baseline["overall_daily_avg"] = float(np.median(df_work["daily_earnings"].values))
    else:
        baseline["overall_daily_avg"] = 0

    logger.info(f"Calculated baseline: {baseline}")
    return baseline


def blend_baselines_for_new_worker(
    weeks_since_registration: int,
    personal_baseline: Dict[str, float],
    city_average: Dict[str, float],
) -> Dict[str, float]:
    """
    Blend personal and city-average baselines for new workers.

    Transition schedule:
      Week 1-2: 100% city average (worker too new to have reliable data)
      Week 3: 30% personal, 70% city
      Week 4: 60% personal, 40% city
      Week 5+: 100% personal

    Args:
        weeks_since_registration: Number of weeks since worker registered
        personal_baseline: Personal earnings baseline per day-of-week
        city_average: City-average earnings baseline per day-of-week

    Returns:
        Blended baseline dict
    """
    # Cap weeks at 5 (blend weights max out at 100% personal)
    week = min(weeks_since_registration, 5)

    # Get blend weights for this week
    if week in NEW_WORKER_BLEND_SCHEDULE:
        personal_weight, city_weight = NEW_WORKER_BLEND_SCHEDULE[week]
    else:
        # Default to 100% personal for week 5+
        personal_weight, city_weight = 1.0, 0.0

    # Blend each day-of-week and overall average
    blended = {}
    for key in DAYS_OF_WEEK + ["overall_daily_avg"]:
        personal_val = personal_baseline.get(key, 0)
        city_val = city_average.get(key, 0)

        blended[key] = (personal_val * personal_weight) + (city_val * city_weight)

    logger.info(
        f"Blended baseline for week {week}: "
        f"{personal_weight*100:.0f}% personal, {city_weight*100:.0f}% city"
    )
    return blended


def get_weeks_since_registration(registration_date: str) -> int:
    """
    Calculate weeks since worker registration.

    Args:
        registration_date: ISO format date string (YYYY-MM-DD)

    Returns:
        Number of complete weeks since registration (1-4+)
    """
    if not registration_date:
        return 0

    reg_date = pd.to_datetime(registration_date).date()
    today = datetime.utcnow().date()
    days_diff = (today - reg_date).days

    # Return number of weeks (minimum 1, even if same day)
    if days_diff < 0:
        return 1
    return max(1, (days_diff // 7) + 1)


# ─────────────────────────────────────────────────────────────────────────────
# Main Baseline Calculation Function
# ─────────────────────────────────────────────────────────────────────────────

def calculate_baseline(
    worker_id: str,
    supabase_client=None,
    use_city_average_fallback: bool = True,
) -> Dict[str, float]:
    """
    Calculate and return a worker's baseline earnings.

    Main entry point for baseline calculation. Handles:
      1. Data fetching (activity log, worker metadata)
      2. Filtering (disruptions, festivals, outliers)
      3. Median calculation per day-of-week
      4. New worker blending (if < 4 weeks registered)

    Args:
        worker_id: Unique worker identifier
        supabase_client: Optional Supabase client (for testing)
        use_city_average_fallback: Use city average if insufficient personal data

    Returns:
        Dict mapping day-of-week to baseline earnings (₹):
            {
                "monday": 750,
                "tuesday": 780,
                "wednesday": 800,
                "thursday": 820,
                "friday": 880,
                "saturday": 920,
                "sunday": 900,
                "overall_daily_avg": 835
            }
    """
    logger.info(f"Calculating baseline for worker {worker_id}")

    # Step 1: Fetch activity log and worker metadata
    activity_df = fetch_activity_log(worker_id, supabase_client=supabase_client)
    metadata = fetch_worker_metadata(worker_id, supabase_client=supabase_client)

    if not metadata:
        logger.error(f"Cannot calculate baseline: worker {worker_id} not found")
        return {day: 0 for day in DAYS_OF_WEEK} | {"overall_daily_avg": 0}

    # Step 2: Filter activity data
    filtered_df = filter_activity_data(activity_df)

    # Step 3: Calculate personal baseline
    personal_baseline = calculate_rolling_median_per_dow(filtered_df)

    # Step 4: Check if worker is new (< 4 weeks) and blend with city average
    weeks_since_reg = get_weeks_since_registration(metadata.get("registration_date"))

    if weeks_since_reg < 5:
        # Worker is still in blending period
        city_avg = fetch_city_segment_average(
            metadata.get("city", "Bengaluru"),
            metadata.get("segment", "food_delivery"),
            supabase_client=supabase_client,
        )

        final_baseline = blend_baselines_for_new_worker(
            weeks_since_reg,
            personal_baseline,
            city_avg,
        )
    else:
        # Worker has 4+ weeks: use 100% personal baseline
        final_baseline = personal_baseline

    logger.info(f"Final baseline for {worker_id}: {final_baseline}")
    return final_baseline


# ─────────────────────────────────────────────────────────────────────────────
# Database Persistence
# ─────────────────────────────────────────────────────────────────────────────

def save_baseline_to_workers_table(
    worker_id: str,
    baseline: Dict[str, float],
    supabase_client=None,
) -> bool:
    """
    Save calculated baseline to the workers table.

    Updates the 'baseline_earnings' column with the computed baseline dict.
    This baseline is then used by payout_service.py for payout calculation.

    Args:
        worker_id: Unique worker identifier
        baseline: Baseline dict from calculate_baseline()
        supabase_client: Optional Supabase client (for testing)

    Returns:
        True if save successful, False otherwise
    """
    try:
        sb = supabase_client or get_supabase()

        response = sb.table("workers").update(
            {
                "baseline_earnings": baseline,
                "baseline_updated_at": datetime.utcnow().isoformat(),
            }
        ).eq(
            "id", worker_id
        ).execute()

        if response.data:
            logger.info(f"Saved baseline for worker {worker_id}")
            return True
        else:
            logger.error(f"Failed to save baseline: no response data")
            return False

    except Exception as e:
        logger.error(f"Error saving baseline for {worker_id}: {str(e)}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Orchestration Function
# ─────────────────────────────────────────────────────────────────────────────

def compute_and_persist_baseline(
    worker_id: str,
    supabase_client=None,
) -> Tuple[bool, Dict[str, float]]:
    """
    Complete workflow: calculate baseline and save to database.

    Args:
        worker_id: Unique worker identifier
        supabase_client: Optional Supabase client (for testing)

    Returns:
        Tuple of (success: bool, baseline: dict)
        - success: True if calculation and save both succeeded
        - baseline: The computed baseline (empty dict if failed)
    """
    try:
        # Calculate baseline
        baseline = calculate_baseline(worker_id, supabase_client=supabase_client)

        # Save to database
        saved = save_baseline_to_workers_table(worker_id, baseline, supabase_client=supabase_client)

        return saved, baseline

    except Exception as e:
        logger.error(f"Error in compute_and_persist_baseline for {worker_id}: {str(e)}")
        return False, {}
