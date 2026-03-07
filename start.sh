#!/bin/bash
# Start both backend and frontend for Friday

ROOT="$(cd "$(dirname "$0")" && pwd)"

# Start backend in background
cd "$ROOT/backend" && source venv/bin/activate && python app/main.py &
BACKEND_PID=$!

# Start frontend in foreground
cd "$ROOT/frontend" && pnpm run dev

# When frontend exits, also kill backend
kill $BACKEND_PID 2>/dev/null
