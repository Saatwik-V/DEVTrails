#!/bin/bash

# 🛡️ GigKavach COMPLETE SUITE — AWS Server Edition
# ──────────────────────────────────────────────
# Handles: Dashboard (3000), Engine (8000), Bot (3001)

echo "🚀 Starting the GigKavach Triple-Suite..."

# Kill any old processes first
echo "🧹 Cleaning up old sessions..."
pkill -f uvicorn > /dev/null 2>&1
pkill -f vite > /dev/null 2>&1
pkill -f bot.js > /dev/null 2>&1

# 1. Start Backend in the background
echo "🐍 Starting Backend Engine (Port 8000)..."
cd backend
source venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
echo "✅ Backend Engine is active (Logs in backend/backend.log)"
cd ..

# 2. Start Frontend in the background
echo "🎨 Starting Frontend Dashboard (Port 3000)..."
cd frontend
nohup npm run dev -- --host 0.0.0.0 --port 3000 > frontend.log 2>&1 &
echo "✅ Frontend Dashboard is active (Logs in frontend/frontend.log)"
cd ..

# 3. Start WhatsApp Bot in the FOREGROUND (to show QR code)
echo "--------------------------------------------------"
echo "📱 Starting WhatsApp Bot (Port 3001)..."
echo "🤳 PLEASE WAIT FOR THE QR CODE AND SCAN IT IMMEDIATELY"
echo "--------------------------------------------------"

cd whatsapp-bot
# Clear the Mac-specific path and let Linux find Chrome automatically
export PUPPETEER_EXECUTABLE_PATH=""
node bot.js
