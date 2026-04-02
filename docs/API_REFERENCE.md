# 🔌 GigKavach API Reference

**API Version**: 0.1.0 (Phase 2)  
**Base URL**: `https://devtrails-backend-dnlr.onrender.com` (Production)  
**Local Dev**: `http://localhost:8000`  
**API Docs**: `/docs` (Swagger UI) | `/redoc` (ReDoc)

---

## 📋 Authentication

All API endpoints require no authentication in Phase 2 (development mode). Production will require:
- API Key header: `X-API-Key: <key>`
- WhatsApp webhook signature verification (enabled)

---

## 🏥 Health & System

### `GET /health`
Basic liveness check (Render monitoring).

**Response** (200 OK):
```json
{
  "status": "ok",
  "service": "GigKavach API",
  "version": "0.1.0-phase2",
  "environment": "development|production",
  "timestamp": "2026-04-02T10:30:45Z"
}
```

---

### `GET /health/full`
Complete dependency check.

**Response** (200 OK):
```json
{
  "status": "ok|degraded",
  "checks": {
    "supabase": { "status": "ok|error", "latency_ms": 45 },
    "cache": { "status": "ok|error", "type": "in-memory" },
    "twilio": { "status": "ok|unconfigured" },
    "tomorrow_io": { "status": "ok|unconfigured" }
  },
  "timestamp": "2026-04-02T10:30:45Z"
}
```

---

## 👷 Workers

### `POST /workers/register`
Register a new worker via WhatsApp.

**Request**:
```json
{
  "phone": "+919876543210",
  "first_name": "Rajesh",
  "last_name": "Kumar",
  "city": "Mumbai",
  "vehicle_type": "bike|scooter|auto|cab",
  "platform": "zomato|swiggy|ola|uber"
}
```

**Response** (201 Created):
```json
{
  "worker_id": "WKR-12547",
  "phone": "+919876543210",
  "first_name": "Rajesh",
  "onboarding_status": "pending|complete",
  "created_at": "2026-04-02T10:30:45Z"
}
```

---

### `GET /workers/{worker_id}`
Fetch worker profile.

**Response** (200 OK):
```json
{
  "worker_id": "WKR-12547",
  "phone": "+919876543210",
  "first_name": "Rajesh",
  "last_name": "Kumar",
  "city": "Mumbai",
  "vehicle_type": "bike",
  "platform": "zomato",
  "policy_id": "POL-123456",
  "coverage_status": "active|inactive|pending",
  "baseline_earnings": 1200.0,
  "dci_tier": "gold|silver|bronze",
  "language": "en|hi|ta|te|ml",
  "created_at": "2026-04-02T10:30:45Z"
}
```

---

## 📋 Policies

### `POST /policies/subscribe`
Worker purchases weekly coverage.

**Request**:
```json
{
  "worker_id": "WKR-12547",
  "tier": "gold|silver|bronze",
  "premium_amount": 69.0,
  "payment_txn_id": "TXN-xyz123",
  "effective_date": "2026-04-01"
}
```

**Response** (201 Created):
```json
{
  "policy_id": "POL-123456",
  "worker_id": "WKR-12547",
  "tier": "gold",
  "premium": 69.0,
  "coverage_period": "2026-04-01 to 2026-04-07",
  "status": "active",
  "created_at": "2026-04-02T10:30:45Z"
}
```

---

### `GET /policies/{policy_id}`
Fetch policy details.

**Response** (200 OK):
```json
{
  "policy_id": "POL-123456",
  "worker_id": "WKR-12547",
  "tier": "gold",
  "coverage_period": "2026-04-01 to 2026-04-07",
  "status": "active|expired|suspended",
  "premium": 69.0,
  "claim_limit": 5000.0,
  "claims_used": 2,
  "created_at": "2026-04-02T10:30:45Z"
}
```

---

## 🌍 DCI (Disruption Composite Index)

### `GET /dci/{pincode}`
Fetch current DCI score for a pincode.

**Path Parameters**:
- `pincode` (string): Indian pincode, e.g., `560001`

**Response** (200 OK):
```json
{
  "pincode": "560001",
  "dci_score": 78.5,
  "status": "high|medium|low|critical",
  "components": {
    "weather": 45.2,
    "aqi": 32.1,
    "social": 28.5,
    "timestamp": "2026-04-02T10:30:00Z"
  },
  "triggered_workers": 127,
  "active_disruption": "Heavy Rainfall"
}
```

---

### `GET /dci/latest-alerts`
Fetch recent DCI trigger alerts.

**Query Parameters**:
- `limit` (int, default=10): Number of alerts to return
- `minutes_back` (int, default=60): Look back period

**Response** (200 OK):
```json
{
  "alerts": [
    {
      "pincode": "560001",
      "dci_score": 78.5,
      "trigger_time": "2026-04-02T10:25:00Z",
      "disruption_type": "Heavy Rainfall",
      "affected_zones": 45,
      "triggered_workers": 127
    }
  ],
  "total_alerts": 1,
  "timestamp": "2026-04-02T10:30:45Z"
}
```

---

### `GET /dci/total/today`
Get total disruption impact for today.

**Response** (200 OK):
```json
{
  "date": "2026-04-02",
  "total_dci_events": 12,
  "total_workers_impacted": 4532,
  "avg_dci_score": 62.3,
  "peak_dci": 89.2,
  "disruption_types": [
    { "type": "Heavy Rainfall", "count": 5 },
    { "type": "Heatwave", "count": 4 }
  ]
}
```

---

## 💸 Payouts

### `POST /payouts/calculate`
Calculate payout for a claim.

**Request**:
```json
{
  "worker_id": "WKR-12547",
  "claim_id": "CLM-12345",
  "dci_score": 78.5,
  "disruption_duration_minutes": 240,
  "baseline_earnings": 1200.0,
  "disruption_type": "heavy_rainfall"
}
```

**Response** (200 OK):
```json
{
  "claim_id": "CLM-12345",
  "worker_id": "WKR-12547",
  "payout_amount": 450.0,
  "currency": "INR",
  "breakdown": {
    "baseline": 1200.0,
    "duration_ratio": 0.5,
    "xgboost_multiplier": 0.75,
    "formula": "1200 × 0.5 × 0.75 = 450"
  },
  "confidence": 0.89,
  "timestamp": "2026-04-02T10:30:45Z"
}
```

---

### `POST /payouts/execute`
Execute a payout to worker's UPI account.

**Request**:
```json
{
  "claim_id": "CLM-12345",
  "worker_id": "WKR-12547",
  "payout_amount": 450.0,
  "upi_id": "rajesh@paytm"
}
```

**Response** (200 OK):
```json
{
  "transaction_id": "TXN-xyz123",
  "claim_id": "CLM-12345",
  "worker_id": "WKR-12547",
  "payout_amount": 450.0,
  "status": "pending|success|failed",
  "upi_id": "rajesh@paytm",
  "timestamp": "2026-04-02T10:30:45Z",
  "estimated_delivery": "2026-04-02T23:59:59Z"
}
```

---

### `GET /payouts/history/{worker_id}`
Fetch payout history for a worker.

**Response** (200 OK):
```json
{
  "worker_id": "WKR-12547",
  "payouts": [
    {
      "claim_id": "CLM-12345",
      "amount": 450.0,
      "status": "success",
      "executed_at": "2026-04-02T10:30:45Z"
    },
    {
      "claim_id": "CLM-12344",
      "amount": 350.0,
      "status": "success",
      "executed_at": "2026-04-01T18:15:30Z"
    }
  ],
  "total_payouts": 800.0,
  "count": 2
}
```

---

### `GET /payouts/total/today`
Get total payouts distributed today.

**Response** (200 OK):
```json
{
  "date": "2026-04-02",
  "total_payouts": 125000.0,
  "total_claims": 450,
  "avg_payout": 277.78,
  "status_breakdown": {
    "success": 440,
    "pending": 8,
    "failed": 2
  }
}
```

---

## 🚨 Fraud Detection

### `POST /fraud/check-fraud`
Fraud assessment for a claim.

**Request**:
```json
{
  "claim_id": "CLM-12345",
  "worker_id": "WKR-12547",
  "dci_score": 78.5,
  "claim_frequency": 2,
  "time_since_last_claim": 1440,
  "policy_age_days": 7
}
```

**Response** (200 OK):
```json
{
  "claim_id": "CLM-12345",
  "is_fraud": false,
  "fraud_score": 0.25,
  "decision": "APPROVE|FLAG_50|BLOCK",
  "payout_action": "100%|50%_HOLD_48H|0%",
  "explanation": "Low risk score. Multiple signals within normal range.",
  "signals": {
    "stage_1_blocks": [],
    "stage_2_anomalies": ["claim_frequency_high"],
    "stage_3_score": 0.25
  },
  "confidence": 0.92,
  "timestamp": "2026-04-02T10:30:45Z"
}
```

---

### `POST /fraud/appeal`
Appeal a fraud hold decision.

**Request**:
```json
{
  "worker_id": "WKR-12547",
  "claim_id": "CLM-12345",
  "appeal_reason": "I was actually working, check my GPS trail",
  "supporting_docs": ["gps_trail.pdf", "delivery_photos.jpg"]
}
```

**Response** (200 OK):
```json
{
  "appeal_id": "APL-xyz123",
  "claim_id": "CLM-12345",
  "status": "filed|approved|rejected",
  "review_deadline": "2026-04-04T23:59:59Z",
  "created_at": "2026-04-02T10:30:45Z"
}
```

---

## 💬 WhatsApp Webhook

### `POST /whatsapp/webhook`
WhatsApp message webhook (Twilio).

**Request** (Signed Twilio payload):
```
From: +919876543210
Body: /join
MessageSid: SM1234567890
```

**Response** (200 OK):
```
Accepted: Message queued for processing
```

**Webhook Events Handled**:
- `/join` → Start onboarding
- `/status` → Check coverage status
- `/renew` → Renew policy
- `/shift` → Update shift timing
- `/lang <code>` → Change language
- `/help` → Get help
- `/appeal` → Appeal fraud hold

---

## 📊 Analytics & Admin

### `GET /stats/workers/active/week`
Active workers this week.

**Response** (200 OK):
```json
{
  "week": "2026-03-31 to 2026-04-07",
  "active_workers": 1234,
  "onboarded_this_week": 45,
  "policies_sold": 890,
  "total_revenue": 61410.0
}
```

---

## ⚠️ Error Responses

All endpoints use standard HTTP status codes:

### 400 Bad Request
```json
{
  "detail": "Invalid request",
  "error_code": "INVALID_PINCODE",
  "timestamp": "2026-04-02T10:30:45Z"
}
```

### 404 Not Found
```json
{
  "detail": "Worker not found",
  "error_code": "WORKER_NOT_FOUND",
  "timestamp": "2026-04-02T10:30:45Z"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error",
  "error_code": "INTERNAL_ERROR",
  "timestamp": "2026-04-02T10:30:45Z"
}
```

---

## 🔐 Environment Variables Required

```bash
# Database
SUPABASE_URL=https://...supabase.co
SUPABASE_KEY=eyJhbGc...

# WhatsApp/SMS
TWILIO_ACCOUNT_SID=ACxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxx
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_WHATSAPP_SANDBOX=+14155238886

# Weather & AQI
TOMORROW_IO_API_KEY=xxxxxxxx
AQICN_API_KEY=xxxxxxxx

# Payment
RAZORPAY_KEY_ID=rzp_xxx
RAZORPAY_SECRET=xxxxxxxx

# Frontend
VITE_BACKEND_PROXY_TARGET=http://localhost:8000

# Deployment
APP_ENV=development|production
PORT=8000
```

---

## 🚀 Getting Started

### Local Development
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Test Quick Endpoints
```bash
# Health check
curl http://localhost:8000/health

# Full health check
curl http://localhost:8000/health/full

# DCI for Mumbai (pincode 400001)
curl http://localhost:8000/dci/400001

# API docs
open http://localhost:8000/docs
```

---

## 📝 Notes

- All timestamps are in ISO 8601 format (UTC)
- Amounts are in Indian Rupees (₹ INR)
- Phone numbers use E.164 format (+country_code)
- Pincodes are exactly 6 digits (Indian postal codes)
- Worker IDs, Policy IDs, Claim IDs are auto-generated
