"""
api/fraud.py
──────────────────────────────────────
Fraud Detection Endpoints

Provides HTTP API for real-time fraud assessment on claims.
Integrates with fraud_service.py which manages the 3-stage detection pipeline.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status

from services.fraud_service import check_fraud

# Setup logging
logger = logging.getLogger("gigkavach.fraud_api")
# Task 8: prefix removed — main.py mounts this with /api/v1 already
router = APIRouter(tags=["Fraud Detection"])


# ─── Request/Response Models ─────────────────────────────────────────────────

class ClaimData(BaseModel):
    """Claim information for fraud assessment."""
    claim_id: str = Field(..., description="Unique claim ID")
    worker_id: str = Field(..., description="Worker ID")
    dci_score: float = Field(..., ge=0, le=100, description="Disruption Composite Index (0-100)")
    gps_coordinates: Optional[tuple] = Field(None, description="(latitude, longitude)")
    gps_verified_pct: Optional[float] = Field(0.9, ge=0, le=1)
    ip_location: Optional[tuple] = Field(None, description="IP-detected (latitude, longitude)")
    claims_in_zone_2min: Optional[int] = Field(0, description="Co-claims in zone within 2 minutes")
    claim_timestamp_std_sec: Optional[float] = Field(500, description="Std dev of claim timestamps")
    platform_earnings_before_disruption: Optional[float] = Field(0)
    platform_orders_before_disruption: Optional[int] = Field(0)
    disruption_outside_shift: Optional[bool] = Field(False)
    device_id: Optional[str] = Field(None, description="Device identifier")
    

class WorkerHistory(BaseModel):
    """Historical data for a worker."""
    claims_last_7_days: Optional[int] = 2
    dci_scores_at_claim: Optional[list] = Field(None, description="Historical DCI scores")
    last_claim_timestamp: Optional[datetime] = None
    claim_amounts: Optional[list] = None
    zone_claim_density: Optional[float] = 2.0
    device_ids: Optional[Dict[str, list]] = None
    co_claim_count_10min: Optional[int] = 0


class FraudCheckRequest(BaseModel):
    """Request payload for fraud assessment."""
    claim: ClaimData
    worker_history: Optional[WorkerHistory] = None
    user_context: Optional[Dict[str, Any]] = None


class FraudCheckResponse(BaseModel):
    """Response payload from fraud assessment."""
    is_fraud: bool = Field(..., description="True if claim is flagged as fraudulent")
    fraud_score: float = Field(..., ge=0, le=1, description="Fraud probability (0-1)")
    decision: str = Field(..., description="APPROVE|FLAG_50|BLOCK")
    fraud_type: Optional[str] = Field(None, description="Type of fraud detected (if any)")
    payout_action: str = Field(..., description="'100%'|'50%_HOLD_48H'|'0%'")
    explanation: str = Field(..., description="Human-readable reason for decision")
    timestamp: str = Field(..., description="ISO timestamp of assessment")
    confidence: Optional[float] = Field(None, description="Confidence of detection")
    audit_log: Optional[Dict[str, Any]] = Field(None, description="Stage-wise scores for debugging")


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post(
    "/check-fraud",
    response_model=FraudCheckResponse,
    summary="Check claim for fraud",
    description="""
    Perform 3-stage fraud detection on a claim:
    
    **Stage 1**: Rule-based hard blocks (device farming, rapid reclaim, etc.)
    
    **Stage 2**: Isolation Forest anomaly detection (unsupervised)
    
    **Stage 3**: XGBoost multi-class classifier (fraud type + confidence)
    
    **Ensemble**: Rule-aware blending
    - If Stage 1 rules trigger: fraud_score = 0.9 (high confidence)
    - Otherwise: fraud_score = 0.2×IF + 0.8×XGB
    
    **Returns**:
    - is_fraud: boolean flag
    - fraud_score: 0-1 probability
    - decision: categorical (APPROVE|FLAG_50|BLOCK)
    - payout_action: what to do with worker payment
    - explanation: why this decision was made
    
    **Example**:
    ```json
    {
      "claim": {
        "claim_id": "CLM_2024_001",
        "worker_id": "W123",
        "dci_score": 78.5,
        "gps_coordinates": [13.0827, 80.2707],
        "gps_verified_pct": 0.95
      },
      "worker_history": {
        "claims_last_7_days": 5,
        "dci_scores_at_claim": [75, 76, 78, 79]
      }
    }
    ```
    """
)
async def check_fraud_endpoint(request: FraudCheckRequest):
    """Check a claim for fraud using the 3-stage detection pipeline."""
    try:
        logger.info(
            f"[FRAUD CHECK] Assessing claim {request.claim.claim_id} "
            f"for worker {request.claim.worker_id}..."
        )
        
        # Convert pydantic models to dicts for service layer
        claim_dict = request.claim.dict(exclude_none=True)
        worker_history_dict = (
            request.worker_history.dict(exclude_none=True)
            if request.worker_history
            else None
        )
        
        # Call fraud detection service
        result = check_fraud(
            claim=claim_dict,
            worker_history=worker_history_dict,
            user_context=request.user_context,
        )
        
        logger.info(
            f"[FRAUD RESULT] claim={request.claim.claim_id} | "
            f"decision={result['decision']} | score={result['fraud_score']:.3f}"
        )
        
        return FraudCheckResponse(**result)
        
    except Exception as e:
        logger.error(f"[FRAUD ERROR] Failed to assess claim: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fraud assessment failed: {str(e)}"
        )


@router.get(
    "/fraud/health",
    summary="Fraud detection system health",
    description="Check if fraud detection models are loaded and ready"
)
async def fraud_health():
    """Health check for fraud detection system."""
    try:
        from ml.fraud_detector import get_detector
        detector = get_detector()
        
        return {
            "status": "healthy",
            "models_loaded": True,
            "timestamp": datetime.utcnow().isoformat(),
            "stages": {
                "stage_1": "rule_based_hard_blocks",
                "stage_2": "isolation_forest_v2.0",
                "stage_3": "xgboost_multiclass_v3+"
            },
            "ensemble": "rule_aware (if_rule: 0.9 else: 0.2*IF + 0.8*XGB)"
        }
    except Exception as e:
        logger.error(f"Fraud health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Fraud detection system unavailable: {str(e)}"
        )


@router.post(
    "/fraud/batch-check",
    summary="Batch fraud assessment (async)",
    description="Check multiple claims for fraud in a single request (useful for bulk operations)"
)
async def batch_fraud_check(claims: list[FraudCheckRequest]):
    """
    Assess multiple claims for fraud.
    
    Note: This is synchronous for now but suitable for small batches (< 100 claims).
    For large batches, recommend using message queue (Celery/RabbitMQ).
    """
    try:
        results = []
        for claim_request in claims:
            result = await check_fraud_endpoint(claim_request)
            results.append(result)
        
        return {
            "total": len(results),
            "assessed_at": datetime.utcnow().isoformat(),
            "results": results
        }
    except Exception as e:
        logger.error(f"Batch fraud check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch assessment failed: {str(e)}"
        )
