"""
api/routes/workers.py — Worker Registration Endpoint
──────────────────────────────────────────────────────
Sumukh's endpoint: POST /api/v1/register

Handles the complete worker + policy creation in one atomic flow:
  1. Validate incoming data (Pydantic does most of this automatically)
  2. Check for duplicate phone number → 409 Conflict
  3. Insert worker row into `workers` table
  4. Compute current Mon–Sun week window
  5. Insert policy row into `policies` table (is_active=True)
  6. Return RegistrationResponse with coverage start time

Coverage delay: New worker payouts are blocked for 24hrs from registration.
This prevents the "sign-up during an active storm" moral hazard (edge case #8).

Usage (from WhatsApp webhook, after onboarding flow completes):
    from api.routes.workers import router as workers_router
    # Already wired in main.py
"""

from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timedelta
import logging
import uuid

from models.worker import (
    WorkerCreate,
    RegistrationResponse,
    PlanType,
)
from utils.db import get_supabase
from config.settings import settings

logger = logging.getLogger("gigkavach.workers")

router = APIRouter(prefix="/api/v1", tags=["Workers"])


# ─── Helper: Current week window ─────────────────────────────────────────────

def get_current_week_window() -> tuple[datetime, datetime]:
    """
    Returns (Monday 00:00, Sunday 23:59:59) for the current calendar week.
    GigKavach policies are strictly Monday–Sunday weekly cycles.
    """
    today = datetime.utcnow().date()
    # weekday() returns 0=Monday ... 6=Sunday
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    week_start = datetime(monday.year, monday.month, monday.day, 0, 0, 0)
    week_end   = datetime(sunday.year, sunday.month, sunday.day, 23, 59, 59)
    return week_start, week_end


# ─── Premium amount lookup ────────────────────────────────────────────────────

# Plan → (weekly_premium_₹, coverage_pct)
PLAN_PREMIUMS = {
    PlanType.BASIC: (69.0,  40),   # ₹69/week, 40% loss coverage
    PlanType.PLUS:  (89.0,  50),   # ₹89/week, 50% loss coverage
    PlanType.PRO:   (99.0,  70),   # ₹99/week, 70% loss coverage
}


# ─── POST /api/v1/register ───────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new worker and create their first policy",
    responses={
        201: {"description": "Worker and policy created successfully"},
        409: {"description": "Phone number already registered"},
        422: {"description": "Validation error (bad UPI, invalid pin code, etc.)"},
        503: {"description": "Database unavailable"},
    },
)
async def register_worker(worker_data: WorkerCreate) -> RegistrationResponse:
    """
    Onboards a new worker into GigKavach.

    This endpoint is called by the WhatsApp webhook (api/routes/whatsapp.py)
    after the 5-step onboarding conversation is complete.

    Workflow:
      1. Pydantic auto-validates fields (phone format, UPI, pin codes)
      2. Duplicate phone check → 409 if already registered
      3. Worker row inserted → generates worker_id
      4. Policy row inserted → generates policy_id
      5. Coverage starts 24hrs later (moral hazard prevention)
    """
    sb = get_supabase()

    # ── Step 1: Phone number format check ────────────────────────────────────
    # Basic E.164 validation for Indian numbers (+91XXXXXXXXXX)
    phone = worker_data.phone_number.strip()
    if not phone.startswith("+91") or len(phone) != 13 or not phone[3:].isdigit():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "field": "phone_number",
                "error": "Must be a valid Indian mobile number in E.164 format: +91XXXXXXXXXX",
                "received": phone,
            }
        )

    # ── Step 2: Duplicate phone check ────────────────────────────────────────
    try:
        existing = (
            sb.table("workers")
            .select("id, phone_number")
            .eq("phone_number", phone)
            .limit(1)
            .execute()
        )
        if existing.data:
            logger.warning(f"Duplicate registration attempt: {phone}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "This phone number is already registered with GigKavach.",
                    "phone_number": phone,
                    "existing_worker_id": existing.data[0]["id"],
                    "hint": "Use PATCH /api/v1/workers/{id} to update profile details.",
                }
            )
    except HTTPException:
        raise  # re-raise our own exceptions (don't catch them as DB errors)
    except Exception as e:
        logger.error(f"Supabase error during duplicate check: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable. Please try again shortly."
        )

    # ── Step 3: Compute timing fields ────────────────────────────────────────
    now = datetime.utcnow()
    week_start, week_end = get_current_week_window()

    # 24-hour coverage delay — moral hazard prevention (edge case #8)
    # New workers cannot claim payouts until 24hrs after registration.
    coverage_active_from = now + timedelta(hours=settings.COVERAGE_DELAY_HOURS)

    # ── Step 4: Insert worker into Supabase ──────────────────────────────────
    worker_id = str(uuid.uuid4())
    worker_row = {
        "id":                   worker_id,
        "phone_number":         phone,          # schema column: phone_number
        "phone":                phone,          # legacy alias: phone
        "name":                 getattr(worker_data, 'name', ''),  # optional if WhatsApp flow sets it
        "platform":             worker_data.platform.value,
        "shift":                worker_data.shift.value,
        "upi_id":               worker_data.upi_id,
        "pin_codes":            worker_data.pin_codes,
        "plan":                 worker_data.plan.value,
        "language":             worker_data.language.value,
        "gig_score":            100.0,          # perfect trust score on join
        "is_active":            True,
        "coverage_active_from": coverage_active_from.isoformat(),
        "onboarded_at":         now.isoformat(),
        "created_at":           now.isoformat(),
        "updated_at":           now.isoformat(),
    }

    try:
        sb.table("workers").insert(worker_row).execute()
        logger.info(f"Worker created: id={worker_id} phone={phone} plan={worker_data.plan.value}")
    except Exception as e:
        logger.error(f"Failed to insert worker: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to create worker record. Please try again."
        )

    # ── Step 5: Insert policy into Supabase ──────────────────────────────────
    policy_id = str(uuid.uuid4())
    policy_row = {
        "id":           policy_id,
        "worker_id":    worker_id,
        "plan":         worker_data.plan.value,
        "shift":        worker_data.shift.value,       # schema column: shift
        "pin_codes":    worker_data.pin_codes,         # schema column: pin_codes
        "week_start":   week_start.date().isoformat(), # schema expects DATE not TIMESTAMP
        "week_end":     week_end.date().isoformat(),   # schema column: week_end
        "coverage_pct": PLAN_PREMIUMS[worker_data.plan][1],  # 40|50|70
        "premium_paid": PLAN_PREMIUMS[worker_data.plan][0],  # ₹69|89|99
        "is_active":    True,
        "created_at":   now.isoformat(),
    }

    try:
        sb.table("policies").insert(policy_row).execute()
        logger.info(f"Policy created: id={policy_id} worker={worker_id} plan={worker_data.plan.value}")
    except Exception as e:
        logger.error(f"Failed to insert policy (worker {worker_id}): {e}")
        # Worker row was created — log for manual reconciliation
        # In production we'd wrap both inserts in a Supabase RPC transaction
        logger.critical(f"ORPHAN WORKER: id={worker_id} has no policy! Manual fix needed.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to create policy record. Worker has been registered — contact support."
        )

    # ── Step 6: Return registration response ─────────────────────────────────
    logger.info(
        f"Registration complete: worker={worker_id} policy={policy_id} "
        f"coverage_from={coverage_active_from.isoformat()}"
    )
    return RegistrationResponse(
        worker_id=worker_id,
        policy_id=policy_id,
        phone_number=phone,
        plan=worker_data.plan,
        coverage_active_from=coverage_active_from,
        week_start=week_start,
        week_end=week_end,
        message=(
            f"Welcome to GigKavach! Your {worker_data.plan.value.upper()} plan is active. "
            f"Payout coverage starts at {coverage_active_from.strftime('%d %b %Y %H:%M')} UTC."
        )
    )
