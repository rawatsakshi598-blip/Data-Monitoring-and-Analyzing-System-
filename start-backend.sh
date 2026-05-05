#!/bin/bash
cd /home/z/my-project/mini-services/backend
source venv/bin/activate
exec python3 -c "
import uvicorn
from index import app
uvicorn.run(app, host='0.0.0.0', port=3001, log_level='info')
"
