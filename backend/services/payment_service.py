"""
services/payment_service.py — Razorpay UPI Payout Integration
──────────────────────────────────────────────────────────────

This service handles all financial transactions:
  1. Payout initiation via Razorpay UPI (TEST MODE)
  2. Webhook callbacks for payout status updates
  3. Retry logic for failed payouts (up to 3 attempts, 40-min intervals)
  4. Escrow flow for workers to correct failed payouts
  5. Payout history tracking

Payout Pipeline:
  1. calculate_payout() → returns payout amount
  2. check_fraud() → fraud scoring and Tier 1/2/3 assignment
  3. initiate_payout() → sends payment to UPI via Razorpay
  4. Worker gets WhatsApp confirmation → money in UPI
  5. If UPI fails → Retry loop (3 attempts) → Escrow hold
  6. Escrow window (48 hours) → Worker corrects UPI/bank → Retry payoutRazorpay Payout States:
  - "initiated" → Payout created, waiting for processing
  - "processing" → Razorpay processing the transfer
  - "processed" → Transfer successful ✅
  - "failed" → Transfer failed → Initiated retry or escrow
  - "rejected" → Invalid UPI or permanently blocked

Escrow Logic:
  If payout fails after 3 retries:
  1. Hold funds in escrow (48-hour window)
  2. Send WhatsApp: "Your payment failed. Verify UPI: [link to correction form]"
  3. Worker corrects UPI/account details (or provides proof of successful transfer)
  4. System automatically refires payout after correction
  5. If uncorrected after 48h → Manual support review or fund return to account

Usage:
    from services.payment_service import initiate_payout, get_payout_status
    
    # Initiate payout
    result = await initiate_payout(
        worker_id='w_123',
        upi_id='ravi@upi',
        amount=280,
        dci_score=72,
        payout_reason='rainfall_disruption',
    )
    # Returns: {"payout_id": "payout_...", "status": "initiated", ...}
    
    # Check payout status
    status = await get_payout_status(payout_id="payout_...")
"""

import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from enum import Enum
import httpx

from config.settings import settings
from utils.supabase_client import get_supabase
from utils.validators import validate_upi_id

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("gigkavach.payment_service")


# ─── Enums ───────────────────────────────────────────────────────────────────

class PayoutStatus(str, Enum):
    """Payout lifecycle states."""
    INITIATED = "initiated"      # Created, waiting for Razorpay processing
    PROCESSING = "processing"    # Razorpay processing
    PROCESSED = "processed"      # Success ✅
    FAILED = "failed"            # Transfer failed, retrying
    REJECTED = "rejected"        # Permanent failure (bad UPI)
    ESCROW = "escrow"           # Held in escrow (worker correcting UPI)
    REFUNDED = "refunded"        # Escrow expired, funds returned


class RetryReason(str, Enum):
    """Reasons for payout retries."""
    INITIAL_FAILURE = "initial_failure"
    TEMPORARY_NETWORK = "temporary_network_failure"
    BANK_SYSTEM_DOWN = "bank_system_failure"
    INVALID_UPI_FORMAT = "invalid_upi_format"


# ─── Configuration ───────────────────────────────────────────────────────────

RAZORPAY_BASE_URL = "https://api.razorpay.com/v1"
RAZORPAY_TEST_MODE = settings.APP_ENV != "production"  # Use test mode in dev/staging
MAX_UPI_RETRY_ATTEMPTS = settings.MAX_UPI_RETRY_ATTEMPTS  # 3 attempts
UPI_RETRY_INTERVAL_MINUTES = settings.UPI_RETRY_INTERVAL_MINUTES  # 40 min between retries
ESCROW_HOLD_HOURS = settings.ESCROW_WINDOW_HOURS  # 48 hours


class PaymentInitializationError(Exception):
    """Raised when payout initiation fails."""
    pass


class PayoutStatusError(Exception):
    """Raised when payout status check fails."""
    pass


async def initiate_payout(
    worker_id: str,
    upi_id: str,
    amount: float,
    dci_score: float,
    payout_reason: str,
    fraud_tier: Optional[int] = None,
    fraud_payout_action: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> Dict:
    """
    Initiate a UPI payout via Razorpay.
    
    This integrates with the full payout pipeline:
    1. Called after payout calculation
    2. After fraud detection scoring
    3. Handles soft fraud flags (50% holds) and hard blocks
    4. Initiates upi transfer via Razorpay
    5. Stores payout record in payouts table
    6. Returns immediately — Razorpay webhook confirms actual success
    
    Args:
        worker_id (str): GigKavach worker ID
        upi_id (str): Worker's UPI ID (e.g., "ravi@upi")
        amount (float): Payout amount in INR
        dci_score (float): DCI score at trigger time (used in messaging)
        payout_reason (str): Reason for payout (e.g., "rainfall", "aqi_spike")
        fraud_tier (int, optional): Fraud tier if flagged (1, 2, or 3)
        fraud_payout_action (str, optional): "100%" | "50%_hold_48h" | "0%_block"
        idempotency_key (str, optional): For deduplication (defaults to auto-generated)
        
    Returns:
        Dict with structure:
        {
            "payout_id": "payout_...",  # Razorpay payout ID
            "worker_id": "w_123",
            "upi_id": "ravi@upi",
            "amount_initiated": 280.0,
            "amount_held": 0.0,  # Amount in escrow (Tier 1 fraud = 50%)
            "status": "initiated",
            "payout_reason": "rainfall_disruption",
            "fraud": {
                "tier": 0,  # 0 (none), 1 (soft flag), 2 (hard block), 3 (blacklist)
                "action": "100%_payout",
                "message": "OK — No fraud detected"
            },
            "retry": {
                "attempt": 1,
                "next_retry_at": None,
            },
            "created_at": "2026-03-30T18:45:00Z",
            "timestamp": "2026-03-30T18:45:00Z",
        }
        
    Raises:
        PaymentInitializationError: If Razorpay request fails
        
    Example:
        >>> result = await initiate_payout(
        ...     worker_id='w_123',
        ...     upi_id='ravi@upi',
        ...     amount=280,
        ...     dci_score=72,
        ...     payout_reason='rainfall_disruption',
        ... )
        >>> print(f"Payout ID: {result['payout_id']}")
    """
    
    try:
        # ─── STEP 1: Validate Inputs ────────────────────────────────────────
        
        if not validate_upi_id(upi_id):
            raise PaymentInitializationError(f"Invalid UPI ID format: {upi_id}")
        
        if amount <= 0 or amount > 10000:  # Sanity check
            logger.warning(f"Unusual payout amount: ₹{amount}")
        
        # Generate idempotency key if not provided
        if not idempotency_key:
            idempotency_key = _generate_idempotency_key(worker_id, amount)
        
        logger.info(
            f"Initiating payout for {worker_id}: ₹{amount} → {upi_id} "
            f"(idempotency_key={idempotency_key})"
        )
        
        # ─── STEP 2: Map Fraud Tier to Payout Action ────────────────────────
        
        amount_to_send = amount
        amount_held = 0.0
        fraud_message = "OK — No fraud detected"
        
        if fraud_tier == 1:
            # Soft flag: 50% payout, 50% held ✅ for 48 hours with silent re-verify
            amount_to_send = amount * 0.5
            amount_held = amount * 0.5
            fraud_message = "Soft fraud flag — 50% payout initiated, 50% re-verifying for 48h"
            logger.warning(f"Tier 1 fraud flag for {worker_id} — 50% hold applied")
        
        elif fraud_tier == 2:
            # Hard block: 0% payout, full hold pending appeal
            amount_to_send = 0.0
            amount_held = amount
            fraud_message = "Hard fraud block — payout on hold pending appeal"
            logger.error(f"Tier 2 fraud block for {worker_id} — full hold")
        
        elif fraud_tier == 3:
            # Blacklist: rejected entirely
            raise PaymentInitializationError(
                f"Worker {worker_id} is blacklisted — payout rejected"
            )
        
        # ─── STEP 3: Call Razorpay Payout API ───────────────────────────────
        
        if amount_to_send > 0:
            razorpay_payout_id = await _call_razorpay_payout(
                upi_id=upi_id,
                amount=amount_to_send,
                worker_id=worker_id,
                idempotency_key=idempotency_key,
            )
        else:
            razorpay_payout_id = None  # No payout sent (fraud block or blacklist)
        
        # ─── STEP 4: Create Payout Record in Database ────────────────────────
        
        sb = get_supabase()
        
        payout_record = {
            "worker_id": worker_id,
            "upi_id": upi_id,
            "amount_calculated": amount,
            "amount_initiated": amount_to_send,
            "amount_held": amount_held,
            "razorpay_payout_id": razorpay_payout_id,
            "base_amount": amount,  # For historical reference
            "status": "initiated" if razorpay_payout_id else "pending",
            "payout_reason": payout_reason,
            "dci_score": dci_score,
            "fraud_tier": fraud_tier or 0,
            "fraud_action": fraud_payout_action or "100%_payout",
            "idempotency_key": idempotency_key,
            "retry_attempt": 1,
            "next_retry_at": None,
            "triggered_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        payout_response = sb.table("payouts").insert(payout_record).execute()
        
        if not payout_response.data:
            raise PaymentInitializationError("Failed to create payout record in database")
        
        payout_id = payout_response.data[0].get("id", "payout_no_id")
        
        logger.info(
            f"✅ Payout initiated: {payout_id} for {worker_id} "
            f"(amount: ₹{amount_to_send})"
        )
        
        # ─── STEP 5: Build Response ─────────────────────────────────────────
        
        result = {
            "payout_id": payout_id,
            "razorpay_payout_id": razorpay_payout_id,
            "worker_id": worker_id,
            "upi_id": upi_id,
            "amount_calculated": amount,
            "amount_initiated": amount_to_send,
            "amount_held": amount_held,
            "status": "initiated" if razorpay_payout_id else "pending",
            "payout_reason": payout_reason,
            "dci_score": dci_score,
            "fraud": {
                "tier": fraud_tier or 0,
                "action": fraud_payout_action or "100%_payout",
                "message": fraud_message,
            },
            "retry": {
                "attempt": 1,
                "max_attempts": MAX_UPI_RETRY_ATTEMPTS,
                "next_retry_at": None,
            },
            "idempotency_key": idempotency_key,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        return result
    
    except PaymentInitializationError:
        raise
    except Exception as e:
        logger.error(f"❌ Payout initiation failed for {worker_id}: {str(e)}")
        raise PaymentInitializationError(f"Payout initiation failed: {str(e)}")


async def get_payout_status(payout_id: str) -> Dict:
    """
    Get current status of a payout.
    
    Queries the payouts table and optionally checks Razorpay status
    if a razorpay_payout_id is available.
    
    Args:
        payout_id (str): GigKavach payout ID
        
    Returns:
        Dict with payout details and current status
        
    Raises:
        PayoutStatusError: If payout not found or API call fails
    """
    
    try:
        sb = get_supabase()
        
        response = sb.table("payouts").select("*").eq("id", payout_id).execute()
        
        if not response.data:
            raise PayoutStatusError(f"Payout {payout_id} not found")
        
        payout = response.data[0]
        
        # If Razorpay ID exists, optionally check real-time status
        if payout.get("razorpay_payout_id"):
            try:
                razorpay_status = await _get_razorpay_payout_status(
                    payout["razorpay_payout_id"]
                )
                payout["razorpay_status"] = razorpay_status
                
                # Update local status if Razorpay has more recent info
                if razorpay_status.get("state") == "processed":
                    payout["status"] = "processed"
            
            except Exception as e:
                logger.warning(f"Could not fetch Razorpay status: {e}")
        
        return payout
    
    except PayoutStatusError:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get payout status for {payout_id}: {str(e)}")
        raise PayoutStatusError(f"Failed to get payout status: {str(e)}")


async def retry_payout(
    payout_id: str,
    reason: RetryReason = RetryReason.INITIAL_FAILURE,
) -> Dict:
    """
    Retry a failed payout (up to 3 times).
    
    Called when:
    1. Razorpay webhook reports payout failure
    2. Manual retry initiated by user via APPEAL command
    3. Auto-retry triggered after 40 minutes
    
    Args:
        payout_id (str): GigKavach payout ID
        reason (RetryReason): Why we're retrying
        
    Returns:
        Dict with retry result
        
    Raises:
        PaymentInitializationError: If max retries exceeded or other failure
    """
    
    try:
        sb = get_supabase()
        
        # Fetch current payout
        response = sb.table("payouts").select("*").eq("id", payout_id).execute()
        if not response.data:
            raise PaymentInitializationError(f"Payout {payout_id} not found")
        
        payout = response.data[0]
        retry_attempt = payout.get("retry_attempt", 1)
        
        # Check retry limit
        if retry_attempt >= MAX_UPI_RETRY_ATTEMPTS:
            logger.error(
                f"Max retries ({MAX_UPI_RETRY_ATTEMPTS}) exceeded for {payout_id}"
            )
            
            # Move to escrow
            sb.table("payouts").update({
                "status": "escrow",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", payout_id).execute()
            
            raise PaymentInitializationError(
                f"Max retries exceeded. Payout moved to escrow."
            )
        
        # Attempt re-payout
        logger.info(
            f"Retrying payout {payout_id} (attempt {retry_attempt + 1}/{MAX_UPI_RETRY_ATTEMPTS})"
        )
        
        razorpay_payout_id = await _call_razorpay_payout(
            upi_id=payout["upi_id"],
            amount=payout["amount_initiated"],
            worker_id=payout["worker_id"],
            idempotency_key=_generate_idempotency_key(
                payout["worker_id"],
                payout["amount_initiated"],
                suffix=f"_retry_{retry_attempt + 1}"
            ),
        )
        
        # Update payout record
        sb.table("payouts").update({
            "razorpay_payout_id": razorpay_payout_id,
            "retry_attempt": retry_attempt + 1,
            "last_retry_reason": reason.value,
            "next_retry_at": (
                (datetime.now(timezone.utc) + timedelta(minutes=UPI_RETRY_INTERVAL_MINUTES))
                .isoformat()
            ) if retry_attempt + 1 < MAX_UPI_RETRY_ATTEMPTS else None,
            "status": "processing",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", payout_id).execute()
        
        logger.info(f"✅ Payout retry submitted for {payout_id}")
        
        return {
            "payout_id": payout_id,
            "retry_attempt": retry_attempt + 1,
            "status": "processing",
            "message": f"Retry attempt {retry_attempt + 1}/{MAX_UPI_RETRY_ATTEMPTS}",
        }
    
    except Exception as e:
        logger.error(f"❌ Retry failed for {payout_id}: {str(e)}")
        raise PaymentInitializationError(f"Retry failed: {str(e)}")


async def move_to_escrow(payout_id: str, reason: str = "max_retries_exceeded") -> Dict:
    """
    Move a failed payout to escrow (48-hour correction window).
    
    After max retries exhausted:
    1. Funds held in escrow (48 hours)
    2. Worker notified to verify/correct UPI details
    3. Worker submits correction via APPEAL command
    4. Payout retried after correction
    5. If uncorrected after 48h → Manual review or return to account
    
    Args:
        payout_id (str): Payout ID
        reason (str): Reason for escrow
        
    Returns:
        Dict with escrow details
    """
    
    try:
        sb = get_supabase()
        
        escrow_until = datetime.now(timezone.utc) + timedelta(hours=ESCROW_HOLD_HOURS)
        
        sb.table("payouts").update({
            "status": "escrow",
            "escrow_reason": reason,
            "escrow_until": escrow_until.isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", payout_id).execute()
        
        logger.warning(f"Payout {payout_id} moved to escrow until {escrow_until}")
        
        return {
            "payout_id": payout_id,
            "status": "escrow",
            "escrow_until": escrow_until.isoformat(),
            "hours_to_resolve": ESCROW_HOLD_HOURS,
            "reason": reason,
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to move to escrow: {str(e)}")
        raise PaymentInitializationError(f"Escrow move failed: {str(e)}")


# ─── Razorpay API Helpers ──────────────────────────────────────────────────

async def _call_razorpay_payout(
    upi_id: str,
    amount: float,
    worker_id: str,
    idempotency_key: str,
) -> str:
    """
    Make Razorpay UPI payout request.
    
    In TEST mode: Uses test credentials, payouts succeed instantly
    In PRODUCTION: Uses live Razorpay credentials, real UPI transfer
    
    Args:
        upi_id (str): UPI ID
        amount (float): Amount in INR
        worker_id (str): Worker ID (for reference)
        idempotency_key (str): For deduplication
        
    Returns:
        str: Razorpay payout ID
        
    Raises:
        PaymentInitializationError: If API call fails
    """
    
    try:
        # In TEST mode, return mock payout ID
        # In production, call actual Razorpay API
        
        if RAZORPAY_TEST_MODE:
            # Mock successful payout for testing
            mock_payout_id = f"payout_test_{idempotency_key[:16]}"
            logger.info(f"[TEST MODE] Razorpay payout: {mock_payout_id}")
            return mock_payout_id
        
        # ─── PRODUCTION: Real Razorpay API Call ─────────────────────────────
        
        auth = (settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        
        payload = {
            "account_number": settings.RAZORPAY_ACCOUNT_NUMBER,  # Contact Razorpay support
            "fund_account_id": upi_id,  # UPI would need separate fund account creation
            "amount": int(amount * 100),  # In paise
            "currency": "INR",
            "mode": "UPI",  # Direct UPI transfer
            "purpose": "partner_income_protection",
            "description": f"GigKavach disruption payout — {worker_id}",
            "reference_id": idempotency_key,
            "metadata": {
                "worker_id": worker_id,
                "platform": "gigkavach",
            },
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{RAZORPAY_BASE_URL}/payouts",
                auth=auth,
                json=payload,
                timeout=10.0,
            )
        
        if response.status_code not in [200, 201]:
            raise PaymentInitializationError(
                f"Razorpay API error: {response.status_code} — {response.text}"
            )
        
        data = response.json()
        payout_id = data.get("id")
        
        logger.info(f"✅ Razorpay payout created: {payout_id}")
        return payout_id
    
    except Exception as e:
        logger.error(f"❌ Razorpay payout failed: {str(e)}")
        raise PaymentInitializationError(f"Razorpay payout failed: {str(e)}")


async def _get_razorpay_payout_status(payout_id: str) -> Dict:
    """
    Get real-time payout status from Razorpay.
    
    Args:
        payout_id (str): Razorpay payout ID (not GigKavach ID)
        
    Returns:
        Dict with Razorpay payout state and details
    """
    
    try:
        in_test_mode = RAZORPAY_TEST_MODE
        
        if in_test_mode:
            # Mock status for testing
            return {"state": "processed", "id": payout_id}
        
        auth = (settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{RAZORPAY_BASE_URL}/payouts/{payout_id}",
                auth=auth,
                timeout=5.0,
            )
        
        if response.status_code != 200:
            raise PayoutStatusError(f"Razorpay API error: {response.status_code}")
        
        return response.json()
    
    except Exception as e:
        logger.error(f"❌ Failed to get Razorpay status: {str(e)}")
        raise PayoutStatusError(str(e))


def _generate_idempotency_key(
    worker_id: str,
    amount: float,
    suffix: str = "",
) -> str:
    """
    Generate a unique idempotency key for payout deduplication.
    
    Razorpay uses this to prevent duplicate payouts if our request is retried.
    
    Args:
        worker_id (str): Worker ID
        amount (float): Payout amount
        suffix (str): Optional suffix (e.g., for retries)
        
    Returns:
        str: 32-char hex idempotency key
    """
    
    id_string = f"{worker_id}_{amount}_{datetime.now(timezone.utc).isoformat()}{suffix}"
    hash_obj = hashlib.md5(id_string.encode())
    return hash_obj.hexdigest()


# ─── Example Usage & Testing ───────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio
    
    async def main():
        print("\n" + "="*60)
        print("  Payment Service Test")
        print("="*60)
        
        try:
            # Example payout initiation
            result = await initiate_payout(
                worker_id="w_test_001",
                upi_id="test@upi",
                amount=280.0,
                dci_score=72,
                payout_reason="rainfall_disruption",
            )
            
            print(f"\n✅ Payout Initiated:")
            print(f"   Payout ID: {result['payout_id']}")
            print(f"   Razorpay ID: {result['razorpay_payout_id']}")
            print(f"   Amount: ₹{result['amount_initiated']}")
            print(f"   Status: {result['status']}")
            print(f"   Fraud Tier: {result['fraud']['tier']}")
            
            # Check status
            if result['payout_id']:
                status = await get_payout_status(result['payout_id'])
                print(f"\n   Current Status: {status.get('status', 'unknown')}")
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
        
        print("\n" + "="*60)
    
    asyncio.run(main())
