#!/bin/bash
cd /home/z/my-project/mini-services/backend
while true; do
    python3 -m uvicorn index:app --host 0.0.0.0 --port 3001 --log-level info
    echo "Backend crashed, restarting in 3s..." >&2
    sleep 3
done
