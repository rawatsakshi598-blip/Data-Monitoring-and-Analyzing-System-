# DataGuard — Complete Project Overview & Technical Reference

> **Purpose:** This document is the single source of truth for the DataGuard project. Any LLM, AI coding agent, or developer should be able to read this file and instantly understand the entire codebase architecture, every file's purpose, how files connect to each other, where to find specific functionality, and where to fix any bug or issue.

---

## Table of Contents

1. [Project Summary](#1-project-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Technology Stack](#3-technology-stack)
4. [How to Run Locally](#4-how-to-run-locally)
5. [Full Folder Structure](#5-full-folder-structure)
6. [Database Layer](#6-database-layer)
7. [Python FastAPI Backend — Complete Reference](#7-python-fastapi-backend--complete-reference)
8. [Next.js Frontend — Complete Reference](#8-nextjs-frontend--complete-reference)
9. [API Route Proxy Map](#9-api-route-proxy-map)
10. [Frontend Component → API → Backend Endpoint Map](#10-frontend-component--api--backend-endpoint-map)
11. [Python Backend Module Deep-Dive](#11-python-backend-module-deep-dive)
12. [Data Flow Diagrams](#12-data-flow-diagrams)
13. [File Dependency Graph](#13-file-dependency-graph)
14. [Bug Fixing Guide — Where to Look](#14-bug-fixing-guide--where-to-look)
15. [Known Issues & Technical Debt](#15-known-issues--technical-debt)
16. [Environment Variables Reference](#16-environment-variables-reference)
17. [Database Schema — Python Backend (27 Tables)](#17-database-schema--python-backend-27-tables)
18. [Database Schema — Node.js schema.sql (15 Tables)](#18-database-schema--nodejs-schemasql-15-tables)
19. [Schema Mismatch Reference](#19-schema-mismatch-reference)
20. [Startup Scripts Reference](#20-startup-scripts-reference)
21. [LLM Integration Architecture](#21-llm-integration-architecture)
22. [Quality Check Engine Architecture](#22-quality-check-engine-architecture)
23. [Transformation Engine Architecture](#23-transformation-engine-architecture)
24. [Test Suite Reference](#24-test-suite-reference)

---

## 1. Project Summary

**Name:** DataGuard — Unified Data Intelligence Platform

**Tagline:** An OpenMetadata-inspired data quality monitoring, governance, lineage tracking, and metadata management platform.

**Core Concept:** DataGuard is a dual-stack web application where a Next.js 16 frontend (port 3000) serves as the UI layer, proxying ALL data operations to a Python FastAPI backend (port 3001). The Python backend owns all business logic, database operations, AI/LLM features, quality checks, transformations, statistical tests, and data connectors. The frontend contains ZERO business logic — every Next.js API route is a thin proxy that forwards requests to `http://localhost:3001/api/...`.

**Key Design Principles:**
- ALL services MUST work through the Python FastAPI backend — NO better-sqlite3 fallbacks in Next.js API routes
- The Python backend is the single source of truth for all data and business logic
- LLM-powered features (rule generation, fix suggestions, copilot, report generation) gracefully degrade to heuristic/template fallbacks when no LLM API key is configured
- Quality checks run on real pandas DataFrames when data is available, falling back to profile-based estimation, and finally to simulated results

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        BROWSER (User)                            │
│                   http://localhost:3000                          │
└────────────────────────┬─────────────────────────────────────────┘
                         │ HTTP Requests
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                  NEXT.JS 16 FRONTEND (Port 3000)                 │
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐ │
│  │  React UI    │──▶│  Zustand     │   │  33 DQ Components    │ │
│  │  (page.tsx)  │   │  Store       │   │  (src/components/dq/) │ │
│  └──────────────┘   └──────────────┘   └──────────┬───────────┘ │
│                                                    │ fetch()     │
│  ┌─────────────────────────────────────────────────▼───────────┐ │
│  │              NEXT.JS API ROUTES (40+ proxies)               │ │
│  │  src/app/api/*/route.ts → fetch('http://localhost:3001/...')│ │
│  └─────────────────────────┬───────────────────────────────────┘ │
└────────────────────────────┼─────────────────────────────────────┘
                             │ HTTP Proxy (no business logic)
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│               PYTHON FASTAPI BACKEND (Port 3001)                 │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              index.py (2872 lines — MONOLITHIC)            │  │
│  │  77+ endpoints covering ALL business logic                 │  │
│  └────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬─────┘  │
│       │      │      │      │      │      │      │      │        │
│  ┌────▼──┐┌──▼───┐┌─▼────┐┌▼─────┐┌▼─────┐┌▼─────┐┌▼──────┐  │
│  │checks/││engine││llm/  ││eda/  ││models││conn- ││trans- │  │
│  │7 types││rule  ││4 mods││auto  ││3 data││ectors││forms/ │  │
│  │       ││exec  ││      ││EDA   ││models││5 src ││10 xfrms│  │
│  └───────┘└──────┘└──────┘└──────┘└──────┘└──────┘└───────┘  │
│       │      │      │      │      │               │            │
│  ┌────▼──────▼──────▼──────▼──────▼───────────────▼──────────┐  │
│  │              SQLite Database (db/custom.db)                │  │
│  │              27 tables (Python schema)                     │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              Data Files (data/*.csv)                       │  │
│  │              Uploaded data saved as CSV for real checks     │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              SQL Playground DBs (db/*.db)                  │  │
│  │              cities.db, sales.db, hr.db, custom.db         │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

### Frontend
| Technology | Version | Purpose |
|---|---|---|
| Next.js | 16 | React framework, SSR, API routes |
| React | 19 | UI library |
| TypeScript | 5.x | Type safety |
| Tailwind CSS | 4 | Utility-first styling |
| shadcn/ui | latest | Component library (45 components) |
| Zustand | latest | State management (view routing) |
| Recharts | latest | Charts and visualizations |
| Lucide React | latest | Icon library |
| PapaParse | latest | CSV parsing (client-side preview) |
| xlsx | latest | Excel parsing (client-side preview) |
| dnd-kit | latest | Drag-and-drop for pipeline builder |
| framer-motion | latest | Animations |
| Sonner | latest | Toast notifications |
| better-sqlite3 | latest | **DEPRECATED** — still in `src/lib/db.ts` but should NOT be used in API routes |

### Backend
| Technology | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Runtime |
| FastAPI | 0.115.0 | Web framework |
| Uvicorn | 0.30.0 | ASGI server |
| aiosqlite | 0.20.0 | Async SQLite driver |
| Pandas | 2.2.0 | Data manipulation, quality checks, transformations |
| NumPy | 1.26.0 | Numerical operations |
| SciPy | 1.14.0 | Statistical tests |
| OpenAI | 1.50.0 | LLM client (OpenAI-compatible APIs) |
| openpyxl | 3.1.5 | Excel file reading |
| Pydantic | 2.9.0 | Data validation models |
| NetworkX | 3.3 | DAG pipeline builder |
| python-multipart | 0.0.9 | File upload handling |

### Infrastructure
| Technology | Purpose |
|---|---|
| SQLite | Database (file-based, zero config) |
| Caddy | Reverse proxy (port 81 → port 3000) |
| Supervisord | Process manager (backend + frontend) |
| Bun | Package manager (alternative to npm) |

---

## 4. How to Run Locally

### Prerequisites
- Node.js 18+ and npm/bun
- Python 3.10+
- Git

### Setup

```bash
# 1. Clone/unzip the project
cd my-project

# 2. Install frontend dependencies
npm install

# 3. Setup Python backend
cd mini-services/backend
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ../..

# 4. Seed the playground databases (optional — creates cities.db, sales.db, hr.db)
cd db && python seed_databases.py && cd ..

# 5. Start the Python backend
# Terminal 1:
cd mini-services/backend
source venv/bin/activate
python -m uvicorn index:app --host 0.0.0.0 --port 3001 --reload

# 6. Start the Next.js frontend
# Terminal 2:
npm run dev

# 7. Open browser
# http://localhost:3000
```

### Using start scripts
```bash
# Start both services (from project root)
./start.sh

# Or individually
./start_backend.sh    # Python backend on port 3001
./start-frontend.sh   # Next.js on port 3000
```

### LLM Configuration (Optional)
Create a `.env` file in `mini-services/backend/`:
```
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=gpt-4o-mini
```

---

## 5. Full Folder Structure

```
/home/z/my-project/
│
├── .env                              # DATABASE_URL=file:/home/z/my-project/db/custom.db
├── .gitignore
├── Caddyfile                         # Caddy reverse proxy config (port 81 → 3000)
├── components.json                   # shadcn/ui configuration
├── bun.lock                          # Bun lockfile
├── eslint.config.mjs                 # ESLint config
├── next-env.d.ts                     # Next.js TypeScript env declarations
├── next.config.ts                    # Next.js config (standalone output, 100MB body limit)
├── package.json                      # Frontend dependencies
├── package-lock.json                 # npm lockfile
├── postcss.config.mjs                # PostCSS config
├── tailwind.config.ts                # Tailwind CSS config with shadcn/ui theme
├── tsconfig.json                     # TypeScript config
│
├── run_backend.py                    # Python wrapper to start uvicorn
├── start.sh                          # Start both backend + frontend
├── start-backend.sh                  # Start Python backend with venv
├── start_backend.sh                  # Start Python backend directly
├── start-frontend.sh                 # Start Next.js with bun
├── start_services.sh                 # Start both with PID tracking
├── supervisord.conf                  # Supervisord process manager config
│
├── worklog.md                        # Agent work log
├── backend.log                       # Python backend log
├── backend.pid                       # Python backend PID file
├── frontend.pid                      # Next.js frontend PID file
├── dev.log                           # Development log
│
├── db/                               # Database directory
│   ├── schema.sql                    # Node.js schema (15 tables — used by better-sqlite3)
│   ├── seed_databases.py             # Seeds cities.db, sales.db, hr.db, custom.db
│   ├── custom.db                     # Main application database (created at runtime)
│   ├── cities.db                     # SQL Playground: 3,530 cities (created by seed)
│   ├── sales.db                      # SQL Playground: 5000 orders (created by seed)
│   └── hr.db                         # SQL Playground: 1000 employees (created by seed)
│
├── data/                             # Uploaded data files (CSV/JSON/XLSX saved here)
│
├── upload/                           # Temporary upload directory
│
├── public/                           # Static assets
│   ├── logo.svg                      # DataGuard logo
│   └── robots.txt                    # SEO robots file
│
├── mini-services/                    # Backend services
│   └── backend/
│       ├── index.py                  # ★ MAIN FastAPI APP (2872 lines, 77+ endpoints)
│       ├── config.py                 # Configuration (DB path, LLM settings, server config)
│       ├── requirements.txt          # Python dependencies
│       ├── run.sh                    # Shell script to start uvicorn
│       ├── package.json              # Placeholder (not used for Python)
│       ├── venv/                     # Python virtual environment (NOT in zip)
│       │
│       ├── checks/                   # Quality Check Engine (7 check types)
│       │   ├── __init__.py           # Registry: get_check() factory + aliases
│       │   ├── base_check.py         # Abstract BaseCheck class
│       │   ├── completeness_check.py # Null/missing value check
│       │   ├── uniqueness_check.py   # Duplicate detection check
│       │   ├── validity_check.py     # Value format/range/regex check
│       │   ├── freshness_check.py    # Data recency check
│       │   ├── schema_check.py       # Schema conformance check
│       │   ├── volume_check.py       # Row count check
│       │   └── anomaly_check.py      # Statistical anomaly detection (z-score)
│       │
│       ├── engine/                   # Rule Execution Engine
│       │   ├── __init__.py
│       │   ├── rule_executor.py      # Execute rules on DataFrames, load/save data
│       │   └── quality_scorer.py     # Weighted quality scoring across dimensions
│       │
│       ├── models/                   # Pydantic Data Models
│       │   ├── __init__.py
│       │   ├── check_result.py       # CheckResult, RunRulesRequest
│       │   ├── rule.py               # CheckConfig, RuleCreate, NLRuleRequest
│       │   └── quality_report.py     # Report request/response models
│       │
│       ├── llm/                      # LLM Integration Layer
│       │   ├── __init__.py
│       │   ├── client.py             # Multi-provider LLM client with fallback
│       │   ├── rule_generator.py     # NL→Rule generation (LLM + keyword fallback)
│       │   ├── fix_generator.py      # Fix code generation (LLM + template fallback)
│       │   ├── report_generator.py   # Quality report generation (LLM + template fallback)
│       │   └── prompts.py            # System/user prompt templates for LLM
│       │
│       ├── copilot/                  # AI Data Preparation Copilot
│       │   ├── __init__.py
│       │   └── engine.py             # Chat engine + heuristic suggestions fallback
│       │
│       ├── eda/                      # Auto Exploratory Data Analysis
│       │   ├── __init__.py
│       │   └── auto_eda.py           # Full EDA report generation
│       │
│       ├── forecasting/              # Quality Trend Forecasting
│       │   ├── __init__.py
│       │   └── engine.py             # SMA, exponential smoothing, linear trend
│       │
│       ├── ml_readiness/             # ML Readiness Scoring
│       │   ├── __init__.py
│       │   └── scorer.py             # 7-dimension ML readiness assessment
│       │
│       ├── statistical/              # Statistical Hypothesis Testing
│       │   ├── __init__.py
│       │   └── tests.py             # 8 statistical tests (t-test, chi-square, etc.)
│       │
│       ├── connectors/               # External Data Connectors
│       │   ├── __init__.py
│       │   └── data_connectors.py    # PostgreSQL, MySQL, S3, BigQuery, SQLite
│       │
│       ├── contracts/                # Data Contract Validation
│       │   ├── __init__.py
│       │   └── validator.py          # Schema, column, row-level, freshness validation
│       │
│       ├── scheduler/                # Job Scheduling
│       │   ├── __init__.py
│       │   └── scheduler.py          # Cron + interval scheduling, file-based persistence
│       │
│       ├── profiling/                # Data Profiler
│       │   ├── __init__.py
│       │   └── profiler.py           # Column-level statistics and type detection
│       │
│       ├── transformations/          # Data Transformation Engine (10 transformers)
│       │   ├── __init__.py
│       │   ├── base_transform.py     # NEWER base class (with snapshots)
│       │   ├── base_transformer.py   # OLDER base class (legacy)
│       │   ├── imputation.py         # Fill missing values (mean, median, mode, etc.)
│       │   ├── outlier.py            # Remove/cap outliers (IQR, z-score, percentile)
│       │   ├── dedup.py              # Remove duplicates
│       │   ├── deduplication.py      # Alternative dedup implementation
│       │   ├── encoding.py           # Categorical encoding (one-hot, label, ordinal)
│       │   ├── normalization.py      # Feature scaling (standard, minmax, robust)
│       │   ├── string_clean.py       # String cleaning (trim, lowercase, etc.)
│       │   ├── date_parser.py        # Date parsing and extraction
│       │   ├── data_split.py         # Train/test split
│       │   ├── type_conversion.py    # Column type conversion
│       │   ├── pipeline.py           # DAG-based pipeline builder
│       │   └── history.py            # Transformation history with rollback
│       │
│       ├── db/                       # Database Connection
│       │   ├── __init__.py
│       │   └── connection.py         # Async SQLite wrapper (Database class)
│       │
│       ├── tests/                    # Test Suite (30+ test files)
│       │   ├── test_transformations.py
│       │   ├── test_data_connectors.py
│       │   ├── test_data_contracts.py
│       │   ├── test_statistical_tests.py
│       │   ├── test_checks_freshness.py
│       │   ├── test_forecasting.py
│       │   ├── test_scheduler.py
│       │   ├── test_copilot.py
│       │   ├── test_checks_validity.py
│       │   ├── test_transform_history.py
│       │   ├── test_engine_quality_scorer.py
│       │   ├── test_checks_schema.py
│       │   ├── test_models_rule.py
│       │   ├── test_checks_uniqueness.py
│       │   ├── test_checks_base.py
│       │   ├── test_ml_readiness.py
│       │   ├── test_system.py
│       │   ├── test_config.py
│       │   ├── test_checks_completeness.py
│       │   ├── test_llm_prompts.py
│       │   ├── test_checks_volume.py
│       │   ├── test_integration.py
│       │   ├── test_auto_eda.py
│       │   ├── test_models_check_result.py
│       │   ├── test_db_connection.py
│       │   ├── test_profiling_profiler.py
│       │   └── ... (more test files)
│       │
│       └── src/app/api/              # Legacy Next.js route stubs (NOT USED)
│           ├── ai/generate-report/route.ts
│           ├── ai/generate-rule/route.ts
│           ├── ai/generate-fix/route.ts
│           ├── run-rules/route.ts
│           └── profile/route.ts
│
├── src/                              # Next.js Frontend Source
│   ├── app/
│   │   ├── layout.tsx                # Root layout (Geist fonts, Sonner toaster)
│   │   ├── page.tsx                  # ★ Main SPA page (22 views, lazy-loaded)
│   │   ├── globals.css               # Global styles + Tailwind + custom CSS
│   │   │
│   │   └── api/                      # ★ 40+ API Route Proxies (ALL forward to Python)
│   │       ├── route.ts              # GET /api → health check proxy
│   │       ├── stats/route.ts        # GET /api/stats
│   │       ├── services/
│   │       │   ├── route.ts          # GET/POST /api/services
│   │       │   └── [id]/route.ts     # GET/PUT/DELETE /api/services/:id
│   │       ├── tables/
│   │       │   ├── route.ts          # GET /api/tables
│   │       │   └── [id]/route.ts     # GET /api/tables/:id
│   │       ├── datasets/
│   │       │   ├── route.ts          # GET/POST /api/datasets
│   │       │   └── [id]/route.ts     # GET/PUT/DELETE /api/datasets/:id
│   │       ├── rules/
│   │       │   ├── route.ts          # GET/POST /api/rules
│   │       │   └── [id]/route.ts     # PUT/DELETE /api/rules/:id
│   │       ├── quality/
│   │       │   ├── route.ts          # GET /api/quality
│   │       │   └── results/route.ts  # GET /api/quality/results
│   │       ├── checks/route.ts       # GET /api/checks
│   │       ├── run-check/route.ts    # POST /api/run-check
│   │       ├── lineage/route.ts      # GET /api/lineage
│   │       ├── alerts/route.ts       # GET/PUT /api/alerts
│   │       ├── tags/route.ts         # GET/POST /api/tags
│   │       ├── glossary/route.ts     # GET/POST /api/glossary
│   │       ├── teams/route.ts        # GET /api/teams
│   │       ├── activity/route.ts     # GET /api/activity
│   │       ├── search/route.ts       # GET /api/search
│   │       ├── compliance/route.ts   # GET /api/compliance
│   │       ├── ingest/route.ts       # POST /api/ingest (multipart file upload proxy)
│   │       ├── profile/
│   │       │   └── route.ts          # GET/POST /api/profile
│   │       ├── nl-rule/route.ts      # POST /api/nl-rule
│   │       ├── ai/
│   │       │   ├── generate-report/route.ts  # POST /api/ai/generate-report
│   │       │   └── generate-fix/route.ts     # POST /api/ai/generate-fix
│   │       ├── anomaly/route.ts      # GET /api/anomaly
│   │       ├── transforms/
│   │       │   ├── route.ts          # GET/POST /api/transforms
│   │       │   └── [...slug]/route.ts # Dynamic: list, execute, history, rollback
│   │       ├── pipelines/
│   │       │   ├── route.ts          # GET/POST /api/pipelines
│   │       │   ├── [id]/route.ts     # GET/PUT/DELETE /api/pipelines/:id
│   │       │   ├── [id]/run/route.ts # POST /api/pipelines/:id/run
│   │       │   └── runs/route.ts     # GET /api/pipelines/runs
│   │       ├── auto-eda/route.ts     # POST/GET /api/auto-eda
│   │       ├── ml-readiness/route.ts # POST/GET /api/ml-readiness
│   │       ├── connectors/
│   │       │   ├── route.ts          # GET/POST /api/connectors
│   │       │   ├── [id]/route.ts     # DELETE /api/connectors/:id
│   │       │   ├── [id]/test/route.ts   # POST /api/connectors/:id/test
│   │       │   └── [id]/fetch/route.ts  # POST /api/connectors/:id/fetch
│   │       ├── schedules/
│   │       │   ├── route.ts          # GET/POST /api/schedules
│   │       │   ├── [id]/route.ts     # PUT/DELETE /api/schedules/:id
│   │       │   └── [id]/run/route.ts # POST /api/schedules/:id/run
│   │       ├── copilot/route.ts      # POST/GET /api/copilot
│   │       ├── statistical/route.ts  # GET/POST /api/statistical
│   │       ├── contracts/
│   │       │   ├── route.ts          # GET/POST /api/contracts
│   │       │   ├── [id]/route.ts     # DELETE /api/contracts/:id
│   │       │   └── [id]/validate/route.ts # POST /api/contracts/:id/validate
│   │       ├── forecast/route.ts     # GET/POST /api/forecast
│   │       ├── sql/
│   │       │   ├── route.ts          # GET /api/sql
│   │       │   ├── databases/route.ts # GET /api/sql/databases
│   │       │   ├── tables/route.ts   # GET /api/sql/tables
│   │       │   └── query/route.ts    # POST /api/sql/query
│   │       └── auto-fix/
│   │           ├── route.ts          # GET /api/auto-fix/pending + POST /api/auto-fix/propose
│   │           ├── [fixId]/approve/route.ts  # POST /api/auto-fix/:fixId/approve
│   │           ├── [fixId]/reject/route.ts   # POST /api/auto-fix/:fixId/reject
│   │           └── [fixId]/apply/route.ts    # POST /api/auto-fix/:fixId/apply
│   │
│   ├── components/
│   │   ├── dq/                       # ★ 33 Domain-Specific Components
│   │   │   ├── sidebar.tsx           # Navigation sidebar (22 menu items)
│   │   │   ├── overview.tsx          # Dashboard overview (stats, charts, recent activity)
│   │   │   ├── dashboard.tsx         # Quality dashboard (stats, checks, alerts)
│   │   │   ├── services.tsx          # Data source CRUD management
│   │   │   ├── tables.tsx            # Table explorer with filtering/sorting
│   │   │   ├── ingest.tsx            # File upload (CSV/JSON/XLSX) with drag-and-drop
│   │   │   ├── quality.tsx           # Quality rules, checks, NL rule builder, AI report
│   │   │   ├── checks.tsx            # Quality check results viewer
│   │   │   ├── rules.tsx             # Rule CRUD management
│   │   │   ├── anomalies.tsx         # Anomaly detection results
│   │   │   ├── alerts.tsx            # Alert management (filter, resolve, assign)
│   │   │   ├── lineage.tsx           # Data lineage visualization
│   │   │   ├── governance.tsx        # Tags, glossary, teams management
│   │   │   ├── activity.tsx          # Activity feed
│   │   │   ├── datasets.tsx          # Dataset CRUD management
│   │   │   ├── profile-viewer.tsx    # Column profile viewer
│   │   │   ├── quality-report.tsx    # AI-generated quality report viewer
│   │   │   ├── pipeline-builder.tsx  # Drag-and-drop pipeline builder
│   │   │   ├── auto-eda.tsx          # Auto EDA report generation/viewing
│   │   │   ├── ml-readiness.tsx      # ML readiness scoring
│   │   │   ├── connectors.tsx        # External data connector management
│   │   │   ├── scheduler.tsx         # Job scheduling (CRUD, manual run)
│   │   │   ├── copilot.tsx           # AI data prep assistant (chat interface)
│   │   │   ├── statistical-tests.tsx # Statistical hypothesis testing
│   │   │   ├── data-contracts.tsx    # Data contract validation
│   │   │   ├── forecasting.tsx       # Quality trend forecasting
│   │   │   ├── sql-playground.tsx    # SQL query playground (database dropdown, query editor)
│   │   │   ├── auto-fix.tsx          # Auto-fix approval workflow
│   │   │   ├── ai-rule-builder.tsx   # Natural language rule builder
│   │   │   ├── fix-suggestion.tsx    # AI fix suggestions
│   │   │   ├── compliance.tsx        # Compliance reports
│   │   │   └── settings.tsx          # App settings (teams management)
│   │   │
│   │   └── ui/                       # 45 shadcn/ui Components (standard library)
│   │       ├── accordion.tsx
│   │       ├── alert.tsx
│   │       ├── alert-dialog.tsx
│   │       ├── aspect-ratio.tsx
│   │       ├── avatar.tsx
│   │       ├── badge.tsx
│   │       ├── breadcrumb.tsx
│   │       ├── button.tsx
│   │       ├── calendar.tsx
│   │       ├── card.tsx
│   │       ├── carousel.tsx
│   │       ├── chart.tsx             # Recharts wrapper
│   │       ├── checkbox.tsx
│   │       ├── collapsible.tsx
│   │       ├── command.tsx
│   │       ├── context-menu.tsx
│   │       ├── dialog.tsx
│   │       ├── drawer.tsx
│   │       ├── dropdown-menu.tsx
│   │       ├── form.tsx
│   │       ├── hover-card.tsx
│   │       ├── input-otp.tsx
│   │       ├── input.tsx
│   │       ├── label.tsx
│   │       ├── menubar.tsx
│   │       ├── navigation-menu.tsx
│   │       ├── pagination.tsx
│   │       ├── popover.tsx
│   │       ├── progress.tsx
│   │       ├── radio-group.tsx
│   │       ├── resizable.tsx
│   │       ├── scroll-area.tsx
│   │       ├── select.tsx
│   │       ├── separator.tsx
│   │       ├── sheet.tsx
│   │       ├── sidebar.tsx
│   │       ├── skeleton.tsx
│   │       ├── slider.tsx
│   │       ├── sonner.tsx
│   │       ├── switch.tsx
│   │       ├── table.tsx
│   │       ├── tabs.tsx
│   │       ├── textarea.tsx
│   │       ├── toast.tsx
│   │       ├── toaster.tsx
│   │       ├── toggle-group.tsx
│   │       ├── toggle.tsx
│   │       └── tooltip.tsx
│   │
│   ├── hooks/
│   │   ├── use-toast.ts             # Toast notification hook
│   │   └── use-mobile.ts            # Mobile detection hook
│   │
│   └── lib/
│       ├── store.ts                  # ★ Zustand store (ViewType, AppState, shared interfaces)
│       ├── db.ts                     # ⚠️ better-sqlite3 connection (DEPRECATED — do not use in API routes)
│       ├── seed.ts                   # Seed data for initial setup
│       └── utils.ts                  # Utility functions (cn helper, etc.)
│
└── download/                         # Generated output files directory
```

---

## 6. Database Layer

### Database Files
| File | Purpose | Created By |
|---|---|---|
| `db/custom.db` | Main application database (ALL metadata) | Python backend `init_db()` |
| `db/cities.db` | SQL Playground: Indian/world cities data | `db/seed_databases.py` |
| `db/sales.db` | SQL Playground: customers, products, orders | `db/seed_databases.py` |
| `db/hr.db` | SQL Playground: employees, departments, payroll | `db/seed_databases.py` |

### CRITICAL: Dual Schema Problem

The project has **TWO competing schema definitions** that can cause bugs:

1. **Python Backend Schema** — Defined inline in `mini-services/backend/index.py` → `init_db()` function. Creates 27 tables. This is the ACTIVE schema used by the running application.

2. **Node.js Schema** — Defined in `db/schema.sql`. Creates 15 tables. This is executed by `src/lib/db.ts` on Next.js startup using better-sqlite3. **This should NOT be running** since all operations must go through the Python backend.

**The Python backend's `init_db()` runs on every FastAPI startup and creates its tables with `CREATE TABLE IF NOT EXISTS`. Since it runs AFTER the Node.js schema (if both start), the Python schema takes precedence for any overlapping tables.**

### Data Files
| Directory | Purpose | Created By |
|---|---|---|
| `data/` | Saved DataFrames as CSV/JSON/XLSX for real quality checks | `engine/rule_executor.py` → `save_dataframe()` |
| `/tmp/dataguard_chunks/` | Temporary upload chunks | `index.py` → ingest endpoint |

### How Data Persistence Works
1. User uploads a file via `/api/ingest`
2. Python backend parses the file into a pandas DataFrame
3. Metadata (table name, columns, row count) is stored in SQLite (`custom.db`)
4. The actual DataFrame is saved to `data/{table_id}.csv`
5. When a quality check runs, `load_dataframe()` reads the CSV back
6. If the CSV is missing, checks fall back to profile-based estimation

---

## 7. Python FastAPI Backend — Complete Reference

### Entry Point: `mini-services/backend/index.py`

This is a **2872-line monolithic file** containing ALL 77+ API endpoints. It includes:
- Database helpers (`get_db()`, `query_one()`, `query_all()`, `query_scalar()`)
- JSON utilities (`NumpyEncoder`, `safe_json_dumps`, `_sanitize_for_json`)
- Database initialization (`init_db()` — creates 27 tables)
- All API endpoint handlers

### Complete Endpoint List

| Method | Path | Purpose | Key Dependencies |
|---|---|---|---|
| GET | `/` | Health check + LLM status | `config.py` |
| GET | `/api/llm-status` | LLM configuration status | `config.py` |
| GET | `/api/stats` | Dashboard statistics | DB: Service, Table, DQTest, Alert, Activity |
| GET | `/api/services` | List all services | DB: Service, Table |
| POST | `/api/services` | Create a service | DB: Service |
| GET | `/api/services/{sid}` | Get service details | DB: Service, Table |
| PUT | `/api/services/{sid}` | Update a service | DB: Service |
| DELETE | `/api/services/{sid}` | Delete a service | DB: Service |
| GET | `/api/tables` | List tables (filter/sort/search) | DB: Table, Service, DQTest |
| GET | `/api/tables/{tid}` | Get table details | DB: Table, Service, DQTest, DQTestResult, TableProfile |
| GET | `/api/quality` | List quality tests | DB: DQTest, Table, DQTestResult |
| GET | `/api/quality/results` | List test results | DB: DQTestResult, DQTest |
| GET | `/api/rules` | List quality rules | DB: QualityRule, Dataset |
| POST | `/api/rules` | Create a quality rule | DB: QualityRule |
| PUT | `/api/rules/{rid}` | Update a quality rule | DB: QualityRule |
| DELETE | `/api/rules/{rid}` | Delete a quality rule | DB: QualityRule |
| GET | `/api/checks` | List quality checks | DB: QualityCheck, QualityRule, Dataset |
| POST | `/api/run-check` | Execute a quality check | `engine/rule_executor.py`, `checks/`, DB: QualityRule, Dataset, Table, QualityCheck, Alert |
| GET | `/api/lineage` | List data lineage edges | DB: DataLineage, Table |
| GET | `/api/alerts` | List alerts (filter by status/severity) | DB: Alert |
| PUT | `/api/alerts` | Update alert (resolve, assign) | DB: Alert |
| GET | `/api/tags` | List tags | DB: Tag |
| POST | `/api/tags` | Create a tag | DB: Tag |
| GET | `/api/glossary` | List glossary terms | DB: GlossaryTerm |
| POST | `/api/glossary` | Create glossary term | DB: GlossaryTerm |
| GET | `/api/teams` | List teams | DB: Team |
| GET | `/api/activity` | List activity log | DB: Activity |
| GET | `/api/search` | Search across entities | DB: Service, Table, Dataset |
| GET | `/api/compliance` | List compliance reports | DB: ComplianceReport |
| GET | `/api/datasets` | List datasets | DB: Dataset |
| POST | `/api/datasets` | Create a dataset | DB: Dataset |
| GET | `/api/datasets/{did}` | Get dataset details | DB: Dataset |
| PUT | `/api/datasets/{did}` | Update a dataset | DB: Dataset |
| DELETE | `/api/datasets/{did}` | Delete a dataset | DB: Dataset |
| POST | `/api/nl-rule` | Generate rule from natural language | `llm/rule_generator.py` |
| POST | `/api/ingest` | Upload file (CSV/JSON/XLSX) | pandas, openpyxl, DB: Service, Table, TableProfile |
| POST | `/api/profile` | Profile a table's data | `profiling/profiler.py`, DB: TableProfile |
| GET | `/api/profile` | Get profile for a table | DB: TableProfile |
| POST | `/api/ai/generate-rule` | AI rule generation | `llm/rule_generator.py` |
| POST | `/api/ai/generate-report` | AI report generation | `llm/report_generator.py` |
| POST | `/api/ai/generate-fix` | AI fix suggestion generation | `llm/fix_generator.py` |
| POST | `/api/run-rules` | Run multiple rules | `engine/rule_executor.py` |
| GET | `/api/transforms/list` | List available transformations | `transformations/` |
| POST | `/api/transforms/execute` | Execute a transformation | `transformations/`, `engine/rule_executor.py` |
| GET | `/api/transforms/history/{tableId}` | Get transform history | DB: TransformHistory |
| POST | `/api/transforms/rollback` | Rollback a transformation | `transformations/history.py` |
| GET | `/api/pipelines` | List pipelines | DB: Pipeline |
| POST | `/api/pipelines` | Create a pipeline | DB: Pipeline |
| GET | `/api/pipelines/{pid}` | Get pipeline details | DB: Pipeline |
| PUT | `/api/pipelines/{pid}` | Update a pipeline | DB: Pipeline |
| DELETE | `/api/pipelines/{pid}` | Delete a pipeline | DB: Pipeline |
| POST | `/api/pipelines/{pid}/run` | Execute a pipeline | `transformations/pipeline.py`, DB: PipelineRun |
| GET | `/api/pipelines/{pid}/runs` | List pipeline runs | DB: PipelineRun |
| POST | `/api/auto-eda` | Generate EDA report | `eda/auto_eda.py`, DB: AutoEDARport |
| GET | `/api/auto-eda/{tableId}` | Get EDA report | DB: AutoEDARport |
| POST | `/api/auto-fix/propose` | Propose auto-fix | `llm/fix_generator.py`, DB: FixApproval |
| GET | `/api/auto-fix/pending` | List pending fixes | DB: FixApproval |
| POST | `/api/auto-fix/{fix_id}/approve` | Approve a fix | DB: FixApproval |
| POST | `/api/auto-fix/{fix_id}/reject` | Reject a fix | DB: FixApproval |
| POST | `/api/auto-fix/{fix_id}/apply` | Apply an approved fix | `transformations/`, DB: FixApproval |
| GET | `/api/connectors/sources` | List connector types | `connectors/data_connectors.py` |
| GET | `/api/connectors` | List connectors | DB: Connector |
| POST | `/api/connectors` | Create a connector | DB: Connector |
| POST | `/api/connectors/{cid}/test` | Test connector connection | `connectors/data_connectors.py` |
| POST | `/api/connectors/{cid}/fetch` | Fetch data from connector | `connectors/data_connectors.py` |
| DELETE | `/api/connectors/{cid}` | Delete a connector | DB: Connector |
| GET | `/api/schedules` | List scheduled jobs | DB: ScheduledJob |
| POST | `/api/schedules` | Create a scheduled job | DB: ScheduledJob |
| PUT | `/api/schedules/{sid}` | Update a scheduled job | DB: ScheduledJob |
| DELETE | `/api/schedules/{sid}` | Delete a scheduled job | DB: ScheduledJob |
| POST | `/api/schedules/{sid}/run` | Manually trigger a job | DB: ScheduledJob |
| POST | `/api/ml-readiness` | Score ML readiness | `ml_readiness/scorer.py`, DB: MLReadinessScore |
| GET | `/api/ml-readiness/{tableId}` | Get ML readiness score | DB: MLReadinessScore |
| POST | `/api/copilot/chat` | Chat with AI copilot | `copilot/engine.py`, DB: CopilotChat |
| GET | `/api/copilot/suggestions/{tableId}` | Get copilot suggestions | `copilot/engine.py` |
| GET | `/api/statistical/tests` | List available stat tests | `statistical/tests.py` |
| POST | `/api/statistical/run` | Run a statistical test | `statistical/tests.py`, DB: StatisticalTest |
| GET | `/api/statistical/results/{tableId}` | Get stat test results | DB: StatisticalTest |
| GET | `/api/contracts` | List data contracts | DB: DataContract |
| POST | `/api/contracts` | Create a data contract | DB: DataContract |
| POST | `/api/contracts/{cid}/validate` | Validate a contract | `contracts/validator.py`, DB: ContractValidation |
| GET | `/api/contracts/{cid}/validations` | Get contract validations | DB: ContractValidation |
| DELETE | `/api/contracts/{cid}` | Delete a contract | DB: DataContract |
| POST | `/api/forecast/{tableId}` | Generate quality forecast | `forecasting/engine.py` |
| GET | `/api/forecast/{tableId}` | Get quality forecast | `forecasting/engine.py` |
| GET | `/api/sql/databases` | List SQL playground databases | File system: db/*.db |
| GET | `/api/sql/tables` | List tables in a database | SQLite PRAGMA |
| POST | `/api/sql/query` | Execute SQL query | SQLite direct query |
| GET | `/api/anomaly` | List anomaly detection results | DB: QualityCheck (anomaly type) |

---

## 8. Next.js Frontend — Complete Reference

### Entry Point: `src/app/page.tsx`

This is a **Single Page Application** with:
- **22 views** managed by Zustand store's `currentView` state
- All views are lazy-loaded with `React.lazy()` for code splitting
- `ViewRenderer` component switches on `currentView` to render the active view
- `Sidebar` component provides navigation
- Header shows current view name + search bar

### Zustand Store: `src/lib/store.ts`

```typescript
ViewType = 'overview' | 'services' | 'tables' | 'ingest' | 'quality' | 'checks' |
           'lineage' | 'governance' | 'activity' | 'alerts' | 'settings' | 'pipeline' |
           'auto-eda' | 'auto-fix' | 'ml-readiness' | 'connectors' | 'scheduler' |
           'copilot' | 'statistical' | 'contracts' | 'forecasting' | 'sql-playground'

AppState = {
  currentView: ViewType (default: 'overview')
  sidebarOpen: boolean (default: true)
}
```

Shared TypeScript interfaces: `Dataset`, `QualityRule`, `QualityCheck`, `Alert`, `ComplianceReport`

### API Route Proxy Pattern

Every Next.js API route follows one of these patterns:

**Pattern 1: Simple GET Proxy** (most routes)
```typescript
const BACKEND = 'http://localhost:3001/api'
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const qs = searchParams.toString()
  const path = request.nextUrl.pathname.replace(/^\/api/, '')
  const url = `${BACKEND}${path}${qs ? '?' + qs : ''}`
  try {
    const res = await fetch(url)
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 502 })
  }
}
```

**Pattern 2: POST Proxy with JSON body**
```typescript
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const res = await fetch(`${BACKEND}/endpoint`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 502 })
  }
}
```

**Pattern 3: Multipart File Upload Proxy** (ingest only)
```typescript
export async function POST(request: NextRequest) {
  const contentType = request.headers.get('content-type') || ''
  const bodyBuffer = await request.arrayBuffer()
  const headers = {}
  if (contentType) headers['content-type'] = contentType
  const res = await fetch(`${BACKEND_URL}/api/ingest`, {
    method: 'POST',
    headers,
    body: bodyBuffer,
  })
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
```

**ALL routes return 502 with "Backend unavailable" when the Python backend is down.**

---

## 9. API Route Proxy Map

Every Next.js API route maps 1:1 to a Python backend endpoint:

| Next.js Route File | Frontend Path | Backend Endpoint |
|---|---|---|
| `api/route.ts` | `GET /api` | `GET http://localhost:3001/api/` |
| `api/stats/route.ts` | `GET /api/stats` | `GET http://localhost:3001/api/stats` |
| `api/services/route.ts` | `GET/POST /api/services` | `GET/POST http://localhost:3001/api/services` |
| `api/services/[id]/route.ts` | `GET/PUT/DELETE /api/services/:id` | Same path on port 3001 |
| `api/tables/route.ts` | `GET /api/tables` | `GET http://localhost:3001/api/tables` |
| `api/tables/[id]/route.ts` | `GET /api/tables/:id` | Same on port 3001 |
| `api/quality/route.ts` | `GET /api/quality` | Same on port 3001 |
| `api/quality/results/route.ts` | `GET /api/quality/results` | Same on port 3001 |
| `api/rules/route.ts` | `GET/POST /api/rules` | Same on port 3001 |
| `api/rules/[id]/route.ts` | `PUT/DELETE /api/rules/:id` | Same on port 3001 |
| `api/checks/route.ts` | `GET /api/checks` | Same on port 3001 |
| `api/run-check/route.ts` | `POST /api/run-check` | Same on port 3001 |
| `api/lineage/route.ts` | `GET /api/lineage` | Same on port 3001 |
| `api/alerts/route.ts` | `GET/PUT /api/alerts` | Same on port 3001 |
| `api/tags/route.ts` | `GET/POST /api/tags` | Same on port 3001 |
| `api/glossary/route.ts` | `GET/POST /api/glossary` | Same on port 3001 |
| `api/teams/route.ts` | `GET /api/teams` | Same on port 3001 |
| `api/activity/route.ts` | `GET /api/activity` | Same on port 3001 |
| `api/search/route.ts` | `GET /api/search` | Same on port 3001 |
| `api/compliance/route.ts` | `GET /api/compliance` | Same on port 3001 |
| `api/datasets/route.ts` | `GET/POST /api/datasets` | Same on port 3001 |
| `api/datasets/[id]/route.ts` | `GET/PUT/DELETE /api/datasets/:id` | Same on port 3001 |
| `api/ingest/route.ts` | `POST /api/ingest` | Same on port 3001 |
| `api/profile/route.ts` | `GET/POST /api/profile` | Same on port 3001 |
| `api/nl-rule/route.ts` | `POST /api/nl-rule` | Same on port 3001 |
| `api/ai/generate-report/route.ts` | `POST /api/ai/generate-report` | Same on port 3001 |
| `api/ai/generate-fix/route.ts` | `POST /api/ai/generate-fix` | Same on port 3001 |
| `api/anomaly/route.ts` | `GET /api/anomaly` | Same on port 3001 |
| `api/transforms/route.ts` | `GET/POST /api/transforms` | Same on port 3001 |
| `api/transforms/[...slug]/route.ts` | `Dynamic sub-paths` | Same on port 3001 |
| `api/pipelines/route.ts` | `GET/POST /api/pipelines` | Same on port 3001 |
| `api/pipelines/[id]/route.ts` | `GET/PUT/DELETE /api/pipelines/:id` | Same on port 3001 |
| `api/pipelines/[id]/run/route.ts` | `POST /api/pipelines/:id/run` | Same on port 3001 |
| `api/pipelines/runs/route.ts` | `GET /api/pipelines/runs` | Same on port 3001 |
| `api/auto-eda/route.ts` | `POST/GET /api/auto-eda` | Same on port 3001 |
| `api/ml-readiness/route.ts` | `POST/GET /api/ml-readiness` | Same on port 3001 |
| `api/connectors/route.ts` | `GET/POST /api/connectors` | Same on port 3001 |
| `api/connectors/[id]/route.ts` | `DELETE /api/connectors/:id` | Same on port 3001 |
| `api/connectors/[id]/test/route.ts` | `POST /api/connectors/:id/test` | Same on port 3001 |
| `api/connectors/[id]/fetch/route.ts` | `POST /api/connectors/:id/fetch` | Same on port 3001 |
| `api/schedules/route.ts` | `GET/POST /api/schedules` | Same on port 3001 |
| `api/schedules/[id]/route.ts` | `PUT/DELETE /api/schedules/:id` | Same on port 3001 |
| `api/schedules/[id]/run/route.ts` | `POST /api/schedules/:id/run` | Same on port 3001 |
| `api/copilot/route.ts` | `POST/GET /api/copilot` | Same on port 3001 |
| `api/statistical/route.ts` | `GET/POST /api/statistical` | Same on port 3001 |
| `api/contracts/route.ts` | `GET/POST /api/contracts` | Same on port 3001 |
| `api/contracts/[id]/route.ts` | `DELETE /api/contracts/:id` | Same on port 3001 |
| `api/contracts/[id]/validate/route.ts` | `POST /api/contracts/:id/validate` | Same on port 3001 |
| `api/forecast/route.ts` | `GET/POST /api/forecast` | Same on port 3001 |
| `api/sql/route.ts` | `GET /api/sql` | Same on port 3001 |
| `api/sql/databases/route.ts` | `GET /api/sql/databases` | Same on port 3001 |
| `api/sql/tables/route.ts` | `GET /api/sql/tables` | Same on port 3001 |
| `api/sql/query/route.ts` | `POST /api/sql/query` | Same on port 3001 |
| `api/auto-fix/route.ts` | `GET/POST /api/auto-fix` | Same on port 3001 |
| `api/auto-fix/[fixId]/approve/route.ts` | `POST /api/auto-fix/:fixId/approve` | Same on port 3001 |
| `api/auto-fix/[fixId]/reject/route.ts` | `POST /api/auto-fix/:fixId/reject` | Same on port 3001 |
| `api/auto-fix/[fixId]/apply/route.ts` | `POST /api/auto-fix/:fixId/apply` | Same on port 3001 |

---

## 10. Frontend Component → API → Backend Endpoint Map

This is the most critical section for debugging. When a user reports a bug in a specific view, trace the issue through this chain:

### Overview (`overview.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| Page load | `fetch('/api/stats')` | `api/stats/route.ts` | `GET /api/stats` |

### Dashboard (`dashboard.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| Page load | `fetch('/api/stats')` | `api/stats/route.ts` | `GET /api/stats` |
| Page load | `fetch('/api/checks?limit=5')` | `api/checks/route.ts` | `GET /api/checks` |
| Page load | `fetch('/api/alerts?status=active')` | `api/alerts/route.ts` | `GET /api/alerts` |

### Services (`services.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| List services | `fetch('/api/services')` | `api/services/route.ts` | `GET /api/services` |

### Tables (`tables.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| List tables | `fetch('/api/tables?...')` | `api/tables/route.ts` | `GET /api/tables` |

### Ingest (`ingest.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| List existing tables | `fetch('/api/tables?sort=name&limit=50')` | `api/tables/route.ts` | `GET /api/tables` |
| Upload file | `fetch('/api/ingest', {method:'POST', body:formData})` | `api/ingest/route.ts` | `POST /api/ingest` |

### Quality (`quality.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| Load rules + checks + datasets | `fetch('/api/rules')` + `fetch('/api/checks?limit=20')` + `fetch('/api/datasets')` | Multiple | Multiple |
| Create NL rule | `fetch('/api/nl-rule', {method:'POST', body})` | `api/nl-rule/route.ts` | `POST /api/nl-rule` |
| Run check | `fetch('/api/run-check', {method:'POST', body})` | `api/run-check/route.ts` | `POST /api/run-check` |
| Generate AI report | `fetch('/api/ai/generate-report', {method:'POST'})` | `api/ai/generate-report/route.ts` | `POST /api/ai/generate-report` |
| Generate AI fix | `fetch('/api/ai/generate-fix', {method:'POST'})` | `api/ai/generate-fix/route.ts` | `POST /api/ai/generate-fix` |
| Toggle rule | `fetch('/api/rules/${ruleId}', {method:'PUT'})` | `api/rules/[id]/route.ts` | `PUT /api/rules/{rid}` |
| Delete rule | `fetch('/api/rules/${ruleId}', {method:'DELETE'})` | `api/rules/[id]/route.ts` | `DELETE /api/rules/{rid}` |

### Checks (`checks.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| List checks | `fetch('/api/checks?...')` | `api/checks/route.ts` | `GET /api/checks` |
| Load datasets | `fetch('/api/datasets')` | `api/datasets/route.ts` | `GET /api/datasets` |

### Rules (`rules.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| List rules | `fetch('/api/rules')` | `api/rules/route.ts` | `GET /api/rules` |
| Load datasets | `fetch('/api/datasets')` | `api/datasets/route.ts` | `GET /api/datasets` |
| Toggle rule | `fetch('/api/rules/${ruleId}', {method:'PUT'})` | `api/rules/[id]/route.ts` | `PUT /api/rules/{rid}` |
| Delete rule | `fetch('/api/rules/${ruleId}', {method:'DELETE'})` | `api/rules/[id]/route.ts` | `DELETE /api/rules/{rid}` |
| Create NL rule | `fetch('/api/nl-rule', {method:'POST'})` | `api/nl-rule/route.ts` | `POST /api/nl-rule` |

### Lineage (`lineage.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| Load lineage | `fetch('/api/lineage')` | `api/lineage/route.ts` | `GET /api/lineage` |

### Governance (`governance.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| Load tags + glossary | `fetch('/api/tags')` + `fetch('/api/glossary')` | Multiple | Multiple |

### Activity (`activity.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| Load activity | `fetch('/api/activity?limit=50')` | `api/activity/route.ts` | `GET /api/activity` |

### Alerts (`alerts.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| List alerts | `fetch('/api/alerts?...')` | `api/alerts/route.ts` | `GET /api/alerts` |
| Resolve alert | `fetch('/api/alerts', {method:'PUT', body})` | `api/alerts/route.ts` | `PUT /api/alerts` |

### Settings (`settings.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| Load teams | `fetch('/api/teams')` | `api/teams/route.ts` | `GET /api/teams` |

### Pipeline Builder (`pipeline-builder.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| Load pipelines + runs + datasets | `fetch('/api/pipelines')` + `fetch('/api/pipelines/runs')` + `fetch('/api/datasets')` | Multiple | Multiple |
| Create pipeline | `fetch('/api/pipelines', {method:'POST'})` | `api/pipelines/route.ts` | `POST /api/pipelines` |
| Run pipeline | `fetch('/api/pipelines/${id}/run', {method:'POST'})` | `api/pipelines/[id]/run/route.ts` | `POST /api/pipelines/{pid}/run` |
| Delete pipeline | `fetch('/api/pipelines/${id}', {method:'DELETE'})` | `api/pipelines/[id]/route.ts` | `DELETE /api/pipelines/{pid}` |

### Auto-EDA (`auto-eda.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| Load tables | `fetch('/api/tables')` | `api/tables/route.ts` | `GET /api/tables` |
| Generate/view EDA | `fetch('/api/auto-eda/${tableId}')` | `api/auto-eda/route.ts` | `GET /api/auto-eda/{tableId}` |

### ML Readiness (`ml-readiness.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| Load tables | `fetch('/api/tables')` | `api/tables/route.ts` | `GET /api/tables` |
| Score readiness | `fetch('/api/ml-readiness/${tableId}')` | `api/ml-readiness/route.ts` | `GET /api/ml-readiness/{tableId}` |

### Connectors (`connectors.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| List connectors | `fetch('/api/connectors')` | `api/connectors/route.ts` | `GET /api/connectors` |
| Create connector | `fetch('/api/connectors', {method:'POST'})` | `api/connectors/route.ts` | `POST /api/connectors` |
| Test connection | `fetch('/api/connectors/${id}/test', {method:'POST'})` | `api/connectors/[id]/test/route.ts` | `POST /api/connectors/{cid}/test` |
| Fetch data | `fetch('/api/connectors/${id}/fetch', {method:'POST'})` | `api/connectors/[id]/fetch/route.ts` | `POST /api/connectors/{cid}/fetch` |
| Delete connector | `fetch('/api/connectors/${id}', {method:'DELETE'})` | `api/connectors/[id]/route.ts` | `DELETE /api/connectors/{cid}` |

### Scheduler (`scheduler.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| List jobs | `fetch('/api/schedules')` | `api/schedules/route.ts` | `GET /api/schedules` |
| Create job | `fetch('/api/schedules', {method:'POST'})` | `api/schedules/route.ts` | `POST /api/schedules` |
| Update job | `fetch('/api/schedules/${id}', {method:'PUT'})` | `api/schedules/[id]/route.ts` | `PUT /api/schedules/{sid}` |
| Delete job | `fetch('/api/schedules/${id}', {method:'DELETE'})` | `api/schedules/[id]/route.ts` | `DELETE /api/schedules/{sid}` |
| Run job manually | `fetch('/api/schedules/${id}/run', {method:'POST'})` | `api/schedules/[id]/run/route.ts` | `POST /api/schedules/{sid}/run` |

### Copilot (`copilot.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| Load tables | `fetch('/api/tables')` | `api/tables/route.ts` | `GET /api/tables` |
| Send chat message | `fetch('/api/copilot/chat', {method:'POST'})` | `api/copilot/route.ts` | `POST /api/copilot/chat` |

### Statistical Tests (`statistical-tests.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| Load tables | `fetch('/api/tables')` | `api/tables/route.ts` | `GET /api/tables` |
| Load results | `fetch('/api/statistical/results/${tableName}')` | `api/statistical/route.ts` | `GET /api/statistical/results/{tableId}` |
| Run test | `fetch('/api/statistical/run', {method:'POST'})` | `api/statistical/route.ts` | `POST /api/statistical/run` |

### Data Contracts (`data-contracts.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| List contracts | `fetch('/api/contracts')` | `api/contracts/route.ts` | `GET /api/contracts` |
| Create contract | `fetch('/api/contracts', {method:'POST'})` | `api/contracts/route.ts` | `POST /api/contracts` |
| Validate contract | `fetch('/api/contracts/${id}/validate', {method:'POST'})` | `api/contracts/[id]/validate/route.ts` | `POST /api/contracts/{cid}/validate` |
| Delete contract | `fetch('/api/contracts/${id}', {method:'DELETE'})` | `api/contracts/[id]/route.ts` | `DELETE /api/contracts/{cid}` |

### Forecasting (`forecasting.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| Load tables | `fetch('/api/tables')` | `api/tables/route.ts` | `GET /api/tables` |
| Get forecast | `fetch('/api/forecast/${tableId}')` | `api/forecast/route.ts` | `GET /api/forecast/{tableId}` |

### SQL Playground (`sql-playground.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| List databases | `fetch('/api/sql/databases')` | `api/sql/databases/route.ts` | `GET /api/sql/databases` |
| List tables in DB | `fetch('/api/sql/tables?database=...')` | `api/sql/tables/route.ts` | `GET /api/sql/tables` |
| Execute query | `fetch('/api/sql/query', {method:'POST', body})` | `api/sql/query/route.ts` | `POST /api/sql/query` |

### Auto-Fix (`auto-fix.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| List pending fixes | `fetch('/api/auto-fix/pending')` | `api/auto-fix/route.ts` | `GET /api/auto-fix/pending` |
| Approve fix | `fetch('/api/auto-fix/${id}/approve', {method:'POST'})` | `api/auto-fix/[fixId]/approve/route.ts` | `POST /api/auto-fix/{fix_id}/approve` |
| Reject fix | `fetch('/api/auto-fix/${id}/reject', {method:'POST'})` | `api/auto-fix/[fixId]/reject/route.ts` | `POST /api/auto-fix/{fix_id}/reject` |
| Apply fix | `fetch('/api/auto-fix/${id}/apply', {method:'POST'})` | `api/auto-fix/[fixId]/apply/route.ts` | `POST /api/auto-fix/{fix_id}/apply` |

### Anomalies (`anomalies.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| List anomalies | `fetch('/api/anomaly')` | `api/anomaly/route.ts` | `GET /api/anomaly` |

### Compliance (`compliance.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| Load compliance | `fetch('/api/compliance')` | `api/compliance/route.ts` | `GET /api/compliance` |

### Profile Viewer (`profile-viewer.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| Load profiles | `fetch('/api/profile')` | `api/profile/route.ts` | `GET /api/profile` |

### Datasets (`datasets.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| List datasets | `fetch('/api/datasets')` | `api/datasets/route.ts` | `GET /api/datasets` |
| Create dataset | `fetch('/api/datasets', {method:'POST'})` | `api/datasets/route.ts` | `POST /api/datasets` |
| Delete dataset | `fetch('/api/datasets/${id}', {method:'DELETE'})` | `api/datasets/[id]/route.ts` | `DELETE /api/datasets/{did}` |

### AI Rule Builder (`ai-rule-builder.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| Generate rule from NL | `fetch('/api/nl-rule', {method:'POST'})` | `api/nl-rule/route.ts` | `POST /api/nl-rule` |

### Fix Suggestion (`fix-suggestion.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| Generate fix | `fetch('/api/ai/generate-fix', {method:'POST'})` | `api/ai/generate-fix/route.ts` | `POST /api/ai/generate-fix` |

### Quality Report (`quality-report.tsx`)
| User Action | Frontend Fetch | Next.js API Route | Python Backend |
|---|---|---|---|
| Generate report | `fetch('/api/ai/generate-report', {method:'POST'})` | `api/ai/generate-report/route.ts` | `POST /api/ai/generate-report` |

---

## 11. Python Backend Module Deep-Dive

### 11.1 Checks Engine (`checks/`)

**Registry Pattern:**
```
checks/__init__.py → get_check(check_type) → returns check class
```

**Check Types and Aliases:**
| Canonical Type | Class | Aliases |
|---|---|---|
| `completeness` | `CompletenessCheck` | `missing`, `not_null` |
| `uniqueness` | `UniquenessCheck` | `unique`, `duplicate` |
| `validity` | `ValidityCheck` | `valid_values`, `regex`, `range` |
| `freshness` | `FreshnessCheck` | `timeliness` |
| `schema` | `SchemaCheck` | `schema_change` |
| `volume` | `VolumeCheck` | `row_count` |
| `anomaly` | `AnomalyCheck` | `outlier`, `drift`, `zscore` |

**Execution Chain:**
```
POST /api/run-check
  → index.py: run_check()
    → DB: load QualityRule
    → DB: load Dataset → find matching Table
    → engine/rule_executor.py: load_dataframe(table_id)
      → Reads data/{table_id}.csv (or .json/.xlsx)
    → engine/rule_executor.py: execute_rule(rule, df, table_name)
      → checks/__init__.py: get_check(rule.type)
      → CheckClass.execute(df, config, rule_id, table_name, column_name)
      → Returns CheckResult
    → If no DataFrame: execute_profile_check(rule, profile_data, table_name)
    → If no profile: random simulated result (LEGACY)
    → DB: Save QualityCheck record
    → If failed: DB: Create Alert
    → DB: Update QualityRule.lastTriggered
    → DB: Recalculate Dataset.qualityScore
```

### 11.2 LLM Client (`llm/client.py`)

**Multi-Provider Fallback:**
```
call_llm(system_prompt, user_prompt)
  → Provider 1 (primary): LLM_API_KEY + LLM_BASE_URL + LLM_MODEL
  → Provider 2 (fallback_1): LLM_FALLBACK_1_API_KEY + ...
  → Provider 3 (fallback_2): LLM_FALLBACK_2_API_KEY + ...
  → ... up to 5 fallbacks
  → If ALL fail: returns None (caller handles fallback)
```

**Provider Call:** Uses `urllib.request` (no OpenAI SDK dependency for HTTP) to call OpenAI-compatible chat completions API.

**JSON Extraction:** `extract_json()` handles markdown code blocks, nested objects, escaped newlines.

### 11.3 Rule Generator (`llm/rule_generator.py`)

**Flow:**
```
generate(prompt, dataset_id, table_name, columns_info)
  → If LLM_API_KEY exists:
    → _llm_generate(): Call LLM with prompts.py templates
    → Parse response → extract rule type, severity, column, config
    → _infer_from_prompt(): Post-process to fill missing min/max values
    → If LLM succeeds: return rule with generationMethod="llm"
  → Fallback: _keyword_generate()
    → Keyword matching: "null" → completeness, "unique" → uniqueness, etc.
    → _detect_column(): Match column names from columns_info
    → Return rule with generationMethod="keyword"
```

### 11.4 Fix Generator (`llm/fix_generator.py`)

**Flow:**
```
generate(rule, check_result, table_name, columns_info)
  → If LLM available:
    → Call LLM with fix generation prompts
    → Parse response → extract fix code, explanation, transform type
    → Return fix with generationMethod="llm"
  → Fallback: Template-based fix suggestions
    → Match check type to known fix templates
    → Return fix with generationMethod="template"
```

### 11.5 Report Generator (`llm/report_generator.py`)

**Flow:**
```
generate(check_results, table_name, quality_score)
  → If LLM available:
    → Call LLM with report generation prompts
    → Parse response → extract summary, diagnosis, action plan
    → Return report with generationMethod="llm"
  → Fallback: Template-based report
    → Aggregate check results into sections
    → Return report with generationMethod="template"
```

### 11.6 Copilot Engine (`copilot/engine.py`)

**Two Modes:**

1. **Chat Mode:** `chat(message, table_context)`
   - If LLM available: Send system prompt + user message → parse JSON response
   - Fallback: `_heuristic_chat()` — keyword-based intent detection → predefined responses
   - Returns: `{ message, suggested_actions, generation_method }`

2. **Suggestions Mode:** `get_suggestions(profile_data, check_results, table_name)`
   - If LLM available: Send context → parse suggestions JSON
   - Fallback: `_heuristic_suggestions()` — rule-based analysis of check results + profile
   - Returns: Array of suggestion objects

**Heuristic Suggestion Priority:**
1. Failed completeness checks → imputation suggestion
2. Failed uniqueness checks → dedup suggestion
3. Failed validity checks → quality rule suggestion
4. Columns with >5% missing → imputation
5. Categorical columns → encoding
6. Highly skewed numeric columns → outlier handling
7. Small dataset → data augmentation
8. After encoding → train/test split

### 11.7 Auto EDA (`eda/auto_eda.py`)

**Report Sections:**
| Section | Method | Output |
|---|---|---|
| Overview | `_overview()` | Row/column count, missing %, duplicates, memory |
| Column Profiles | `_column_profiles()` | Per-column: dtype, null %, unique, mean/std/min/max, top values |
| Correlations | `_correlations()` | Pearson correlation matrix, high correlations (>0.7) |
| Missing Analysis | `_missing_analysis()` | Columns with missing values, counts and percentages |
| Distribution | `_distribution_analysis()` | Histograms, skewness, kurtosis, Shapiro-Wilk normality test |
| Outliers | `_outlier_summary()` | IQR outliers, z-score outliers, fences |
| Insights | `_auto_insights()` | Auto-generated warnings: high missing, duplicates, high cardinality, multicollinearity, zero variance |
| Warnings | `_warnings()` | Critical: empty dataset, entirely null columns |

### 11.8 ML Readiness (`ml_readiness/scorer.py`)

**7 Dimensions:**
| Dimension | Weight | What It Checks |
|---|---|---|
| Completeness | 25% | Missing values rate, per-column missing |
| Feature Quality | 20% | Zero-variance columns, ID-like columns |
| Encoding Needed | 15% | Categorical columns requiring encoding |
| Distribution | 15% | Highly skewed numeric columns |
| Target Suitability | 10% | Target column missing, class imbalance |
| Data Size | 10% | Row count, column count |
| Multicollinearity | 5% | High correlation between numeric features |

**Grading:** A (90+), B (80+), C (70+), D (60+), F (<60)

### 11.9 Statistical Tests (`statistical/tests.py`)

**8 Tests:**
| Test | Purpose | Required Config |
|---|---|---|
| `t_test` | Compare means of two groups | `column` + `group_column` OR `column1` + `column2` |
| `chi_square` | Test independence of categorical variables | `column1` + `column2` |
| `anova` | Compare means across multiple groups | `value_column` + `group_column` |
| `ks_test` | Test if data follows a distribution | `column` + optional `distribution` |
| `mann_whitney` | Non-parametric comparison of two groups | `column` + `group_column` OR `column1` + `column2` |
| `pearson` | Linear correlation | `column1` + `column2` |
| `spearman` | Rank correlation | `column1` + `column2` |
| `normality` | Test normal distribution | `column` |

All tests use `scipy.stats` and return: `{ success, test_type, statistic, p_value, significant, conclusion }`

### 11.10 Connectors (`connectors/data_connectors.py`)

**5 Connector Types:**
| Type | Test Connection | Fetch Data | Extra Dependencies |
|---|---|---|---|
| PostgreSQL | `psycopg2.connect()` | `pd.read_sql()` | `psycopg2-binary` |
| MySQL | `pymysql.connect()` | `pd.read_sql()` | `pymysql` |
| S3 | `boto3.client.head_bucket()` | `s3.get_object()` → pandas | `boto3` |
| BigQuery | Stub (not implemented) | N/A | `google-cloud-bigquery` |
| SQLite | `sqlite3.connect()` + `SELECT 1` | `pd.read_sql()` | Built-in |

### 11.11 Data Contracts (`contracts/validator.py`)

**Validation Types:**
- Schema validation: Check required columns exist with correct types
- Column rules: Check value ranges, regex patterns, null constraints
- Row-level rules: Custom validation logic per row
- Freshness: Check data recency against threshold
- Unique keys: Verify unique constraint on specified columns

### 11.12 Forecasting (`forecasting/engine.py`)

**3 Forecasting Methods:**
| Method | Description |
|---|---|
| Simple Moving Average (SMA) | Average of last N scores |
| Exponential Smoothing | Weighted average with trend projection |
| Linear Trend | Polynomial fit (degree 1) projection |

**Output:** Trend direction, predicted score, degradation risk assessment

### 11.13 Transformations (`transformations/`)

**10 Transformers:**
| Transformer | Purpose | Methods |
|---|---|---|
| `imputation.py` | Fill missing values | mean, median, mode, forward_fill, constant |
| `outlier.py` | Handle outliers | iqr, zscore, percentile, winsorize |
| `dedup.py` / `deduplication.py` | Remove duplicates | keep_first, keep_last, keep_none |
| `encoding.py` | Encode categoricals | one_hot, label, ordinal, target |
| `normalization.py` | Scale features | standard, minmax, robust |
| `string_clean.py` | Clean strings | trim, lowercase, uppercase, remove_special, strip_html |
| `date_parser.py` | Parse dates | auto, iso8601, us_format, eu_format |
| `data_split.py` | Split data | random, stratified, temporal |
| `type_conversion.py` | Convert types | to_numeric, to_string, to_datetime, to_category |

**Pipeline Builder:** `pipeline.py` — DAG-based pipeline using NetworkX, supports conditional execution

**History & Rollback:** `history.py` — Saves snapshots before transforms, supports rollback to previous state

**Two Base Classes:**
- `base_transform.py` (NEWER): Has snapshot support, used by newer transformers
- `base_transformer.py` (OLDER): Legacy base class, used by some older transformers

---

## 12. Data Flow Diagrams

### 12.1 File Upload Flow
```
User drops CSV/JSON/XLSX file
  → ingest.tsx: fetch('/api/ingest', {method:'POST', body:formData})
    → api/ingest/route.ts: Forward multipart body to Python backend
      → Python POST /api/ingest:
        1. Parse file with pandas (CSV/JSON/XLSX)
        2. Validate: size ≤100MB, columns ≤1000, rows ≤10M
        3. Generate table ID (uuid)
        4. Save DataFrame → data/{table_id}.csv
        5. Create Service record in DB (if new service)
        6. Create Table record in DB (name, columns, row count, serviceId)
        7. Profile columns → Create TableProfile record in DB
        8. Create Activity record in DB
        9. Return {success, tableId, tableName, rowCount, columnCount, columns}
```

### 12.2 Quality Check Execution Flow
```
User clicks "Run Check" on a rule
  → quality.tsx: fetch('/api/run-check', {method:'POST', body:{ruleId}})
    → api/run-check/route.ts → Python POST /api/run-check
      1. Load QualityRule from DB
      2. Load Dataset from DB (via rule.datasetId)
      3. Find matching Table record (by dataset name)
      4. Try load_dataframe(table_id) → data/{table_id}.csv
         ├─ DataFrame found → execute_rule(rule, df, table_name)
         │   → get_check(rule.type) → CheckClass.execute(df, config)
         │   → Returns REAL CheckResult
         ├─ No DataFrame → Try profile-based estimation
         │   → Load TableProfile from DB
         │   → execute_profile_check(rule, profile_data, table_name)
         │   → Returns ESTIMATED CheckResult
         └─ No profile → Random simulated result (LEGACY)
      5. Save QualityCheck record to DB
      6. If status="failed" → Create Alert record
      7. Update QualityRule.lastTriggered
      8. Recalculate Dataset.qualityScore (avg of last 10 checks)
      9. Return {check, ruleName, datasetName, alertCreated, executionMode}
```

### 12.3 NL Rule Generation Flow
```
User types "email column should not be null" → clicks Generate
  → quality.tsx: fetch('/api/nl-rule', {method:'POST', body:{prompt,...}})
    → api/nl-rule/route.ts → Python POST /api/nl-rule
      → llm/rule_generator.py: generate(prompt, dataset_id, table_name, columns_info)
        ├─ LLM_API_KEY exists:
        │   → call_llm(RULE_SYSTEM, RULE_USER, temperature=0.2)
        │   → Parse JSON response → extract type, severity, column, config
        │   → _infer_from_prompt(): Fill missing min/max from prompt text
        │   → Return rule with generationMethod="llm"
        └─ No LLM key:
            → _keyword_generate(): Match keywords to rule types
            → "null" → completeness, "unique" → uniqueness, etc.
            → _detect_column(): Find column name in prompt text
            → Return rule with generationMethod="keyword"
      → DB: Create QualityRule record
      → Return rule definition
```

### 12.4 SQL Playground Flow
```
User selects database from dropdown
  → sql-playground.tsx: fetch('/api/sql/databases')
    → Python GET /api/sql/databases → Scans db/*.db files

User selects table from dropdown
  → sql-playground.tsx: fetch('/api/sql/tables?database=cities')
    → Python GET /api/sql/tables → SQLite PRAGMA table_list

User writes and executes SQL
  → sql-playground.tsx: fetch('/api/sql/query', {method:'POST', body:{database, query}})
    → Python POST /api/sql/query
      → Connect to specified .db file
      → Execute query (SELECT only — DDL/DML blocked)
      → Return {columns, rows, rowCount, executionTime}
```

---

## 13. File Dependency Graph

### Python Backend Dependencies
```
index.py (main app)
  ├── config.py (DB_PATH, LLM settings, server config)
  ├── models/check_result.py (CheckResult, RunRulesRequest)
  ├── models/rule.py (CheckConfig, RuleCreate, NLRuleRequest)
  ├── models/quality_report.py (Report models)
  ├── engine/rule_executor.py
  │   ├── checks/__init__.py (get_check registry)
  │   │   ├── checks/base_check.py
  │   │   ├── checks/completeness_check.py
  │   │   ├── checks/uniqueness_check.py
  │   │   ├── checks/validity_check.py
  │   │   ├── checks/freshness_check.py
  │   │   ├── checks/schema_check.py
  │   │   ├── checks/volume_check.py
  │   │   └── checks/anomaly_check.py
  │   └── models/rule.py (CheckConfig)
  ├── engine/quality_scorer.py
  │   └── models/check_result.py
  ├── llm/rule_generator.py
  │   ├── llm/client.py (call_llm, extract_json)
  │   └── llm/prompts.py
  ├── llm/fix_generator.py
  │   ├── llm/client.py
  │   └── llm/prompts.py
  ├── llm/report_generator.py
  │   ├── llm/client.py
  │   └── llm/prompts.py
  ├── copilot/engine.py
  │   └── llm/client.py
  ├── eda/auto_eda.py
  ├── forecasting/engine.py
  ├── ml_readiness/scorer.py
  ├── statistical/tests.py
  ├── connectors/data_connectors.py
  ├── contracts/validator.py
  ├── scheduler/scheduler.py
  ├── profiling/profiler.py
  ├── transformations/imputation.py
  ├── transformations/outlier.py
  ├── transformations/dedup.py
  ├── transformations/encoding.py
  ├── transformations/normalization.py
  ├── transformations/string_clean.py
  ├── transformations/date_parser.py
  ├── transformations/data_split.py
  ├── transformations/type_conversion.py
  ├── transformations/pipeline.py
  │   └── NetworkX (DAG)
  ├── transformations/history.py
  └── db/connection.py (Database class — alternate DB wrapper)
```

### Frontend Dependencies
```
page.tsx (SPA shell)
  ├── lib/store.ts (Zustand store — ViewType, AppState)
  ├── components/dq/sidebar.tsx (Navigation)
  └── components/dq/[view].tsx (22 lazy-loaded views)
       ├── Each component uses fetch('/api/...')
       └── components/ui/* (shadcn/ui components)

layout.tsx (Root layout)
  ├── Geist fonts
  └── Sonner toaster

api/*/route.ts (40+ proxy routes)
  └── All forward to http://localhost:3001/api/...
```

---

## 14. Bug Fixing Guide — Where to Look

### Symptom: "Backend unavailable" (502 error)
**Cause:** Python backend is not running on port 3001
**Fix:** Start the Python backend:
```bash
cd mini-services/backend && source venv/bin/activate
python -m uvicorn index:app --host 0.0.0.0 --port 3001 --reload
```
**Files to check:**
- `mini-services/backend/index.py` — Is it running? Check for import errors
- `mini-services/backend/config.py` — Is DB_PATH correct?
- `api/*/route.ts` — Is BACKEND URL correct? Should be `http://localhost:3001/api`

### Symptom: Empty Overview/Dashboard after data upload
**Cause:** Stats endpoint returns zeros because metadata is not being created properly
**Debug chain:**
1. Check `GET /api/stats` response → Are counts zero?
2. Check `GET /api/tables` → Are tables showing?
3. Check `GET /api/services` → Are services showing?
4. If tables/services exist but stats still zero → Check Python backend DB queries
5. **Key file:** `mini-services/backend/index.py` → `get_stats()` function
6. **Key file:** `mini-services/backend/index.py` → `init_db()` — Are tables created correctly?

### Symptom: Quality check returns simulated results
**Cause:** DataFrame file missing from `data/` directory
**Debug chain:**
1. Check `data/` directory → Does `{table_id}.csv` exist?
2. Check `engine/rule_executor.py` → `load_dataframe()` — Is it finding the file?
3. Check ingest endpoint → Is `save_dataframe()` being called after upload?
4. **Key file:** `mini-services/backend/engine/rule_executor.py`
5. **Key file:** `mini-services/backend/index.py` → `POST /api/ingest`

### Symptom: NL rule generation returns keyword-based rules instead of LLM
**Cause:** LLM_API_KEY not set or LLM call failing
**Debug chain:**
1. Check `GET /api/llm-status` → Is LLM configured?
2. Check `mini-services/backend/config.py` → LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
3. Check `mini-services/backend/llm/client.py` → Provider list, fallback chain
4. Check backend logs for LLM errors
5. **Key file:** `mini-services/backend/llm/rule_generator.py`
6. **Key file:** `mini-services/backend/llm/client.py`

### Symptom: SQL Playground not working
**Cause:** Playground databases not seeded
**Fix:**
```bash
cd db && python seed_databases.py
```
**Debug chain:**
1. Check `GET /api/sql/databases` → Are .db files listed?
2. Check `db/` directory → Do cities.db, sales.db, hr.db exist?
3. **Key file:** `mini-services/backend/index.py` → SQL endpoints
4. **Key file:** `db/seed_databases.py`

### Symptom: File upload fails
**Cause:** Multipart proxy not forwarding correctly, or file too large
**Debug chain:**
1. Check `src/app/api/ingest/route.ts` → Is it proxying correctly?
2. Check Python backend logs → Is `POST /api/ingest` receiving the file?
3. Check file size limits: 100MB max, 1000 columns max, 10M rows max
4. **Key file:** `src/app/api/ingest/route.ts`
5. **Key file:** `mini-services/backend/index.py` → `POST /api/ingest`

### Symptom: "Table" SQL keyword error
**Cause:** SQLite reserved word — the Table entity is named "Table" (with quotes)
**Fix:** All SQL queries referencing the Table entity must use `"Table"` (double-quoted)
**Key file:** `mini-services/backend/index.py` → Any query with `"Table"`

### Symptom: Component not loading / blank page
**Cause:** React lazy import failing
**Debug chain:**
1. Open browser DevTools → Console → Check for import errors
2. Check `src/app/page.tsx` → React.lazy() import paths
3. Check the specific component file in `src/components/dq/`
4. Check for missing dependencies or syntax errors

### Symptom: Data not persisting across restarts
**Cause:** `data/` directory or `db/custom.db` being deleted
**Fix:** Ensure `data/` and `db/` directories are not in `.gitignore` or being cleaned
**Key files:** `data/*.csv`, `db/custom.db`

---

## 15. Known Issues & Technical Debt

### Critical Issues

1. **Monolithic index.py (2872 lines)** — Should be split into FastAPI routers for maintainability. Currently all 77+ endpoints are in one file.

2. **Dual Schema Definitions** — Python `init_db()` creates 27 tables with different column names than Node.js `schema.sql` (15 tables). The Node.js schema is still executed by `src/lib/db.ts` on startup, which can conflict with the Python schema.

3. **better-sqlite3 in API Routes** — `src/lib/db.ts` still exists and uses better-sqlite3. Some API routes may still import it. All must use Python backend proxy pattern exclusively.

4. **Stale supervisord.conf** — References `DataMonitor` directory instead of `my-project`.

5. **Multiple Start Scripts** — 5+ different start scripts with varying quality and some stale references.

### Schema Mismatches (Python vs Node.js)

| Table | Python Column | Node.js Column | Issue |
|---|---|---|---|
| Service | `serviceType` | `type` | Different names |
| Service | `connectionUrl` | `connection` | Different names |
| Service | `owner` | (missing) | Extra column in Python |
| Table | `"Table"` (quoted) | `Table_entity` | Different table names! |
| QualityRule | `type` | `ruleType` | Different names |
| QualityRule | `dimension` | (missing) | Extra column in Python |
| Alert | `message` | `description` | Different names |
| Alert | `alertType` | (same) | OK |
| Alert | `source` | `sourceType` + `sourceId` + `sourceName` | Split in Node.js |

### Security Issues

1. **No Authentication** — All APIs are open (CORS allows `*`)
2. **SQL Injection Risk** — Some dynamic SQL construction with f-strings in `index.py`
3. **SQL Playground** — DDL/DML should be blocked to prevent data corruption
4. **File Upload** — No virus scanning or content validation beyond size/column limits

### Performance Issues

1. **N+1 Queries** — Many endpoints do per-row subqueries (e.g., loading table count for each service)
2. **No Caching** — Every request hits the database
3. **No Pagination** — Some list endpoints return all records
4. **Large File Processing** — Entire files loaded into memory with pandas

---

## 16. Environment Variables Reference

### Python Backend (`mini-services/backend/.env`)
| Variable | Default | Purpose |
|---|---|---|
| `DB_PATH` | `../../db/custom.db` (absolute) | SQLite database file path |
| `LLM_API_KEY` | `""` (empty) | Primary LLM API key |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | LLM API base URL |
| `LLM_MODEL` | `gpt-4o-mini` | LLM model name |
| `LLM_MAX_TOKENS` | `8192` | Max tokens per LLM response |
| `LLM_TEMPERATURE` | `0.1` | LLM temperature |
| `LLM_FALLBACK_1_API_KEY` | `""` | Fallback provider 1 API key |
| `LLM_FALLBACK_1_BASE_URL` | `""` | Fallback provider 1 base URL |
| `LLM_FALLBACK_1_MODEL` | `""` | Fallback provider 1 model |
| `LLM_FALLBACK_2_API_KEY` | `""` | Fallback provider 2 (same pattern up to 5) |
| `SERVER_PORT` | `3001` | Backend server port |
| `SERVER_HOST` | `0.0.0.0` | Backend server host |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `CHUNKS_DIR` | `/tmp/dataguard_chunks` | Temporary upload chunks directory |
| `MAX_FILE_SIZE` | `104857600` (100MB) | Maximum upload file size |
| `MAX_COLUMNS` | `1000` | Maximum number of columns |
| `MAX_ROWS` | `10000000` (10M) | Maximum number of rows |

### Next.js Frontend (`.env`)
| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `file:/home/z/my-project/db/custom.db` | Database URL (used by better-sqlite3) |

---

## 17. Database Schema — Python Backend (27 Tables)

These are created by `init_db()` in `mini-services/backend/index.py`:

| # | Table Name | Purpose | Key Columns |
|---|---|---|---|
| 1 | `Service` | Data sources (databases, APIs) | id, name, description, serviceType, platform, connectionUrl, status, owner |
| 2 | `"Table"` | Table metadata | id, name, fullyQualifiedName, description, database, schema, serviceId, columns (JSON), columnCount, rowCount, qualityScore, freshnessStatus, lastProfiled, tier, tags (JSON), owners (JSON) |
| 3 | `Dataset` | Dataset records | id, name, description, type, connectionInfo, status, rowCount, columnCount, qualityScore, lastChecked |
| 4 | `QualityRule` | Quality rule definitions | id, name, description, type, dimension, severity, config (JSON), enabled, schedule, lastTriggered, datasetId |
| 5 | `QualityCheck` | Check execution results | id, ruleId, datasetId, status, score, recordsChecked, recordsFailed, duration, failures (JSON) |
| 6 | `ComplianceReport` | Compliance audit results | id, framework, datasetId, status, findings (JSON), score |
| 7 | `DQTest` | Data quality tests | id, name, tableId, description, status, testType, config (JSON), enabled, lastRunAt |
| 8 | `DQTestResult` | Test execution results | id, testId, status, score, recordsChecked, recordsFailed, duration, result (JSON) |
| 9 | `Alert` | Alert notifications | id, title, message, severity, alertType, source, status, assignedTo, resolvedAt |
| 10 | `Team` | Team management | id, name, displayName, description, email, slack |
| 11 | `Activity` | Activity log | id, entityType, entityId, entityName, action, description, tags (JSON) |
| 12 | `DataLineage` | Data lineage edges | id, fromTableId, toTableId, edgeType, description |
| 13 | `Tag` | Tag taxonomy | id, name, displayName, description, color, tagFQN, usageCount |
| 14 | `GlossaryTerm` | Business glossary | id, name, qualifiedName, description, definition, category, status, reviewers (JSON), tags (JSON) |
| 15 | `TableProfile` | Column profiling data | id, tableId, profileData (JSON), rowCount, duration |
| 16 | `TransformHistory` | Transformation audit trail | id, tableId, snapshotId, transformType, config (JSON), resultSummary (JSON), rowsAffected, columnsAffected (JSON) |
| 17 | `Pipeline` | Transformation pipelines | id, name, description, steps (JSON), version, tableId, status |
| 18 | `PipelineRun` | Pipeline execution records | id, pipelineId, tableId, status, totalSteps, completedSteps, failedSteps, totalDurationMs, stepResults (JSON), finalShape (JSON) |
| 19 | `AutoEDARport` | EDA report storage | id, tableId, tableName, overview (JSON), columnProfiles (JSON), correlations (JSON), missingAnalysis (JSON), distributionAnalysis (JSON), outlierSummary (JSON), insights (JSON), warnings (JSON) |
| 20 | `MLReadinessScore` | ML readiness results | id, tableId, tableName, overallScore, grade, dimensions (JSON), issues (JSON), recommendations (JSON), isMLReady |
| 21 | `DataContract` | Data contract definitions | id, name, description, contractDef (JSON), tableId, lastValidated, lastScore |
| 22 | `ContractValidation` | Contract validation results | id, contractId, tableId, valid, score, violations (JSON), totalChecks, passedChecks, failedChecks |
| 23 | `ScheduledJob` | Job scheduling | id, name, type, targetId, cron, interval, enabled, lastRun, nextRun, runCount, failureCount, alertOnFailure, alertChannels (JSON), config (JSON) |
| 24 | `Connector` | External connectors | id, name, type, config (JSON), status, lastTested, lastError |
| 25 | `StatisticalTest` | Statistical test results | id, tableId, testType, config (JSON), result (JSON) |
| 26 | `FixApproval` | Auto-fix approval workflow | id, tableId, checkId, fixType, fixConfig (JSON), proposedBy, status, appliedAt, rolledBackAt, resultSummary (JSON) |
| 27 | `CopilotChat` | Copilot conversation history | id, tableId, role, content, metadata (JSON) |

---

## 18. Database Schema — Node.js schema.sql (15 Tables)

These are defined in `db/schema.sql` (used by `src/lib/db.ts` with better-sqlite3):

| # | Table Name | Key Columns |
|---|---|---|
| 1 | `Service` | id, name, type, description, platform, connection, status |
| 2 | `Table_entity` | id, name, fullyQualifiedName, serviceId, columns, columnCount, rowCount, qualityScore, freshnessStatus, schemaHash, tags, owners |
| 3 | `Dataset` | id, name, serviceId, tableName, filePath, format, rowCount, columnCount, qualityScore, metadata |
| 4 | `QualityRule` | id, name, description, ruleType, category, severity, checkType, checkConfig, generatedCode, naturalLanguage, codeLanguage, datasetId, tableName, columnName, isActive, lastTriggered, lastResult, runCount, failCount |
| 5 | `QualityCheck` | id, ruleId, datasetId, tableName, columnName, status, passed, message, totalRows, passedRows, failedRows, passRate, metricValue, thresholdValue, failedSamples, executionTimeMs |
| 6 | `DQTest` | id, name, type, status, tableId, columnName, config, severity |
| 7 | `DQTestResult` | id, testId, status, score, message, metrics |
| 8 | `TableProfile` | id, tableId, profileData, rowCount, columnCount, duration |
| 9 | `DataLineage` | id, sourceTableId, targetTableId, transformation, columnLineage |
| 10 | `Alert` | id, title, description, alertType, severity, status, sourceType, sourceId, sourceName, metricValue, suggestion |
| 11 | `Tag` | id, name, category, description, color |
| 12 | `GlossaryTerm` | id, name, definition, category, status, relatedTerms |
| 13 | `Team` | id, name, description, members |
| 14 | `Activity` | id, action, entityType, entityId, entityName, description, userId, metadata |
| 15 | `QualityReport` | id, tableName, datasetId, overallScore, totalChecks, passedChecks, failedChecks, summary, diagnosis, actionPlan, fixCode, fixLanguage, checkResults |

---

## 19. Schema Mismatch Reference

**CRITICAL:** The Python backend (`init_db()`) and Node.js (`schema.sql`) define different schemas for the same tables. Since the Python backend is the source of truth, the Node.js schema should NOT be used. However, `src/lib/db.ts` still runs `schema.sql` on startup.

**Key Differences:**

| Aspect | Python Backend | Node.js schema.sql |
|---|---|---|
| Table name for tables | `"Table"` (quoted, reserved word) | `Table_entity` |
| Service type column | `serviceType` | `type` |
| Service connection | `connectionUrl` | `connection` |
| Rule type column | `type` | `ruleType` |
| Alert message column | `message` | `description` |
| Number of tables | 27 | 15 |
| Extra tables (Python only) | ComplianceReport, TransformHistory, Pipeline, PipelineRun, AutoEDARport, MLReadinessScore, DataContract, ContractValidation, ScheduledJob, Connector, StatisticalTest, FixApproval, CopilotChat | — |

**Recommendation:** Remove `src/lib/db.ts` schema execution, or reconcile both schemas. The Python backend's `init_db()` with `CREATE TABLE IF NOT EXISTS` will win on overlapping tables, but the Node.js schema may create `Table_entity` which nothing reads.

---

## 20. Startup Scripts Reference

| Script | What It Does | Issues |
|---|---|---|
| `start.sh` | Starts both backend + frontend in parallel | Works |
| `start-backend.sh` | Activates venv + runs uvicorn | Works |
| `start_backend.sh` | Runs uvicorn directly (no venv) | May fail if deps not in system Python |
| `start-frontend.sh` | `bun run dev` | Works if bun installed |
| `start_services.sh` | Starts both with PID tracking | Works |
| `run_backend.py` | Python wrapper for uvicorn | Works |
| `supervisord.conf` | Manages both processes | Stale `DataMonitor` directory reference |

---

## 21. LLM Integration Architecture

```
┌─────────────────────────────────────────────────────┐
│                   LLM Integration                    │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │         llm/client.py (Multi-Provider)        │   │
│  │                                                │   │
│  │  Primary: LLM_API_KEY + LLM_BASE_URL + MODEL │   │
│  │  Fallback 1: LLM_FALLBACK_1_*                 │   │
│  │  Fallback 2: LLM_FALLBACK_2_*                 │   │
│  │  Fallback 3: LLM_FALLBACK_3_*                 │   │
│  │  Fallback 4: LLM_FALLBACK_4_*                 │   │
│  │  Fallback 5: LLM_FALLBACK_5_*                 │   │
│  │                                                │   │
│  │  Uses urllib.request (no SDK dependency)       │   │
│  │  OpenAI-compatible chat/completions endpoint   │   │
│  └──────────┬───────────────────────────────────┘   │
│             │                                        │
│  ┌──────────┴───────────────────────────────────┐   │
│  │              llm/prompts.py                    │   │
│  │  RULE_SYSTEM, RULE_USER                       │   │
│  │  FIX_SYSTEM, FIX_USER                         │   │
│  │  REPORT_SYSTEM, REPORT_USER                   │   │
│  └──────────┬───────────────────────────────────┘   │
│             │                                        │
│  ┌──────────┴────────────────────────────────────┐  │
│  │          Feature Generators                     │  │
│  │  ┌───────────────┐  ┌──────────────────────┐  │  │
│  │  │rule_generator │  │ fix_generator         │  │  │
│  │  │NL → Quality   │  │ Check result → Fix   │  │  │
│  │  │Rule           │  │ code/suggestion       │  │  │
│  │  │Fallback:      │  │ Fallback: Template   │  │  │
│  │  │keyword match  │  │ based                │  │  │
│  │  └───────────────┘  └──────────────────────┘  │  │
│  │  ┌───────────────┐  ┌──────────────────────┐  │  │
│  │  │report_generator│ │ copilot/engine.py     │  │  │
│  │  │Check results  │  │ Chat-based data prep  │  │  │
│  │  │→ Summary,     │  │ Fallback: Heuristic  │  │  │
│  │  │diagnosis,     │  │ keyword matching     │  │  │
│  │  │action plan    │  │                      │  │  │
│  │  │Fallback:      │  │                      │  │  │
│  │  │Template based │  │                      │  │  │
│  │  └───────────────┘  └──────────────────────┘  │  │
│  └────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## 22. Quality Check Engine Architecture

```
┌─────────────────────────────────────────────────────────┐
│                Quality Check Engine                       │
│                                                          │
│  POST /api/run-check {ruleId}                            │
│    │                                                     │
│    ▼                                                     │
│  ┌─────────────────────────────────────┐                │
│  │ Load QualityRule from DB             │                │
│  │ Load Dataset from DB (via rule)      │                │
│  │ Find matching Table record           │                │
│  └──────────────┬──────────────────────┘                │
│                 │                                        │
│    ┌────────────▼────────────┐                          │
│    │ load_dataframe(table_id)│                          │
│    │ Reads data/{id}.csv     │                          │
│    └────┬──────────────┬─────┘                          │
│         │ Found        │ Not Found                      │
│         ▼              ▼                                │
│  ┌──────────────┐  ┌────────────────────┐               │
│  │ REAL CHECK   │  │ Load TableProfile   │              │
│  │ execute_rule │  │ from DB             │              │
│  │ (DataFrame)  │  └────────┬───────────┘              │
│  │              │           │ Found                     │
│  │ get_check()  │           ▼                           │
│  │    │         │  ┌────────────────────┐               │
│  │    ▼         │  │ PROFILE ESTIMATE   │              │
│  │ ┌──────────┐ │  │ execute_profile_   │              │
│  │ │Complete- │ │  │ check()            │              │
│  │ │nessCheck │ │  └────────┬───────────┘              │
│  │ │Uniqueness│ │           │ Not Found                │
│  │ │Check     │ │           ▼                           │
│  │ │Validity  │ │  ┌────────────────────┐               │
│  │ │Check     │ │  │ SIMULATED (random) │              │
│  │ │Freshness │ │  │ Legacy fallback    │              │
│  │ │Check     │ │  └────────────────────┘              │
│  │ │Schema    │ │                                     │
│  │ │Check     │ │                                     │
│  │ │Volume    │ │                                     │
│  │ │Check     │ │                                     │
│  │ │Anomaly   │ │                                     │
│  │ │Check     │ │                                     │
│  │ └──────────┘ │                                     │
│  └──────┬───────┘                                     │
│         │                                               │
│         ▼                                               │
│  ┌──────────────────────────────────────┐              │
│  │ CheckResult                          │              │
│  │ {status, score, recordsChecked,      │              │
│  │  recordsFailed, duration, failures}  │              │
│  └──────────────┬───────────────────────┘              │
│                 │                                        │
│    ┌────────────▼────────────────────────┐             │
│    │ Save QualityCheck to DB             │             │
│    │ If failed → Create Alert in DB      │             │
│    │ Update Rule.lastTriggered           │             │
│    │ Recalculate Dataset.qualityScore    │             │
│    └─────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────┘
```

---

## 23. Transformation Engine Architecture

```
┌──────────────────────────────────────────────────────────┐
│              Transformation Engine                         │
│                                                           │
│  POST /api/transforms/execute                             │
│    {tableId, transform_type, config}                      │
│    │                                                      │
│    ▼                                                      │
│  ┌──────────────────────────────────────┐                │
│  │ load_dataframe(table_id)              │                │
│  │ Save snapshot (for rollback)          │                │
│  └──────────────┬───────────────────────┘                │
│                 │                                         │
│    ┌────────────▼────────────────────────┐              │
│    │ Transform Registry                   │              │
│    │ ┌────────────┐ ┌──────────────┐     │              │
│    │ │ imputation │ │ outlier      │     │              │
│    │ │ (mean,     │ │ (iqr, zscore,│     │              │
│    │ │  median,   │ │  percentile, │     │              │
│    │ │  mode,     │ │  winsorize)  │     │              │
│    │ │  ffill,    │ │              │     │              │
│    │ │  constant) │ │              │     │              │
│    │ └────────────┘ └──────────────┘     │              │
│    │ ┌────────────┐ ┌──────────────┐     │              │
│    │ │ dedup      │ │ encoding     │     │              │
│    │ │ (keep_     │ │ (one_hot,    │     │              │
│    │ │  first,    │ │  label,      │     │              │
│    │ │  last,     │ │  ordinal,    │     │              │
│    │ │  none)     │ │  target)     │     │              │
│    │ └────────────┘ └──────────────┘     │              │
│    │ ┌────────────┐ ┌──────────────┐     │              │
│    │ │normalizaton│ │ string_clean │     │              │
│    │ │ (standard, │ │ (trim, lower,│     │              │
│    │ │  minmax,   │ │  upper,      │     │              │
│    │ │  robust)   │ │  special,    │     │              │
│    │ │            │ │  html)       │     │              │
│    │ └────────────┘ └──────────────┘     │              │
│    │ ┌────────────┐ ┌──────────────┐     │              │
│    │ │date_parser │ │ data_split   │     │              │
│    │ │ (auto,     │ │ (random,     │     │              │
│    │ │  iso8601,  │ │  stratified, │     │              │
│    │ │  us, eu)   │ │  temporal)   │     │              │
│    │ └────────────┘ └──────────────┘     │              │
│    │ ┌────────────┐                      │              │
│    │ │type_conver-│                      │              │
│    │ │sion        │                      │              │
│    │ │ (numeric,  │                      │              │
│    │ │  string,   │                      │              │
│    │ │  datetime, │                      │              │
│    │ │  category) │                      │              │
│    │ └────────────┘                      │              │
│    └──────────────┬──────────────────────┘              │
│                   │                                      │
│    ┌──────────────▼──────────────────────┐              │
│    │ Execute transform on DataFrame       │              │
│    │ save_dataframe(table_id, result_df)  │              │
│    │ Save TransformHistory to DB          │              │
│    │ Return result summary                │              │
│    └──────────────────────────────────────┘              │
│                                                           │
│  Pipeline Execution:                                      │
│  POST /api/pipelines/{pid}/run                            │
│    → Load pipeline steps (DAG) from DB                    │
│    → Execute steps in topological order (NetworkX)        │
│    → Save PipelineRun to DB with step results             │
│                                                           │
│  Rollback:                                                │
│  POST /api/transforms/rollback                            │
│    → Load snapshot from TransformHistory                  │
│    → Restore DataFrame from snapshot                      │
│    → Save as current data                                 │
└──────────────────────────────────────────────────────────┘
```

---

## 24. Test Suite Reference

### Test Files (`mini-services/backend/tests/`)

| Test File | What It Tests | Key Assertions |
|---|---|---|
| `test_checks_base.py` | BaseCheck abstract class | Cannot instantiate directly, subclasses must implement execute() |
| `test_checks_completeness.py` | CompletenessCheck | Detects nulls, scores correctly, respects threshold |
| `test_checks_uniqueness.py` | UniquenessCheck | Detects duplicates, scores correctly |
| `test_checks_validity.py` | ValidityCheck | Validates regex, range, valid_values |
| `test_checks_freshness.py` | FreshnessCheck | Checks date recency against threshold |
| `test_checks_schema.py` | SchemaCheck | Validates column existence and types |
| `test_checks_volume.py` | VolumeCheck | Checks row count against min/max |
| `test_checks_registry.py` | Check registry | get_check() returns correct class, aliases work |
| `test_engine_quality_scorer.py` | QualityScorer | Weighted scoring calculation, edge cases |
| `test_transformations.py` | All 10 transformers | Each transform produces valid DataFrame |
| `test_transform_history.py` | TransformHistory | Snapshot save/restore works |
| `test_data_connectors.py` | DataConnectorEngine | Source listing, connection test stubs |
| `test_data_contracts.py` | ContractValidator | Schema, column, row-level validation |
| `test_statistical_tests.py` | StatisticalTestsEngine | All 8 tests return correct structure |
| `test_forecasting.py` | QualityForecastEngine | SMA, exponential smoothing, linear trend |
| `test_ml_readiness.py` | MLReadinessEngine | 7 dimensions scored, grade assigned |
| `test_copilot.py` | CopilotEngine | Chat + suggestions (heuristic fallback) |
| `test_scheduler.py` | Scheduler | CRUD, cron parsing, run tracking |
| `test_auto_eda.py` | AutoEDAEngine | Report generation with all sections |
| `test_models_rule.py` | Rule models | Pydantic validation |
| `test_models_check_result.py` | CheckResult model | Field validation |
| `test_config.py` | Configuration | Env var loading, defaults |
| `test_db_connection.py` | Database class | Async CRUD operations |
| `test_profiling_profiler.py` | Profiler | Column profiling statistics |
| `test_llm_prompts.py` | LLM prompts | Template formatting |
| `test_integration.py` | End-to-end flows | Full check pipeline |
| `test_system.py` | System-level tests | App startup, health check |

### Running Tests
```bash
cd mini-services/backend
source venv/bin/activate
python -m pytest tests/ -v
```

---

## Quick Reference: Most Important Files

| Priority | File | Why It Matters |
|---|---|---|
| ★★★★★ | `mini-services/backend/index.py` | The entire backend — ALL 77+ endpoints |
| ★★★★★ | `src/app/page.tsx` | The entire SPA — 22 views |
| ★★★★☆ | `src/lib/store.ts` | Zustand state — view routing + shared types |
| ★★★★☆ | `mini-services/backend/engine/rule_executor.py` | Quality check execution engine |
| ★★★★☆ | `mini-services/backend/checks/__init__.py` | Check type registry |
| ★★★★☆ | `mini-services/backend/llm/client.py` | LLM multi-provider client |
| ★★★★☆ | `mini-services/backend/config.py` | All configuration |
| ★★★☆☆ | `src/app/api/ingest/route.ts` | File upload proxy |
| ★★★☆☆ | `mini-services/backend/llm/rule_generator.py` | NL rule generation |
| ★★★☆☆ | `mini-services/backend/copilot/engine.py` | AI copilot |
| ★★★☆☆ | `mini-services/backend/eda/auto_eda.py` | Auto EDA |
| ★★★☆☆ | `mini-services/backend/ml_readiness/scorer.py` | ML readiness |
| ★★★☆☆ | `mini-services/backend/statistical/tests.py` | Statistical tests |
| ★★☆☆☆ | `db/schema.sql` | Node.js schema (conflicting) |
| ★★☆☆☆ | `src/lib/db.ts` | better-sqlite3 (deprecated) |
| ★☆☆☆☆ | `mini-services/backend/src/app/api/` | Legacy route stubs (not used) |

---

## Quick Reference: Error Messages & Solutions

| Error Message | Cause | Solution |
|---|---|---|
| `Backend unavailable` | Python backend not running on port 3001 | Start backend: `cd mini-services/backend && python -m uvicorn index:app --port 3001` |
| `no such table: Table` | SQLite reserved word not quoted | Ensure all queries use `"Table"` with double quotes |
| `Empty overview/dashboard` | Stats endpoint returning zeros | Check `GET /api/stats` directly, verify DB has data |
| `Simulated check result` | No DataFrame file in `data/` directory | Re-upload data, check `data/{table_id}.csv` exists |
| `Keyword-based rule` | LLM not configured | Set `LLM_API_KEY` in `.env` |
| `Heuristic copilot` | LLM not configured | Set `LLM_API_KEY` in `.env` |
| `502 Bad Gateway` | Next.js can't reach Python backend | Ensure Python backend is running on port 3001 |
| `psycopg2 not installed` | PostgreSQL connector used without dependency | `pip install psycopg2-binary` |
| `pymysql not installed` | MySQL connector used without dependency | `pip install pymysql` |
| `boto3 not installed` | S3 connector used without dependency | `pip install boto3` |

---

---

## Appendix A: Glossary of Domain Terms

| Term | Definition |
|---|---|
| **DataGuard** | The name of this application — a unified data intelligence platform |
| **DataMonitor** | A previous name for this project — still referenced in some stale config files like supervisord.conf |
| **Quality Rule** | A configurable check that validates data against a specific criterion (completeness, uniqueness, validity, freshness, schema, volume, anomaly) |
| **Quality Check** | A single execution of a quality rule against a dataset, producing a pass/fail result with a score |
| **DQTest** | A data quality test — similar to a quality rule but associated with a specific table rather than a dataset |
| **DQTestResult** | The result of executing a DQTest |
| **Dataset** | A logical data entity representing an uploaded file or connected data source |
| **Service** | A data source (database, API, file system) that contains tables |
| **Table** | A table within a service — contains column metadata, quality scores, and profiling data |
| **DataLineage** | A directed edge showing data flow from one table to another |
| **DataContract** | A formal agreement defining expected schema, column rules, and freshness requirements for a dataset |
| **Auto-EDA** | Automated Exploratory Data Analysis — generates a comprehensive profiling report with one click |
| **ML Readiness** | A score (A-F grade) indicating how prepared a dataset is for machine learning |
| **Pipeline** | A directed acyclic graph (DAG) of transformation steps to be executed in sequence |
| **Transform** | A data transformation operation (imputation, encoding, normalization, etc.) applied to a DataFrame |
| **Copilot** | An AI-powered data preparation assistant that suggests transformations and quality rules |
| **NL Rule** | A quality rule generated from natural language input (e.g., "email should not be null") |
| **Auto-Fix** | An AI-proposed fix for a quality issue that requires human approval before application |
| **Forecasting** | Predicting future quality scores based on historical trends using exponential smoothing and linear regression |
| **Profile** | Column-level statistics (type, null %, unique count, mean, std, min, max, top values) for a table |
| **Check Result** | The outcome of a quality check execution — includes status (passed/failed), score, records checked/failed |
| **Compliance Report** | An audit report showing whether a dataset meets regulatory or policy requirements |
| **Scheduled Job** | A cron-based or interval-based job that automatically runs quality checks on a schedule |
| **Connector** | A configuration for connecting to an external data source (PostgreSQL, MySQL, S3, BigQuery, SQLite) |

---

## Appendix B: Port Reference

| Port | Service | Protocol | Notes |
|---|---|---|---|
| 3000 | Next.js Frontend | HTTP | Main user-facing application |
| 3001 | Python FastAPI Backend | HTTP | All business logic, database operations |
| 81 | Caddy Reverse Proxy | HTTP | Optional — proxies to port 3000 |

---

## Appendix C: Key Configuration Files Summary

| File | Format | Purpose | When Modified |
|---|---|---|---|
| `mini-services/backend/.env` | KEY=VALUE | Python backend environment variables | When changing DB path, LLM keys, server config |
| `.env` | KEY=VALUE | Next.js environment variables | When changing database URL |
| `next.config.ts` | TypeScript | Next.js configuration | When changing output mode, body limits, dev origins |
| `tailwind.config.ts` | TypeScript | Tailwind CSS theme | When changing colors, fonts, spacing |
| `components.json` | JSON | shadcn/ui configuration | When adding new UI components |
| `tsconfig.json` | TypeScript | TypeScript compiler options | When changing module resolution, paths |
| `Caddyfile` | Caddy | Reverse proxy configuration | When changing proxy targets |
| `supervisord.conf` | INI | Process manager configuration | When changing service startup commands |

---

*This document was auto-generated for the DataGuard project. Last updated: 2026-05-03*
