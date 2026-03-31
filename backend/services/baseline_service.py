"""
services/baseline_service.py — Worker Baseline Earnings Service
──────────────────────────────────────────────────────────────────
Determines a worker's baseline daily earnings for payout calculation.

Strategy (in priority order):
  1. 4-week rolling median from activity_log table (most accurate)
  2. Plan-based fallback defaults (when no history exists yet)

This is used by:
  - payout_service.calculate_payout() to seed baseline_earnings
  - settlement_service.run_daily_settlement() for new claim creation
  - claims_trigger.py when a claim is auto-created from DCI trigger

Baseline fallbacks by plan tier (conservative estimates):
  basic → ₹800/day
  plus  → ₹1100/day
  pro   → ₹1500/day
"""

import logging
from typing import Optional
import statistics

logger = logging.getLogger("gigkavach.baseline_service")

# ─── Fallback Defaults (used when no activity_log history exists) ─────────────
PLAN_BASELINE_DEFAULTS = {
    "basic":   800.0,
    "plus":    1100.0,
    "pro":     1500.0,
    # Legacy plan names (for backward compatibility)
    "shield basic": 800.0,
    "shield plus":  1100.0,
    "shield pro":   1500.0,
}

# ─── How many weeks of history to aggregate ───────────────────────────────────
BASELINE_LOOKBACK_WEEKS = 4


def get_worker_baseline(worker_id: str, plan: str = "basic") -> float:
    """
    Returns the worker's daily baseline earnings (₹).

    Fetches 4-week rolling median from activity_log if available.
    Falls back to plan-tier defaults otherwise.

    Args:
        worker_id: UUID string of the worker
        plan:      Worker's current plan tier ('basic'|'plus'|'pro')

    Returns:
        float: daily baseline earnings in ₹
    """
    try:
        from utils.supabase_client import get_supabase
        sb = get_supabase()

        if not sb:
            logger.warning(f"[BASELINE] Supabase unavailable for worker {worker_id}. Using plan default.")
            return _get_plan_default(plan)

        # Query 4 weeks of daily estimated_earnings from activity_log
        from datetime import datetime, timedelta, timezone
        cutoff = (datetime.now(timezone.utc) - timedelta(weeks=BASELINE_LOOKBACK_WEEKS)).isoformat()

        response = sb.table("activity_log") \
            .select("estimated_earnings") \
            .eq("worker_id", worker_id) \
            .gte("log_date", cutoff) \
            .order("log_date", desc=True) \
            .limit(BASELINE_LOOKBACK_WEEKS * 7) \
            .execute()

        rows = response.data if response.data else []

        # Filter rows where the worker was actually active
        earnings_values = [
            float(r["estimated_earnings"])
            for r in rows
            if r.get("estimated_earnings", 0) > 0
        ]

        if len(earnings_values) < 3:
            # Not enough data — fall back to plan default
            logger.info(
                f"[BASELINE] worker={worker_id}: only {len(earnings_values)} data points. "
                f"Using plan '{plan}' default."
            )
            return _get_plan_default(plan)

        # 4-week rolling median (more robust than mean to outlier days)
        baseline = statistics.median(earnings_values)
        logger.info(f"[BASELINE] worker={worker_id}: computed median ₹{baseline:.0f} from {len(earnings_values)} records")
        return round(baseline, 2)

    except Exception as e:
        logger.error(f"[BASELINE] Error fetching baseline for worker {worker_id}: {e}")
        return _get_plan_default(plan)


def _get_plan_default(plan: str) -> float:
    """
    Returns the conservative plan-based baseline fallback.
    Used when Supabase is unreachable or history is insufficient.

    Args:
        plan: plan tier string

    Returns:
        float: daily earnings baseline in ₹
    """
    key = plan.lower() if plan else "basic"
    default = PLAN_BASELINE_DEFAULTS.get(key, 800.0)
    logger.debug(f"[BASELINE] Using plan default for '{key}': ₹{default}")
    return default


def get_baseline_batch(worker_ids: list[str]) -> dict[str, float]:
    """
    Fetches baselines for multiple workers in one call.
    Useful for the settlement service to avoid N+1 Supabase queries.

    Args:
        worker_ids: list of worker UUID strings

    Returns:
        dict mapping worker_id → daily baseline float
    """
    results = {}
    for wid in worker_ids:
        results[wid] = get_worker_baseline(wid)
    return results
