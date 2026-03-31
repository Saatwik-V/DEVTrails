"""
cron/settlement_service.py — Daily Payout Settlement
────────────────────────────────────────────────────
Runs at 11:55 PM Daily.
Aggregates all disruption data for the day, calculates total hours per worker, 
and triggers the final payout settlement via api/payouts.py.
"""
import logging
import asyncio
from datetime import datetime, time, timedelta, timezone
from api.payouts import calculate_payout, PayoutRequest
from services.eligibility_service import check_eligibility, WORKER_POLICIES_DB

logger = logging.getLogger("gigkavach.settlement")

async def run_daily_settlement():
    """Main settlement loop triggered by APScheduler at 11:55 PM."""
    logger.info("🌓 SYSTEM SETTLEMENT INITIATED (11:55 PM)...")

    # 1. Determine the day boundary
    now = datetime.now(timezone.utc)
    day_start = datetime.combine(now.date(), time.min).replace(tzinfo=timezone.utc)

    # 2. Fetch disruption windows from DCI logs (Task 7: DB-backed)
    disruption_windows = _get_todays_disruptions(day_start)
    if not disruption_windows:
        logger.info("[SETTLEMENT] No disruption events today. Exiting.")
        return

    # 3. Fetch active workers with their policies (Task 7: DB-backed)
    workers = _get_active_worker_policies()
    if not workers:
        logger.warning("[SETTLEMENT] No active workers found. Exiting.")
        return

    settled_count = 0
    rejected_count = 0

    # 4. Iterate through all workers with active policies
    for worker in workers:
        worker_id = worker["id"]
        active_policies = [
            p for p in (worker.get("policies") or []) if p.get("is_active")
        ]
        if not active_policies:
            continue

        policy = active_policies[0]  # Use most recent active policy

        for d_start, d_end, d_score in disruption_windows:
            # 5. Eligibility check firewall (24-hr coverage delay + shift alignment)
            eligible, reason = check_eligibility(worker_id, dci_event={
                "disruption_start": d_start.isoformat(),
                "shift_affected":   policy.get("shift", "day"),
                "dci_score":        d_score,
            })

            if not eligible:
                logger.debug(f"[SETTLEMENT] ❌ Ineligible: worker={worker_id} reason={reason}")
                rejected_count += 1
                continue

            # 6. Task 6: Call SERVICE layer, not API endpoint function
            #    payout_service.calculate_payout handles midnight splits internally
            try:
                duration_hours = (d_end - d_start).total_seconds() / 3600
                duration_minutes = int(duration_hours * 60)
                baseline = get_worker_baseline(worker_id, plan=worker.get("plan", "basic"))

                # Import here to avoid circular dependency at module load time
                from services.payout_service import calculate_payout as svc_calculate_payout

                payout_result = svc_calculate_payout(
                    baseline_earnings=baseline,
                    disruption_duration=min(duration_minutes, 480),
                    dci_score=d_score,
                    worker_id=worker_id,
                    city="Bengaluru",
                    zone_density="Mid",
                    shift=policy.get("shift", "day").capitalize(),
                    disruption_type="Disruption",
                    hour_of_day=d_start.hour,
                    day_of_week=d_start.weekday(),
                    include_confidence=False,
                )

                payout_amount = payout_result.get("payout", 0.0)
                logger.info(f"✅ SETTLED: Worker {worker_id} | Amount: ₹{payout_amount:.2f}")
                settled_count += 1

                # 7. Trigger WhatsApp settlement alert
                try:
                    from services.whatsapp_service import send_settlement_alert
                    await send_settlement_alert(
                        worker_id=worker_id,
                        amount=payout_amount,
                        upi_id=worker.get("upi_id", "your UPI"),
                        ref=f"RZP_SETTLE_{worker_id[:4].upper()}",
                    )
                except Exception as wa_err:
                    logger.warning(f"[SETTLEMENT] WhatsApp alert failed for {worker_id}: {wa_err}")

            except Exception as e:
                logger.error(f"[SETTLEMENT] Payout failed for worker {worker_id}: {e}")

    logger.info(
        f"🏁 DAILY SETTLEMENT COMPLETED | Settled: {settled_count} | Rejected: {rejected_count}"
    )

if __name__ == "__main__":
    asyncio.run(run_daily_settlement())
