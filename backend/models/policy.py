"""
models/policy.py
──────────────────────────────────────────────────────────────
Pydantic Models for Policy Management

Defines request/response schemas for:
  - Policy creation at onboarding
  - Policy renewal (weekly)
  - Policy tier changes (with queuing for next Monday)
  - Policy updates (shift, pin codes)
  - Premium payments and tracking
  - Policy status and eligibility

References:
  - README Section 7: Weekly Premium Model (₹69–₹99 tiers)
  - README Section 5: Application Workflow (policy activation after 24h delay)
  - Folder structure docs: Policy CRUD, tier updates, coverage status

Business Rules:
  - Premiums: BASIC (₹69, 40%), PLUS (₹89, 50%), PRO (₹99, 70% coverage)
  - Plan upgrades: queued for next Monday (tier_lock on mid-week changes)
  - Shift changes: effective immediately
  - Pin code updates: effective immediately
  - Coverage activation: 24 hours after premium payment (moral hazard prevention)
  - Weekly cycle: Monday 00:00 IST to Sunday 23:59 IST
  - Annual cycle: 52 renewable weeks
"""

from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


# ─── ENUMS (Duplicated from worker.py for standalone usage) ────────────────

class ShiftType(str, Enum):
    """Worker's typical working shift — used for DCI trigger eligibility"""
    MORNING = "morning"      # 6AM – 2PM
    DAY = "day"              # 9AM – 9PM (most common)
    NIGHT = "night"          # 6PM – 2AM
    FLEXIBLE = "flexible"    # No fixed window — eligible during any active DCI event


class PlanType(str, Enum):
    """Three fixed weekly premium tiers with coverage percentages"""
    BASIC = "basic"          # ₹69/week → 40% daily earnings covered
    PLUS = "plus"            # ₹89/week → 50% daily earnings covered
    PRO = "pro"              # ₹99/week → 70% daily earnings covered


class PaymentStatus(str, Enum):
    """Status of premium payment"""
    INITIATED = "initiated"          # Payment flow started
    PENDING = "pending"              # Awaiting payment confirmation
    COMPLETED = "completed"          # Payment verified, coverage activates in 24h
    FAILED = "failed"                # Payment declined or timeout
    REFUNDED = "refunded"            # Worker asked for refund


class PolicyStatus(str, Enum):
    """Lifecycle status of a policy"""
    PENDING_ACTIVATION = "pending_activation"    # Payment done, waiting 24h
    ACTIVE = "active"                            # Coverage is live
    EXPIRED = "expired"                          # Week ended, awaiting renewal
    CANCELLED = "cancelled"                      # Worker opted out
    SUSPENDED = "suspended"                      # Due to fraud (Tier 3 blacklist)


# ─── PREMIUM PRICING ──────────────────────────────────────────────────────────

class PremiumTier(BaseModel):
    """Premium pricing and coverage details for each tier"""
    plan: PlanType = Field(..., description="Plan identifier")
    weekly_premium_inr: float = Field(..., ge=0, description="Weekly premium in ₹")
    coverage_percentage: float = Field(..., ge=0, le=1, description="Payout coverage (e.g., 0.40 = 40%)")
    description: str = Field(..., description="Human-readable tier description")

    class Config:
        schema_extra = {
            "example": {
                "plan": "basic",
                "weekly_premium_inr": 69.0,
                "coverage_percentage": 0.40,
                "description": "Shield Basic: ₹69/week, covers 40% of daily earnings"
            }
        }


class PremiumStructure(BaseModel):
    """Complete premium structure for all tiers"""
    basic: PremiumTier = Field(
        ...,
        description="Shield Basic tier"
    )
    plus: PremiumTier = Field(
        ...,
        description="Shield Plus tier"
    )
    pro: PremiumTier = Field(
        ...,
        description="Shield Pro tier"
    )

    class Config:
        schema_extra = {
            "example": {
                "basic": {
                    "plan": "basic",
                    "weekly_premium_inr": 69.0,
                    "coverage_percentage": 0.40,
                    "description": "Shield Basic: ₹69/week"
                },
                "plus": {
                    "plan": "plus",
                    "weekly_premium_inr": 89.0,
                    "coverage_percentage": 0.50,
                    "description": "Shield Plus: ₹89/week"
                },
                "pro": {
                    "plan": "pro",
                    "weekly_premium_inr": 99.0,
                    "coverage_percentage": 0.70,
                    "description": "Shield Pro: ₹99/week"
                }
            }
        }


# ─── POLICY CREATION ──────────────────────────────────────────────────────────

class PolicyCreate(BaseModel):
    """Data required to create a new policy (at onboarding end)"""
    worker_id: str = Field(..., description="Worker ID from workers table")
    plan: PlanType = Field(..., description="Selected coverage tier")
    shift: ShiftType = Field(..., description="Working shift window")
    pin_codes: List[str] = Field(
        ...,
        min_items=1,
        max_items=5,
        description="Delivery zones (1–5 pin codes)"
    )
    weekly_premium_inr: float = Field(..., ge=69, le=99, description="Premium amount in ₹")
    coverage_percentage: float = Field(..., ge=0.40, le=0.70, description="Coverage tier (0.40–0.70)")
    
    week_start: datetime = Field(..., description="Week start (Monday 00:00 IST)")
    week_end: datetime = Field(..., description="Week end (Sunday 23:59 IST)")

    class Config:
        schema_extra = {
            "example": {
                "worker_id": "W123",
                "plan": "basic",
                "shift": "day",
                "pin_codes": ["560047", "560034"],
                "weekly_premium_inr": 69.0,
                "coverage_percentage": 0.40,
                "week_start": "2025-03-31T00:00:00Z",
                "week_end": "2025-04-06T23:59:59Z"
            }
        }


# ─── POLICY UPDATES ──────────────────────────────────────────────────────────

class PolicyUpdate(BaseModel):
    """Fields that can be updated on an existing policy (PATCH endpoint)"""
    plan: Optional[PlanType] = Field(None, description="New plan tier (queued for next Monday)")
    shift: Optional[ShiftType] = Field(None, description="New shift window (immediate)")
    pin_codes: Optional[List[str]] = Field(
        None,
        min_items=1,
        max_items=5,
        description="Updated delivery zones (immediate)"
    )

    @model_validator(mode="after")
    def validate_at_least_one_field(self):
        """Ensure at least one field is being updated"""
        if all(v is None for v in [self.plan, self.shift, self.pin_codes]):
            raise ValueError("At least one of plan, shift, or pin_codes must be provided")
        return self

    class Config:
        schema_extra = {
            "example": {
                "plan": "pro",
                "shift": None,
                "pin_codes": None
            }
        }


# ─── TIER CHANGE MANAGEMENT ──────────────────────────────────────────────────

class TierChangeQueuedEvent(BaseModel):
    """Event triggered when a tier change is queued for next Monday"""
    policy_id: str = Field(...)
    worker_id: str = Field(...)
    current_plan: PlanType = Field(...)
    requested_plan: PlanType = Field(...)
    effective_date: date = Field(..., description="Next Monday when change takes effect")
    current_coverage_pct: float = Field(...)
    new_coverage_pct: float = Field(...)
    current_premium: float = Field(...)
    new_premium: float = Field(...)
    queued_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        schema_extra = {
            "example": {
                "policy_id": "POL_123",
                "worker_id": "W123",
                "current_plan": "basic",
                "requested_plan": "pro",
                "effective_date": "2025-04-07",
                "current_coverage_pct": 0.40,
                "new_coverage_pct": 0.70,
                "current_premium": 69.0,
                "new_premium": 99.0
            }
        }


class TierChangeActivationEvent(BaseModel):
    """Event triggered when a queued tier change takes effect (Monday 00:01)"""
    policy_id: str = Field(...)
    worker_id: str = Field(...)
    previous_plan: PlanType = Field(...)
    new_plan: PlanType = Field(...)
    activated_at: datetime = Field(...)
    active_until: datetime = Field(...)

    class Config:
        schema_extra = {
            "example": {
                "policy_id": "POL_123",
                "worker_id": "W123",
                "previous_plan": "basic",
                "new_plan": "pro",
                "activated_at": "2025-04-07T00:01:00Z",
                "active_until": "2025-04-13T23:59:59Z"
            }
        }


# ─── PREMIUM PAYMENT TRACKING ──────────────────────────────────────────────────

class PremiumPaymentCreate(BaseModel):
    """Record of a premium payment at initiation or renewal"""
    worker_id: str = Field(...)
    policy_id: str = Field(...)
    plan: PlanType = Field(...)
    amount_inr: float = Field(..., ge=69, le=99)
    payment_gateway: str = Field(default="razorpay", description="Payment processor")
    payment_reference_id: Optional[str] = Field(None, description="Razorpay/external reference")
    initiated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        schema_extra = {
            "example": {
                "worker_id": "W123",
                "policy_id": "POL_123",
                "plan": "basic",
                "amount_inr": 69.0,
                "payment_gateway": "razorpay",
                "payment_reference_id": "RZP_123456"
            }
        }


class PremiumPaymentConfirm(BaseModel):
    """Confirmation of successful premium payment"""
    payment_id: str = Field(...)
    status: PaymentStatus = Field(...)
    completed_at: datetime = Field(...)
    next_renewal_date: datetime = Field(..., description="Date next renewal is due")

    class Config:
        schema_extra = {
            "example": {
                "payment_id": "PAY_123",
                "status": "completed",
                "completed_at": "2025-03-31T10:30:00Z",
                "next_renewal_date": "2025-04-07T00:00:00Z"
            }
        }


class PremiumPaymentResponse(BaseModel):
    """Full premium payment record"""
    payment_id: str = Field(...)
    worker_id: str = Field(...)
    policy_id: str = Field(...)
    plan: PlanType = Field(...)
    amount_inr: float = Field(...)
    status: PaymentStatus = Field(...)
    payment_gateway: str = Field(...)
    payment_reference_id: Optional[str] = None
    initiated_at: datetime = Field(...)
    completed_at: Optional[datetime] = None
    failed_reason: Optional[str] = Field(None, description="If status=failed, why?")
    refund_amount: Optional[float] = Field(None)
    refunded_at: Optional[datetime] = None

    class Config:
        schema_extra = {
            "example": {
                "payment_id": "PAY_123",
                "worker_id": "W123",
                "policy_id": "POL_123",
                "plan": "basic",
                "amount_inr": 69.0,
                "status": "completed",
                "payment_gateway": "razorpay",
                "initiated_at": "2025-03-31T10:30:00Z",
                "completed_at": "2025-03-31T10:35:00Z"
            }
        }


# ─── POLICY RESPONSE ──────────────────────────────────────────────────────────

class PolicyResponse(BaseModel):
    """Complete policy details (returned by GET and PATCH endpoints)"""
    policy_id: str = Field(..., description="Unique policy ID from database")
    worker_id: str = Field(...)
    
    # Current tier (active this week)
    plan: PlanType = Field(...)
    coverage_percentage: float = Field(..., description="As decimal: 0.40, 0.50, or 0.70")
    weekly_premium_inr: float = Field(...)
    
    # Pending tier change (if any)
    next_plan: Optional[PlanType] = Field(None, description="Pending tier for next Monday")
    tier_change_effective: Optional[date] = Field(None, description="When next_plan becomes active")
    
    # Shift and zones
    shift: ShiftType = Field(...)
    pin_codes: List[str] = Field(...)
    
    # Policy lifecycle
    status: PolicyStatus = Field(...)
    week_start: datetime = Field(...)
    week_end: datetime = Field(...)
    coverage_activation_timestamp: datetime = Field(
        ...,
        description="24h after premium payment (coverage becomes active)"
    )
    is_active: bool = Field(..., description="True if coverage is currently active")
    
    # Payment tracking
    premium_paid_inr: float = Field(...)
    last_payment_status: PaymentStatus = Field(...)
    last_payment_date: Optional[datetime] = None
    next_renewal_due: datetime = Field(...)
    
    # Renewal tracking
    renewal_count: int = Field(default=0, ge=0, description="Number of times renewed")
    original_purchase_date: datetime = Field(...)
    
    # Metadata
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)

    class Config:
        schema_extra = {
            "example": {
                "policy_id": "POL_123",
                "worker_id": "W123",
                "plan": "basic",
                "coverage_percentage": 0.40,
                "weekly_premium_inr": 69.0,
                "next_plan": None,
                "tier_change_effective": None,
                "shift": "day",
                "pin_codes": ["560047", "560034"],
                "status": "active",
                "week_start": "2025-03-31T00:00:00Z",
                "week_end": "2025-04-06T23:59:59Z",
                "coverage_activation_timestamp": "2025-04-01T10:35:00Z",
                "is_active": True,
                "premium_paid_inr": 69.0,
                "last_payment_status": "completed",
                "next_renewal_due": "2025-04-07T00:00:00Z"
            }
        }


# ─── POLICY RENEWAL ───────────────────────────────────────────────────────────

class PolicyRenewalRequest(BaseModel):
    """Request to renew a policy for the next week"""
    policy_id: str = Field(...)
    plan: Optional[PlanType] = Field(None, description="Keep same tier or upgrade?")
    payment_method: str = Field(default="razorpay", description="razorpay|upi|wallet")

    class Config:
        schema_extra = {
            "example": {
                "policy_id": "POL_123",
                "plan": None,
                "payment_method": "razorpay"
            }
        }


class PolicyRenewalResponse(BaseModel):
    """Response after successful policy renewal"""
    old_policy_id: str = Field(...)
    new_policy_id: str = Field(...)
    old_plan: PlanType = Field(...)
    new_plan: PlanType = Field(...)
    renewal_count: int = Field(...)
    payment_initiated: bool = Field(default=False)
    payment_id: Optional[str] = None
    new_week_start: datetime = Field(...)
    new_week_end: datetime = Field(...)
    next_renewal_due: datetime = Field(...)

    class Config:
        schema_extra = {
            "example": {
                "old_policy_id": "POL_123",
                "new_policy_id": "POL_456",
                "old_plan": "basic",
                "new_plan": "basic",
                "renewal_count": 2,
                "new_week_start": "2025-04-07T00:00:00Z",
                "new_week_end": "2025-04-13T23:59:59Z"
            }
        }


# ─── POLICY ELIGIBILITY & STATUS ──────────────────────────────────────────────

class PolicyEligibilityCheck(BaseModel):
    """Result of checking if a policy qualifies for a payout"""
    policy_id: str = Field(...)
    worker_id: str = Field(...)
    is_eligible: bool = Field(...)
    
    # Eligibility criteria
    policy_active: bool = Field(...)
    coverage_activated: bool = Field(...)
    coverage_not_expired: bool = Field(...)
    worker_not_blacklisted: bool = Field(...)
    disruption_within_shift: bool = Field(...)
    
    reason: str = Field(..., description="Why eligible or not?")
    
    # For eligible policies, relevant payout info
    applicable_coverage_pct: Optional[float] = None
    estimated_payout_basis: Optional[Dict[str, Any]] = Field(None, description="DCI score, baseline, etc.")

    class Config:
        schema_extra = {
            "example": {
                "policy_id": "POL_123",
                "worker_id": "W123",
                "is_eligible": True,
                "policy_active": True,
                "coverage_activated": True,
                "coverage_not_expired": True,
                "worker_not_blacklisted": True,
                "disruption_within_shift": True,
                "reason": "Policy is active and all checks passed",
                "applicable_coverage_pct": 0.40
            }
        }


class PolicyStatusOverview(BaseModel):
    """Complete policy status for STATUS command (WhatsApp)"""
    policy_id: str = Field(...)
    worker_id: str = Field(...)
    current_plan: PlanType = Field(...)
    coverage_percentage: float = Field(...)
    weekly_premium: float = Field(...)
    status: PolicyStatus = Field(...)
    shift_window: ShiftType = Field(...)
    delivery_zones: List[str] = Field(...)
    
    is_coverage_active: bool = Field(...)
    days_remaining_in_week: int = Field(...)
    next_renewal_date: date = Field(...)
    
    pending_tier_change: Optional[Dict[str, Any]] = Field(None)
    last_payout_claim: Optional[Dict[str, Any]] = Field(None)
    
    # Quick status message for WhatsApp
    status_message: str = Field(...)

    class Config:
        schema_extra = {
            "example": {
                "policy_id": "POL_123",
                "worker_id": "W123",
                "current_plan": "basic",
                "coverage_percentage": 0.40,
                "weekly_premium": 69.0,
                "status": "active",
                "shift_window": "day",
                "delivery_zones": ["560047", "560034"],
                "is_coverage_active": True,
                "days_remaining_in_week": 4,
                "next_renewal_date": "2025-04-07",
                "pending_tier_change": None,
                "status_message": "✅ Coverage active: Shield Basic (40% coverage). Renew on 2025-04-07."
            }
        }


# ─── POLICY HISTORY & TIMELINE ────────────────────────────────────────────────

class PolicyHistoryEntry(BaseModel):
    """Single entry in a worker's policy timeline"""
    timestamp: datetime = Field(...)
    event_type: str = Field(..., description="created|renewed|activated|tier_change_queued|tier_change_activated|expired|cancelled")
    plan: PlanType = Field(...)
    prev_plan: Optional[PlanType] = None
    coverage_percentage: float = Field(...)
    weekly_premium: float = Field(...)
    details: Optional[Dict[str, Any]] = None

    class Config:
        schema_extra = {
            "example": {
                "timestamp": "2025-03-31T10:35:00Z",
                "event_type": "created",
                "plan": "basic",
                "coverage_percentage": 0.40,
                "weekly_premium": 69.0
            }
        }


class PolicyHistory(BaseModel):
    """Complete policy history for a worker"""
    worker_id: str = Field(...)
    total_weeks_active: int = Field(...)
    current_policy_id: str = Field(...)
    entries: List[PolicyHistoryEntry] = Field(...)

    class Config:
        schema_extra = {
            "example": {
                "worker_id": "W123",
                "total_weeks_active": 5,
                "current_policy_id": "POL_123",
                "entries": [
                    {
                        "timestamp": "2025-03-31T10:35:00Z",
                        "event_type": "created",
                        "plan": "basic",
                        "coverage_percentage": 0.40,
                        "weekly_premium": 69.0
                    }
                ]
            }
        }


# ─── BATCH POLICY OPERATIONS ──────────────────────────────────────────────────

class BatchPolicyRenewalRequest(BaseModel):
    """Bulk renew policies (triggered at Monday 00:01 by cron)"""
    policy_ids: List[str] = Field(..., min_items=1, max_items=1000)
    auto_renew_at_same_tier: bool = Field(default=True, description="Keep same plan or prompt upgrade?")

    class Config:
        schema_extra = {
            "example": {
                "policy_ids": ["POL_123", "POL_456"],
                "auto_renew_at_same_tier": True
            }
        }


class BatchPolicyRenewalResponse(BaseModel):
    """Response from batch renewal operation"""
    total_policies: int = Field(...)
    successful_renewals: int = Field(...)
    failed_renewals: int = Field(...)
    pending_payment: int = Field(...)
    
    renewal_summary: Dict[str, int] = Field(
        ...,
        description="Count by plan: {basic: N, plus: M, pro: K}"
    )
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        schema_extra = {
            "example": {
                "total_policies": 100,
                "successful_renewals": 95,
                "failed_renewals": 5,
                "pending_payment": 0,
                "renewal_summary": {
                    "basic": 60,
                    "plus": 25,
                    "pro": 10
                }
            }
        }


# ─── POLICY CONFIGURATION ──────────────────────────────────────────────────────

class PolicyConfig(BaseModel):
    """System-wide policy configuration (tunable parameters)"""
    premium_structure: PremiumStructure = Field(...)
    coverage_activation_delay_hours: int = Field(default=24, description="Hours after payment before coverage is live")
    weekly_cycle_start_day: str = Field(default="monday", description="Usually Monday")
    weeks_per_year: int = Field(default=52, description="Standard 52-week year")
    
    # Tier lock rules
    allow_mid_week_tier_change: bool = Field(default=True, description="Allow tier change request anytime?")
    tier_change_applies_on: str = Field(default="next_monday", description="When changes take effect")
    
    # Renewal grace period
    renewal_grace_period_hours: int = Field(default=12, description="Hours after expiry to renew without gap")

    class Config:
        schema_extra = {
            "example": {
                "premium_structure": {
                    "basic": {
                        "plan": "basic",
                        "weekly_premium_inr": 69.0,
                        "coverage_percentage": 0.40,
                        "description": "Shield Basic: ₹69/week"
                    },
                    "plus": {
                        "plan": "plus",
                        "weekly_premium_inr": 89.0,
                        "coverage_percentage": 0.50,
                        "description": "Shield Plus: ₹89/week"
                    },
                    "pro": {
                        "plan": "pro",
                        "weekly_premium_inr": 99.0,
                        "coverage_percentage": 0.70,
                        "description": "Shield Pro: ₹99/week"
                    }
                },
                "coverage_activation_delay_hours": 24
            }
        }
