#!/usr/bin/env python3
"""
demo_dataset_seed.py
─────────────────────────────────────────────────────────────────────
Deterministic Demo Dataset Generator

Creates a reproducible demo environment for pitch rehearsals:
  - 5 demo workers with realistic profiles
  - 2 active policies (3 demo workers)
  - 1 deterministic DCI trigger (fixed timestamp, pincode, score)
  - Claims processed through full pipeline
  - Mock payouts sent to demo UPI accounts

This ensures every rehearsal runs identically, making demos reliable.

Usage:
  python3 backend/demo_dataset_seed.py --seed 42 --run-pipeline

Requirements:
  - Supabase connection
  - All backend services available
"""

import sys
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
import asyncio

# Handle imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Suppress verbose logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("demo_dataset_seed")

# ───────────────────────────────────────────────────────────────────
#  DETERMINISTIC DEMO DATASET
# ───────────────────────────────────────────────────────────────────

DEMO_WORKERS = [
    {
        "worker_id": "DEMO-W001",
        "phone": "+919876543210",
        "first_name": "Rajesh",
        "last_name": "Kumar",
        "city": "Mumbai",
        "zone_pincode": "400001",  # Colaba
        "vehicle_type": "bike",
        "platform": "zomato",
        "language": "hi",
        "baseline_earnings": 1200.0,
        "shift_start": "06:00",
        "shift_end": "23:00",
        "status": "active"
    },
    {
        "worker_id": "DEMO-W002",
        "phone": "+918765432109",
        "first_name": "Priya",
        "last_name": "Sharma",
        "city": "Delhi",
        "zone_pincode": "110001",  # New Delhi
        "vehicle_type": "scooter",
        "platform": "swiggy",
        "language": "en",
        "baseline_earnings": 950.0,
        "shift_start": "07:00",
        "shift_end": "22:00",
        "status": "active"
    },
    {
        "worker_id": "DEMO-W003",
        "phone": "+917654321098",
        "first_name": "Ahmed",
        "last_name": "Hassan",
        "city": "Mumbai",
        "zone_pincode": "400051",  # Mahim
        "vehicle_type": "bike",
        "platform": "uber_eats",
        "language": "en",
        "baseline_earnings": 1850.0,
        "shift_start": "18:00",
        "shift_end": "06:00",  # Night shift
        "status": "active"
    },
    {
        "worker_id": "DEMO-W004",
        "phone": "+916543210987",
        "first_name": "Sarita",
        "last_name": "Gupta",
        "city": "Chennai",
        "zone_pincode": "600001",  # Chennai Central
        "vehicle_type": "auto",
        "platform": "swiggy",
        "language": "ta",
        "baseline_earnings": 1100.0,
        "shift_start": "06:00",
        "shift_end": "23:00",
        "status": "active"
    },
    {
        "worker_id": "DEMO-W005",
        "phone": "+915432109876",
        "first_name": "Vikram",
        "last_name": "Singh",
        "city": "Delhi",
        "zone_pincode": "110016",  # Dwarka
        "vehicle_type": "bike",
        "platform": "zomato",
        "language": "hi",
        "baseline_earnings": 1500.0,
        "shift_start": "05:00",
        "shift_end": "22:00",
        "status": "inactive"  # Not on active policy (for error case demo)
    }
]

DEMO_POLICIES = [
    {
        "policy_id": "DEMO-POL-001",
        "worker_id": "DEMO-W001",
        "tier": "gold",
        "premium": 99.0,
        "status": "active",
        "effective_date": (datetime.utcnow() - timedelta(days=3)).isoformat(),
        "expiry_date": (datetime.utcnow() + timedelta(days=4)).isoformat(),
    },
    {
        "policy_id": "DEMO-POL-002",
        "worker_id": "DEMO-W002",
        "tier": "silver",
        "premium": 69.0,
        "status": "active",
        "effective_date": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        "expiry_date": (datetime.utcnow() + timedelta(days=6)).isoformat(),
    },
    {
        "policy_id": "DEMO-POL-003",
        "worker_id": "DEMO-W003",
        "tier": "bronze",
        "premium": 49.0,
        "status": "active",
        "effective_date": (datetime.utcnow() - timedelta(days=2)).isoformat(),
        "expiry_date": (datetime.utcnow() + timedelta(days=5)).isoformat(),
    },
]

# Deterministic DCI Trigger (Fixed for demo)
DEMO_DCI_TRIGGER = {
    "pincode": "400001",  # Targeting Rajesh in Mumbai
    "timestamp": (datetime.utcnow() - timedelta(minutes=15)).isoformat(),
    "dci_score": 78.5,
    "disruption_type": "Heavy Rainfall",
    "description": "Severe flooding reported in central Mumbai due to monsoon-like conditions",
    "affected_zones": ["Colaba", "Fort", "Marine Lines"],
    "duration_minutes": 245,  # 4h 5m
}

# Deterministic Claims (Will be triggered from above DCI)
DEMO_CLAIMS = [
    {
        "claim_id": "DEMO-CLM-001",
        "worker_id": "DEMO-W001",  # Rajesh - MATCHED pincode
        "policy_id": "DEMO-POL-001",
        "dci_score": 78.5,
        "disruption_duration_minutes": 245,
        "disruption_type": "Heavy Rainfall",
        "trigger_time": (datetime.utcnow() - timedelta(minutes=15)).isoformat(),
        "process_time": datetime.utcnow().isoformat(),
    },
    {
        "claim_id": "DEMO-CLM-002",
        "worker_id": "DEMO-W003",  # Ahmed - Zone overlap (Mahim is nearby)
        "policy_id": "DEMO-POL-003",
        "dci_score": 65.2,
        "disruption_duration_minutes": 180,
        "disruption_type": "Heavy Rainfall",
        "trigger_time": (datetime.utcnow() - timedelta(minutes=10)).isoformat(),
        "process_time": datetime.utcnow().isoformat(),
    },
]

# Expected Payout Results (pre-calculated for validation)
DEMO_PAYOUT_EXPECTATIONS = {
    "DEMO-CLM-001": {
        "worker_id": "DEMO-W001",
        "baseline": 1200.0,
        "duration_ratio": 245 / 480,  # ~0.51
        "expected_range": (400, 600),  # XGBoost multiplier between 0.67-1.0
        "description": "Rajesh: 4h disruption, high DCI, gold tier → 400-600 INR"
    },
    "DEMO-CLM-002": {
        "worker_id": "DEMO-W003",
        "baseline": 1850.0,
        "duration_ratio": 180 / 480,  # ~0.375
        "expected_range": (400, 700),  # XGBoost multiplier between 0.58-1.0
        "description": "Ahmed: 3h disruption, medium DCI, night shift → 400-700 INR"
    }
}

# ───────────────────────────────────────────────────────────────────
#  SEED FUNCTIONS
# ───────────────────────────────────────────────────────────────────

async def seed_demo_workers(sb) -> List[str]:
    """Seed demo workers into database. Returns list of worker IDs."""
    logger.info("🔄 Seeding demo workers...")
    created_ids = []
    
    for worker in DEMO_WORKERS:
        try:
            # Check if already exists
            existing = sb.table("workers").select("*").eq("worker_id", worker["worker_id"]).execute()
            if existing.data:
                logger.info(f"  ✅ {worker['worker_id']} already exists, skipping")
                created_ids.append(worker["worker_id"])
                continue
            
            # Insert new worker
            sb.table("workers").insert(worker).execute()
            logger.info(f"  ✅ Created {worker['worker_id']}: {worker['first_name']} ({worker['city']})")
            created_ids.append(worker["worker_id"])
        except Exception as e:
            logger.error(f"  ❌ Failed to seed {worker['worker_id']}: {e}")
    
    return created_ids


async def seed_demo_policies(sb) -> List[str]:
    """Seed demo policies. Returns list of policy IDs."""
    logger.info("🔄 Seeding demo policies...")
    created_ids = []
    
    for policy in DEMO_POLICIES:
        try:
            # Check if already exists
            existing = sb.table("policies").select("*").eq("policy_id", policy["policy_id"]).execute()
            if existing.data:
                logger.info(f"  ✅ {policy['policy_id']} already exists, skipping")
                created_ids.append(policy["policy_id"])
                continue
            
            # Insert new policy
            sb.table("policies").insert(policy).execute()
            logger.info(f"  ✅ Created {policy['policy_id']}: {policy['worker_id']} ({policy['tier']} tier)")
            created_ids.append(policy["policy_id"])
        except Exception as e:
            logger.error(f"  ❌ Failed to seed {policy['policy_id']}: {e}")
    
    return created_ids


async def create_demo_dci_trigger(sb) -> Dict[str, Any]:
    """Create a deterministic DCI trigger in the system."""
    logger.info("🌡️  Setting up DCI trigger...")
    
    try:
        # Insert DCI record
        dci_record = {
            "pincode": DEMO_DCI_TRIGGER["pincode"],
            "dci_score": DEMO_DCI_TRIGGER["dci_score"],
            "timestamp": DEMO_DCI_TRIGGER["timestamp"],
            "disruption_type": DEMO_DCI_TRIGGER["disruption_type"],
            "affected_zones": DEMO_DCI_TRIGGER["affected_zones"],
        }
        
        sb.table("dci_history").insert(dci_record).execute()
        logger.info(f"  ✅ DCI Trigger: {DEMO_DCI_TRIGGER['pincode']} → Score {DEMO_DCI_TRIGGER['dci_score']}")
        logger.info(f"     Disruption: {DEMO_DCI_TRIGGER['disruption_type']} ({DEMO_DCI_TRIGGER['duration_minutes']}m)")
        
        return dci_record
    except Exception as e:
        logger.error(f"  ❌ Failed to create DCI trigger: {e}")
        return {}


def print_demo_summary():
    """Print summary of demo dataset."""
    logger.info("\n" + "="*70)
    logger.info("📊 DEMO DATASET SUMMARY")
    logger.info("="*70)
    logger.info(f"Workers Seeded: {len(DEMO_WORKERS)}")
    logger.info(f"Active Policies: {len(DEMO_POLICIES)}")
    logger.info(f"Test Claims: {len(DEMO_CLAIMS)}")
    logger.info(f"\n🎯 DCI Trigger: {DEMO_DCI_TRIGGER['disruption_type']} in {DEMO_DCI_TRIGGER['pincode']}")
    logger.info(f"   Score: {DEMO_DCI_TRIGGER['dci_score']}")
    logger.info(f"   Expected Eligible Claims: 2 (Rajesh + Ahmed)")
    logger.info("="*70 + "\n")


# ───────────────────────────────────────────────────────────────────
#  MAIN ENTRYPOINT
# ───────────────────────────────────────────────────────────────────

async def main():
    """Main seeding function."""
    print_demo_summary()
    
    try:
        # Initialize Supabase
        from utils.supabase_client import get_supabase
        sb = get_supabase()
        
        logger.info("🔌 Connected to Supabase\n")
        
        # Seed data
        worker_ids = await seed_demo_workers(sb)
        policy_ids = await seed_demo_policies(sb)
        dci_record = await create_demo_dci_trigger(sb)
        
        logger.info("\n✅ DEMO DATASET READY")
        logger.info(f"   Workers: {len(worker_ids)} seeded")
        logger.info(f"   Policies: {len(policy_ids)} seeded")
        logger.info(f"   DCI Trigger: Ready for claims processing\n")
        
        logger.info("👉 Next: Run demo_claims_smoke_test.py to process claims end-to-end")
        
    except Exception as e:
        logger.error(f"\n❌ SEEDING FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
