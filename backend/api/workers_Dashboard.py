from fastapi import APIRouter
from datetime import datetime, timezone
from utils.db import get_supabase

router = APIRouter()

@router.get("/workers/active/week")
async def get_active_workers_week():
    try:
        sb = get_supabase()

        today = datetime.now(timezone.utc).date().isoformat()

        result = (
            sb.table("policies")
            .select("worker_id, status, week_start, week_end")
            .eq("status", "active")
            .lte("week_start", today)
            .gte("week_end", today)
            .execute()
        )

        unique_workers = set(row["worker_id"] for row in result.data or [])

        return {
            "active_workers_week": len(unique_workers)
        }

    except Exception as e:
        return {
            "active_workers_week": 0,
            "error": str(e)
        }