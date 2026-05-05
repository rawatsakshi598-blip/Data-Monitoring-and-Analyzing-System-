#!/bin/bash
cd /home/z/my-project/mini-services/backend
exec python3 -m uvicorn index:app --host 0.0.0.0 --port 3001 --log-level info
