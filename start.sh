#!/bin/bash
# Start backend
cd /home/z/my-project/mini-services/backend
python3 -m uvicorn index:app --host 0.0.0.0 --port 3001 --log-level info &
BACKEND_PID=$!

# Start frontend  
cd /home/z/my-project
npx next dev -p 3000 &
FRONTEND_PID=$!

# Wait for either to die
wait
