"""
tests/test_surge_multiplier.py
───────────────────────────────
Validation script for the Platform Surge Multiplier logic.
Tests peak hours, DCI correlation, shift overlap, and earnings fingerprint.
"""
import sys
import os
import asyncio
from datetime import datetime

# Ensure the backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.payouts import calculate_payout, PayoutRequest

async def run_surge_tests():
    print("🚀 STARTING SURGE MULTIPLIER VALIDATION...")
    print("------------------------------------------")
    
    # CASE 1: Worker W101 (Evening Shift) during DINNER SURGE (8 PM)
    # W101 shift: 18-23.  8 PM is in dinner surge (19-22).
    # W101 history: Habitual Surge Worker (Velocity 260 > 187*1.3)
    start_time = datetime(2026, 7, 14, 20, 0, 0) # Tuesday 8 PM
    end_time = datetime(2026, 7, 14, 23, 0, 0)
    
    req_1 = PayoutRequest(
        worker_id="W101",
        disruption_start=start_time,
        disruption_end=end_time,
        dci_score=75 # High disruption
    )
    
    res_1 = await calculate_payout(req_1)
    surge_mult_1 = res_1.breakdown["platform_surge_multiplier"]
    
    print(f"CASE 1 (W101 Dinner Peak - Habitual Surge Worker):")
    print(f"  -> Detected Mult: {surge_mult_1}x")
    print(f"  -> Result: {'✅ PASSED' if surge_mult_1 > 1.0 else '❌ FAILED (Expected > 1.0)'}")

    # CASE 2: Worker W100 (Morning Shift) during same DINNER SURGE (8 PM)
    # W100 shift: 9 AM - 5 PM. 8 PM is OUTSIDE shift.
    # Prediction: No surge multiplier should be applied.
    req_2 = PayoutRequest(
        worker_id="W100",
        disruption_start=start_time,
        disruption_end=end_time,
        dci_score=75
    )
    
    res_2 = await calculate_payout(req_2)
    surge_mult_2 = res_2.breakdown["platform_surge_multiplier"]
    
    print(f"\nCASE 2 (W100 Morning Shift during Evening Surge):")
    print(f"  -> Detected Mult: {surge_mult_2}x")
    print(f"  -> Result: {'✅ PASSED' if surge_mult_2 == 1.0 else '❌ FAILED (Shift overlap check failed)'}")

    # CASE 3: Worker W102 (Night Shift) during OFF-PEAK Time (4 AM)
    # W102 shift: 0-8 AM. 4 AM is in shift but NOT a peak surge window.
    start_time_3 = datetime(2026, 7, 14, 4, 0, 0)
    end_time_3 = datetime(2026, 7, 14, 6, 0, 0)
    
    req_3 = PayoutRequest(
        worker_id="W102",
        disruption_start=start_time_3,
        disruption_end=end_time_3,
        dci_score=85 # Catastrophic
    )
    
    res_3 = await calculate_payout(req_3)
    surge_mult_3 = res_3.breakdown["platform_surge_multiplier"]
    
    print(f"\nCASE 3 (W102 Night Shift during 4 AM - Off Peak):")
    print(f"  -> Detected Mult: {surge_mult_3}x")
    print(f"  -> Result: {'✅ PASSED' if surge_mult_3 == 1.0 else '❌ FAILED (Surge triggered incorrectly during off-peak)'}")

if __name__ == "__main__":
    asyncio.run(run_surge_tests())
