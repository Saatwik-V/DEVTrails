"""
DCI Alerts API
Returns latest high-severity DCI events (score > 65)
"""

from fastapi import APIRouter, HTTPException
from config.settings import settings
from utils.supabase_client import get_supabase
import logging
from utils.pincode_mapper import PINCODE_MAP

def get_neighborhood(pincode: str):
    return PINCODE_MAP.get(pincode, {}).get("neighborhood", "Unknown")

def format_trigger(row):
    dtypes = row.get("disruption_types", [])
    
    if dtypes:
        return " + ".join([t.capitalize() for t in dtypes]) + f" · DCI {row['dci_score']}"
    
    return f"DCI {row['dci_score']}"

router = APIRouter(tags=["DCI Alerts"])

logger = logging.getLogger("gigkavach.api.dci_alerts")


@router.get("/dci-alerts/latest")
async def get_latest_dci_alerts(limit: int = 3):
    try:
        sb = get_supabase()

        response = (
            sb.table("dci_events")
            .select("pin_code, dci_score, severity, triggered_at, disruption_types")
            .gt("dci_score", 64)
            .order("triggered_at", desc=True)
            .limit(limit)
            .execute()
        )

        data = response.data or []

        return {
            "count": len(data),
            "alerts": [
                {
                    "id": idx + 1,
                    "pin_code": row["pin_code"],
                    "neighborhood": get_neighborhood(row["pin_code"]),  # ✅ HERE
                    "dci": round(float(row["dci_score"])),
                    "trigger": format_trigger(row),
                    "disruption_types": row.get("disruption_types", []),
                    "status": row["severity"],
                    "triggered_at": row["triggered_at"]
                }
                for idx, row in enumerate(data)
            ]
        }

    except Exception as e:
        return {"error": str(e)}