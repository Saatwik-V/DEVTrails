"""
tests/test_workers_and_policies.py — Unit Tests
─────────────────────────────────────────────────
Tests for:
  - POST /api/v1/register
  - GET  /api/v1/policy/{id}
  - PATCH /api/v1/policy/{id}

Uses FastAPI's TestClient with a MOCK Supabase client so no real
DB connection is needed. Varshit can run real integration tests
once Supabase is configured by simply setting .env credentials.

Run with:
    cd gigkavach-backend
    source venv/bin/activate
    pip install pytest httpx -q
    pytest tests/test_workers_and_policies.py -v
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from main import app

# Module-level client — shared across all tests to avoid module caching issues
client = TestClient(app, raise_server_exceptions=False)


# ─── Mock Supabase Factory ────────────────────────────────────────────────────

def make_mock_sb(existing_worker=None, policy_row=None, update_result=None):
    """
    Creates a chainable Supabase mock that mimics the fluent interface:
        sb.table("x").select("*").eq("id", id).execute()
    """
    mock_sb = MagicMock()

    workers_chain = MagicMock()
    workers_chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[existing_worker] if existing_worker else []
    )
    workers_chain.insert.return_value.execute.return_value = MagicMock(data=[{"id": "MOCK-WORKER-ID"}])

    policies_chain = MagicMock()
    policies_chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[policy_row] if policy_row else []
    )
    policies_chain.insert.return_value.execute.return_value = MagicMock(data=[{"id": "MOCK-POLICY-ID"}])
    policies_chain.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[update_result] if update_result else []
    )

    def table_router(table_name):
        if table_name == "workers":
            return workers_chain
        if table_name == "policies":
            return policies_chain
        return MagicMock()

    mock_sb.table.side_effect = table_router
    return mock_sb


# ─── Shared Fixtures ──────────────────────────────────────────────────────────

VALID_REGISTER_PAYLOAD = {
    "phone_number": "+919876543210",
    "platform": "zomato",
    "shift": "day",
    "upi_id": "ravi@upi",
    "pin_codes": ["560047", "560034"],
    "plan": "basic",
    "language": "kn",
}

_now = datetime.utcnow()
SAMPLE_POLICY_ROW = {
    "id":           "POLICY-001",
    "worker_id":    "WORKER-001",
    "plan":         "basic",
    "shift":        "day",
    "pin_codes":    ["560047"],
    "week_start":   _now.replace(hour=0, minute=0, second=0).isoformat(),
    "week_end":     (_now + timedelta(days=6)).replace(hour=23, minute=59, second=59).isoformat(),
    "premium_paid": 69.0,
    "is_active":    True,
    "created_at":   _now.isoformat(),
    "next_plan":    None,
}


# ─── POST /api/v1/register ────────────────────────────────────────────────────

class TestRegisterWorker:

    def test_register_success_happy_path(self):
        """TC-REG-01: Valid payload → 201, returns worker_id and policy_id"""
        with patch("api.workers.get_supabase", return_value=make_mock_sb()):
            response = client.post("/api/v1/register", json=VALID_REGISTER_PAYLOAD)
        assert response.status_code == 201
        body = response.json()
        assert "worker_id" in body
        assert "policy_id" in body
        assert "coverage_active_from" in body
        assert body["plan"] == "basic"
        assert body["phone_number"] == "+919876543210"

    def test_register_duplicate_phone_returns_409(self):
        """TC-REG-02: Duplicate phone number → 409 Conflict"""
        existing = {"id": "EXISTING-WORKER", "phone_number": "+919876543210"}
        with patch("api.workers.get_supabase", return_value=make_mock_sb(existing_worker=existing)):
            response = client.post("/api/v1/register", json=VALID_REGISTER_PAYLOAD)
        assert response.status_code == 409
        assert "already registered" in response.json()["detail"]["error"]

    def test_register_invalid_phone_format_returns_422(self):
        """TC-REG-03: Phone without +91 prefix → 422"""
        bad_payload = {**VALID_REGISTER_PAYLOAD, "phone_number": "9876543210"}
        with patch("api.workers.get_supabase", return_value=make_mock_sb()):
            response = client.post("/api/v1/register", json=bad_payload)
        assert response.status_code == 422

    def test_register_invalid_upi_returns_422(self):
        """TC-REG-04: UPI ID without @ → 422 from Pydantic validator"""
        bad_payload = {**VALID_REGISTER_PAYLOAD, "upi_id": "raviupi"}
        with patch("api.workers.get_supabase", return_value=make_mock_sb()):
            response = client.post("/api/v1/register", json=bad_payload)
        assert response.status_code == 422

    def test_register_invalid_pin_code_returns_422(self):
        """TC-REG-05: 5-digit pin code → 422"""
        bad_payload = {**VALID_REGISTER_PAYLOAD, "pin_codes": ["56004"]}
        with patch("api.workers.get_supabase", return_value=make_mock_sb()):
            response = client.post("/api/v1/register", json=bad_payload)
        assert response.status_code == 422

    def test_register_too_many_pin_codes_returns_422(self):
        """TC-REG-06: 6 pin codes (over limit of 5) → 422"""
        bad_payload = {**VALID_REGISTER_PAYLOAD, "pin_codes": [f"56000{i}" for i in range(6)]}
        with patch("api.workers.get_supabase", return_value=make_mock_sb()):
            response = client.post("/api/v1/register", json=bad_payload)
        assert response.status_code == 422

    def test_register_coverage_delay_is_24h(self):
        """TC-REG-07: coverage_active_from must be ~24 hours from now"""
        with patch("api.workers.get_supabase", return_value=make_mock_sb()):
            response = client.post("/api/v1/register", json=VALID_REGISTER_PAYLOAD)
        assert response.status_code == 201
        coverage_from = datetime.fromisoformat(response.json()["coverage_active_from"])
        delta = (coverage_from - datetime.utcnow()).total_seconds()
        assert 23 * 3600 < delta < 25 * 3600, f"Expected ~24hr delay, got {delta/3600:.1f}h"

    def test_register_pro_plan(self):
        """TC-REG-08: Pro plan accepted and returned correctly"""
        pro_payload = {**VALID_REGISTER_PAYLOAD, "plan": "pro"}
        with patch("api.workers.get_supabase", return_value=make_mock_sb()):
            response = client.post("/api/v1/register", json=pro_payload)
        assert response.status_code == 201
        assert response.json()["plan"] == "pro"

    def test_register_all_5_languages_accepted(self):
        """TC-REG-09: All 5 supported languages must be valid"""
        for lang in ["en", "kn", "hi", "ta", "te"]:
            payload = {
                **VALID_REGISTER_PAYLOAD,
                "language": lang,
                "phone_number": f"+9198765432{ord(lang[0]) % 10:02d}",
            }
            with patch("api.workers.get_supabase", return_value=make_mock_sb()):
                response = client.post("/api/v1/register", json=payload)
            assert response.status_code == 201, f"Language '{lang}' failed: {response.json()}"


# ─── GET /api/v1/policy/{id} ─────────────────────────────────────────────────

class TestGetPolicy:

    def test_get_policy_valid_id_returns_200(self):
        """TC-POL-01: Valid policy_id → 200 with full policy object"""
        with patch("api.policies.get_supabase", return_value=make_mock_sb(policy_row=SAMPLE_POLICY_ROW)):
            response = client.get("/api/v1/policy/POLICY-001")
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == "POLICY-001"
        assert body["worker_id"] == "WORKER-001"
        assert body["plan"] == "basic"
        assert body["shift"] == "day"
        assert "pin_codes" in body
        assert "week_start" in body
        assert "week_end" in body

    def test_get_policy_invalid_id_returns_404(self):
        """TC-POL-02: Non-existent policy_id → 404"""
        with patch("api.policies.get_supabase", return_value=make_mock_sb(policy_row=None)):
            response = client.get("/api/v1/policy/DOES-NOT-EXIST")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]["error"].lower()


# ─── PATCH /api/v1/policy/{id} ───────────────────────────────────────────────

class TestUpdatePolicy:

    def test_tier_upgrade_queued_for_next_monday(self):
        """TC-POL-03: Tier upgrade → 200, tier_change_effective must be a Monday"""
        updated_row = {**SAMPLE_POLICY_ROW, "next_plan": "pro"}
        with patch("api.policies.get_supabase",
                   return_value=make_mock_sb(policy_row=SAMPLE_POLICY_ROW, update_result=updated_row)):
            response = client.patch("/api/v1/policy/POLICY-001", json={"plan": "pro"})
        assert response.status_code == 200
        body = response.json()
        assert body["tier_change_effective"] is not None
        effective_date = datetime.fromisoformat(body["tier_change_effective"]).date()
        assert effective_date.weekday() == 0, f"Expected Monday, got {effective_date.strftime('%A')}"

    def test_same_tier_patch_is_noop(self):
        """TC-POL-04: Patching with same plan → tier_change_effective is None"""
        with patch("api.policies.get_supabase",
                   return_value=make_mock_sb(policy_row=SAMPLE_POLICY_ROW, update_result=SAMPLE_POLICY_ROW)):
            response = client.patch("/api/v1/policy/POLICY-001", json={"plan": "basic"})
        assert response.status_code == 200
        assert response.json()["tier_change_effective"] is None

    def test_shift_change_is_immediate(self):
        """TC-POL-05: Shift change → 200, shift updated, no tier_change_effective"""
        updated_row = {**SAMPLE_POLICY_ROW, "shift": "night"}
        with patch("api.policies.get_supabase",
                   return_value=make_mock_sb(policy_row=SAMPLE_POLICY_ROW, update_result=updated_row)):
            response = client.patch("/api/v1/policy/POLICY-001", json={"shift": "night"})
        assert response.status_code == 200
        body = response.json()
        assert body["tier_change_effective"] is None
        assert body["shift"] == "night"

    def test_pin_codes_change_is_immediate(self):
        """TC-POL-06: Pin code update → 200, new pin codes reflected"""
        new_pins = ["560076", "560103"]
        updated_row = {**SAMPLE_POLICY_ROW, "pin_codes": new_pins}
        with patch("api.policies.get_supabase",
                   return_value=make_mock_sb(policy_row=SAMPLE_POLICY_ROW, update_result=updated_row)):
            response = client.patch("/api/v1/policy/POLICY-001", json={"pin_codes": new_pins})
        assert response.status_code == 200
        assert response.json()["pin_codes"] == new_pins

    def test_patch_with_no_fields_returns_400(self):
        """TC-POL-07: Empty PATCH body → 400 Bad Request"""
        with patch("api.policies.get_supabase",
                   return_value=make_mock_sb(policy_row=SAMPLE_POLICY_ROW)):
            response = client.patch("/api/v1/policy/POLICY-001", json={})
        assert response.status_code == 400
        assert "No update fields" in response.json()["detail"]

    def test_patch_invalid_policy_id_returns_404(self):
        """TC-POL-08: PATCH on non-existent policy → 404"""
        with patch("api.policies.get_supabase", return_value=make_mock_sb(policy_row=None)):
            response = client.patch("/api/v1/policy/FAKE-ID", json={"shift": "morning"})
        assert response.status_code == 404

    def test_patch_invalid_shift_value_returns_422(self):
        """TC-POL-09: 'afternoon' is not a valid ShiftType → 422"""
        with patch("api.policies.get_supabase",
                   return_value=make_mock_sb(policy_row=SAMPLE_POLICY_ROW)):
            response = client.patch("/api/v1/policy/POLICY-001", json={"shift": "afternoon"})
        assert response.status_code == 422

    def test_patch_invalid_pin_code_returns_422(self):
        """TC-POL-10: 4-digit pin code → 422 from Pydantic validator"""
        with patch("api.policies.get_supabase",
                   return_value=make_mock_sb(policy_row=SAMPLE_POLICY_ROW)):
            response = client.patch("/api/v1/policy/POLICY-001", json={"pin_codes": ["5600"]})
        assert response.status_code == 422

    def test_multi_field_patch_works(self):
        """TC-POL-11: PATCH shift + pin_codes together → 200"""
        new_pins = ["560095"]
        updated_row = {**SAMPLE_POLICY_ROW, "shift": "morning", "pin_codes": new_pins}
        with patch("api.policies.get_supabase",
                   return_value=make_mock_sb(policy_row=SAMPLE_POLICY_ROW, update_result=updated_row)):
            response = client.patch(
                "/api/v1/policy/POLICY-001",
                json={"shift": "morning", "pin_codes": new_pins}
            )
        assert response.status_code == 200
        body = response.json()
        assert body["shift"] == "morning"
        assert body["pin_codes"] == new_pins
