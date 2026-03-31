"""
services/dci_engine.py — Disruption Composite Index Engine
──────────────────────────────────────────────────────────────
Core business logic for computing the DCI composite score from
5 weighted environmental and social components.

DCI Formula (5 components, max 100):
  Weather (rainfall) : weight 0.30
  AQI                : weight 0.20
  Heat               : weight 0.20
  Social disruption  : weight 0.20
  Platform signals   : weight 0.10

Severity Tiers:
  0-29   → none
  30-49  → low
  50-64  → moderate
  65-79  → high
  80-94  → critical
  ≥ 95   → catastrophic  (NDMA override also forces this)

The DCI poller calls calculate_dci() after collecting individual
component scores, then persists the result to Redis + Supabase.
"""

import logging
from typing import Dict

logger = logging.getLogger("gigkavach.dci_engine")

# ─── Severity Tier Thresholds ────────────────────────────────────────────────
SEVERITY_TIERS = [
    (95, "catastrophic"),   # NDMA override also forces ≥95
    (80, "critical"),
    (65, "high"),
    (50, "moderate"),
    (30, "low"),
    (0,  "none"),
]

# ─── Component Weights (must sum to 1.0) ─────────────────────────────────────
COMPONENT_WEIGHTS = {
    "weather":  0.30,  # rainfall / flooding signal
    "aqi":      0.20,  # air quality index
    "heat":     0.20,  # temperature stress
    "social":   0.20,  # bandh / unrest / protest (NLP feed)
    "platform": 0.10,  # delivery platform-reported surge / block
}


def calculate_dci(
    weather_score: float,
    aqi_score: float,
    heat_score: float,
    social_score: float,
    platform_score: float,
    ndma_override: bool = False,
) -> int:
    """
    Computes the composite DCI score (0–100) from 5 component scores.

    Args:
        weather_score:  0–100 rainfall/flood signal
        aqi_score:      0–100 air quality disruption
        heat_score:     0–100 temperature stress (38–42°C gradient)
        social_score:   0–100 social unrest / bandh from NLP classifier
        platform_score: 0–100 platform-reported delivery blocks
        ndma_override:  If True, DCI is forced to 95 (catastrophic override)

    Returns:
        int: composite DCI score clamped to [0, 100]
    """
    if ndma_override:
        logger.warning("[DCI ENGINE] NDMA catastrophic override active — forcing DCI = 95")
        return 95

    composite = (
        weather_score  * COMPONENT_WEIGHTS["weather"]  +
        aqi_score      * COMPONENT_WEIGHTS["aqi"]      +
        heat_score     * COMPONENT_WEIGHTS["heat"]      +
        social_score   * COMPONENT_WEIGHTS["social"]   +
        platform_score * COMPONENT_WEIGHTS["platform"]
    )

    # Clamp to valid range and return as integer
    return min(100, max(0, round(composite)))


def get_severity_tier(score: int) -> str:
    """
    Maps a numeric DCI score to a named severity tier.

    Args:
        score: DCI score (0–100)

    Returns:
        str: one of 'none', 'low', 'moderate', 'high', 'critical', 'catastrophic'
    """
    for threshold, tier in SEVERITY_TIERS:
        if score >= threshold:
            return tier
    return "none"


def is_payout_triggered(score: int) -> bool:
    """
    Returns True if DCI score is at or above the 65-point payout trigger threshold.
    This is the minimum score required for a worker to become eligible for a payout.

    The threshold of 65 (≥ 'high') is specified in the GigKavach requirements.
    """
    return score >= 65


def build_dci_log_payload(
    pincode: str,
    dci_score: int,
    weather: Dict,
    aqi: Dict,
    heat: Dict,
    social: Dict,
    platform: Dict,
    ndma_override: bool = False,
    shift_active: str = None,
) -> Dict:
    """
    Builds the full DB row payload for the `dci_logs` Supabase table.

    Args:
        pincode:        Zone pin code being tracked
        dci_score:      Final composite score from calculate_dci()
        weather/aqi/heat/social/platform: Raw component dicts with {score, ...}
        ndma_override:  Whether NDMA catastrophic override was active
        shift_active:   Name of the currently active shift window

    Returns:
        Dict ready for sb.table("dci_logs").insert(payload)
    """
    return {
        "pincode":              pincode,
        "total_score":          dci_score,
        "rainfall_score":       int(weather.get("score", 0)),
        "aqi_score":            int(aqi.get("score", 0)),
        "heat_score":           int(heat.get("score", 0)),
        "social_score":         int(social.get("score", 0)),
        "platform_score":       int(platform.get("score", 0)),
        "severity_tier":        get_severity_tier(dci_score),
        "ndma_override_active": ndma_override,
        "shift_active":         shift_active,
        "is_shift_window_active": shift_active is not None,
    }
