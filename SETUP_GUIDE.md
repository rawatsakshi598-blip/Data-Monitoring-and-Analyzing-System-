# DataGuard — Complete Setup Guide

> **Last Updated:** May 2026
> **Architecture:** Next.js 16 Frontend (Port 3000) + Python FastAPI Backend (Port 3001) + SQLite
> **Important:** This project does NOT use Prisma. All database operations go through the Python FastAPI backend.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Quick Start (5 Minutes)](#3-quick-start-5-minutes)
4. [Detailed Installation](#4-detailed-installation)
   - 4.1 [Frontend Setup (Next.js)](#41-frontend-setup-nextjs)
   - 4.2 [Backend Setup (Python FastAPI)](#42-backend-setup-python-fastapi)
   - 4.3 [Database Setup (SQLite)](#43-database-setup-sqlite)
5. [Running the Application](#5-running-the-application)
6. [Environment Variables Reference](#6-environment-variables-reference)
7. [LLM Configuration (Optional)](#7-llm-configuration-optional)
8. [Data Ingestion Methods](#8-data-ingestion-methods)
9. [SQL Playground Setup](#9-sql-playground-setup)
10. [Production Deployment](#10-production-deployment)
11. [Troubleshooting](#11-troubleshooting)
12. [Project Structure Quick Reference](#12-project-structure-quick-reference)
13. [Common Development Tasks](#13-common-development-tasks)
14. [Migration Notes (Prisma → No Prisma)](#14-migration-notes-prisma--no-prisma)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     BROWSER (User)                              │
│                  http://localhost:3000                           │
└───────────────────────┬─────────────────────────────────────────┘
                        │ HTTP Requests
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│               NEXT.JS 16 FRONTEND (Port 3000)                   │
│                                                                  │
│   React UI (page.tsx)                                           │
│   Zustand Store (store.ts)                                      │
│   33 DQ Components (src/components/dq/)                         │
│                     │ fetch()                                    │
│   ┌─────────────────▼────────────────────────────────────────┐  │
│   │         NEXT.JS API ROUTES (55+ thin proxies)            │  │
│   │  src/app/api/*/route.ts → fetch('http://localhost:3001') │  │
│   └──────────────────┬───────────────────────────────────────┘  │
└───────────────────────┼─────────────────────────────────────────┘
                        │ HTTP Proxy (NO business logic)
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│            PYTHON FASTAPI BACKEND (Port 3001)                    │
│                                                                  │
│   index.py — 77+ endpoints, ALL business logic                  │
│   ├── checks/      — 7 quality check types                      │
│   ├── engine/      — Rule execution, quality scoring            │
│   ├── llm/         — LLM integration (4 modules)                │
│   ├── models/      — Pydantic data models                       │
│   ├── profiling/   — Data profiler                              │
│   ├── transformations/ — 10 data transformers                   │
│   ├── connectors/  — 5 data source types                        │
│   ├── statistical/ — 8 hypothesis tests                         │
│   ├── eda/         — Auto EDA                                   │
│   ├── ml_readiness/ — ML readiness scoring                      │
│   ├── copilot/     — AI copilot engine                          │
│   ├── forecasting/ — Quality trend forecasting                  │
│   ├── contracts/   — Data contract validation                   │
│   ├── scheduler/   — Job scheduling                             │
│   └── db/          — Async SQLite connection                    │
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │          SQLite Database (db/custom.db)                  │   │
│   │          ~30 tables (created by Python init_db())        │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Key Architecture Rules

1. **ALL services MUST work through the Python FastAPI backend** — NO better-sqlite3 fallbacks in Next.js API routes
2. Next.js API routes are **thin proxies only** — they forward requests to `http://localhost:3001` and return the response
3. The Python backend owns **ALL business logic** — database queries, data processing, quality checks, AI features
4. The frontend contains **ZERO business logic** — it only renders UI and calls API endpoints
5. **No Prisma** — database access is through Python's aiosqlite directly
6. **No ORM** — raw SQL queries via Python's `aiosqlite` library

---

## 2. Prerequisites

### System Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| Operating System | Linux (Ubuntu 20.04+) | Ubuntu 22.04+ / Debian 12+ |
| Python | 3.10+ | 3.12+ |
| Node.js | 18+ | 20+ |
| Bun | 1.0+ | 1.3+ |
| RAM | 4GB | 8GB |
| Disk Space | 2GB | 5GB |
| Network | Internet for dependency install | — |

### Verify Your System

```bash
# Check Python version
python3 --version    # Should be 3.10+

# Check Node.js version
node --version       # Should be v18+

# Check Bun version (optional — npm works too)
bun --version        # Should be 1.0+

# Check available memory
free -h

# Check disk space
df -h .

# Check Git
git --version
```

### Install Missing Prerequisites (Ubuntu/Debian)

```bash
# Update package manager
sudo apt update && sudo apt upgrade -y

# Install Python 3 and pip
sudo apt install -y python3 python3-pip python3-venv

# Install Node.js (via NodeSource)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install Bun (optional)
curl -fsSL https://bun.sh/install | bash
source ~/.bashrc

# Install Git
sudo apt install -y git

# Install build tools (needed for better-sqlite3 native compilation)
sudo apt install -y build-essential python3-dev
```

---

## 3. Quick Start (5 Minutes)

Get DataGuard up and running as fast as possible:

```bash
# 1. Navigate to project directory
cd /path/to/my-project

# 2. Install frontend dependencies
npm install          # or: bun install

# 3. Setup Python backend
cd mini-services/backend
python3 -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ../..

# 4. Start the Python backend (Terminal 1)
cd mini-services/backend
source venv/bin/activate
python -m uvicorn index:app --host 0.0.0.0 --port 3001 --reload

# 5. Start the Next.js frontend (Terminal 2)
npm run dev          # or: bun run dev

# 6. Open browser
# http://localhost:3000
```

> **That's it!** The Python backend automatically creates all database tables on first startup via its `init_db()` function. No manual database migration steps needed.

---

## 4. Detailed Installation

### 4.1 Frontend Setup (Next.js)

#### Install Node.js Dependencies

```bash
cd /path/to/my-project

# Using npm (recommended for compatibility)
npm install

# OR using Bun (faster)
bun install
```

#### What Gets Installed

The frontend has the following key dependencies:

| Package | Purpose |
|---|---|
| `next` 16.1.1 | React framework with SSR and API routes |
| `react` / `react-dom` 19 | UI library |
| `tailwindcss` 4 | Utility-first CSS framework |
| `recharts` | Chart components |
| `better-sqlite3` | **LEGACY** — only used by `src/lib/seed.ts` (standalone seeder), NOT by API routes |
| `xlsx` | Excel file parsing (client-side preview) |
| `papaparse` | CSV parsing (client-side preview) |
| `@radix-ui/*` | Radix UI primitives (used by shadcn/ui components) |
| `zustand` | State management |
| `framer-motion` | Animations |
| `sonner` | Toast notifications |

> **Note about better-sqlite3:** This package is still listed in `package.json` for the standalone `src/lib/seed.ts` seeder script. At runtime, ALL database access goes through the Python FastAPI backend. The `src/lib/db.ts` file that wraps better-sqlite3 is **NOT imported by any API route** — it is only used by `seed.ts`. If you encounter build issues with better-sqlite3's native module, you can safely skip it as it is not required for the application to run.

#### Frontend Configuration

The Next.js configuration is in `next.config.ts`:

```typescript
// next.config.ts
const nextConfig = {
  output: "standalone",           // For Docker/deployment
  typescript: { ignoreBuildErrors: true },
  reactStrictMode: false,
  experimental: {
    serverActions: {
      bodySizeLimit: '100mb',     // Allow large file uploads
    },
  },
}
```

No changes needed for development — this works out of the box.

### 4.2 Backend Setup (Python FastAPI)

#### Create Virtual Environment

```bash
cd /path/to/my-project/mini-services/backend

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate       # Linux/Mac
# venv\Scripts\activate        # Windows

# Upgrade pip
pip install --upgrade pip
```

#### Install Python Dependencies

```bash
pip install -r requirements.txt
```

#### What Gets Installed (`requirements.txt`)

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.115.0 | Web framework |
| `uvicorn[standard]` | 0.30.0 | ASGI server (with websocket support) |
| `aiosqlite` | 0.20.0 | Async SQLite driver |
| `pandas` | 2.2.0 | Data manipulation, quality checks, transformations |
| `numpy` | 1.26.0 | Numerical operations |
| `scipy` | 1.14.0 | Statistical tests |
| `openpyxl` | 3.1.5 | Excel file reading |
| `pydantic` | 2.9.0 | Data validation models |
| `openai` | 1.50.0 | LLM client (OpenAI-compatible APIs) |
| `networkx` | 3.3 | DAG pipeline builder, lineage graphs |
| `python-multipart` | 0.0.9 | File upload handling |

#### Verify Backend Installation

```bash
# From mini-services/backend/ with venv activated
python -c "import fastapi; print(f'FastAPI {fastapi.__version__}')"
python -c "import pandas; print(f'Pandas {pandas.__version__}')"
python -c "import aiosqlite; print(f'aiosqlite OK')"
```

If all imports succeed, the backend is ready.

### 4.3 Database Setup (SQLite)

**There is NO manual database migration step.** The Python FastAPI backend automatically creates all required tables on startup.

#### How Database Initialization Works

1. When the Python backend starts, the `init_db()` function in `index.py` runs automatically
2. It connects to `db/custom.db` (creating the file if it doesn't exist)
3. It executes `CREATE TABLE IF NOT EXISTS` for all ~30 tables
4. Tables include: `Service`, `Table_entity`, `Dataset`, `QualityRule`, `QualityCheck`, `DQTest`, `DQTestResult`, `TableProfile`, `DataLineage`, `Alert`, `Tag`, `GlossaryTerm`, `Team`, `Activity`, `QualityReport`, `Connector`, `ScheduledJob`, `Pipeline`, `PipelineRun`, `PipelineStep`, `TransformHistory`, `AutoEDAReport`, `MLReadinessScore`, `FixApproval`, `CopilotChat`, `DataContract`, `ContractValidation`, `StatisticalTest`, `ScheduledJobLog`
5. The `data/` directory is auto-created for storing uploaded DataFrames as CSV

#### ⚠️ No Prisma Migrations

This project does **NOT** use Prisma. There are no Prisma migration commands to run:

- ❌ `bun run db:push` — does NOT exist (this was from the old Prisma setup)
- ❌ `npx prisma migrate dev` — does NOT exist
- ❌ `npx prisma generate` — does NOT exist
- ✅ Database tables are created automatically by `index.py:init_db()` on backend startup

#### Legacy Schema File

There is a `db/schema.sql` file that was used in the old Node.js/better-sqlite3 architecture. This file is **NOT used** at runtime. The Python backend's inline schema in `init_db()` is the actual schema. You can safely ignore `db/schema.sql`.

#### The `src/lib/db.ts` File

The `src/lib/db.ts` file wraps better-sqlite3 and reads `db/schema.sql`. This file is **NOT imported by any API route** — it is only used by `src/lib/seed.ts` (a standalone seeder script). At runtime, all database access goes through the Python backend. Do NOT add imports of this file to any API route.

---

## 5. Running the Application

### Method 1: Two Terminal Windows (Recommended for Development)

```bash
# Terminal 1: Start Python Backend
cd /path/to/my-project/mini-services/backend
source venv/bin/activate
python -m uvicorn index:app --host 0.0.0.0 --port 3001 --reload
```

```bash
# Terminal 2: Start Next.js Frontend
cd /path/to/my-project
npm run dev          # or: bun run dev
```

Then open **http://localhost:3000** in your browser.

### Method 2: Using Start Scripts

```bash
# Start both services (from project root)
./start.sh

# Start individually
./start-backend.sh    # Python backend on port 3001
./start-frontend.sh   # Next.js on port 3000
```

### Method 3: Using start_services.sh (with PID tracking)

```bash
./start_services.sh

# This writes PID files for process management:
#   backend.pid  — Python backend PID
#   frontend.pid — Next.js frontend PID

# To stop the services later:
kill $(cat backend.pid) 2>/dev/null
kill $(cat frontend.pid) 2>/dev/null
```

### Method 4: Using Supervisord (Production-like)

```bash
# Install supervisord if not already installed
sudo apt install -y supervisor

# Start with the project's supervisord config
supervisord -c supervisord.conf

# Check status
supervisorctl status

# Stop
supervisorctl shutdown
```

> **⚠️ Note:** The `supervisord.conf` file may have stale paths referencing `/DataMonitor/`. Update the paths to match your project directory before using it.

### Verify Both Services Are Running

```bash
# Check Python backend
curl http://localhost:3001/
# Should return: {"status":"ok","llm_configured":false}

# Check Next.js frontend
curl http://localhost:3000/api
# Should return: same as above (proxied through)

# Check both ports are listening
ss -tlnp | grep -E '3000|3001'
```

### Startup Order

1. **Python backend first** (port 3001) — it needs to be running for the frontend API routes to proxy correctly
2. **Next.js frontend second** (port 3000) — it will show "Backend unavailable" errors if the Python backend is down

If you see **"Backend unavailable — please ensure the Python backend is running on port 3001"** in the UI, it means the Python backend is not running or has crashed.

---

## 6. Environment Variables Reference

### Frontend (.env in project root)

```bash
# .env — DataGuard Frontend Configuration

# Database URL (used by src/lib/db.ts for the standalone seeder only)
DATABASE_URL="file:./db/custom.db"

# Application
NEXT_PUBLIC_APP_NAME="DataGuard"
PORT=3000

# Optional: Authentication
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="your-secret-key-here"
```

### Backend (.env in `mini-services/backend/`)

Create this file in the `mini-services/backend/` directory:

```bash
# .env — DataGuard Python Backend Configuration

# Database path (relative to backend directory)
# Default: ../../db/custom.db
DB_PATH=../../db/custom.db

# LLM Configuration — Primary Provider
LLM_API_KEY=                        # Your OpenAI-compatible API key
LLM_BASE_URL=https://api.groq.com/openai/v1  # OpenAI-compatible endpoint
LLM_MODEL=gpt-4o-mini               # Model to use

# LLM Fallback Providers (up to 5 — tried if primary fails or is rate-limited)
LLM_FALLBACK_1_API_KEY=
LLM_FALLBACK_1_BASE_URL=
LLM_FALLBACK_1_MODEL=
LLM_FALLBACK_2_API_KEY=
LLM_FALLBACK_2_BASE_URL=
LLM_FALLBACK_2_MODEL=
# ... up to LLM_FALLBACK_5_*

# Upload limits
MAX_FILE_SIZE=104857600    # 100MB in bytes
MAX_COLUMNS=1000           # Maximum columns per table
MAX_ROWS=10000000          # Maximum rows per table (10M)

# Server
SERVER_PORT=3001

# Chunked upload directory
CHUNKS_DIR=/tmp/dataguard_chunks
```

### Environment Variable Priority

| Variable | Where | Required | Default |
|---|---|---|---|
| `DB_PATH` | Backend .env | No | `../../db/custom.db` |
| `LLM_API_KEY` | Backend .env | No | Empty (AI features degraded) |
| `LLM_BASE_URL` | Backend .env | No | `https://api.groq.com/openai/v1` |
| `LLM_MODEL` | Backend .env | No | `gpt-4o-mini` |
| `DATABASE_URL` | Frontend .env | No | `file:./db/custom.db` |
| `SERVER_PORT` | Backend .env | No | `3001` |

---

## 7. LLM Configuration (Optional)

DataGuard uses LLM integration for several AI-powered features. **These features work without an API key** (they fall back to heuristic/template-based generation), but they produce much better results with a configured LLM.

### AI Features That Use LLM

| Feature | Endpoint | What It Does | Fallback Without LLM |
|---|---|---|---|
| NL Rule Generation | `POST /api/nl-rule` | Generate quality rules from natural language | Keyword-based matching |
| AI Rule Generation | `POST /api/ai/generate-rule` | AI-powered rule suggestions | Keyword-based matching |
| Fix Suggestions | `POST /api/ai/generate-fix` | Generate fix code for quality issues | Template-based fixes |
| Quality Reports | `POST /api/ai/generate-report` | Generate quality analysis reports | Template-based reports |
| Copilot Chat | `POST /api/copilot/chat` | AI data preparation assistant | Heuristic chat responses |
| Copilot Suggestions | `GET /api/copilot/suggestions/{tableId}` | Suggest data preparation steps | Rule-based suggestions |

### Configure LLM

1. Create/edit `mini-services/backend/.env`
2. Add your API key and endpoint. Use the **fallback provider** format for additional providers:

```bash
# .env — mini-services/backend/.env

# ── Primary Provider (ONE only) ──
LLM_API_KEY=gsk_your-groq-key
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.3-70b-versatile

# ── Fallback Provider 1 (tried if primary fails/rate-limits) ──
LLM_FALLBACK_1_API_KEY=nvapi_your-nvidia-key
LLM_FALLBACK_1_BASE_URL=https://integrate.api.nvidia.com/v1
LLM_FALLBACK_1_MODEL=minimaxai/minimax-m2.7

# ── Fallback Provider 2 ──
LLM_FALLBACK_2_API_KEY=sk-or_your-openrouter-key
LLM_FALLBACK_2_BASE_URL=https://openrouter.ai/api/v1
LLM_FALLBACK_2_MODEL=z-ai/glm-4.5-air:free

# ── Up to 5 fallbacks: LLM_FALLBACK_3_*, LLM_FALLBACK_4_*, LLM_FALLBACK_5_* ──
```

> **⚠️ CRITICAL FORMAT RULES:**
> - Only ONE primary provider — use `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`
> - Additional providers MUST use `LLM_FALLBACK_1_*`, `LLM_FALLBACK_2_*` format (NOT duplicate `LLM_API_KEY`)
> - The `BASE_URL` should NOT include `/chat/completions` — the LLM client appends it automatically
> - The `.env` parser uses `os.environ.setdefault()`, so duplicate keys silently keep the first value

3. Restart the Python backend
4. Verify: `curl http://localhost:3001/api/llm-status` should return `{"configured": true}`

### Check LLM Status

```bash
# From the API
curl http://localhost:3001/api/llm-status

# Or check in the browser at:
# http://localhost:3000 → Settings → check LLM status indicator
```

---

## 8. Data Ingestion Methods

### Method 1: UI Upload (Drag-and-Drop)

Navigate to the **Ingest Data** page in the sidebar. Drag and drop your files or click to browse. Supports **CSV**, **JSON**, and **Excel** files up to **100MB**.

Supported formats:
- `.csv` — Comma-separated values
- `.json` — JSON array of objects
- `.xlsx` — Excel 2007+
- `.xls` — Legacy Excel

### Method 2: API Upload (curl)

```bash
curl -X POST http://localhost:3000/api/ingest \
  -F "file=@/path/to/your/data.csv" \
  -F "tableName=my_dataset" \
  -F "serviceName=My Data"
```

The upload is proxied through the Next.js frontend to the Python backend at `http://localhost:3001/api/ingest`. You can also call the Python backend directly:

```bash
curl -X POST http://localhost:3001/api/ingest \
  -F "file=@/path/to/your/data.csv" \
  -F "tableName=my_dataset" \
  -F "serviceName=My Data"
```

### Method 3: Bulk Upload Script

```bash
#!/bin/bash
# bulk-upload.sh — Upload all CSV/JSON files in a directory

DATA_DIR="./data"
API_URL="http://localhost:3000/api/ingest"

for file in "${DATA_DIR}"/*.{csv,json}; do
  [ -f "$file" ] || continue

  BASENAME=$(basename "$file")
  TABLE_NAME=$(echo "$BASENAME" | sed 's/\.[^.]*$//')

  echo "Uploading: $BASENAME -> $TABLE_NAME"

  curl -s -X POST "$API_URL" \
    -F "file=@$file" \
    -F "tableName=$TABLE_NAME" \
    -F "serviceName=Bulk Import"
done

echo "Done!"
```

### What Happens After Upload

1. Python backend parses the file into a pandas DataFrame
2. Validates: size ≤ 100MB, columns ≤ 1000, rows ≤ 10M
3. Generates a unique table ID (UUID)
4. Saves the DataFrame as `data/{table_id}.csv` for later quality checks
5. Creates a `Service` record in the database
6. Creates a `Table` record with column names, types, and row count
7. Profiles each column and creates `TableProfile` records
8. Creates an `Activity` log entry
9. Returns: `{success, tableId, tableName, rowCount, columnCount, columns}`

---

## 9. SQL Playground Setup

The SQL Playground lets users run SQL queries against sample databases. This is an optional but useful feature.

### Seed Sample Databases

```bash
cd /path/to/my-project/db
python3 seed_databases.py
cd ..
```

This creates four SQLite databases:

| Database | Tables | Records | Description |
|---|---|---|---|
| `cities.db` | cities, infrastructure, economy | 3,530+ | Indian/world cities data |
| `sales.db` | customers, products, orders, returns | 5,750+ | E-commerce data |
| `hr.db` | employees, departments, attendance, payroll | 10,000+ | HR management data |
| `custom.db` | (app tables) | varies | Main application database |

### Using the SQL Playground

1. Start both services (frontend + backend)
2. Navigate to **SQL Playground** in the sidebar
3. Select a database from the dropdown
4. The tables list will populate automatically
5. Write SQL queries and click **Run**

### Supported SQL

The SQL Playground uses SQLite's built-in SQL engine. All standard SQLite syntax is supported:

```sql
-- Select with filtering
SELECT * FROM cities WHERE population > 1000000 ORDER BY population DESC;

-- Aggregation
SELECT state, COUNT(*) as city_count, AVG(population) as avg_pop
FROM cities
GROUP BY state
HAVING city_count > 5;

-- Join tables
SELECT c.name, o.total_amount
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.status = 'completed';

-- Subqueries
SELECT * FROM employees
WHERE salary > (SELECT AVG(salary) FROM employees)
ORDER BY salary DESC;
```

---

## 10. Production Deployment

### Build for Production

```bash
# Build the Next.js frontend
cd /path/to/my-project
npm run build        # or: bun run build
```

This creates an optimized production bundle in the `.next/` directory with `output: "standalone"` mode.

### Run Production Frontend

```bash
# Using the standalone server
node .next/standalone/server.js

# Or with bun
bun .next/standalone/server.js

# Or with npm start
npm run start
```

### Run Production Backend

```bash
cd /path/to/my-project/mini-services/backend
source venv/bin/activate

# Production mode (no --reload)
python -m uvicorn index:app --host 0.0.0.0 --port 3001 --workers 1
```

> **Note:** SQLite does not support concurrent writes well. Use `--workers 1` for the Python backend. If you need higher concurrency, consider migrating to PostgreSQL.

### Process Management with PM2

```bash
# Install PM2 globally
npm install -g pm2

# Start both services
pm2 start "python -m uvicorn index:app --host 0.0.0.0 --port 3001" \
  --name "dataguard-backend" \
  --cwd /path/to/my-project/mini-services/backend

pm2 start "node .next/standalone/server.js" \
  --name "dataguard-frontend" \
  --cwd /path/to/my-project

# Save for auto-restart on reboot
pm2 save
pm2 startup

# Monitor
pm2 monit
pm2 logs
```

### Reverse Proxy with Nginx

```nginx
# /etc/nginx/sites-available/dataguard
server {
    listen 80;
    server_name dataguard.yourdomain.com;

    # Frontend
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_cache_bypass $http_upgrade;
        client_max_body_size 100M;
    }
}
```

### Reverse Proxy with Caddy

The project includes a `Caddyfile`:

```
:81 {
    reverse_proxy localhost:3000
}
```

This serves the frontend on port 81 with automatic HTTPS (if domain is configured).

### Docker Deployment (Future)

While the project is not currently Dockerized, the architecture supports it:

```dockerfile
# Future Dockerfile concept
FROM node:20-slim AS frontend
# Build Next.js standalone...

FROM python:3.12-slim AS backend
# Install Python deps...

FROM node:20-slim
# Copy both, run with supervisord
```

---

## 11. Troubleshooting

### Problem: "Backend unavailable" Error in UI

**Symptoms:** All pages show "Backend unavailable — please ensure the Python backend is running on port 3001"

**Cause:** The Python FastAPI backend is not running or has crashed.

**Solution:**

```bash
# 1. Check if the backend is running
curl http://localhost:3001/
# If connection refused, the backend is down

# 2. Start the backend
cd /path/to/my-project/mini-services/backend
source venv/bin/activate
python -m uvicorn index:app --host 0.0.0.0 --port 3001 --reload

# 3. Check backend logs for errors
# The backend outputs to stdout/stderr in the terminal

# 4. Common causes:
#    - Virtual environment not activated
#    - Python dependencies not installed (run: pip install -r requirements.txt)
#    - Port 3001 already in use (run: lsof -i :3001)
#    - Database path incorrect (check DB_PATH in config.py or .env)
```

### Problem: Port Already in Use

**Symptoms:** `Address already in use` error when starting either service

**Solution:**

```bash
# Find what's using the port
lsof -i :3000    # For frontend
lsof -i :3001    # For backend

# Kill the process
kill -9 <PID>

# Or kill all node/python processes on those ports
fuser -k 3000/tcp
fuser -k 3001/tcp
```

### Problem: SQLite Database Locked Errors

**Symptoms:** `database is locked` error in backend logs

**Cause:** SQLite uses file-level locking. Concurrent writes from multiple processes cause this.

**Solution:**

```bash
# 1. Check for stale lock files
ls -la db/*.db-journal
ls -la db/*.db-wal
ls -la db/*.db-shm

# 2. Remove stale locks (make sure NO processes are using the database)
rm -f db/*.db-journal db/*.db-wal db/*.db-shm

# 3. Restart the Python backend
# The backend will recreate the database cleanly

# 4. Prevention: Use --workers 1 for uvicorn (SQLite doesn't support
#    concurrent writes from multiple processes)
```

> **⚠️ Do NOT run `bun run db:push`** — this command does not exist in the current architecture. The old Prisma command will not work and is not needed. Database tables are created automatically by the Python backend.

### Problem: Python Dependencies Won't Install

**Symptoms:** `pip install -r requirements.txt` fails

**Solution:**

```bash
# 1. Make sure you're in the virtual environment
source venv/bin/activate

# 2. Upgrade pip first
pip install --upgrade pip

# 3. Install build tools
sudo apt install -y build-essential python3-dev

# 4. Install dependencies one by one to identify the problem
pip install fastapi==0.115.0
pip install uvicorn[standard]==0.30.0
pip install aiosqlite==0.20.0
pip install pandas==2.2.0
pip install numpy==1.26.0
pip install scipy==1.14.0
pip install openpyxl==3.1.5
pip install pydantic==2.9.0
pip install openai==1.50.0
pip install networkx==3.3
pip install python-multipart==0.0.9
```

### Problem: better-sqlite3 Build Fails

**Symptoms:** `npm install` fails on better-sqlite3 native compilation

**Solution:**

```bash
# better-sqlite3 is only used by src/lib/seed.ts (standalone seeder)
# It is NOT required for the application to run

# Option 1: Install build tools
sudo apt install -y build-essential python3-dev
npm install   # Should work now

# Option 2: Skip it entirely (application will still work)
# All runtime DB access goes through the Python backend
# The only thing that breaks is the standalone Node.js seeder script
```

### Problem: Empty Overview Page After Data Upload

**Symptoms:** Data uploads successfully but the overview/dashboard shows zero counts

**Cause:** The stats endpoint queries specific database tables that may not have been populated correctly.

**Solution:**

```bash
# 1. Verify the backend received the data
curl http://localhost:3001/api/tables
# Should show your uploaded tables

curl http://localhost:3001/api/stats
# Should show non-zero counts

# 2. If stats are zero, check the database directly
cd /path/to/my-project
python3 -c "
import sqlite3
conn = sqlite3.connect('db/custom.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM Service')
print(f'Services: {cursor.fetchone()[0]}')
cursor.execute('SELECT COUNT(*) FROM Table_entity')
print(f'Tables: {cursor.fetchone()[0]}')
cursor.execute('SELECT COUNT(*) FROM Activity')
print(f'Activities: {cursor.fetchone()[0]}')
conn.close()
"

# 3. If counts are zero, the upload didn't persist. Restart the backend and try again.
```

### Problem: Large File Upload Failures

**Symptoms:** Upload fails for files > 10MB

**Solution:**

```bash
# The next.config.ts already has a 100MB body size limit.
# If using Nginx as a reverse proxy, add:
# client_max_body_size 100M;

# For very large files (>100MB), consider:
# 1. Splitting into smaller files before upload
# 2. Increasing MAX_FILE_SIZE in the backend .env
# 3. Using the chunked upload API
```

### Problem: Backend Crashes on Startup

**Symptoms:** Python backend exits immediately after starting

**Solution:**

```bash
# Run the backend directly to see error messages
cd mini-services/backend
source venv/bin/activate
python -c "from index import app; print('Backend imports OK')"

# Common issues:
# 1. Missing dependencies: pip install -r requirements.txt
# 2. Database path issues: check DB_PATH in config.py
# 3. Port already in use: lsof -i :3001
# 4. Python version mismatch: python3 --version (need 3.10+)
```

---

## 12. Project Structure Quick Reference

```
my-project/
├── db/                          # SQLite databases
│   ├── custom.db                # Main application DB (auto-created)
│   ├── cities.db                # SQL Playground (seed)
│   ├── sales.db                 # SQL Playground (seed)
│   ├── hr.db                    # SQL Playground (seed)
│   ├── schema.sql               # LEGACY — not used at runtime
│   └── seed_databases.py        # Seed playground databases
│
├── data/                        # Uploaded DataFrames (auto-created)
│   └── {table_id}.csv           # Saved CSVs for quality checks
│
├── mini-services/backend/       # Python FastAPI Backend
│   ├── index.py                 # ★ Main app (77+ endpoints, init_db())
│   ├── config.py                # Configuration (DB path, LLM settings)
│   ├── requirements.txt         # Python dependencies
│   ├── .env                     # Backend environment variables
│   ├── venv/                    # Python virtual environment (you create this)
│   ├── checks/                  # Quality check engines
│   ├── engine/                  # Rule execution + quality scoring
│   ├── llm/                     # LLM client + generators
│   ├── models/                  # Pydantic data models
│   ├── transformations/         # Data transformers + pipeline builder
│   ├── profiling/               # Data profiler
│   ├── connectors/              # External data connectors
│   ├── statistical/             # Statistical hypothesis tests
│   ├── eda/                     # Auto EDA
│   ├── ml_readiness/            # ML readiness scoring
│   ├── copilot/                 # AI copilot engine
│   ├── forecasting/             # Quality trend forecasting
│   ├── contracts/               # Data contract validation
│   ├── scheduler/               # Job scheduling
│   ├── db/                      # Async SQLite connection wrapper
│   └── tests/                   # 30+ test files
│
├── src/                         # Next.js Frontend Source
│   ├── app/
│   │   ├── page.tsx             # ★ Main SPA page (22 views)
│   │   ├── layout.tsx           # Root layout
│   │   ├── globals.css          # Global styles
│   │   └── api/                 # ★ 55+ API route proxies
│   │       ├── ingest/route.ts  # File upload proxy
│   │       ├── sql/query/route.ts # SQL query proxy
│   │       └── ...              # All other route proxies
│   ├── components/
│   │   ├── dq/                  # 33 domain-specific components
│   │   └── ui/                  # 45 shadcn/ui components
│   ├── hooks/                   # Custom React hooks
│   └── lib/
│       ├── store.ts             # Zustand state management
│       ├── db.ts                # ⚠️ LEGACY better-sqlite3 (not used in API routes)
│       ├── seed.ts              # Standalone Node.js seeder
│       └── utils.ts             # Utility functions
│
├── .env                         # Frontend environment variables
├── next.config.ts               # Next.js configuration
├── package.json                 # Frontend dependencies
├── tailwind.config.ts           # Tailwind CSS configuration
├── start.sh                     # Start both services
├── start-backend.sh             # Start Python backend (with venv)
├── start-frontend.sh            # Start Next.js frontend
├── supervisord.conf             # Supervisord process manager
└── Caddyfile                    # Caddy reverse proxy config
```

---

## 13. Common Development Tasks

### Adding a New API Endpoint

1. **Add the endpoint in the Python backend** (`mini-services/backend/index.py`):
```python
@app.get("/api/my-new-endpoint")
async def my_new_endpoint():
    db = await get_db()
    # ... business logic here ...
    return {"result": "data"}
```

2. **Create a Next.js API route proxy** (`src/app/api/my-new-endpoint/route.ts`):
```typescript
import { NextRequest, NextResponse } from 'next/server'

const BACKEND = 'http://localhost:3001/api'

export async function GET(request: NextRequest) {
  try {
    const res = await fetch(`${BACKEND}/my-new-endpoint`)
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json(
      { error: 'Backend unavailable — please ensure the Python backend is running on port 3001' },
      { status: 502 }
    )
  }
}
```

3. **Add the frontend component call** in the relevant `src/components/dq/*.tsx` file

### Adding a New Database Table

1. **Add the table in the Python backend's `init_db()`** function in `index.py`:
```python
await db.execute("""
    CREATE TABLE IF NOT EXISTS MyNewTable (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    )
""")
```

2. **Restart the Python backend** — `init_db()` runs on startup and creates the table

3. **Do NOT add the table to `db/schema.sql`** — that file is legacy and not used at runtime

### Running Tests

```bash
# Python backend tests
cd mini-services/backend
source venv/bin/activate
python -m pytest tests/ -v

# Run a specific test
python -m pytest tests/test_checks_completeness.py -v

# Run integration tests
python -m pytest tests/test_integration.py -v
```

### Resetting the Database

```bash
# ⚠️ This will DELETE all your data!

# Stop both services first

# Delete the database files
rm -f db/custom.db db/custom.db-wal db/custom.db-shm db/custom.db-journal

# Restart the Python backend — it will recreate all tables via init_db()
cd mini-services/backend
source venv/bin/activate
python -m uvicorn index:app --host 0.0.0.0 --port 3001 --reload

# Re-seed playground databases if needed
cd db
python3 seed_databases.py
```

### Checking Backend Health

```bash
# Quick health check
curl -s http://localhost:3001/ | python3 -m json.tool

# Check LLM status
curl -s http://localhost:3001/api/llm-status | python3 -m json.tool

# Check database tables
curl -s http://localhost:3001/api/tables | python3 -m json.tool

# Check stats
curl -s http://localhost:3001/api/stats | python3 -m json.tool
```

---

## 14. Migration Notes (Prisma → No Prisma)

If you are migrating from an older version of DataGuard that used Prisma, here are the key changes:

### What Changed

| Before (Old) | After (Current) |
|---|---|
| Prisma ORM for database access | Python aiosqlite (raw SQL) |
| `prisma/` directory with schema.prisma | No prisma directory |
| `npx prisma migrate dev` for migrations | `init_db()` in Python creates tables on startup |
| `npx prisma generate` for client | No code generation needed |
| `@prisma/client` in package.json | Removed |
| `bun run db:push` command | Does NOT exist — tables auto-created on startup |
| Next.js API routes used Prisma client | Next.js API routes are pure proxies to Python backend |
| Database operations in Next.js process | All DB operations in Python FastAPI backend |
| `src/lib/db.ts` used at runtime | `src/lib/db.ts` is LEGACY — only for standalone seeder |

### Migration Steps

1. **Remove Prisma dependencies:**
   ```bash
   npm uninstall prisma @prisma/client
   rm -rf prisma/
   ```

2. **Update `src/lib/db.ts`** — This file can remain but should NOT be imported by any API route. It's only used by `src/lib/seed.ts`.

3. **Ensure all API routes are pure proxies** — Check that every route in `src/app/api/` only does `fetch('http://localhost:3001/...')` and does NOT import `db` from `src/lib/db.ts`.

4. **Remove `db:push` from package.json scripts** — The command no longer exists.

5. **Update any documentation or settings** that reference Prisma commands.

### Files That Still Reference Old Architecture (Safe to Ignore)

| File | What It References | Impact |
|---|---|---|
| `src/lib/db.ts` | better-sqlite3, schema.sql | Only used by seed.ts, not by API routes |
| `src/lib/seed.ts` | better-sqlite3 | Standalone seeder script |
| `db/schema.sql` | Old Node.js schema | Not used at runtime |
| `supervisord.conf` | `/DataMonitor/` paths | Update paths for your setup |

---

## Quick Reference Card

```
┌──────────────────────────────────────────────────────────────┐
│                    DATAGUARD QUICK REFERENCE                  │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  START BACKEND:  cd mini-services/backend && source          │
│                  venv/bin/activate && python -m               │
│                  uvicorn index:app --port 3001 --reload       │
│                                                               │
│  START FRONTEND: npm run dev  (or: bun run dev)              │
│                                                               │
│  URL:           http://localhost:3000                         │
│  API:           http://localhost:3001                         │
│                                                               │
│  DB:            db/custom.db (auto-created on startup)       │
│  DATA:          data/{table_id}.csv (uploaded datasets)      │
│                                                               │
│  NO PRISMA:     Database tables auto-created by Python       │
│  NO DB PUSH:    bun run db:push does NOT exist               │
│  NO MIGRATIONS: init_db() handles everything                 │
│                                                               │
│  LLM CONFIG:    mini-services/backend/.env                   │
│                 LLM_API_KEY=your-key                          │
│                 LLM_BASE_URL=https://api.groq.com/openai/v1  │
│                                                               │
│  TROUBLESHOOT:  Backend unavailable? → Start Python backend  │
│                 Port in use?     → lsof -i :PORT             │
│                 DB locked?       → rm -f db/*.db-journal     │
│                 Empty data?      → Check /api/stats          │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```
