"""
tests/test_midnight_split.py
──────────────────────────────
Verification for Section 12: Midnight-Split Shift Support.
Tests a disruption spanning across midnight (11 PM to 2 AM).
"""
import sys
import os
import asyncio
from datetime import datetime, timezone

# Ensure backend is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.payouts import calculate_payout, PayoutRequest

async def run_split_tests():
    print("🚀 STARTING MIDNIGHT-SPLIT VALIDATION...")
    print("-----------------------------------------")
    
    # CASE: 11:00 PM (Monday) to 2:00 AM (Tuesday)
    # Total duration: 3.0 hours
    # Expected: 1 hour on Day 1, 2 hours on Day 2.
    
    # Using UTC for consistency in test
    start_time = datetime(2026, 7, 13, 23, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2026, 7, 14, 2, 0, 0, tzinfo=timezone.utc)
    
    req = PayoutRequest(
        worker_id="W102", # Night Shift worker (0-8)
        disruption_start=start_time,
        disruption_end=end_time,
        dci_score=70
    )
    
    res = await calculate_payout(req)
    
    print(f"Disruption: {start_time.isoformat()} TO {end_time.isoformat()}")
    print(f"Total Payout: {res.payout_amount}")
    print(f"Total Duration: {res.breakdown['total_duration_hours']} hours")
    
    split = res.breakdown["daily_split"]
    print("\nDaily Breakdown:")
    for day in split:
        print(f"  - {day['date']}: {day['hours']} hours | Payout: {day['payout']}")

    # Validation
    if len(split) == 2 and res.breakdown['total_duration_hours'] == 3.0:
        print("\n✅ PASSED: Disruption successfully split across midnight.")
        if split[0]['hours'] == 1.0 and split[1]['hours'] == 2.0:
            print("✅ PASSED: Hourly allocation per day is mathematically correct.")
    else:
        print("\n❌ FAILED: Split logic did not trigger correctly.")

if __name__ == "__main__":
    asyncio.run(run_split_tests())
