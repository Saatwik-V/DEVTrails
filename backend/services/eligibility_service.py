"""
services/eligibility_service.py
──────────────────────────────
Enforces strict policy and fraud eligibility rules before allowing a payout.
Uses Supabase for real worker and policy data (removed stubs).
"""

from datetime import datetime, timezone, timedelta
import logging
from config.settings import settings
from utils.db import get_supabase

logger = logging.getLogger("gigkavach.eligibility")


async def check_eligibility(worker_id: str, dci_event: dict) -> tuple[bool, str]:
    """
    Core gatekeeper function. Validates 4 strict rules before payout pipeline begins.
    Now queries Supabase for real worker data instead of using stubs.
    """
    try:
        sb = get_supabase()
        
        # RULE 1: Fetch active policy from Supabase
        policy_response = (
            sb.table("policies")
            .select("*")
            .eq("worker_id", worker_id)
            .eq("status", "active")
            .execute()
        )
        
        if not policy_response.data:
            return False, "NO_ACTIVE_POLICY"
        
        policy = policy_response.data[0]
        
        # Validate DCI event has timestamp
        disruption_time_str = dci_event.get("disruption_start") or dci_event.get("triggered_at")
        if not disruption_time_str:
            return False, "INVALID_DCI_EVENT"
        
        try:
            disruption_time = datetime.fromisoformat(disruption_time_str.replace('Z', '+00:00'))
        except:
            disruption_time = datetime.utcnow()
        
        # Get policy start date
        coverage_start_str = policy.get("week_start")
        if coverage_start_str:
            coverage_start = datetime.fromisoformat(coverage_start_str) if isinstance(coverage_start_str, str) else coverage_start_str
        else:
            coverage_start = datetime.utcnow()
        
        # RULE 2: 24-hr Coverage Delay Enforcement
        coverage_age = (disruption_time - coverage_start).total_seconds() / 3600.0
        min_delay = getattr(settings, 'COVERAGE_DELAY_HOURS', 24)
        
        if coverage_age < min_delay:
            return False, f"COVERAGE_DELAY_LOCK_{min_delay}H"
        
        # RULE 3: Get worker and check shift alignment
        worker_response = sb.table("workers").select("*").eq("id", worker_id).execute()
        if not worker_response.data:
            return False, "WORKER_NOT_FOUND"
        
        worker = worker_response.data[0]
        worker_shift = worker.get("shift", "flexible")
        
        # Check if disruption is within worker's shift window
        from utils.datetime_utils import is_within_shift
        if not is_within_shift(worker_shift, disruption_time):
            return False, f"SHIFT_MISMATCH_FOR_{worker_shift.upper()}"
        
        # RULE 4: Recent platform activity
        last_seen = worker.get("last_seen_at")
        if last_seen:
            try:
                last_seen_time = datetime.fromisoformat(last_seen.replace('Z', '+00:00')) if isinstance(last_seen, str) else last_seen
                time_since_active_hours = (disruption_time - last_seen_time).total_seconds() / 3600.0
            except:
                time_since_active_hours = 0
        else:
            time_since_active_hours = 0
        
        # Check for catastrophic override (high DCI or NDMA event)
        ndma_active = dci_event.get("ndma_override_active", False)
        dci_score = dci_event.get("dci_score", 0)
        catastrophic_threshold = getattr(settings, 'DCI_CATASTROPHIC_THRESHOLD', 75)
        is_catastrophic = (dci_score >= catastrophic_threshold) or ndma_active
        
        if not is_catastrophic and time_since_active_hours > 2.0:
            return False, "NO_RECENT_PLATFORM_ACTIVITY"
        
        return True, "ELIGIBLE_FOR_PAYOUT"
        
    except Exception as e:
        logger.error(f"[ELIGIBILITY] Error checking eligibility for {worker_id}: {e}")
        return False, f"ERROR_{str(e)[:30]}"
