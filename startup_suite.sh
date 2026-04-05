#!/bin/bash

# GigKavach Multi-Service Startup
# Supports both localhost and server IP (13.51.165.52) deployments
# Works with tmux on server
# Usage: ./startup_suite.sh [server|local]
# Default: server (so it can run directly on EC2 without extra flags)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track PIDs for cleanup
BACKEND_PID=""
FRONTEND_PID=""
BOT_PID=""
PROJECT_ROOT=""

# Cleanup function - runs on Ctrl+C or script exit
cleanup() {
  echo -e "\n${YELLOW}Shutting down all services...${NC}"
  [ -n "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null || true
  wait 2>/dev/null || true
  echo -e "${GREEN}✅ All services stopped${NC}"
  exit 0
}

# Set trap to call cleanup on Ctrl+C and normal exit
trap cleanup SIGINT SIGTERM

set -e  # Exit on any error during setup

# Determine deployment mode
# Default to server mode for direct EC2 usage.
MODE="${1:-server}"

if [[ "$MODE" != "local" && "$MODE" != "server" ]]; then
  echo "Usage: ./startup_suite.sh [server|local]"
  echo "  server - Run on http://13.51.165.52 (production, default)"
  echo "  local  - Run on http://localhost (development)"
  exit 1
fi

if [[ "$MODE" == "local" ]]; then
  API_HOST="localhost"
  API_URL="http://localhost:8000"
  BOT_URL="http://localhost:3001"
  FRONTEND_URL="http://localhost:3000"
else
  API_HOST="13.51.165.52"
  API_URL="http://13.51.165.52:8000"
  BOT_URL="http://13.51.165.52:3001"
  FRONTEND_URL="http://13.51.165.52:3000"
fi

# Install Chromium runtime dependencies on Ubuntu when running on server.
# Skip silently if sudo without prompt is unavailable.
if [[ "$MODE" == "server" ]] && command -v apt-get >/dev/null 2>&1; then
  if sudo -n true 2>/dev/null; then
    echo -e "${YELLOW}🔧 Ensuring Chrome runtime libraries are present...${NC}"
    sudo apt-get update -y >/dev/null 2>&1 || true
    sudo apt-get install -y \
      ca-certificates fonts-liberation libasound2t64 libatk-bridge2.0-0 \
      libatk1.0-0 libc6 libcairo2 libcups2t64 libdbus-1-3 libexpat1 \
      libfontconfig1 libgbm1 libgcc-s1 libglib2.0-0 libgtk-3-0t64 libnspr4 \
      libnss3 libpango-1.0-0 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 \
      libxdamage1 libxext6 libxfixes3 libxkbcommon0 libxrandr2 xdg-utils \
      >/dev/null 2>&1 || true
  else
    echo -e "${YELLOW}⚠️ Skipping apt package install (sudo -n not available).${NC}"
  fi
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🚀 Starting GigKavach Services ($MODE mode)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}📍 API:${NC}      $API_URL"
echo -e "${BLUE}📍 Bot:${NC}      $BOT_URL"
echo -e "${BLUE}📍 Frontend:${NC} $FRONTEND_URL"
echo ""

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Use a project-local temp dir in case /tmp is unavailable or full on small EC2 hosts.
TMP_WORKDIR="$PROJECT_ROOT/.tmp"
mkdir -p "$TMP_WORKDIR"
export TMPDIR="$TMP_WORKDIR"
export TEMP="$TMP_WORKDIR"
export TMP="$TMP_WORKDIR"

# Kill old processes if they exist
echo -e "${YELLOW}🧹 Cleaning up old processes...${NC}"
pkill -9 -f "uvicorn main:app" > /dev/null 2>&1 || true
pkill -9 -f "vite" > /dev/null 2>&1 || true
pkill -9 -f "node bot.js" > /dev/null 2>&1 || true
pkill -9 -f "node.*bot" > /dev/null 2>&1 || true
sleep 3

# Free up ports if still in use
for port in 8000 3000 3001; do
  lsof -i :$port -t | xargs -r kill -9 2>/dev/null || true
done
sleep 2

# Kill any lingering Chrome/browser processes
pkill -9 -f "Chrome" > /dev/null 2>&1 || true
pkill -9 -f "Chromium" > /dev/null 2>&1 || true

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/backend/logs"

# Update frontend .env
cat > "$PROJECT_ROOT/frontend/.env" << 'EOF'
VITE_SUPABASE_URL=https://rwzjpuxyaxjymhjkpxrm.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ3empwdXh5YXhqeW1oamtweHJtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQyNjU2MzEsImV4cCI6MjA4OTg0MTYzMX0.t51gBkCcxvFG47PRGoBd4rOp1swaTxFCbZLNl_qeAr4
EOF

cat >> "$PROJECT_ROOT/frontend/.env" << EOF
VITE_API_URL=$API_URL
VITE_API_BASE_URL=$API_URL
VITE_BACKEND_PROXY_TARGET=$API_URL
VITE_WS_BASE_URL=ws://$API_HOST:8000
VITE_ENABLE_MOCK_DATA=false
VITE_DEBUG_MODE=false
EOF

# Update backend .env
cat > "$PROJECT_ROOT/backend/.env" << 'EOF'
APP_ENV=development
APP_SECRET_KEY=your-secret-key-here
FRONTEND_LOCAL_URL=http://localhost:3000
FRONTEND_SERVER_URL=http://13.51.165.52:3000
FRONTEND_URL=http://13.51.165.52:3000
FRONTEND_PRODUCTION_URL=https://gigkavach-delta.vercel.app
SUPABASE_URL=https://rwzjpuxyaxjymhjkpxrm.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ3empwdXh5YXhqeW1oamtweHJtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQyNjU2MzEsImV4cCI6MjA4OTg0MTYzMX0.t51gBkCcxvFG47PRGoBd4rOp1swaTxFCbZLNl_qeAr4
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ3empwdXh5YXhqeW1oamtweHJtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NDI2NTYzMSwiZXhwIjoyMDg5ODQxNjMxfQ.eoo61p_aP4VH0wRixdGrki_6LZjJw2WBVYXLydgqFxQ
REDIS_URL=redis://localhost:6379/0
TOMORROW_IO_API_KEY=MD36I2GcYp3gBoUlnKvdQeHkBJQvTF19
OPENAQ_API_KEY=885d52c7b9d35c87345de923622c6481fb5be3ec1b2a57952956cd5c386c2f0b
AQICN_API_TOKEN=ca8e43f08a82415e64b9d84111785b2bf7e8db70
DCI_POLL_INTERVAL_SECONDS=300
DCI_TRIGGER_THRESHOLD=65
DCI_CATASTROPHIC_THRESHOLD=85
DCI_CACHE_TTL_SECONDS=1800
FRAUD_SOFT_FLAG_SIGNALS=3
FRAUD_HARD_BLOCK_SIGNALS=5
FRAUD_CONTAMINATION_RATE=0.05
COVERAGE_DELAY_HOURS=24
MAX_UPI_RETRY_ATTEMPTS=3
UPI_RETRY_INTERVAL_MINUTES=40
ESCROW_WINDOW_HOURS=48
SHIELD_BASIC_PREMIUM=69
SHIELD_PLUS_PREMIUM=89
SHIELD_PRO_PREMIUM=99
SHIELD_BASIC_COVERAGE_PCT=0.40
SHIELD_PLUS_COVERAGE_PCT=0.50
SHIELD_PRO_COVERAGE_PCT=0.70
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
MAPPLS_API_KEY=your-mappls-key-here
WHATSAPP_PHONE_NUMBER=8792525542
EOF

# Update whatsapp-bot .env
cat > "$PROJECT_ROOT/whatsapp-bot/.env" << EOF
BACKEND_URL=$API_URL
BOT_PORT=3001
DEBUG=false
LOG_LEVEL=info
SESSION_DIR=./sessions
WHATSAPP_PHONE_NUMBER=8792525542
EOF

echo -e "${GREEN}✅ Environment files configured for $MODE mode${NC}"
echo ""

# ══════════════════════════════════════════════════════════════════════════════
# START BACKEND
# ══════════════════════════════════════════════════════════════════════════════
echo -e "${YELLOW}🐍 Starting Backend (port 8000)...${NC}"
cd "$PROJECT_ROOT/backend"

# Ensure venv exists
if [ ! -d ".venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv .venv
fi

# Install/upgrade dependencies only when needed.
if [ ! -f ".venv/.deps_installed" ] || [ requirements.txt -nt ".venv/.deps_installed" ]; then
  .venv/bin/pip install -q --no-cache-dir -r requirements.txt
  touch .venv/.deps_installed
else
  echo "Backend dependencies up-to-date. Skipping pip install."
fi

# Start backend using absolute path (bypasses venv activation issues)
nohup .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload > backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 4

# Verify backend started
if ps -p $BACKEND_PID > /dev/null 2>&1; then
  echo -e "${GREEN}✅ Backend started (PID: $BACKEND_PID)${NC}"
else
  echo -e "${RED}❌ Backend failed to start${NC}"
  echo -e "${RED}Error log:${NC}"
  tail -30 backend.log
  cd "$PROJECT_ROOT"
  exit 1
fi
cd "$PROJECT_ROOT"

# ══════════════════════════════════════════════════════════════════════════════
# START FRONTEND
# ══════════════════════════════════════════════════════════════════════════════
echo -e "${YELLOW}🎨 Starting Frontend (port 3000)...${NC}"
cd "$PROJECT_ROOT/frontend"

# Ensure dependencies are installed
if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies (with Linux native bindings)..."
  npm install --legacy-peer-deps --include=optional --no-audit --no-fund || {
    echo -e "${RED}❌ npm install failed${NC}"
    cd "$PROJECT_ROOT"
    exit 1
  }
fi

# Prefer RAM-backed cache for Puppeteer on tiny EC2 disks.
if [ -d "/dev/shm" ] && [ -w "/dev/shm" ]; then
  export PUPPETEER_CACHE_DIR="/dev/shm/puppeteer-cache"
else
  export PUPPETEER_CACHE_DIR="$PROJECT_ROOT/.puppeteer-cache"
fi
mkdir -p "$PUPPETEER_CACHE_DIR"
echo "Using Puppeteer cache: $PUPPETEER_CACHE_DIR"

# Repair legacy/broken installs where optional native binding was skipped.
if [ ! -d "node_modules/@rolldown/binding-linux-x64-gnu" ] && [ ! -d "node_modules/@rolldown/binding-linux-x64-musl" ]; then
  echo "Repairing frontend dependencies (missing rolldown native binding)..."
  rm -rf node_modules
  npm install --legacy-peer-deps --include=optional --no-audit --no-fund || {
    echo -e "${RED}❌ frontend dependency repair failed${NC}"
    cd "$PROJECT_ROOT"
    exit 1
  }
fi

nohup npm run dev -- --host 0.0.0.0 --port 3000 > frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to start
echo "Waiting for frontend to start..."
sleep 4

# Verify frontend started
if ps -p $FRONTEND_PID > /dev/null 2>&1; then
  echo -e "${GREEN}✅ Frontend started (PID: $FRONTEND_PID)${NC}"
else
  echo -e "${RED}❌ Frontend failed to start${NC}"
  echo -e "${RED}Error log:${NC}"
  tail -30 frontend.log
  cd "$PROJECT_ROOT"
  exit 1
fi
cd "$PROJECT_ROOT"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 Backend and Frontend started successfully!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Service URLs:${NC}"
echo -e "  Frontend:  ${BLUE}$FRONTEND_URL${NC}"
echo -e "  Backend:   ${BLUE}$API_URL/docs${NC}"
echo ""
echo -e "${YELLOW}Background Logs:${NC}"
echo -e "  Backend:   ${BLUE}$PROJECT_ROOT/backend/backend.log${NC}"
echo -e "  Frontend:  ${BLUE}$PROJECT_ROOT/frontend/frontend.log${NC}"
echo ""
echo -e "${YELLOW}Running processes:${NC}"
echo -e "  Backend:   ${BLUE}PID $BACKEND_PID${NC}"
echo -e "  Frontend:  ${BLUE}PID $FRONTEND_PID${NC}"
echo ""
echo -e "${GREEN}✅ Backend and Frontend are running in detached mode${NC}"
echo -e "${YELLOW}Stop all:${NC} pkill -f 'uvicorn main:app'; pkill -f 'vite'"
