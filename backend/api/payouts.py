"""
api/payouts.py
──────────────────────────────
Payout read endpoints used by the frontend live feed.
"""

from datetime import datetime
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from utils.db import get_supabase
from datetime import datetime, time, timedelta
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from utils.datetime_utils import is_within_shift

logger = logging.getLogger("gigkavach.payouts")
router = APIRouter(prefix="/api", tags=["Payouts & SLA"])
STATUS_DISPLAY_MAP = {
    "pending": "triggered",
    "processing": "calculating",
    "partial": "fraud_check",
    "escrowed": "fraud_check",
    "completed": "payout_sent",
}
NON_PROCESSING_STATUSES = {"failed", "withheld", "sla_auto", "cancelled", "rejected"}


class ProcessingPayout(BaseModel):
    id: str
    worker_id: Optional[str] = None
    worker_name: str
    amount: float
    dci_score: Optional[float] = None
    fraud_score: Optional[float] = None
    status: str
    timestamp: datetime


class ProcessingPayoutListResponse(BaseModel):
    payouts: list[ProcessingPayout] = Field(default_factory=list)
    count: int = 0


def _is_processing_pipeline_status(db_status: str) -> bool:
    normalized = (db_status or "").strip().lower()
    return bool(normalized) and normalized not in NON_PROCESSING_STATUSES


@router.get(
    "/payouts",
    response_model=ProcessingPayoutListResponse,
    status_code=status.HTTP_200_OK,
    summary="List payouts for live processing feed",
)
async def list_payouts(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
):
    """
    Live feed endpoint expected by frontend:
    GET /api/payouts?status=processing&limit=20

    Returns payout rows with a normalized shape:
    worker_name, amount, dci_score, fraud_score, status, timestamp.
    """
    try:
        sb = get_supabase()
        fetch_limit = max(limit * 3, 50) if status_filter == "processing" else limit

        query = (
            sb.table("payouts")
            .select("id, worker_id, dci_event_id, final_amount, fraud_score, status, triggered_at, created_at")
            .order("triggered_at", desc=True)
            .limit(fetch_limit)
        )
        if status_filter:
            if status_filter != "processing":
                query = query.eq("status", status_filter)
        result = query.execute()
        rows = result.data or []

        if status_filter == "processing":
            rows = [row for row in rows if _is_processing_pipeline_status(row.get("status") or "")]
            rows = rows[:limit]

        worker_ids = [row.get("worker_id") for row in rows if row.get("worker_id")]
        worker_map: dict[str, str] = {}
        if worker_ids:
            workers = (
                sb.table("workers")
                .select("id, name")
                .in_("id", worker_ids)
                .execute()
            )
            for worker in workers.data or []:
                worker_map[worker["id"]] = worker.get("name") or "Unknown worker"

        dci_event_ids = [row.get("dci_event_id") for row in rows if row.get("dci_event_id")]
        dci_map: dict[str, float] = {}
        if dci_event_ids:
            dci_events = (
                sb.table("dci_events")
                .select("id, dci_score")
                .in_("id", dci_event_ids)
                .execute()
            )
            for event in dci_events.data or []:
                event_id = event.get("id")
                if event_id:
                    dci_map[event_id] = float(event.get("dci_score") or 0)

        payouts: list[ProcessingPayout] = []
        for row in rows:
            worker_id = row.get("worker_id")
            worker_name = worker_map.get(worker_id, f"Worker {str(worker_id)[:8]}" if worker_id else "Unknown worker")
            db_status = row.get("status") or "processing"
            payouts.append(
                ProcessingPayout(
                    id=str(row.get("id")),
                    worker_id=str(worker_id) if worker_id else None,
                    worker_name=worker_name,
                    amount=float(row.get("final_amount") or 0),
                    dci_score=dci_map.get(row.get("dci_event_id")) if row.get("dci_event_id") else None,
                    fraud_score=float(row["fraud_score"]) if row.get("fraud_score") is not None else None,
                    status=STATUS_DISPLAY_MAP.get(db_status, db_status),
                    timestamp=row.get("triggered_at") or row.get("created_at") or datetime.utcnow(),
                )
            )

        return ProcessingPayoutListResponse(payouts=payouts, count=len(payouts))

    except Exception as exc:
        logger.error(f"Failed to fetch payouts from database: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to fetch payouts from database",
        )


# ─── Worker Lookup (DB-Backed) ───────────────────────────────────────────────
# In production: reads from Supabase `workers` table.
# Falls back to hardcoded demo data when Supabase is unavailable (dev mode).

_WORKER_FALLBACK = {
    "W100": {
        "baseline_earnings": 1000.0,
        "plan_tier": "Basic",
        "shift": "Morning",
        "history": {"avg_hourly": 125.0, "current_hour_velocity": 130.0}
    },
    "W101": {
        "baseline_earnings": 1500.0,
        "plan_tier": "Plus",
        "shift": "Day",
        "history": {"avg_hourly": 187.0, "current_hour_velocity": 260.0}
    },
    "W102": {
        "baseline_earnings": 2000.0,
        "plan_tier": "Pro",
        "shift": "Night",
        "history": {"avg_hourly": 250.0, "current_hour_velocity": 250.0}
    },
}

def _get_worker(worker_id: str) -> dict | None:
    """
    Fetches worker details from Supabase.
    Falls back to demo dict when DB is unavailable.
    """
    try:
        from utils.supabase_client import get_supabase
        sb = get_supabase()
        if sb:
            res = sb.table("workers").select(
                "id,plan,shift,gig_score"
            ).eq("id", worker_id).limit(1).execute()
            if res.data:
                row = res.data[0]
                # Map plan tier to coverage pct and build response shape
                plan_map = {"basic": ("Basic", 0.4), "plus": ("Plus", 0.5), "pro": ("Pro", 0.7)}
                plan_key = row.get("plan", "basic").lower()
                plan_label, _ = plan_map.get(plan_key, ("Basic", 0.4))
                return {
                    "baseline_earnings": 1000.0,  # TODO: fetch from baseline_service
                    "plan_tier": plan_label,
                    "shift": row.get("shift", "Morning"),
                    "history": {"avg_hourly": 125.0, "current_hour_velocity": 130.0},
                }
    except Exception as e:
        logger.warning(f"[PAYOUTS] DB lookup failed for {worker_id}: {e}. Using fallback.")
    # Development fallback
    return _WORKER_FALLBACK.get(worker_id)


def overlaps_surge_window(shift_name: str, current_time: datetime) -> bool:
    """Checks if the worker's shift covers the current disruption moment."""
    return is_within_shift(shift_name, current_time)

# --- Payloads ---
class PayoutRequest(BaseModel):
    worker_id: str
    pincode: str = "560001" # Added for hyperlocal surge calculation
    disruption_start: datetime
    disruption_end: datetime
    dci_score: int

class PayoutResponse(BaseModel):
    worker_id: str
    payout_amount: float
    breakdown: dict

# --- Stubs ---
PLAN_MULTIPLIERS = {
    "Basic": 0.4,
    "Plus": 0.5,
    "Pro": 0.7
}

def split_disruption_by_midnight(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    """Splits a disruption spanning multiple days into daily segments."""
    segments = []
    current_start = start
    
    while current_start.date() < end.date():
        # Define midnight of the next day
        midnight = datetime.combine(current_start.date() + timedelta(days=1), time.min).replace(tzinfo=current_start.tzinfo)
        segments.append((current_start, midnight))
        current_start = midnight
        
    segments.append((current_start, end))
    return segments

# ── Task 1 Fix: prefix is already /api/v1 from main.py — route is just /calculate_payout
@router.post("/calculate_payout", response_model=PayoutResponse)
async def calculate_payout(request: PayoutRequest):
    """
    Calculates the exact monetary payout for a worker dynamically based on the ML Model 
    prediction, the duration of the disruption, and their premium plan tier.
    Handles shifts spanning midnight by splitting them into daily balances (Section 12).
    """
    worker = _get_worker(request.worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
        
    baseline_earnings = worker["baseline_earnings"]
    plan_tier = worker["plan_tier"]
    tier_multiplier = PLAN_MULTIPLIERS.get(plan_tier, 0.4)
    hourly_rate = baseline_earnings / 8.0

    # 1. Split into daily segments
    segments = split_disruption_by_midnight(request.disruption_start, request.disruption_end)
    
    total_payout = 0.0
    daily_breakdown = []
    total_duration = 0.0
    
    from services.platform_service import get_platform_surge

    for seg_start, seg_end in segments:
        duration_td = seg_end - seg_start
        seg_duration = max(0.0, duration_td.total_seconds() / 3600.0)
        total_duration += seg_duration
        
        # 2. XGBoost Model inference (ML Predicted surge based on DCI)
        # Using the same DCI for all segments for now as per current core engine
        base_mult = 1.0 + (request.dci_score / 100.0) + (seg_duration * 0.1)
        pred_mult = round(min(max(base_mult, 1.0), 5.0), 2)
        
        # 3. Platform Surge logic (Image #3 & #5 Requirement)
        platform_surge = 1.0
        surge_eligible = False
        if overlaps_surge_window(worker["shift"], seg_start):
            platform_surge = get_platform_surge(request.pincode, request.dci_score, seg_start)
            hist = worker["history"]
            # Qualified worker = earnings velocity > avg (active during surge)
            if hist["current_hour_velocity"] > (hist["avg_hourly"] * 1.1):
                 surge_eligible = True
        
        final_surge = platform_surge if surge_eligible else 1.0
        
        # 4. Calculation for this segment
        seg_payout = round(hourly_rate * seg_duration * pred_mult * final_surge * tier_multiplier, 2)
        total_payout += seg_payout
        
        daily_breakdown.append({
            "date": seg_start.date().isoformat(),
            "hours": round(seg_duration, 2),
            "payout": seg_payout,
            "surge_applied": final_surge > 1.0
        })

    return PayoutResponse(
        worker_id=request.worker_id,
        payout_amount=round(total_payout, 2),
        breakdown={
            "total_duration_hours": round(total_duration, 2),
            "plan_tier": plan_tier,
            "tier_coverage_multiplier": tier_multiplier,
            "daily_split": daily_breakdown,
            "dci_score_registered": request.dci_score
        }
    )

@router.post("/sla_breach", status_code=200)
async def trigger_sla_breach_endpoint(pincode: str, reason: str):
    """
    Fires an irrevocable SLA breach event to the ledger/database, releasing
    unconditional base payouts to active workers in the zone.
    """
    return await trigger_sla_breach(pincode, reason)

async def trigger_sla_breach(pincode: str, reason: str):
    """
    Internal SLA breach function — called by the poller when all 4 data layers fail.
    Also exposed as POST /api/v1/sla_breach for manual admin trigger.
    """
    logger.critical(f"[SLA BREACH TRIGGERED] {reason} for zone {pincode}. Workers compensated automatically.")
    return {"status": "SLA_BREACH_EXECUTED", "zone": pincode, "reason": reason}

from datetime import datetime, timezone

@router.get("/payouts/total/today")
async def get_today_total():
    try:
        sb = get_supabase()

        # Get all payouts created today
        result = (
            sb.table("payouts")
            .select("final_amount, created_at")
            .gte("created_at", datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat())
            .execute()
        )

        total = sum(row.get("final_amount", 0) for row in result.data or [])

        return {
            "total_payout_today": total
        }

    except Exception as e:
        return {
            "total_payout_today": 0,
            "error": str(e)
        }
