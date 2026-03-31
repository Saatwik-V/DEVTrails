"""
tests/test_dci_engine.py — Unit tests for the DCI Engine
──────────────────────────────────────────────────────────
Tests cover:
  - Weighted composite score math (all 5 components)
  - Severity tier thresholds
  - NDMA catastrophic override
  - Payout trigger threshold (≥ 65)
  - Score clamping (0–100 boundary)
  - build_dci_log_payload shape and content
"""

import pytest
import sys
import os

# Add backend/ to path so local imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.dci_engine import (
    calculate_dci,
    get_severity_tier,
    is_payout_triggered,
    build_dci_log_payload,
    COMPONENT_WEIGHTS,
)


# ── Weighted Composite Math ──────────────────────────────────────────────────

class TestCalculateDCI:
    def test_all_zero_inputs_gives_zero(self):
        score = calculate_dci(0, 0, 0, 0, 0)
        assert score == 0

    def test_all_100_inputs_gives_100(self):
        score = calculate_dci(100, 100, 100, 100, 100)
        assert score == 100

    def test_weighted_math_precision(self):
        # Expected: 50*0.3 + 70*0.2 + 80*0.2 + 40*0.2 + 60*0.1
        # = 15 + 14 + 16 + 8 + 6 = 59
        score = calculate_dci(
            weather_score=50,
            aqi_score=70,
            heat_score=80,
            social_score=40,
            platform_score=60,
        )
        assert score == 59

    def test_only_weather_component(self):
        # 100 * 0.3 = 30
        score = calculate_dci(100, 0, 0, 0, 0)
        assert score == 30

    def test_only_social_component(self):
        # 100 * 0.2 = 20
        score = calculate_dci(0, 0, 0, 100, 0)
        assert score == 20

    def test_score_is_integer(self):
        score = calculate_dci(33, 47, 51, 22, 88)
        assert isinstance(score, int)

    def test_score_clamps_to_100(self):
        # Inputs of 200 should still clamp at 100
        score = calculate_dci(200, 200, 200, 200, 200)
        assert score == 100

    def test_score_clamps_to_0(self):
        score = calculate_dci(-10, -20, -5, 0, 0)
        assert score == 0


# ── NDMA Override ──────────────────────────────────────────────────────────

class TestNDMAOverride:
    def test_override_forces_95_regardless_of_components(self):
        # Even with all-zero components, NDMA override should produce 95
        score = calculate_dci(0, 0, 0, 0, 0, ndma_override=True)
        assert score == 95

    def test_override_forces_95_even_with_high_components(self):
        # Even with all components at 100, override locks score at 95 (not 100)
        score = calculate_dci(100, 100, 100, 100, 100, ndma_override=True)
        assert score == 95

    def test_override_false_uses_components(self):
        # When override=False, normal math applies
        score = calculate_dci(0, 0, 0, 0, 0, ndma_override=False)
        assert score == 0


# ── Severity Tiers ──────────────────────────────────────────────────────────

class TestGetSeverityTier:
    def test_zero_is_none(self):
        assert get_severity_tier(0) == "none"

    def test_29_is_none(self):
        assert get_severity_tier(29) == "none"

    def test_30_is_low(self):
        assert get_severity_tier(30) == "low"

    def test_49_is_low(self):
        assert get_severity_tier(49) == "low"

    def test_50_is_moderate(self):
        assert get_severity_tier(50) == "moderate"

    def test_64_is_moderate(self):
        assert get_severity_tier(64) == "moderate"

    def test_65_is_high(self):
        assert get_severity_tier(65) == "high"

    def test_79_is_high(self):
        assert get_severity_tier(79) == "high"

    def test_80_is_critical(self):
        assert get_severity_tier(80) == "critical"

    def test_94_is_critical(self):
        assert get_severity_tier(94) == "critical"

    def test_95_is_catastrophic(self):
        assert get_severity_tier(95) == "catastrophic"

    def test_100_is_catastrophic(self):
        assert get_severity_tier(100) == "catastrophic"


# ── Payout Trigger ──────────────────────────────────────────────────────────

class TestIsPayoutTriggered:
    def test_score_64_does_not_trigger(self):
        assert is_payout_triggered(64) is False

    def test_score_65_triggers(self):
        assert is_payout_triggered(65) is True

    def test_score_100_triggers(self):
        assert is_payout_triggered(100) is True

    def test_score_0_does_not_trigger(self):
        assert is_payout_triggered(0) is False


# ── DB Payload Builder ───────────────────────────────────────────────────────

class TestBuildDCILogPayload:
    def test_payload_has_all_required_fields(self):
        payload = build_dci_log_payload(
            pincode="560001",
            dci_score=72,
            weather={"score": 80},
            aqi={"score": 60},
            heat={"score": 40},
            social={"score": 30},
            platform={"score": 20},
            ndma_override=False,
            shift_active="day",
        )
        required_keys = [
            "pincode", "total_score", "rainfall_score", "aqi_score",
            "heat_score", "social_score", "platform_score", "severity_tier",
            "ndma_override_active", "shift_active", "is_shift_window_active",
        ]
        for key in required_keys:
            assert key in payload, f"Missing key: {key}"

    def test_payload_score_roundtrips(self):
        payload = build_dci_log_payload(
            pincode="560034", dci_score=85,
            weather={"score": 90}, aqi={"score": 70}, heat={"score": 80},
            social={"score": 50}, platform={"score": 40},
        )
        assert payload["total_score"] == 85
        assert payload["severity_tier"] == "critical"

    def test_ndma_override_reflected_in_payload(self):
        payload = build_dci_log_payload(
            pincode="560001", dci_score=95,
            weather={"score": 0}, aqi={"score": 0}, heat={"score": 0},
            social={"score": 0}, platform={"score": 0},
            ndma_override=True,
        )
        assert payload["ndma_override_active"] is True
        assert payload["severity_tier"] == "catastrophic"
