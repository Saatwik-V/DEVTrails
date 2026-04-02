# ⚡ GigKavach Quick Reference Guide

**Last Updated**: April 2, 2026  
**Phase**: 2 (P0 complete, P1 complete, P2 in progress)  
**Status**: Production-ready (Render + Vercel deployed)

---

## 🎯 30-Second Start

```bash
# Clone repo
git clone https://github.com/yourname/DEVTrails.git && cd DEVTrails

# Setup env
cp .env.example .env
# [ Edit .env with Supabase, Twilio, Tomorrow.io keys ]

# Backend
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend && npm install && npm run dev

# Visit http://localhost:5173 (frontend auto-redirects to backend at http://localhost:8000)
```

---

## 📋 Environment Variables

### Required (App breaks without these)

```bash
# Supabase (PostgreSQL database)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Twilio (WhatsApp + SMS)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_WHATSAPP_SANDBOX=+14155238886

# Razorpay (Payments)
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxxxxx
RAZORPAY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
```

### Optional (App uses fallbacks without these)

```bash
# Weather
TOMORROW_IO_API_KEY=xxxxxxxx
(Falls back to Open-Meteo if missing)

# Air Quality
AQICN_API_KEY=xxxxxxxx
(Falls back to static mock data if missing)

# Frontend Backend URL
VITE_BACKEND_PROXY_TARGET=http://localhost:8000
(Defaults to Render production URL)
```

### Deployment-Specific

```bash
APP_ENV=development|production
PORT=8000
DCI_POLL_INTERVAL_SECONDS=300 (5 minutes)
```

---

## 🗂️ Project Structure (Current State - Phase 2)

```
DEVTrails/
├── backend/                      # FastAPI application
│   ├── main.py                   # Entry point
│   ├── api/                      # Endpoints (NO duplicates)
│   │   ├── health.py             # /health, /health/full
│   │   ├── workers.py            # /workers/**
│   │   ├── policies.py           # /policies/**
│   │   ├── dci.py                # /dci/**
│   │   ├── payouts.py            # /payouts/**
│   │   ├── fraud.py              # /fraud/**
│   │   └── whatsapp.py           # /whatsapp/**
│   ├── services/                 # Business logic
│   │   ├── payout_service.py     # XGBoost v3 multiplier
│   │   ├── fraud_service.py      # 3-stage fraud pipeline
│   │   ├── eligibility_service.py# 4-rule eligibility check
│   │   ├── dci_engine.py         # DCI score calculation
│   │   └── ... (others)
│   ├── ml/                       # ML models
│   ├── cron/                     # Background jobs
│   │   ├── dci_poller.py         # Every 5 min
│   │   ├── claims_trigger.py     # Every 5 min
│   │   └── settlement_service.py # Daily 11:55 PM
│   ├── database/                 # Schemas & seeds
│   ├── config/                   # Settings
│   └── tests/                    # Test suite (40+ tests)
│
├── frontend/                     # React + Vite (TSX + JSX)
│   ├── src/
│   │   ├── main.jsx              # Entry point
│   │   ├── App.jsx               # Root component
│   │   ├── pages/                # JSX pages (NO TSX duplicates)
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Analytics.jsx
│   │   │   ├── Fraud.jsx
│   │   │   ├── Payouts.jsx
│   │   │   └── ...
│   │   ├── components/           # Mix of TSX (typed) + JSX
│   │   │   ├── common/           # Button.jsx only (no Button.tsx)
│   │   │   ├── layout/           # Header.jsx only (no Header.tsx)
│   │   │   ├── dci/              # TSX typed components
│   │   │   ├── payouts/          # TSX typed components
│   │   │   └── ...
│   │   └── utils/                # Helpers
│   ├── vite.config.ts            # Vite + Vercel config
│   ├── tailwind.config.js        # Styling
│   └── package.json
│
├── docs/                         # Documentation
│   ├── DEPLOYMENT.md             # Deployment setup
│   ├── API_REFERENCE.md          # API endpoints (NEW)
│   └── folder_structure.md       # Folder layout
│
├── data/                         # Training data
├── models/                       # ML artifacts
│
├── .env.example                  # Template (COMMITTED)
├── .env                          # Actual (GITIGNORED)
├── render.yaml                   # Render config
├── vercel.json                   # Vercel config
├── README.md                     # Main docs
└── requirements.txt              # Python deps
```

---

## 🚀 Deployment

### Backend (Render.com)
```bash
# Service URL: https://devtrails-backend-dnlr.onrender.com

# Deploy process:
1. Push to main branch
2. GitHub Actions triggers render.yaml
3. Render deploys backend automatically
4. Health check: GET /health (200 OK)
```

### Frontend (Vercel)
```bash
# Service URL: https://devtrails-frontend-...vercel.app

# Deploy process:
1. Push to main branch
2. GitHub Actions triggers vercel.json
3. Vercel deploys frontend automatically
4. Frontend proxies /api to backend
```

### Environment Variables (Deployed)
1. Go to Render dashboard → Settings → Environment
2. Add all variables from `.env.example`
3. Critical: `SUPABASE_KEY`, `TWILIO_ACCOUNT_SID`, `RAZORPAY_KEY_ID`
4. Restart service after updating

---

## 📊 API Endpoints Quick List

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Liveness check |
| GET | `/health/full` | Full dependency check |
| POST | `/workers/register` | Register new worker |
| GET | `/workers/{id}` | Fetch worker profile |
| POST | `/policies/subscribe` | Buy weekly policy |
| GET | `/dci/{pincode}` | Get DCI score |
| GET | `/dci/latest-alerts` | Recent disruptions |
| POST | `/payouts/calculate` | Calculate payout |
| POST | `/fraud/check-fraud` | Assess fraud risk |
| POST | `/whatsapp/webhook` | WhatsApp webhook |

**Full API Reference**: See [docs/API_REFERENCE.md](API_REFERENCE.md)

---

## 🧪 Testing

### Run All Tests
```bash
cd backend
pytest tests/ -v

# Specific test file
pytest tests/test_integration_p1.py -v

# With coverage
pytest tests/ --cov=api --cov=services
```

### Run Demo Pipeline
```bash
cd backend
python3 demo_claims_pipeline.py
```

### Frontend Tests (Planned for P3)
```bash
cd frontend
npm run test
```

---

## 🔧 Common Tasks

### Add a new API endpoint
1. Create route in `backend/api/new_model.py`
2. Import router in `backend/main.py`
3. Add to `docs/API_REFERENCE.md`
4. Test with `curl` or Swagger UI at `/docs`

### Update database schema
1. Edit `backend/database/schema.sql`
2. Run migration in Supabase console
3. Update seed data if needed

### Train new ML model
1. Update training code in `backend/ml/`
2. Save model artifact to `models/`
3. Update `xgboost_loader.py` to load new version

### Deploy frontend changes
1. Edit React components in `frontend/src/`
2. Test locally: `npm run dev`
3. Push to main branch → auto-deploys to Vercel

---

## 📈 Performance Targets (Phase 2)

| Component | Target | Current Status |
|-----------|--------|--------|
| API Response Time | <100ms | ✅ Verified |
| Fraud Assessment | <200ms | ✅ Verified |
| Payout Calculation | <50ms | ✅ Verified |
| DCI Poll Interval | 5 min | ✅ Implemented |
| Daily Settlement | 11:55 PM | ✅ Implemented |
| WhatsApp Latency | <2s response | ✅ Verified |

---

## 🚨 Troubleshooting

### Backend won't start
```
Error: ModuleNotFoundError: No module named 'supabase'
→ Run: pip install -r requirements.txt

Error: SUPABASE_URL not set
→ Copy .env.example to .env and fill in credentials
```

### Frontend can't reach backend
```
Error: 404 on /api/health
→ Check VITE_BACKEND_PROXY_TARGET in frontend/.env
→ Ensure backend is running on http://localhost:8000
```

### WhatsApp messages not sending
```
Error: Twilio error
→ Verify TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env
→ Check Twilio console for sandbox configuration
```

---

## 📞 Support

- **API Docs**: http://localhost:8000/docs (Swagger)
- **Architecture**: See README.md section "AI/ML Integration"
- **Deployment**: See docs/DEPLOYMENT.md
- **Contact**: [Your contact info]

---

## 🎯 What's Next (P3)

- [ ] Frontend component testing (Jest + React Testing Library)
- [ ] Load testing (1000+ concurrent claims)
- [ ] Live production monitoring (Sentry + DataDog)
- [ ] Mobile app (React Native)
- [ ] Multilingual customer support (chat)
