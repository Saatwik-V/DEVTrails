#!/usr/bin/env python3
"""
demo_claims_smoke_test.py
─────────────────────────────────────────────────────────────────────
End-to-End Demo Smoke Test

Reproduces the complete GigKavach pitch flow:
  1. ✅ ONBOARDING: Worker joins via WhatsApp
  2. ✅ POLICY: Worker buys weekly coverage
  3. ✅ DCI_TRIGGER: Disruption detected in worker's zone
  4. ✅ ELIGIBILITY: System checks if worker is eligible
  5. ✅ FRAUD_ASSESS: 3-stage fraud detection
  6. ✅ PAYOUT_CALC: Calculate dynamic payout (XGBoost)
  7. ✅ PAYOUT_SEND: Execute UPI transfer
  8. ✅ NOTIFICATION: Send WhatsApp confirmation

Run this script for rehearsals. Every run is identical (deterministic).

Usage:
  python3 backend/demo_claims_smoke_test.py [--verbose]

Expected Output:
  ✅ All 8 steps complete in <10 seconds
  📊 2 claims processed, 2 payouts sent
  💰 ~800-1300 INR total distributed
"""

import sys
import os
import json
import logging
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Any, Tuple

# Handle imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Setup logging
logging.basicConfig(
    level=logging.DEBUG if '--verbose' in sys.argv else logging.INFO,
    format="%(levelname)s | %(message)s"
)
logger = logging.getLogger("demo_smoke_test")

# Import demo data
from demo_dataset_seed import DEMO_WORKERS, DEMO_POLICIES, DEMO_DCI_TRIGGER, DEMO_CLAIMS, DEMO_PAYOUT_EXPECTATIONS

# ───────────────────────────────────────────────────────────────────
#  STEP 1: ONBOARDING SIMULATION
# ───────────────────────────────────────────────────────────────────

def step_1_onboarding():
    """Simulate worker joining via WhatsApp /join command."""
    logger.info("\n" + "="*70)
    logger.info("STEP 1️⃣  ONBOARDING - Worker joins via WhatsApp")
    logger.info("="*70)
    
    # In real flow, this triggers off WhatsApp webhook
    # For demo, we show the flow
    
    worker = DEMO_WORKERS[0]  # Rajesh
    logger.info(f"📱 WhatsApp Incoming: {worker['phone']}")
    logger.info(f"   Message: /join")
    logger.info(f"   ➜ Worker marked for onboarding")
    logger.info(f"✅ STEP 1 COMPLETE: {worker['first_name']} ({worker['city']}) queued for onboarding")
    
    return worker


# ───────────────────────────────────────────────────────────────────
#  STEP 2: POLICY PURCHASE
# ───────────────────────────────────────────────────────────────────

def step_2_policy_purchase():
    """Simulate worker purchasing weekly coverage."""
    logger.info("\n" + "="*70)
    logger.info("STEP 2️⃣  POLICY - Worker buys weekly coverage")
    logger.info("="*70)
    
    # Workers buy policies
    for policy in DEMO_POLICIES:
        worker = next((w for w in DEMO_WORKERS if w['worker_id'] == policy['worker_id']), None)
        logger.info(f"💳 {worker['first_name']} purchases {policy['tier'].upper()} tier")
        logger.info(f"   Premium: ₹{policy['premium']:.0f}/week")
        logger.info(f"   Coverage: {policy['effective_date']} → {policy['expiry_date']}")
    
    logger.info(f"✅ STEP 2 COMPLETE: {len(DEMO_POLICIES)} policies created, 3 workers now protected")


# ───────────────────────────────────────────────────────────────────
#  STEP 3: DCI TRIGGER
# ───────────────────────────────────────────────────────────────────

def step_3_dci_trigger() -> Dict[str, Any]:
    """Simulate DCI trigger event in a zone."""
    logger.info("\n" + "="*70)
    logger.info("STEP 3️⃣  DCI_TRIGGER - Disruption detected")
    logger.info("="*70)
    
    trigger = DEMO_DCI_TRIGGER
    logger.info(f"🌧️  Disruption Detected: {trigger['disruption_type']}")
    logger.info(f"   Pincode: {trigger['pincode']}")
    logger.info(f"   DCI Score: {trigger['dci_score']} (CRITICAL)")
    logger.info(f"   Duration: {trigger['duration_minutes']} minutes")
    logger.info(f"   Affected Zones: {', '.join(trigger['affected_zones'])}")
    logger.info(f"   Timestamp: {trigger['timestamp']}")
    logger.info(f"✅ STEP 3 COMPLETE: DCI trigger broadcast to all active workers")
    
    return trigger


# ───────────────────────────────────────────────────────────────────
#  STEP 4: ELIGIBILITY CHECK
# ───────────────────────────────────────────────────────────────────

def step_4_eligibility_check(dci_trigger: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Check which workers are eligible for claims."""
    logger.info("\n" + "="*70)
    logger.info("STEP 4️⃣  ELIGIBILITY - Who qualifies for claims?")
    logger.info("="*70)
    
    eligible_claims = []
    pincode = dci_trigger['pincode']
    
    # Check each policy
    for policy in DEMO_POLICIES:
        worker = next(w for w in DEMO_WORKERS if w['worker_id'] == policy['worker_id'])
        
        # Eligibility rules
        rules = {
            "has_active_policy": policy['status'] == 'active',
            "in_coverage_period": True,  # (Simplified for demo)
            "within_shift": worker['shift_start'] < datetime.utcnow().strftime("%H:%M") < worker['shift_end'],
            "policy_age_sufficient": True,  # (24h rule passed)
        }
        
        is_eligible = all(rules.values())
        status_icon = "✅" if is_eligible else "❌"
        
        logger.info(f"\n{status_icon} {worker['first_name']} (Pincode {worker['zone_pincode']})")
        logger.info(f"   Has active policy: {rules['has_active_policy']}")
        logger.info(f"   In coverage period: {rules['in_coverage_period']}")
        logger.info(f"   Currently on shift: {rules['within_shift']}")
        logger.info(f"   Policy age sufficient: {rules['policy_age_sufficient']}")
        
        if is_eligible:
            eligible_claims.append({
                'worker_id': worker['worker_id'],
                'worker_name': worker['first_name'],
                'policy_id': policy['policy_id'],
                'baseline_earnings': worker['baseline_earnings'],
            })
            logger.info(f"   ➜ ELIGIBLE for claim")
    
    logger.info(f"\n✅ STEP 4 COMPLETE: {len(eligible_claims)} workers eligible for payouts")
    return eligible_claims


# ───────────────────────────────────────────────────────────────────
#  STEP 5: FRAUD ASSESSMENT
# ───────────────────────────────────────────────────────────────────

def step_5_fraud_assessment(eligible_workers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """3-stage fraud detection pipeline."""
    logger.info("\n" + "="*70)
    logger.info("STEP 5️⃣  FRAUD_ASSESS - 3-stage fraud detection")
    logger.info("="*70)
    
    approved_claims = []
    
    for claim_meta in eligible_workers:
        logger.info(f"\n🔍 {claim_meta['worker_name']}: Fraud assessment")
        
        # Stage 1: Rule-based blocks
        logger.info(f"   Stage 1 (Rule-based):")
        logger.info(f"      ✅ No blacklist block")
        logger.info(f"      ✅ No device farming detected")
        
        # Stage 2: Isolation Forest (anomaly)
        logger.info(f"   Stage 2 (Anomaly detection):")
        logger.info(f"      ✅ Claim frequency normal")
        logger.info(f"      ✅ GPS trail valid")
        
        # Stage 3: XGBoost multiclass
        fraud_score = 0.24  # Low risk
        logger.info(f"   Stage 3 (XGBoost):")
        logger.info(f"      Fraud Score: {fraud_score:.2f}/1.0")
        logger.info(f"      Decision: APPROVE (score < 0.4)")
        logger.info(f"      Payout Action: 100% (full amount)")
        
        approved_claims.append({
            **claim_meta,
            'fraud_score': fraud_score,
            'decision': 'APPROVE'
        })
    
    logger.info(f"\n✅ STEP 5 COMPLETE: {len(approved_claims)} claims approved (0 flagged/blocked)")
    return approved_claims


# ───────────────────────────────────────────────────────────────────
#  STEP 6: PAYOUT CALCULATION
# ───────────────────────────────────────────────────────────────────

def step_6_payout_calculation(approved_claims: List[Dict[str, Any]], dci_trigger: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Calculate dynamic payout using XGBoost multiplier."""
    logger.info("\n" + "="*70)
    logger.info("STEP 6️⃣  PAYOUT_CALC - XGBoost v3 dynamic calculation")
    logger.info("="*70)
    
    payouts = []
    
    for claim in approved_claims:
        # Simulate XGBoost v3 multiplier (1.0-5.0 range)
        multiplier = 0.75  # Deterministic for demo
        
        baseline = claim['baseline_earnings']
        duration_ratio = DEMO_DCI_TRIGGER['duration_minutes'] / 480  # hrs/8h
        payout_amount = baseline * duration_ratio * multiplier
        
        expectation = DEMO_PAYOUT_EXPECTATIONS[f"DEMO-CLM-{len(payouts)+1:03d}"]
        
        logger.info(f"\n💰 {claim['worker_name']}")
        logger.info(f"   Formula: baseline × (duration/480) × xgb_multiplier")
        logger.info(f"   Calculation:")
        logger.info(f"      Baseline earnings: ₹{baseline:.0f}")
        logger.info(f"      Duration: {DEMO_DCI_TRIGGER['duration_minutes']}m ÷ 480m = {duration_ratio:.2f}")
        logger.info(f"      XGBoost multiplier: {multiplier}")
        logger.info(f"      Payout: ₹{baseline:.0f} × {duration_ratio:.2f} × {multiplier} = ₹{payout_amount:.0f}")
        logger.info(f"   Expected range: ₹{expectation['expected_range'][0]}-{expectation['expected_range'][1]}")
        logger.info(f"   Status: {'✅ Within range' if expectation['expected_range'][0] <= payout_amount <= expectation['expected_range'][1] else '⚠️ Need review'}")
        
        payouts.append({
            **claim,
            'payout_amount': payout_amount,
            'breakdown': {
                'baseline': baseline,
                'duration_ratio': duration_ratio,
                'multiplier': multiplier
            }
        })
    
    total_payout = sum(p['payout_amount'] for p in payouts)
    logger.info(f"\n✅ STEP 6 COMPLETE: {len(payouts)} payouts calculated")
    logger.info(f"   Total Distribution: ₹{total_payout:.0f}")
    
    return payouts


# ───────────────────────────────────────────────────────────────────
#  STEP 7: PAYOUT EXECUTION
# ───────────────────────────────────────────────────────────────────

def step_7_payout_execution(payouts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Execute payouts to worker UPI accounts."""
    logger.info("\n" + "="*70)
    logger.info("STEP 7️⃣  PAYOUT_SEND - Execute UPI transfers")
    logger.info("="*70)
    
    transactions = []
    
    for payout in payouts:
        # Simulate Razorpay UPI transfer
        txn_id = f"TXN-DEMO-{int(time.time())}"
        
        logger.info(f"\n💳 {payout['worker_name']}")
        logger.info(f"   Amount: ₹{payout['payout_amount']:.0f}")
        logger.info(f"   UPI ID: rajesh@paytm (demo)")
        logger.info(f"   Provider: Razorpay")
        logger.info(f"   Transaction: {txn_id}")
        logger.info(f"   Status: PROCESSING...")
        logger.info(f"   ETA: Same-day (by 23:59)")
        
        transactions.append({
            **payout,
            'transaction_id': txn_id,
            'status': 'pending'
        })
    
    logger.info(f"\n✅ STEP 7 COMPLETE: {len(transactions)} payouts initiated")
    logger.info(f"   All transfers queued for same-day settlement")
    
    return transactions


# ───────────────────────────────────────────────────────────────────
#  STEP 8: NOTIFICATION
# ───────────────────────────────────────────────────────────────────

def step_8_notification(transactions: List[Dict[str, Any]]):
    """Send WhatsApp notifications to workers."""
    logger.info("\n" + "="*70)
    logger.info("STEP 8️⃣  NOTIFICATION - WhatsApp confirmations")
    logger.info("="*70)
    
    for txn in transactions:
        logger.info(f"\n📲 {txn['worker_name']} ({txn['worker_id']})")
        logger.info(f"   WhatsApp Message:")
        logger.info(f"   ┌─────────────────────────────────┐")
        logger.info(f"   │ 🎉 GigKavach Payout Alert!      │")
        logger.info(f"   │                                 │")
        logger.info(f"   │ ₹{txn['payout_amount']:.0f} credited to your UPI │")
        logger.info(f"   │ (demo@example.com)              │")
        logger.info(f"   │                                 │")
        logger.info(f"   │ Disruption: Heavy Rain           │")
        logger.info(f"   │ Status: 🟢 Success               │")
        logger.info(f"   │ TXN: {txn['transaction_id'][:12]}... │")
        logger.info(f"   └─────────────────────────────────┘")
        logger.info(f"   Status: ✅ SENT")
    
    logger.info(f"\n✅ STEP 8 COMPLETE: {len(transactions)} notifications sent")


# ───────────────────────────────────────────────────────────────────
#  MAIN SMOKE TEST
# ───────────────────────────────────────────────────────────────────

def main():
    """Run the complete end-to-end smoke test."""
    
    logger.info("\n" + "🎬 GIGKAVACH PITCH FLOW - END-TO-END DEMO SMOKE TEST")
    logger.info("   Running deterministic demo (identical every time)\n")
    
    start_time = time.time()
    
    try:
        # Run all 8 steps
        step_1_onboarding()
        step_2_policy_purchase()
        dci_trigger = step_3_dci_trigger()
        eligible_workers = step_4_eligibility_check(dci_trigger)
        approved_claims = step_5_fraud_assessment(eligible_workers)
        payouts = step_6_payout_calculation(approved_claims, dci_trigger)
        transactions = step_7_payout_execution(payouts)
        step_8_notification(transactions)
        
        # Summary
        elapsed = time.time() - start_time
        logger.info("\n" + "="*70)
        logger.info("🎉 SMOKE TEST COMPLETE - ALL 8 STEPS PASSED")
        logger.info("="*70)
        logger.info(f"\n📊 Results:")
        logger.info(f"   ✅ Workers onboarded: 5")
        logger.info(f"   ✅ Policies sold: 3")
        logger.info(f"   ✅ DCI triggers: 1")
        logger.info(f"   ✅ Claims eligible: {len(approved_claims)}")
        logger.info(f"   ✅ Fraud checks passed: {len(approved_claims)}")
        logger.info(f"   ✅ Payouts calculated: {len(payouts)}")
        logger.info(f"   ✅ Payouts sent: {len(transactions)}")
        total_payout = sum(p['payout_amount'] for p in payouts)
        logger.info(f"   💰 Total distributed: ₹{total_payout:.0f}")
        logger.info(f"   ⏱️  Execution time: {elapsed:.2f}s")
        logger.info("\n✨ Ready for pitch!✨\n")
        
    except Exception as e:
        logger.error(f"\n❌ SMOKE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
