"""
models/fraud.py
──────────────────────────────────────
Pydantic Models for Fraud Detection

Defines request/response schemas for the 3-stage fraud detection pipeline:
  Stage 1: Rule-based hard blocks (device farming, rapid reclaim, etc.)
  Stage 2: Isolation Forest anomaly detection (unsupervised)
  Stage 3: XGBoost multi-class classifier (fraud type + confidence)

References:
  - README Section 10: Fraud Detection Architecture
  - README Section 11: Adversarial Defense & Anti-Spoofing Strategy
  - 6 independent signals beyond basic GPS (cell tower, IP geo, earnings velocity, etc.)
  - 3-tier penalization (Tier 1: soft flag 50%, Tier 2: hard block, Tier 3: blacklist)
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator


# ─── FRAUD SIGNALS (6 Independent Signals) ──────────────────────────────────

class GPSSignal(BaseModel):
    """Signal 1: GPS vs IP Address Mismatch - VPN Spoofing Detection"""
    gps_latitude: float = Field(..., ge=-90, le=90, description="GPS latitude coordinate")
    gps_longitude: float = Field(..., ge=-180, le=180, description="GPS longitude coordinate")
    gps_verified_pct: float = Field(0.9, ge=0, le=1, description="GPS verification confidence (0-1)")
    ip_latitude: Optional[float] = Field(None, ge=-90, le=90, description="IP-detected latitude")
    ip_longitude: Optional[float] = Field(None, ge=-180, le=180, description="IP-detected longitude")
    distance_km: Optional[float] = Field(None, ge=0, description="Distance between GPS and IP location (km)")
    mismatch_detected: bool = Field(False, description="True if distance > 10km (suspicious)")

    class Config:
        schema_extra = {
            "example": {
                "gps_latitude": 13.0827,
                "gps_longitude": 80.2707,
                "gps_verified_pct": 0.95,
                "ip_latitude": 13.0950,
                "ip_longitude": 80.2300,
                "distance_km": 5.2,
                "mismatch_detected": False
            }
        }


class CellTowerSignal(BaseModel):
    """Signal 2: Cell Tower Triangulation vs GPS - Carrier Network Validation"""
    cell_tower_id: Optional[str] = Field(None, description="Carrier cell tower ID (cannot be spoofed)")
    cell_tower_latitude: Optional[float] = Field(None, ge=-90, le=90)
    cell_tower_longitude: Optional[float] = Field(None, ge=-180, le=180)
    gps_cell_distance_km: Optional[float] = Field(None, ge=0, description="Distance between GPS and cell tower")
    cell_tower_mismatch: bool = Field(False, description="True if distance > 15km (impossible for real cell)")

    class Config:
        schema_extra = {
            "example": {
                "cell_tower_id": "CT_KA_BLR_001",
                "cell_tower_latitude": 13.0827,
                "cell_tower_longitude": 80.2707,
                "gps_cell_distance_km": 0.5,
                "cell_tower_mismatch": False
            }
        }


class IPGeolocationSignal(BaseModel):
    """Signal 3: IP Geolocation Cross-Check - ISP Node Validation"""
    ip_address: Optional[str] = Field(None, description="Worker's IP address")
    ip_isp: Optional[str] = Field(None, description="Internet Service Provider")
    ip_country: Optional[str] = Field(None, description="GeoIP country")
    ip_state: Optional[str] = Field(None, description="GeoIP state/region")
    ip_city: Optional[str] = Field(None, description="GeoIP city")
    declared_zone: str = Field(..., description="Zone worker declared at onboarding")
    ip_zone_mismatch: bool = Field(False, description="True if IP city != declared zone")

    class Config:
        schema_extra = {
            "example": {
                "ip_address": "203.89.123.45",
                "ip_isp": "ACT Fibernet",
                "ip_country": "IN",
                "ip_state": "Karnataka",
                "ip_city": "Bangalore",
                "declared_zone": "Koramangala",
                "ip_zone_mismatch": False
            }
        }


class EarningsVelocitySignal(BaseModel):
    """Signal 4: Pre-Disruption Earnings Velocity - Platform Activity Baseline"""
    platform_earnings_before_disruption: float = Field(0, ge=0, description="₹ earned before disruption detected")
    platform_orders_before_disruption: int = Field(0, ge=0, description="Orders completed before disruption")
    working_hours_before: float = Field(0, ge=0, description="Hours worker was active before disruption")
    zero_earnings_all_day: bool = Field(False, description="True if worker earned ₹0 entire day (suspicious)")
    low_activity_signal: bool = Field(False, description="True if < 2 orders AND < ₹100 earned before disruption")

    class Config:
        schema_extra = {
            "example": {
                "platform_earnings_before_disruption": 350.50,
                "platform_orders_before_disruption": 8,
                "working_hours_before": 4.5,
                "zero_earnings_all_day": False,
                "low_activity_signal": False
            }
        }


class GPSMovementEntropySignal(BaseModel):
    """Signal 5: GPS Movement Entropy - Human Motion Signature Detection"""
    movement_entropy: float = Field(0.0, ge=0, le=1, description="Movement entropy score (0=static/synthetic, 1=natural)")
    gps_position_variance: float = Field(0.0, ge=0, description="Variance in GPS coordinates over 30 min window")
    acceleration_events: int = Field(0, ge=0, description="Detected acceleration/deceleration events")
    movement_pattern: str = Field("unknown", description="Pattern detected: straight_line|organic|static|teleport")
    synthetic_movement: bool = Field(False, description="True if movement appears mathematically synthetic")

    class Config:
        schema_extra = {
            "example": {
                "movement_entropy": 0.87,
                "gps_position_variance": 0.0045,
                "acceleration_events": 12,
                "movement_pattern": "organic",
                "synthetic_movement": False
            }
        }


class ClaimTimingClusteringSignal(BaseModel):
    """Signal 6: Claim Timing Clustering - Telegram/Telegram Coordination Detection"""
    claims_in_zone_2min: int = Field(0, ge=0, description="Co-claims in same zone within 2 minutes")
    claim_timestamp_std_sec: float = Field(500, ge=0, description="Std dev of claim timestamps (seconds)")
    timing_burst_detected: bool = Field(False, description="True if std_dev < 90 sec (coordinate fraud ring)")
    cluster_probability: float = Field(0.0, ge=0, le=1, description="Probability of coordinated fraud ring (0-1)")

    class Config:
        schema_extra = {
            "example": {
                "claims_in_zone_2min": 2,
                "claim_timestamp_std_sec": 520.5,
                "timing_burst_detected": False,
                "cluster_probability": 0.15
            }
        }


class ZoneHistoryLoyaltySignal(BaseModel):
    """Signal 7 (Bonus): Zone Historical Loyalty - Delivery Geography Validation"""
    declared_zones: List[str] = Field([], description="Zones worker declared at onboarding")
    activity_history_zones: List[str] = Field([], description="Zones worker has delivered in (4-week history)")
    claim_zone: str = Field(..., description="Zone where current claim is from")
    zone_loyalty_score: float = Field(1.0, ge=0, le=1, description="How consistent is claim zone with history")
    zone_mismatch_risk: bool = Field(False, description="True if claim_zone not in history (syndicate behavior)")

    class Config:
        schema_extra = {
            "example": {
                "declared_zones": ["HSR_Layout", "Indiranagar"],
                "activity_history_zones": ["HSR_Layout", "Indiranagar", "Koramangala"],
                "claim_zone": "Koramangala",
                "zone_loyalty_score": 0.95,
                "zone_mismatch_risk": False
            }
        }


class FraudSignalsBreakdown(BaseModel):
    """Comprehensive breakdown of all 6 fraud detection signals"""
    gps_signal: Optional[GPSSignal] = None
    cell_tower_signal: Optional[CellTowerSignal] = None
    ip_geolocation_signal: Optional[IPGeolocationSignal] = None
    earnings_velocity_signal: Optional[EarningsVelocitySignal] = None
    movement_entropy_signal: Optional[GPSMovementEntropySignal] = None
    claim_timing_signal: Optional[ClaimTimingClusteringSignal] = None
    zone_loyalty_signal: Optional[ZoneHistoryLoyaltySignal] = None
    
    signals_triggered: int = Field(0, ge=0, le=6, description="Total number of fraud signals triggered")

    class Config:
        schema_extra = {
            "example": {
                "gps_signal": {"mismatch_detected": False},
                "claim_timing_signal": {"timing_burst_detected": False},
                "signals_triggered": 0
            }
        }


# ─── CLAIM DATA ──────────────────────────────────────────────────────────────

class ClaimData(BaseModel):
    """Complete claim information for fraud assessment"""
    claim_id: str = Field(..., description="Unique claim ID (UUID v4 recommended)")
    worker_id: str = Field(..., description="Worker ID from workers table")
    policy_id: Optional[str] = Field(None, description="Active policy ID")
    
    dci_score: float = Field(..., ge=0, le=100, description="Disruption Composite Index at time of claim")
    dci_component_breakdown: Optional[Dict[str, float]] = Field(
        None,
        description="Component scores: rainfall, aqi, heat, social, platform_activity"
    )
    
    claim_timestamp: datetime = Field(default_factory=datetime.utcnow, description="When claim was triggered")
    shift_start: Optional[datetime] = None
    shift_end: Optional[datetime] = None
    disruption_outside_shift: bool = Field(False, description="True if disruption happened outside worker's shift")
    
    gps_coordinates: Optional[tuple] = Field(None, description="(latitude, longitude)")
    gps_verified_pct: float = Field(0.9, ge=0, le=1)
    
    platform_earnings_before_disruption: float = Field(0, ge=0, description="Platform earnings before disruption (₹)")
    platform_orders_before_disruption: int = Field(0, ge=0)
    
    device_id: Optional[str] = Field(None, description="Device fingerprint (SHA256)")
    device_os: Optional[str] = Field(None, description="Android|iOS")
    app_version: Optional[str] = Field(None, description="App version string")

    class Config:
        schema_extra = {
            "example": {
                "claim_id": "CLM_2024_001",
                "worker_id": "W123",
                "dci_score": 78.5,
                "claim_timestamp": "2025-03-30T14:30:00Z",
                "gps_coordinates": [13.0827, 80.2707],
                "gps_verified_pct": 0.95
            }
        }


# ─── WORKER HISTORY ──────────────────────────────────────────────────────────

class WorkerHistory(BaseModel):
    """Historical data for a worker (from activity_log, payouts, fraud_flags tables)"""
    worker_id: str = Field(..., description="Worker ID")
    registration_date: datetime = Field(..., description="When worker registered with GigKavach")
    registration_age_hours: int = Field(0, ge=0, description="Hours since registration (0-24 = same-day = risky)")
    
    claims_last_7_days: int = Field(0, ge=0, description="Number of claims in last 7 days")
    claims_last_24_hours: int = Field(0, ge=0, description="Number of claims in last 24 hours")
    average_dci_at_claims: Optional[float] = Field(None, description="Average DCI score at previous claims")
    dci_threshold_gaming: bool = Field(False, description="True if consistently claiming at DCI 65-68")
    
    platform_activity_consistency: float = Field(0.5, ge=0, le=1, description="How consistent is platform activity pattern")
    
    fraud_flags_tier1: int = Field(0, ge=0, description="Number of Tier 1 (soft flag 50%) incidents")
    fraud_flags_tier2: int = Field(0, ge=0, description="Number of Tier 2 (hard block) incidents")
    fraud_flags_tier3: int = Field(0, ge=0, description="Number of Tier 3 (permanent blacklist) incidents")
    
    total_payouts: int = Field(0, ge=0, description="Total payout claims processed")
    total_payout_amount: float = Field(0, ge=0, description="Total payout amount (₹)")
    
    device_ids_historical: List[str] = Field([], description="All device IDs used by worker in history")
    ip_addresses_historical: List[str] = Field([], description="All IP addresses used by worker")
    
    known_fraud_ring_member: bool = Field(False, description="True if coordinated fraud confirmed")
    appeal_success_rate: float = Field(1.0, ge=0, le=1, description="Fraction of successful appeals")

    class Config:
        schema_extra = {
            "example": {
                "worker_id": "W123",
                "registration_age_hours": 120,
                "claims_last_7_days": 3,
                "fraud_flags_tier1": 0,
                "appeal_success_rate": 1.0
            }
        }


# ─── FRAUD DETECTION STAGE OUTPUTS ──────────────────────────────────────────

class Stage1HardBlocksResult(BaseModel):
    """Stage 1: Rule-based hard blocks result"""
    passed: bool = Field(True, description="True if all hard block rules passed")
    triggered_rules: List[str] = Field(
        [],
        description="List of hard-block rules triggered (device_farming, same_day_registration, etc.)"
    )
    explanation: Optional[str] = Field(None, description="Human-readable explanation if rule triggered")

    class Config:
        schema_extra = {
            "example": {
                "passed": True,
                "triggered_rules": [],
                "explanation": None
            }
        }


class Stage2IsolationForestResult(BaseModel):
    """Stage 2: Isolation Forest anomaly detection result"""
    anomaly_score: float = Field(0.0, ge=0, le=1, description="Anomaly score (0=normal, 1=extreme anomaly)")
    contamination_parameter: float = Field(0.05, description="Assumed contamination rate (5% of claims)")
    is_anomalous: bool = Field(False, description="True if anomaly_score > threshold")
    anomaly_type: Optional[str] = Field(None, description="Type of anomaly detected (if any)")

    class Config:
        schema_extra = {
            "example": {
                "anomaly_score": 0.15,
                "is_anomalous": False,
                "anomaly_type": None
            }
        }


class Stage3XGBoostResult(BaseModel):
    """Stage 3: XGBoost multi-class classifier result"""
    fraud_probability: float = Field(0.0, ge=0, le=1, description="Probability of fraud (0-1)")
    fraud_class: str = Field(
        "legitimate",
        description="Fraud class: legitimate | gps_spoof | device_farm | ring_coord | behavioral_anomaly"
    )
    class_probabilities: Dict[str, float] = Field(
        {},
        description="Probabilities for each fraud class"
    )
    feature_importance: Optional[Dict[str, float]] = Field(None, description="Top contributing features (optional)")

    class Config:
        schema_extra = {
            "example": {
                "fraud_probability": 0.12,
                "fraud_class": "legitimate",
                "class_probabilities": {
                    "legitimate": 0.88,
                    "gps_spoof": 0.05,
                    "device_farm": 0.04,
                    "ring_coord": 0.02,
                    "behavioral_anomaly": 0.01
                }
            }
        }


# ─── FRAUD CHECK REQUEST/RESPONSE ────────────────────────────────────────────

class FraudCheckRequest(BaseModel):
    """Request payload for fraud assessment"""
    claim: ClaimData = Field(..., description="Claim information to assess")
    fraud_signals: Optional[FraudSignalsBreakdown] = Field(None, description="Pre-computed fraud signals (optional)")
    worker_history: Optional[WorkerHistory] = Field(None, description="Worker's historical data")
    user_context: Optional[Dict[str, Any]] = Field(None, description="Additional context (api_version, user_id, etc.)")

    class Config:
        schema_extra = {
            "example": {
                "claim": {
                    "claim_id": "CLM_2024_001",
                    "worker_id": "W123",
                    "dci_score": 78.5
                },
                "worker_history": {
                    "registration_age_hours": 120,
                    "claims_last_7_days": 3
                }
            }
        }


class FraudCheckResponse(BaseModel):
    """Response payload from fraud assessment (3-stage ensemble result)"""
    claim_id: str = Field(..., description="Echo back the claim ID")
    worker_id: str = Field(..., description="Echo back the worker ID")
    
    is_fraud: bool = Field(..., description="True if claim is flagged as fraudulent")
    fraud_score: float = Field(..., ge=0, le=1, description="Overall fraud probability (0-1)")
    decision: str = Field(
        ...,
        description="Categorical decision: APPROVE | FLAG_50 (Tier 1) | BLOCK (Tier 2) | BLACKLIST (Tier 3)"
    )
    fraud_type: Optional[str] = Field(
        None,
        description="Type of fraud detected: gps_spoofing | device_farming | ring_coordination | behavioral_anomaly"
    )
    
    payout_action: str = Field(
        ...,
        description="What to do with payout: 100% | 50%_HOLD_48H | 0% (BLOCK) | PERMANENT_BLACKLIST"
    )
    
    explanation: str = Field(..., description="Human-readable reason for decision")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in the fraud assessment (0-1)")
    
    timestamp: str = Field(..., description="ISO timestamp of assessment")
    detector_version: str = Field(..., description="Fraud detection model version (e.g., '2.0')")
    
    # Detailed stage results
    stage1_result: Optional[Stage1HardBlocksResult] = None
    stage2_result: Optional[Stage2IsolationForestResult] = None
    stage3_result: Optional[Stage3XGBoostResult] = None
    
    # Signals breakdown
    fraud_signals: Optional[FraudSignalsBreakdown] = None
    
    # Audit trail
    audit_log: Optional[Dict[str, Any]] = Field(
        None,
        description="Detailed audit trail for logging/debugging"
    )

    class Config:
        schema_extra = {
            "example": {
                "claim_id": "CLM_2024_001",
                "worker_id": "W123",
                "is_fraud": False,
                "fraud_score": 0.12,
                "decision": "APPROVE",
                "payout_action": "100%",
                "explanation": "Claim approved: fraud score < 0.30",
                "confidence": 0.95,
                "timestamp": "2025-03-30T14:30:05Z",
                "detector_version": "2.0"
            }
        }


# ─── FRAUD FLAGS (Database Model) ────────────────────────────────────────────

class FraudFlagCreate(BaseModel):
    """Data for creating a fraud flag in fraud_flags table"""
    claim_id: str = Field(..., description="Claim ID that triggered fraud flag")
    worker_id: str = Field(..., description="Flagged worker ID")
    policy_id: Optional[str] = Field(None)
    
    fraud_tier: int = Field(..., ge=1, le=3, description="1=soft flag 50%, 2=hard block, 3=blacklist")
    fraud_score: float = Field(..., ge=0, le=1)
    fraud_type: str = Field(..., description="Type of fraud: gps_spoofing, device_farming, etc.")
    
    triggered_signals: List[str] = Field([], description="Which of 6 signals triggered")
    decision: str = Field(..., description="APPROVE|FLAG_50|BLOCK|BLACKLIST")
    payout_action: str = Field(..., description="100%|50%_HOLD_48H|0%|PERMANENT_BLACKLIST")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field("fraud_detector", description="System or user that created flag")
    
    appeal_eligible: bool = Field(True, description="True if worker can appeal (Tier 1, 2)")
    appeal_deadline: Optional[datetime] = Field(None, description="When appeal window closes (48h for Tier 1)")

    class Config:
        schema_extra = {
            "example": {
                "claim_id": "CLM_2024_001",
                "worker_id": "W123",
                "fraud_tier": 1,
                "fraud_score": 0.55,
                "fraud_type": "gps_spoofing",
                "triggered_signals": ["gps_mismatch", "cell_tower_mismatch"],
                "decision": "FLAG_50"
            }
        }


class FraudFlagResponse(FraudFlagCreate):
    """Response model for fraud flag (with ID from database)"""
    fraud_flag_id: str = Field(..., description="Unique fraud flag ID from database")

    class Config:
        schema_extra = {
            "example": {
                "fraud_flag_id": "FF_2024_001",
                "claim_id": "CLM_2024_001",
                "worker_id": "W123",
                "fraud_tier": 1
            }
        }


# ─── FRAUD APPEAL ────────────────────────────────────────────────────────────

class FraudAppealRequest(BaseModel):
    """Request to appeal a fraud flag decision"""
    fraud_flag_id: str = Field(..., description="ID of fraud flag to appeal")
    worker_id: str = Field(..., description="Worker ID appealing")
    
    appeal_reason: str = Field(..., min_length=10, max_length=500, description="Worker's explanation")
    evidence: Optional[Dict[str, Any]] = Field(None, description="Supporting evidence (doc URLs, etc.)")
    
    submitted_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        schema_extra = {
            "example": {
                "fraud_flag_id": "FF_2024_001",
                "worker_id": "W123",
                "appeal_reason": "I was genuinely working in that zone and disruption affected me"
            }
        }


class FraudAppealResponse(BaseModel):
    """Response to fraud appeal"""
    appeal_id: str = Field(..., description="Unique appeal ID")
    fraud_flag_id: str
    worker_id: str
    
    status: str = Field(..., description="SUBMITTED|UNDER_REVIEW|APPROVED|REJECTED")
    decision: Optional[str] = Field(None, description="If status=APPROVED/REJECTED: explanation")
    
    original_decision: str = Field(..., description="Original fraud decision (FLAG_50|BLOCK)")
    appeal_decision: Optional[str] = Field(None, description="Decision after appeal (e.g., APPROVED, PAYBACK_FULL_AMOUNT)")
    
    payout_corrected: Optional[float] = Field(None, description="If approved, amount to pay back (₹)")
    
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = Field(None, description="System or human reviewer")
    
    class Config:
        schema_extra = {
            "example": {
                "appeal_id": "APP_2024_001",
                "fraud_flag_id": "FF_2024_001",
                "worker_id": "W123",
                "status": "APPROVED",
                "decision": "Appeal validated against IMD records. Worker was in working zone during documented rainfall.",
                "appeal_decision": "PAYBACK_FULL_AMOUNT",
                "payout_corrected": 140.0
            }
        }


# ─── FRAUD BATCH OPERATIONS ─────────────────────────────────────────────────

class BatchFraudCheckRequest(BaseModel):
    """Request for batch fraud assessment"""
    claims: List[FraudCheckRequest] = Field(..., min_items=1, max_items=100)
    priority: str = Field("normal", description="normal|high|low")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Job metadata")

    class Config:
        schema_extra = {
            "example": {
                "claims": [{"claim": {"claim_id": "CLM_1", "worker_id": "W1", "dci_score": 75}}],
                "priority": "normal"
            }
        }


class BatchFraudCheckResponse(BaseModel):
    """Response for batch fraud assessment"""
    job_id: str = Field(..., description="Batch job ID")
    total_claims: int = Field(..., ge=1)
    processed_claims: int = Field(..., ge=0)
    
    results: List[FraudCheckResponse] = Field(...)
    
    summary: Dict[str, int] = Field(
        ...,
        description="Summary: {approved: N, flag_50: N, blocked: N, blacklisted: N}"
    )
    
    processed_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        schema_extra = {
            "example": {
                "job_id": "JOB_2024_001",
                "total_claims": 50,
                "processed_claims": 50,
                "summary": {"approved": 45, "flag_50": 4, "blocked": 1, "blacklisted": 0}
            }
        }


# ─── FRAUD DETECTION CONFIGURATION ──────────────────────────────────────────

class FraudDetectionConfig(BaseModel):
    """Configuration parameters for fraud detection"""
    # Stage 1: Hard blocks
    same_day_registration_block: bool = Field(True)
    device_farming_threshold: int = Field(3, ge=2, description="Max devices per worker")
    
    # Stage 2: Isolation Forest
    isolation_forest_contamination: float = Field(0.05, ge=0, le=0.20)
    anomaly_threshold: float = Field(0.50, ge=0, le=1)
    
    # Stage 3: XGBoost
    xgboost_fraud_threshold: float = Field(0.40, ge=0, le=1)
    
    # Ensemble thresholds
    fraud_score_flag_50_threshold: float = Field(0.30, ge=0, le=1, description="FLAG_50 if score > this")
    fraud_score_block_threshold: float = Field(0.60, ge=0, le=1, description="BLOCK if score > this")
    
    # Signal weights
    signal_weights: Dict[str, float] = Field(
        {
            "gps_mismatch": 0.20,
            "cell_tower_mismatch": 0.20,
            "earnings_velocity": 0.15,
            "movement_entropy": 0.15,
            "claim_timing": 0.20,
            "zone_loyalty": 0.10
        }
    )
    
    # DCI severity adjustment
    catastrophic_dci_threshold: float = Field(85.0, ge=65, le=100, description="DCI >= this: relax fraud thresholds")
    catastrophic_signal_requirement: int = Field(5, ge=1, le=6, description="In catastrophic: need N signals to hard block")

    class Config:
        schema_extra = {
            "example": {
                "fraud_score_flag_50_threshold": 0.30,
                "fraud_score_block_threshold": 0.60,
                "signal_weights": {
                    "gps_mismatch": 0.20,
                    "claim_timing": 0.20
                }
            }
        }
