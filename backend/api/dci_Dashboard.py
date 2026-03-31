from fastapi import APIRouter
from datetime import datetime, timezone
from utils.db import get_supabase

router = APIRouter()

@router.get("/dci/total/today")
async def get_dci_today():
    try:
        sb = get_supabase()

        # Start of today (UTC)
        start_of_today = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()

        # Fetch DCI events triggered today
        result = (
            sb.table("dci_events")
            .select("id, triggered_at")
            .gte("triggered_at", start_of_today)
            .execute()
        )

        total = len(result.data or [])

        return {
            "total_dci_today": total
        }

    except Exception as e:
        return {
            "total_dci_today": 0,
            "error": str(e)
        }