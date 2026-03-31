"""
cron/claims_trigger.py — Claims Processing Pipeline
──────────────────────────────────────────────────────
Runs every 5 minutes driven by APScheduler.
Processes new claims by:
1. Fetching unprocessed claims from database
2. Scoring each claim for fraud risk (XGBoost + Isolation Forest + Rules)
3. Calculating payout based on disruption severity (XGBoost v3)
4. Updating claim status + payout decision
5. Triggering payment if approved
6. Logging audit trail

Integration Points:
- fraud_service.check_fraud() → 3-stage fraud detection pipeline
- payout_service.calculate_payout() → XGBoost v3 payout multiplier
- Database: Supabase claims table
"""

import logging
import asyncio
import datetime
from typing import List, Dict, Any

from services.fraud_service import check_fraud
from services.payout_service import calculate_payout
from utils.supabase_client import get_supabase
from config.settings import settings

logger = logging.getLogger("gigkavach.claims_trigger")


# ──────────────────────────────────────────────────────────────────────────────
# DATABASE & HELPER FUNCTIONS
# ──────────────────────────────────────────────────────────────────────────────

def _get_unprocessed_claims() -> List[Dict[str, Any]]:
    """
    Fetch all claims with status='pending' from Supabase.
    
    Returns list of claim dicts with:
    - claim_id
    - worker_id
    - dci_score
    - disruption_duration
    - baseine_earnings
    - city
    - disruption_type
    - hour_of_day
    - day_of_week
    - etc.
    """
    try:
        sb = get_supabase()
        if not sb or not settings.SUPABASE_URL:
            logger.warning("[CLAIMS] Supabase not configured, skipping claim processing")
            return []
        
        # Query claims with status='pending' ordered by created_at
        response = sb.table("claims") \
            .select("*") \
            .eq("status", "pending") \
            .order("created_at", desc=False) \
            .limit(100) \
            .execute()
        
        claims = response.data if response.data else []
        logger.info(f"[CLAIMS] Fetched {len(claims)} pending claims")
        return claims
        
    except Exception as e:
        logger.error(f"[CLAIMS ERROR] Failed to fetch claims: {str(e)}")
        return []


def _update_claim_status(claim_id: str, status: str, fraud_score: float = None,
                        fraud_decision: str = None, payout_amount: float = None,
                        payout_multiplier: float = None, is_fraud: bool = None):
    """
    Update claim in database with fraud assessment and payout decision.
    
    Statuses:
    - pending → processing → approved → paid
    - pending → processing → rejected
    """
    try:
        sb = get_supabase()
        if not sb or not settings.SUPABASE_URL:
            logger.warning("[CLAIMS] Supabase not configured, skipping update")
            return False
        
        update_dict = {
            "status": status,
            "processed_at": datetime.datetime.utcnow().isoformat(),
        }
        
        if fraud_score is not None:
            update_dict["fraud_score"] = fraud_score
        if fraud_decision is not None:
            update_dict["fraud_decision"] = fraud_decision
        if is_fraud is not None:
            update_dict["is_fraud"] = is_fraud
        if payout_amount is not None:
            update_dict["payout_amount"] = payout_amount
        if payout_multiplier is not None:
            update_dict["payout_multiplier"] = payout_multiplier
        
        sb.table("claims") \
            .update(update_dict) \
            .eq("id", claim_id) \
            .execute()
        
        logger.info(f"[CLAIMS] Updated claim {claim_id} → {status}")
        return True
        
    except Exception as e:
        logger.error(f"[CLAIMS ERROR] Failed to update claim {claim_id}: {str(e)}")
        return False


def _get_worker_history(worker_id: str) -> Dict[str, Any]:
    """
    Fetch worker's historical claims for fraud context.
    
    Returns dict with:
    - total_claims
    - approved_rate
    - fraud_flags_count
    - avg_payout
    - high_fraud_area_count
    """
    try:
        sb = get_supabase()
        if not sb or not settings.SUPABASE_URL:
            return {
                "total_claims": 0,
                "approved_rate": 1.0,
                "fraud_flags_count": 0,
                "avg_payout": 0
            }
        
        # Query all claims for this worker
        response = sb.table("claims") \
            .select("*") \
            .eq("worker_id", worker_id) \
            .order("created_at", desc=True) \
            .limit(50) \
            .execute()
        
        claims_history = response.data if response.data else []
        
        if not claims_history:
            return {
                "total_claims": 0,
                "approved_rate": 1.0,
                "fraud_flags_count": 0,
                "avg_payout": 0
            }
        
        total = len(claims_history)
        approved = sum(1 for c in claims_history if c.get("status") == "approved")
        fraud_flags = sum(1 for c in claims_history if c.get("is_fraud", False))
        avg_payout = sum(c.get("payout_amount", 0) for c in claims_history) / total if total > 0 else 0
        
        return {
            "total_claims": total,
            "approved_rate": approved / total if total > 0 else 1.0,
            "fraud_flags_count": fraud_flags,
            "avg_payout": avg_payout,
            "recent_claims": [
                {
                    "claim_id": c.get("id"),
                    "status": c.get("status"),
                    "is_fraud": c.get("is_fraud", False),
                    "dci_score": c.get("dci_score", 0)
                }
                for c in claims_history[:10]
            ]
        }
        
    except Exception as e:
        logger.error(f"[CLAIMS ERROR] Failed to get worker {worker_id} history: {str(e)}")
        return {
            "total_claims": 0,
            "approved_rate": 1.0,
            "fraud_flags_count": 0,
            "avg_payout": 0
        }


def _trigger_payment(claim_id: str, worker_id: str, payout_amount: float):
    """
    Trigger payment through payment gateway (Razorpay/Stripe).
    
    TODO: Integrate with actual payment provider.
    For now, just log the intent.
    """
    logger.info(
        f"[PAYMENT TRIGGER] claim={claim_id} | "
        f"worker={worker_id} | amount=₹{payout_amount:.0f}"
    )
    
    # TODO: Call payment service
    # - Create payout order in Razorpay
    # - Link to worker's bank account on file
    # - Track payment status
    # - Handle retries and failures
    
    return {
        "payment_triggered": True,
        "claim_id": claim_id,
        "worker_id": worker_id,
        "amount": payout_amount
    }


def _send_whatsapp_alert(worker_id: str, claim_id: str, decision: str, 
                         payout_amount: float, fraud_score: float):
    """
    Send WhatsApp notification to worker about claim decision.
    
    TODO: Integrate with Twilio WhatsApp Business API.
    """
    message = None
    
    if decision == "APPROVED":
        message = (
            f"✅ Your disruption claim #{claim_id} has been approved!\n"
            f"Payout: ₹{payout_amount:.0f}\n"
            f"Confidence: {(1 - fraud_score) * 100:.0f}%\n"
            f"Payment processing..."
        )
    elif decision == "REJECTED_FRAUD":
        message = (
            f"⚠️ Your claim #{claim_id} shows unusual patterns.\n"
            f"Please contact support on our app for details."
        )
    elif decision == "REJECTED_INELIGIBLE":
        message = (
            f"ℹ️ Your claim #{claim_id} doesn't meet eligibility criteria.\n"
            f"Check your account settings or contact support."
        )
    
    if message:
        logger.info(f"[WHATSAPP] worker={worker_id} | {message[:50]}...")
    
    # TODO: Call Twilio WhatsApp API
    return {"whatsapp_sent": message is not None}


# ──────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ──────────────────────────────────────────────────────────────────────────────

def process_single_claim(claim: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single claim through fraud detection and payout pipeline.
    
    Pipeline:
    1. Validate claim data
    2. Get worker's fraud context
    3. Run fraud detection (3-stage: Rules → IF → XGB multi-class)
    4. Calculate payout if approved
    5. Update database
    6. Trigger payment if approved
    7. Send notifications
    
    Returns dict with processing result.
    """
    claim_id = claim.get("id")
    worker_id = claim.get("worker_id")
    
    logger.info(f"[CLAIM PROCESSING] Starting: claim={claim_id} | worker={worker_id}")
    
    try:
        # ──── 1. Prepare Fraud Detection Input ────
        fraud_context = {
            "claim_id": claim_id,
            "worker_id": worker_id,
            "dci_score": claim.get("dci_score", 0),
            "disruption_duration": claim.get("disruption_duration", 0),
            "disruption_type": claim.get("disruption_type", "Unknown"),
            "city": claim.get("city", ""),
            "hour_of_day": claim.get("hour_of_day", 0),
            "day_of_week": claim.get("day_of_week", 0),
            "zone_density": claim.get("zone_density", "Mid"),
            # Additional context from claim record
            "claim_created_at": claim.get("created_at"),
            "shift": claim.get("shift", "Morning"),
        }
        
        worker_history = _get_worker_history(worker_id)
        
        # ──── 2. Run Fraud Detection ────
        logger.debug(f"[FRAUD CHECK] Running 3-stage pipeline for claim={claim_id}")
        
        fraud_result = check_fraud(
            claim=fraud_context,
            worker_history=worker_history,
            user_context={"worker_id": worker_id}
        )
        
        is_fraud = fraud_result.get("is_fraud", False)
        fraud_score = fraud_result.get("fraud_score", 0.0)
        fraud_decision = fraud_result.get("decision", "UNCLEAR")
        fraud_type = fraud_result.get("fraud_type", "clean")
        
        logger.info(
            f"[FRAUD RESULT] claim={claim_id} | is_fraud={is_fraud} | "
            f"score={fraud_score:.3f} | type={fraud_type}"
        )
        
        # ──── 3. Make Approval Decision ────
        if is_fraud:
            # Fraudulent claim → Reject
            logger.warning(f"[CLAIM REJECTED] claim={claim_id} | reason=FRAUD_DETECTED")
            
            _update_claim_status(
                claim_id=claim_id,
                status="rejected",
                fraud_score=fraud_score,
                fraud_decision=fraud_decision,
                is_fraud=True
            )
            
            _send_whatsapp_alert(
                worker_id=worker_id,
                claim_id=claim_id,
                decision="REJECTED_FRAUD",
                payout_amount=0,
                fraud_score=fraud_score
            )
            
            return {
                "claim_id": claim_id,
                "worker_id": worker_id,
                "status": "rejected",
                "reason": "fraud_detected",
                "fraud_score": fraud_score,
                "fraud_type": fraud_type
            }
        
        # ──── 4. Calculate Payout ────
        logger.debug(f"[PAYOUT CALC] claim={claim_id} | DCI={claim.get('dci_score', 0)}")
        
        payout_result = calculate_payout(
            baseline_earnings=claim.get("baseline_earnings", 1000),
            disruption_duration=claim.get("disruption_duration", 0),
            dci_score=claim.get("dci_score", 0),
            worker_id=worker_id,
            city=claim.get("city", ""),
            zone_density=claim.get("zone_density", "Mid"),
            shift=claim.get("shift", "Morning"),
            disruption_type=claim.get("disruption_type", "Unknown"),
            hour_of_day=claim.get("hour_of_day", 0),
            day_of_week=claim.get("day_of_week", 0),
            include_confidence=True
        )
        
        payout_amount = payout_result.get("payout", 0.0)
        multiplier = payout_result.get("multiplier", 1.0)
        confidence = payout_result.get("confidence", 0.0)
        
        logger.info(
            f"[PAYOUT CALCULATED] claim={claim_id} | "
            f"amount=₹{payout_amount:.0f} | multiplier={multiplier:.2f}x"
        )
        
        # ──── 5. Update Database ────
        _update_claim_status(
            claim_id=claim_id,
            status="approved",
            fraud_score=fraud_score,
            fraud_decision=fraud_decision,
            payout_amount=payout_amount,
            payout_multiplier=multiplier,
            is_fraud=False
        )
        
        # ──── 6. Trigger Payment ────
        if payout_amount > 0:
            _trigger_payment(claim_id, worker_id, payout_amount)
        
        # ──── 7. Send Notifications ────
        _send_whatsapp_alert(
            worker_id=worker_id,
            claim_id=claim_id,
            decision="APPROVED",
            payout_amount=payout_amount,
            fraud_score=fraud_score
        )
        
        logger.info(f"[CLAIM APPROVED] claim={claim_id} | payout=₹{payout_amount:.0f}")
        
        return {
            "claim_id": claim_id,
            "worker_id": worker_id,
            "status": "approved",
            "payout_amount": payout_amount,
            "fraud_score": fraud_score,
            "multiplier": multiplier
        }
        
    except Exception as e:
        logger.error(f"[CLAIM PROCESSING ERROR] claim={claim_id}: {str(e)}", exc_info=True)
        
        # Mark as errored
        _update_claim_status(claim_id=claim_id, status="error")
        
        return {
            "claim_id": claim_id,
            "worker_id": worker_id,
            "status": "error",
            "error": str(e)
        }


async def trigger_claims_pipeline():
    """
    Main cron job that runs every 5 minutes.
    
    1. Fetch all pending claims
    2. Process each through fraud + payout pipeline
    3. Log results
    """
    logger.info("[CLAIMS PIPELINE] ========== Starting Claims Processing ==========")
    
    start_time = datetime.datetime.utcnow()
    
    # Fetch pending claims
    pending_claims = _get_unprocessed_claims()
    
    if not pending_claims:
        logger.info("[CLAIMS PIPELINE] No pending claims to process")
        return {
            "total_claims": 0,
            "approved": 0,
            "rejected": 0,
            "errors": 0,
            "duration_seconds": 0
        }
    
    logger.info(f"[CLAIMS PIPELINE] Processing {len(pending_claims)} claims...")
    
    # Process claims sequentially (can optimize to batch later)
    results = {
        "total_claims": len(pending_claims),
        "approved": 0,
        "rejected": 0,
        "errors": 0,
        "claims": []
    }
    
    for claim in pending_claims:
        result = process_single_claim(claim)
        results["claims"].append(result)
        
        if result.get("status") == "approved":
            results["approved"] += 1
        elif result.get("status") == "rejected":
            results["rejected"] += 1
        elif result.get("status") == "error":
            results["errors"] += 1
    
    # Summary logs
    duration = (datetime.datetime.utcnow() - start_time).total_seconds()
    
    logger.info(
        f"[CLAIMS PIPELINE] ========== Complete ==========\n"
        f"  Total Claims: {results['total_claims']}\n"
        f"  Approved: {results['approved']}\n"
        f"  Rejected: {results['rejected']}\n"
        f"  Errors: {results['errors']}\n"
        f"  Duration: {duration:.1f}s"
    )
    
    results["duration_seconds"] = duration
    return results


# ──────────────────────────────────────────────────────────────────────────────
# EXPORT MAIN FUNCTION FOR SCHEDULER
# ──────────────────────────────────────────────────────────────────────────────

async def run_claims_pipeline():
    """Entry point for APScheduler cron job."""
    return await trigger_claims_pipeline()
