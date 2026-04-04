# 🛡️ GigKavach: Zero-Touch Parametric Income Protection

---

## 📋 Table of Contents
1. [🧠 Project Overview](#-1-project-title--description)
2. [🛠 Tech Stack](#-2-tech-stack)
3. [🌐 Live Demo](#-3-live-demo-render--vercel)
4. [🎥 Demo Video](#-4-demo-video)
5. [📸 Screenshots](#-5-screenshots)
6. [🧩 Local Setup (FAILSAFE)](#-6-local-setup-failsafe)
7. [🧪 API Endpoints](#-7-api-endpoints)
8. [🧱 Project Structure](#-8-project-structure)
9. [✨ Key Features](#-9-key-features)
10. [⚠️ Troubleshooting](#-10-troubleshooting)
11. [👥 Team Details](#-11-team-details)
12. [☁️ Deployment Details](#-bonus-deployment-section)

---

## 🧠 1. Project Title + Description

# 🚀 GigKavach

**GigKavach** is an AI-powered parametric income protection platform designed for India's 10M+ gig workers (Zomato/Swiggy partners).

- **The Problem**: External disruptions (heavy rain, heatwaves, traffic gridlocks) can wipe out 20-30% of a worker's monthly income. Traditional insurance is too slow and complex.
- **The Solution**: We automatically detect disruption events using a real-time **Disruption Composite Index (DCI)**. 
- **The Magic**: If the DCI crosses a threshold, payouts are calculated via **XGBoost ML** and sent to the worker's UPI by midnight — **zero claims required.**

---

## 🛠 2. Tech Stack

**Frontend:**
- React 19 (Vite), TypeScript, Tailwind CSS
- Leaflet.js (Maps), Recharts (Charts), React Router
- Axios, Supabase JS

**Backend (Python):**
- FastAPI, Uvicorn, Pydantic, APScheduler
- PostgreSQL (psycopg2), Redis (caching)

**AI/ML:**
- XGBoost, Scikit-learn (Isolation Forest), HuggingFace Transformers, NumPy & Pandas

**External Integrations:**
- Twilio (WhatsApp), Razorpay (UPI), Tomorrow.io (Weather), AQICN (Air Quality)
- Supabase (Database), BeautifulSoup4 & FeedParser (RSS)

**DevOps:**
- Docker, Vercel (Frontend), Render (Backend), PostgreSQL (Supabase), GitHub

---

## 🌐 3. Live Demo

## 🌐 Live Demo

- **Frontend**: [https://gigkavach-delta.vercel.app](https://gigkavach-delta.vercel.app)
- **Backend API Docs**: [https://devtrails-backend-dnlr.onrender.com/docs](https://devtrails-backend-dnlr.onrender.com/docs)

⚠️ *Note: Backend is on Render Free Tier and may take 30-50 seconds to "wake up" on the first request.*

---
## 🎥 4. Demo Video

## 🎥 Demo Video

[Click here to watch the full walkthrough](https://drive.google.com/file/d/14i5vJTVcu6uJG37t0oL7duJEv63TAdXr/view?usp=sharing)

---

## 📸 5. Screenshots

## 📸 Screenshots

### 📊 Admin Dashboard
![Dashboard](./screenshots/dashboard.png)

### 🗺️ Live Disruption Heatmap
![Heatmap](./screenshots/heatmap.png)

### 📱 WhatsApp Interface (Onboarding)
![WhatsApp](./screenshots/whatsapp.png)

---

# 🧩 6. Local Setup (DETAILED GUIDE)

This guide works for **Windows, Mac, and Linux**. You'll have GigKavach running in 15 minutes.

---

## ✅ Prerequisites Check

Before starting, verify you have these installed:

### 1️⃣ Python 3.9 or Higher
```bash
python --version
```
- **Don't have it?** Download from [python.org](https://www.python.org/downloads/)
- **Windows**: Download installer, check ☑️ "Add Python to PATH"
- **Mac**: `brew install python3`
- **Linux**: `sudo apt-get install python3 python3-pip`

### 2️⃣ Node.js v18+ (includes npm)
```bash
node --version
npm --version
```
- **Don't have it?** Download from [nodejs.org](https://nodejs.org/) (LTS recommended)
- After install, restart your terminal

### 3️⃣ Git
```bash
git --version
```
- **Don't have it?** Download from [git-scm.com](https://git-scm.com/)

---

## 🚀 Step 1: Clone Repository

```bash
git clone https://github.com/VG2476/DEVTrails.git
cd DEVTrails
```

You should now see folders: `backend/`, `frontend/`, `data/`, `reports/`, etc.

---

## 🐍 Step 2: Backend Setup (Python/FastAPI)

**Terminal 1 - Keep this open the whole time**

```bash
cd backend

# Create isolated Python environment
python -m venv venv
```

**Activate the environment:**

**Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
venv\Scripts\activate.bat
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

✅ You should see `(venv)` at the start of your terminal line.

---

**Install dependencies:**
```bash
pip install -r requirements.txt
```

This installs FastAPI, XGBoost, ML models, Twilio, Razorpay, etc. Takes ~3 minutes.

---

**Create `.env` file:**

In the `backend/` folder, create a new file called `.env` and add:

```
SUPABASE_URL=https://mock-db.supabase.co
SUPABASE_ANON_KEY=mock-key-for-demo
ENVIRONMENT=development
```

(No quotes needed)

---

**Run the backend:**
```bash
uvicorn main:app --reload --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

✅ **Backend is running!**
- Main app: [http://localhost:8000](http://localhost:8000)
- API docs: [http://localhost:8000/docs](http://localhost:8000/docs) (interactive Swagger UI)

**⚠️ Keep this terminal open!**

---

## ⚛️ Step 3: Frontend Setup (React)

**Terminal 2 - Open a NEW terminal, keep Terminal 1 running**

```bash
cd DEVTrails/frontend
```

**Install dependencies:**
```bash
npm install
```

Takes ~2 minutes. You'll see lots of packages being installed.

---

**Build the production files:**
```bash
npm run build
```

Expected output:
```
✓ built in 2.65s
dist/index.html                  0.63 kB
dist/assets/index-XXX.css       76.66 kB
dist/assets/index-YYY.js     1,008.67 kB
```

---

**Start the frontend:**
```bash
npx serve -s dist -l tcp://0.0.0.0:3000
```

Expected output:
```
   Accepting connections at http://localhost:3000
```

✅ **Frontend is running!**
- App: [http://localhost:3000](http://localhost:3000)

---

## ⚡ 6.1 THE "HERO" STARTUP (Recommended for Demo)
If you want to launch everything (Backend, Frontend, and WhatsApp Bot) with a single command on your server:

```bash
chmod +x startup_suite.sh
./startup_suite.sh
```
*This backgrounds the engines and presents the WhatsApp QR code directly in your terminal.* 🤳✨

---

## 📝 6.2 LOGGING & OBSERVABILITY
GigKavach uses a granular logging system to ensure every disruption is traceable.

### 🔍 Real-Time Monitoring:
- **Backend Logs**: `tail -f backend/backend.log` 🐍
  - Monitor `gigkavach.dci_poller` for every 300s data refresh.
  - Watch `gigkavach.payouts` for SLA Breach triggers.
- **Frontend Logs**: `tail -f frontend/frontend.log` 🎨
- **Health Check**: Access `http://13.51.165.52:8000/api/v1/health/` 🔌
  - Returns: `{"status": "healthy", "engine": "active"}`

---

## 🏗️ 6.3 THE DCI 5-LAYER REDUNDANCY
The **Disruption Composite Index (DCI)** is built for zero-downtime:
1. **Layer 1 (Live APIs)**: Direct Tomorrow.io & WAQI polling.
2. **Layer 2 (Backup Mocks)**: Automatic fallback if primary APIs rate-limit.
3. **Layer 3 (Social Intelligence)**: NLP extraction from RSS & NDMA feeds.
4. **Layer 4 (Platform Density)**: Real-time driver congestion data.
5. **Layer 5 (Redis Cache)**: Last-known-good state for offline resilience.

---

## ✔️ Step 4: Verify Everything Works

1. Open browser → [http://localhost:3000](http://localhost:3000)
2. You should see the GigKavach dashboard
3. Check bottom-right corner for **Judge Console** button
4. Click it to test disruptions

If you see errors, check Troubleshooting below.

---

## 🎮 Step 5: Test with Judge Console

1. Click **"Judge Console"** (bottom-right of page)
2. Simulate disruptions:
   - Adjust DCI slider
   - Choose disruption type (Rain, Heat, etc.)
   - Click "Trigger Disruption"
3. Watch the heatmap update
4. Trigger a test payout

---

## ❌ Troubleshooting

| Error | Fix |
|-------|-----|
| **Port 8000 in use** | `uvicorn main:app --reload --port 8001` then rebuild frontend |
| **`venv` not recognized (Windows)** | Use full path: `.\venv\Scripts\Activate.ps1` or try `py -m venv venv` |
| **`ModuleNotFoundError`** | Activate venv + `pip install -r requirements.txt` again |
| **Frontend shows "Cannot GET /"** | Run `npm run build` again in frontend folder |
| **"npm not found"** | Install Node.js from [nodejs.org](https://nodejs.org), restart terminal |
| **Backend "Internal Server Error"** | Check `.env` file has correct values, restart backend |
| **Port 3000 in use** | Kill the process or use `npx serve -s dist -l tcp://0.0.0.0:3001` |

---

## 💡 Tips

- **Keep both terminals open** - Backend and Frontend must run simultaneously
- **If you restart**, activate venv again before running backend
- **API Documentation** available at [http://localhost:8000/docs](http://localhost:8000/docs) - try endpoints there
- **Changes to backend code?** Uvicorn auto-reloads (wait 2 seconds)
- **Changes to frontend code?** Rebuild with `npm run build`

---

## 🧪 7. API Endpoints

## 🧪 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health/` | Liveness health check (System Pulse) |
| `POST` | `/api/v1/workers/register` | WhatsApp Onboarding endpoint |
| `GET` | `/api/v1/dci/{pincode}` | Get real-time Disruption Index |
| `POST` | `/api/v1/payouts/calculate` | XGBoost Payout & Adaptive Multiplier |
| `POST` | `/api/v1/fraud/check` | ML-based Fraud (XGBoost v3) |
| `POST` | `/api/v1/demo/trigger` | Trigger manual demo disruption (Judge Mode) |

---

## 🧱 8. Project Structure

## 🧱 Project Structure

```bash
DEVTrails/
├── backend/
│   ├── api/             # FastAPI routers (DCI, Workers, Payouts, Fraud, WhatsApp)
│   ├── services/        # Business logic (DCI engine, eligibility, baseline calc)
│   ├── ml/              # ML models (XGBoost, fraud detector, NLP classifier)
│   ├── cron/            # APScheduler jobs (DCI polling, settlement cron)
│   ├── database/        # Database schema & seed scripts
│   ├── config/          # Configuration settings
│   ├── lib/             # Internal utilities
│   ├── models/          # Trained ML model files (XGBoost, Isolation Forest)
│   ├── utils/           # Helper functions
│   ├── tests/           # Unit tests
│   ├── main.py          # FastAPI entry point
│   ├── requirements.txt  # Python dependencies
│   └── .env             # Environment variables
├── frontend/
│   ├── src/
│   │   ├── components/  # React components (DCI Charts, Heatmap, Cards)
│   │   ├── pages/       # Pages (Dashboard, Heatmap, Fraud Monitor)
│   │   ├── services/    # API client (Axios calls to backend)
│   │   ├── api/         # API endpoints folder
│   │   ├── context/     # React Context for state management
│   │   ├── hooks/       # Custom React hooks
│   │   ├── assets/      # Images, icons
│   │   ├── styles/      # CSS/Tailwind styles
│   │   ├── utils/       # Frontend utilities
│   │   └── main.jsx     # React entry point
│   ├── public/          # Static assets
│   ├── dist/            # Production build (after npm run build)
│   ├── package.json     # Node dependencies
│   ├── vite.config.ts   # Vite configuration
│   └── tsconfig.json    # TypeScript config
├── data/                # Training & demo datasets
├── models/              # Trained model artifacts
├── reports/             # Documentation & analysis reports
└── README.md            # Main documentation
```

---

## ✨ 9. Key Features

| 🎯 | Feature | What Makes It Special |
|----|---------|----------------------|
| 🚨 | **DCI - Real-Time Disruption Detection** | 5-factor scoring (Rain + AQI + Heat + Social + Platform) updated every 5 mins at pincode-level precision—not city-level |
| ⚡ | **Zero-Touch Automatic Payouts** | Disruption detected → eligibility check → payout calculated & settled at 11:55 PM daily. No claim form needed. |
| 💰 | **Smart Earnings Baseline** | 4-week rolling median per day-of-week, filtered for disruptions & festivals—ensures fair payouts for all workers |
| 📊 | **XGBoost Adaptive Multiplier** | AI predicts 1.0x-5.0x payout scaling based on 30+ features (location, shift, disruption type, zone density, etc.) |
| 🧠 | **3-Tier Fraud Detection** | Rule-based blockers (device farming, rapid re-claim) + Isolation Forest + XGBoost v3 with 31 engineered features |
| 🌐 | **NLP Social Disruption Detection** | AI-powered RSS feed analysis detects Bandh/Strikes/NDMA alerts + auto-extracts location via HuggingFace NLP |
| 📱 | **WhatsApp-Native Onboarding** | 7-step zero-app-install journey in WhatsApp (Twilio), 5-language support (EN/HI/KN/TA/TE) |
| 🗺️ | **Live Interactive Heatmap Dashboard** | Real-time Leaflet map showing zone-level disruptions, DCI composition, worker counts & eligibility status |
| 🌍 | **Multilingual Alerts & UI** | Full 5-language support (EN, Hindi, Kannada, Tamil, Telugu) for app UI + WhatsApp notifications |
| 🎮 | **Judge Console - Live Demo Mode** | Embedded testing panel on dashboard—simulate disruptions, trigger payouts in seconds, see DCI updates live |

---

## ⚠️ 10. Troubleshooting

## ⚠️ Troubleshooting

### Port 8000 already in use
Kill the process or run backend on a different port:
```bash
uvicorn main:app --reload --port 8001
```

### ModuleNotFoundError
Ensure you have activated the virtual environment and run:
```bash
pip install -r requirements.txt
```

### Backend "Internal Server Error"
Check your `.env` file. Ensure `SUPABASE_URL` and `SUPABASE_ANON_KEY` are valid. If you don't have them, the system will use mock data where possible but backend calls might fail.

---

## 👥 11. Team Details

## 👥 Team Quadcore

- **Varshit**: WhatsApp & API Integration Lead
- **Vijeth**: Frontend & Dashboard Design
- **V Saatwik**: ML Models & Fraud Detection Lead
- **Sumukh Shandilya**:Backend & DCI Engine Architect 

---

## ☁️ BONUS: Deployment Section

## ☁️ Deployment

- **Frontend**: Hosted on **Vercel** with auto-deployment.
- **Backend**: Hosted on **Render** (Dockerized).
- **Database**: **Supabase** (PostgreSQL) with Row-Level Security enabled.

To deploy the backend to Render:
1. Connect your GitHub repo.
2. Choose "Web Service".
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add all `.env` variables to the Environment section.

---

## ⚡ Quick Start (1 Minute Setup)

```bash
git clone https://github.com/VG2476/DEVTrails.git
# Start Backend
cd backend && pip install -r requirements.txt && uvicorn main:app --reload
# Start Frontend (New Terminal)
cd frontend && npm install && npm run dev
```

Done.
