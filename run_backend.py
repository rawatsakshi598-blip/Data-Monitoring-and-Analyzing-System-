#!/usr/bin/env python3
"""Persistent backend runner."""
import os, sys
os.chdir('/home/z/my-project/mini-services/backend')
sys.path.insert(0, '/home/z/my-project/mini-services/backend')
import uvicorn
from index import app
uvicorn.run(app, host='0.0.0.0', port=3001, log_level='info')
