<div align="center">

# 🛡️ DataGuard

**Open-Source Data Intelligence Platform**

Monitor, profile, and improve your data quality with AI-powered insights.

[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)](https://python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
- [PostgreSQL Setup](#-postgresql-setup)
- [Configuration](#-configuration)
- [Project Structure](#-project-structure)
- [API Reference](#-api-reference)
- [Data Quality Checks](#-data-quality-checks)
- [AI Features](#-ai-features)
- [Screenshots](#-screenshots)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🔍 Overview

DataGuard is a self-hosted data intelligence platform that helps you monitor, profile, and improve the quality of your data. It combines automated data quality checks, AI-powered insights, exploratory data analysis, and transformation pipelines in a single, unified dashboard.

**Why DataGuard?**

- **Self-hosted** — Your data never leaves your infrastructure. No cloud dependencies, no vendor lock-in.
- **AI-powered** — Leverages LLMs for natural language queries, auto-fix suggestions, rule generation, and quality forecasting.
- **Comprehensive** — 8 quality check types, automated EDA, ML readiness scoring, data contracts, and statistical tests — all in one place.
- **Real-time** — Live quality scoring, anomaly detection, and alerting so you catch issues before they propagate downstream.
- **Extensible** — Plugin architecture for custom checks, transformations, and connectors. Add PostgreSQL, MySQL, MongoDB, or any data source.

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────┐
│  Browser                                         │
│  http://localhost:3000                           │
└──────────────────────┬───────────────────────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
┌──────────────────┐      ┌──────────────────┐
│  Next.js 16      │      │  FastAPI          │
│  Frontend :3000  │◄────►│  Backend  :3001   │
│                  │      │                   │
│  • React 19      │      │  • pandas/numpy   │
│  • Zustand       │      │  • scipy          │
│  • shadcn/ui     │      │  • OpenAI client  │
│  • Recharts      │      │  • aiosqlite      │
│  • TanStack      │      │  • networkx       │
└────────┬─────────┘      └────────┬──────────┘
         │                         │
         │    ┌────────────────────┘
         ▼    ▼
┌─────────────────────────┐
│  SQLite / PostgreSQL    │
│  27 tables, WAL mode    │
└─────────────────────────┘
```

The **Next.js frontend** renders the dashboard UI and proxies API requests to the **FastAPI Python backend**, which handles all business logic — data ingestion, quality checks, profiling, transformations, LLM calls, and forecasting. The backend stores all metadata in SQLite (default) or PostgreSQL (production).

---

## ✨ Features

### Core Platform

| Feature | Description |
|---------|-------------|
| **Overview Dashboard** | Real-time health scores, quality trends, alerts, and service status at a glance |
| **Service Management** | Register and monitor data sources (databases, APIs, file systems) |
| **Table Explorer** | Browse, search, and profile all registered tables with column-level detail |
| **Data Ingestion** | Upload CSV, JSON, and Excel files via drag-and-drop, API, or bulk scripts |

### Data Quality

| Feature | Description |
|---------|-------------|
| **8 Quality Check Types** | Completeness, Uniqueness, Freshness, Validity, Schema, Volume, Anomaly, and Custom checks |
| **Quality Rules Engine** | Define rules with severity levels, dimensions, and schedules; execute on-demand or via cron |
| **Quality Forecasting** | Predict future quality scores using exponential smoothing and linear trend analysis |
| **Auto-Fix Workflow** | AI proposes fixes → Human approves → System applies → One-click rollback |
| **Alert Management** | Severity-based alerts with assignment tracking and resolution workflow |

### AI & Intelligence

| Feature | Description |
|---------|-------------|
| **AI Data Copilot** | Chat with your data in natural language; get suggestions and insights per table |
| **NL → SQL** | Ask questions in plain English and get executable SQL queries |
| **AI Rule Generator** | Describe quality expectations in natural language; auto-generate rules |
| **AI Report Generator** | Generate comprehensive quality reports with AI-powered analysis |
| **Statistical Tests** | T-tests, Chi-square, ANOVA, KS-test, Mann-Whitney, correlation, and Levene's test |

### Data Engineering

| Feature | Description |
|---------|-------------|
| **Auto-EDA** | Automated exploratory data analysis: distributions, correlations, missing patterns, outliers |
| **ML Readiness** | Score datasets for ML readiness with grades (A–F), issue detection, and recommendations |
| **Transformation Pipeline** | 12 transform types (imputation, dedup, normalization, encoding, outlier, etc.) with visual builder |
| **Data Connectors** | PostgreSQL, MySQL, MongoDB, S3, BigQuery, Snowflake, Redshift, REST API |
| **SQL Playground** | Execute SQL directly against your data with AI-assisted query writing |
| **Job Scheduler** | Cron-based scheduling for automated quality checks and data syncs |

### Governance & Compliance

| Feature | Description |
|---------|-------------|
| **Data Contracts** | Define schema contracts and validate tables against them |
| **Tags & Glossary** | Organize tables with tags and maintain a business glossary |
| **Activity Feed** | Full audit trail of all actions — who did what, when |
| **Compliance Reports** | Framework-based compliance scoring and findings |

---

## 🧰 Tech Stack

### Frontend

| Technology | Purpose |
|------------|---------|
| [Next.js 16](https://nextjs.org/) | React framework with API routes |
| [React 19](https://react.dev/) | UI library |
| [TypeScript 5](https://www.typescriptlang.org/) | Type-safe JavaScript |
| [Zustand](https://zustand.docs.pmnd.rs/) | Lightweight state management |
| [shadcn/ui](https://ui.shadcn.com/) | Copy-paste component library (Radix UI + Tailwind) |
| [Tailwind CSS 4](https://tailwindcss.com/) | Utility-first CSS framework |
| [Recharts](https://recharts.org/) | Charting library |
| [TanStack Table](https://tanstack.com/table) | Headless data tables |
| [react-hook-form](https://react-hook-form.com/) | Form management with Zod validation |
| [Sonner](https://sonner.emilkowal.dev/) | Toast notifications |
| [Lucide React](https://lucide.dev/) | Icon library |

### Backend

| Technology | Purpose |
|------------|---------|
| [FastAPI](https://fastapi.tiangolo.com/) | Python async web framework |
| [Uvicorn](https://www.uvicorn.org/) | ASGI server |
| [pandas](https://pandas.pydata.org/) | Data processing and analysis |
| [NumPy](https://numpy.org/) | Numerical computing |
| [SciPy](https://scipy.org/) | Statistical analysis |
| [OpenAI SDK](https://github.com/openai/openai-python) | LLM integration (OpenAI-compatible APIs) |
| [aiosqlite](https://aiosqlite.readthedocs.io/) | Async SQLite driver |
| [Pydantic](https://docs.pydantic.dev/) | Data validation and serialization |
| [openpyxl](https://openpyxl.readthedocs.io/) | Excel file parsing |
| [NetworkX](https://networkx.org/) | Graph algorithms for lineage |

### Database

| Database | Use Case |
|----------|----------|
| **SQLite** | Default — zero-config, file-based, perfect for development and single-user deployments |
| **PostgreSQL** | Production — concurrent access, advanced queries, scalability for teams |

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.10+ |
| Node.js | 18+ (or Bun) |
| Git | 2.30+ |
| RAM | 4GB minimum (8GB recommended) |
| Disk | 5GB minimum |

### Linux

```bash
# 1. Clone the repository
git clone https://github.com/your-org/dataguard.git
cd dataguard

# 2. Install frontend dependencies
bun install   # or: npm install

# 3. Setup Python backend
cd mini-services/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# For PostgreSQL support (recommended for production)
pip install psycopg2-binary

# 4. Configure environment
cp .env.example .env
# Edit .env with your database URL and LLM API key

# 5. Start the backend
python -m uvicorn index:app --host 0.0.0.0 --port 3001 --reload

# 6. Start the frontend (in a new terminal)
cd ../..
bun run dev   # or: npm run dev

# 7. Open in browser
# http://localhost:3000
```

### Windows

```powershell
# 1. Clone the repository
git clone https://github.com/your-org/dataguard.git
cd dataguard

# 2. Install frontend dependencies
npm install

# 3. Setup Python backend
cd mini-services\backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# For PostgreSQL support
pip install psycopg2-binary

# 4. Configure environment
copy .env.example .env
# Edit .env with your database URL and LLM API key

# 5. Start the backend
python -m uvicorn index:app --host 0.0.0.0 --port 3001 --reload

# 6. Start the frontend (in a new terminal)
cd ..\..
npm run dev

# 7. Open in browser
# http://localhost:3000
```

> **Note:** The backend **must** be running on port 3001 before starting the frontend. The frontend proxies all API calls to the backend.

---

## 🐘 PostgreSQL Setup

SQLite works great for development, but PostgreSQL is recommended for production deployments. It provides better concurrency handling through MVCC, superior query performance for large datasets, and advanced features like full-text search and JSONB support.

### Install PostgreSQL

**Linux (Ubuntu/Debian):**

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**Windows:**

Download the installer from [postgresql.org/download/windows](https://www.postgresql.org/download/windows/) or use a package manager:

```powershell
# Chocolatey
choco install postgresql -y

# Winget
winget install -e --id PostgreSQL.PostgreSQL
```

### Create Database & User

```sql
-- Connect as postgres superuser
sudo -u postgres psql    -- Linux
-- "C:\Program Files\PostgreSQL\16\bin\psql" -U postgres    -- Windows

-- Create user and database
CREATE USER dataguard WITH PASSWORD 'your_secure_password_here';
CREATE DATABASE dataguard_db OWNER dataguard;
GRANT ALL PRIVILEGES ON DATABASE dataguard_db TO dataguard;

\c dataguard_db
GRANT ALL ON SCHEMA public TO dataguard;
\q
```

### Configure DataGuard for PostgreSQL

Edit `mini-services/backend/.env`:

```env
DB_TYPE=postgresql
DATABASE_URL=postgresql://dataguard:your_secure_password_here@localhost:5432/dataguard_db
```

Then add PostgreSQL as a data connector in the DataGuard UI (Connectors page) or via API:

```bash
curl -X POST http://localhost:3000/api/connectors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My PostgreSQL Database",
    "type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "dataguard_db",
    "username": "dataguard"
  }'
```

---

## ⚙️ Configuration

### Backend Environment Variables

Create `mini-services/backend/.env`:

```env
# ── Database ──
# PostgreSQL (production)
DB_TYPE=postgresql
DATABASE_URL=postgresql://dataguard:password@localhost:5432/dataguard_db

# SQLite (development)
# DB_TYPE=sqlite
# DATABASE_URL=sqlite:///../../db/custom.db

# ── Primary LLM Provider ──
LLM_API_KEY=gsk_your-key
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.3-70b-versatile

# ── Fallback Providers (optional) ──
LLM_FALLBACK_1_API_KEY=nvapi_your-key
LLM_FALLBACK_1_BASE_URL=https://integrate.api.nvidia.com/v1
LLM_FALLBACK_1_MODEL=minimaxai/minimax-m2.7

LLM_FALLBACK_2_API_KEY=sk-or_your-key
LLM_FALLBACK_2_BASE_URL=https://openrouter.ai/api/v1
LLM_FALLBACK_2_MODEL=z-ai/glm-4.5-air:free

# ── Upload Limits ──
MAX_FILE_SIZE=104857600    # 100MB
MAX_COLUMNS=1000
MAX_ROWS=10000000

# ── Server ──
SERVER_PORT=3001
CORS_ORIGINS=*
```

### Frontend Environment Variables

Create `.env` in the project root:

```env
DATABASE_URL="file:./db/custom.db"
NEXT_PUBLIC_APP_NAME="DataGuard"
PORT=3000
```

### LLM Providers

DataGuard uses any OpenAI-compatible API for AI features. Supported providers include:

| Provider | Base URL | Models |
|----------|----------|--------|
| Groq | `https://api.groq.com/openai/v1` | llama-3.3-70b-versatile, mixtral-8x7b |
| OpenAI | `https://api.openai.com/v1` | gpt-4o, gpt-4o-mini |
| NVIDIA NIM | `https://integrate.api.nvidia.com/v1` | minimax-m2.7, llama-3.1-nemotron |
| OpenRouter | `https://openrouter.ai/api/v1` | 200+ models |
| Local (Ollama) | `http://localhost:11434/v1` | llama3, mistral, phi3 |

> **Tip:** AI features are optional. DataGuard works fully without an LLM API key — you just won't have access to the Copilot, NL→SQL, AI rule generation, and auto-fix features.

---

## 📁 Project Structure

```
dataguard/
├── src/
│   ├── app/
│   │   ├── api/                    # 67 Next.js API route handlers
│   │   │   ├── ingest/route.ts     # File upload endpoint
│   │   │   ├── stats/route.ts      # Dashboard statistics
│   │   │   ├── forecast/           # Quality forecasting
│   │   │   ├── connectors/         # Data source management
│   │   │   ├── sql/                # SQL playground routes
│   │   │   └── ...                 # 60+ more routes
│   │   ├── layout.tsx              # Root layout
│   │   └── page.tsx                # Main SPA page
│   ├── components/
│   │   ├── dq/                     # DataGuard business components
│   │   │   ├── overview.tsx        # Dashboard overview
│   │   │   ├── forecasting.tsx     # Quality forecasting
│   │   │   ├── auto-eda.tsx        # Automated EDA
│   │   │   ├── copilot.tsx         # AI chat interface
│   │   │   ├── sql-playground.tsx  # SQL query editor
│   │   │   ├── connectors.tsx      # Data connectors
│   │   │   ├── settings.tsx        # Local setup guide
│   │   │   └── ...                 # 25+ more components
│   │   └── ui/                     # 48 shadcn/ui primitives
│   ├── hooks/                      # Custom React hooks
│   └── lib/
│       ├── store.ts                # Zustand global state
│       ├── db.ts                   # better-sqlite3 connection
│       └── utils.ts                # Shared utilities
│
├── mini-services/backend/          # Python FastAPI backend
│   ├── index.py                    # Main app (70 endpoints)
│   ├── requirements.txt
│   ├── checks/                     # Quality check modules
│   │   ├── completeness_check.py
│   │   ├── uniqueness_check.py
│   │   ├── freshness_check.py
│   │   ├── validity_check.py
│   │   ├── schema_check.py
│   │   ├── volume_check.py
│   │   └── anomaly_check.py
│   ├── llm/                        # LLM integration
│   │   ├── client.py               # Multi-provider client with fallback
│   │   ├── rule_generator.py       # NL → quality rules
│   │   ├── fix_generator.py        # AI fix suggestions
│   │   └── report_generator.py     # AI quality reports
│   ├── forecasting/                # Quality forecasting engine
│   ├── eda/                        # Auto-EDA engine
│   ├── profiling/                  # Data profiling
│   ├── ml_readiness/               # ML readiness scorer
│   ├── transformations/            # 12 data transform types
│   ├── connectors/                 # External data connectors
│   ├── scheduler/                  # Job scheduling
│   ├── statistical/                # Statistical test engine
│   ├── contracts/                  # Data contract validator
│   ├── copilot/                    # AI copilot engine
│   └── tests/                      # 30 test files
│
├── db/
│   ├── custom.db                   # Primary SQLite database
│   └── schema.sql                  # Reference schema
│
├── public/                         # Static assets
├── next.config.ts                  # Next.js configuration
├── tailwind.config.ts              # Tailwind CSS configuration
├── supervisord.conf                # Process manager config
└── Caddyfile                       # Reverse proxy config
```

---

## 📡 API Reference

DataGuard exposes **70+ API endpoints** across the Python backend, proxied through Next.js API routes.

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/stats` | Dashboard statistics (scores, alerts, checks) |
| `GET` | `/api/services` | List all registered services |
| `POST` | `/api/services` | Register a new service |
| `GET` | `/api/tables` | List all tables with metadata |
| `GET` | `/api/table-data/{id}` | Get table rows and schema |

### Quality & Checks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/quality` | List quality test definitions |
| `GET` | `/api/quality/results` | Get quality test results |
| `GET` | `/api/rules` | List quality rules |
| `POST` | `/api/rules` | Create a quality rule |
| `POST` | `/api/nl-rule` | Generate rule from natural language |
| `GET` | `/api/checks` | List quality check results |
| `POST` | `/api/run-check` | Execute a quality check |
| `GET` | `/api/forecast/{tableId}` | Get quality score forecast |

### Data Ingestion & Profiling

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/ingest` | Upload CSV/JSON/XLSX file |
| `GET` | `/api/profile` | List table profiles |
| `POST` | `/api/profile` | Generate table profile |
| `GET` | `/api/auto-eda/{tableId}` | Get Auto-EDA report |

### AI & Intelligence

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/copilot/chat` | Chat with AI copilot |
| `GET` | `/api/copilot/suggestions/{tableId}` | Get AI suggestions |
| `POST` | `/api/sql/ai-query` | Natural language to SQL |
| `POST` | `/api/ai/generate-rule` | Generate quality rule via AI |
| `POST` | `/api/ai/generate-fix` | Generate AI fix suggestion |
| `POST` | `/api/ai/generate-report` | Generate AI quality report |

### Transformations & Pipelines

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/transforms/list` | List available transformations |
| `POST` | `/api/transforms/execute` | Execute a transformation |
| `POST` | `/api/transforms/execute-batch` | Execute batch transformations |
| `POST` | `/api/transforms/rollback` | Rollback a transformation |
| `GET` | `/api/pipelines` | List pipelines |
| `POST` | `/api/pipelines` | Create a pipeline |
| `POST` | `/api/pipelines/{id}/run` | Execute a pipeline |

### Connectors & Scheduling

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/connectors` | List data connectors |
| `POST` | `/api/connectors` | Add a connector |
| `POST` | `/api/connectors/{id}/test` | Test connector connection |
| `POST` | `/api/connectors/{id}/fetch` | Sync data from connector |
| `GET` | `/api/schedules` | List scheduled jobs |
| `POST` | `/api/schedules` | Create a scheduled job |
| `POST` | `/api/schedules/{id}/run` | Trigger a scheduled run |

---

## 🛡 Data Quality Checks

DataGuard includes 8 built-in quality check types, each targeting a specific data quality dimension:

| Check Type | Dimension | What It Detects |
|------------|-----------|-----------------|
| **Completeness** | Completeness | Missing values, null columns, empty rows |
| **Uniqueness** | Uniqueness | Duplicate records, non-unique keys |
| **Freshness** | Timeliness | Stale data, outdated timestamps |
| **Validity** | Validity | Out-of-range values, format violations, type mismatches |
| **Schema** | Consistency | Schema drift, unexpected columns, type changes |
| **Volume** | Completeness | Row count anomalies, data loss detection |
| **Anomaly** | Accuracy | Statistical outliers, distribution shifts |
| **Custom** | Any | User-defined Python expressions |

### Quality Dimensions

Each check maps to one of six data quality dimensions defined by the DAMA DMBOK framework:

```
Completeness ── Is all required data present?
Uniqueness ──── Are there no duplicate records?
Timeliness ──── Is the data up-to-date?
Validity ────── Does data conform to expected formats?
Consistency ─── Is data consistent across systems?
Accuracy ────── Does data reflect the real world?
```

### Quality Scoring

DataGuard computes a composite quality score (0–100) for each table based on the weighted average of all executed checks. The scoring algorithm considers:

- **Check severity** — Critical issues weigh more than warnings
- **Records affected** — Percentage of rows that fail the check
- **Dimension balance** — Ensures all dimensions are represented
- **Trend** — Historical scores influence the current rating

---

## 🤖 AI Features

DataGuard integrates with any OpenAI-compatible LLM API to provide intelligent data quality features.

### AI Data Copilot

Ask questions about your data in natural language and receive contextual answers. The copilot has access to table schemas, sample data, quality scores, and profiling results.

```
You: "Which tables have the most missing values?"
Copilot: "Based on the latest quality checks, the top 3 tables with missing values are:
  1. customer_addresses — 23.5% null in the 'zip_code' column
  2. order_items — 12.1% null in 'discount_code'
  3. product_catalog — 8.7% null in 'description'
  I recommend creating a completeness rule for these columns."
```

### Natural Language → SQL

Translate plain English questions into SQL queries that execute directly against your data:

```
"Show me the top 10 customers by total spending last month"
→ SELECT customer_name, SUM(amount) as total_spent
  FROM orders WHERE order_date >= DATE('now', '-1 month')
  GROUP BY customer_name ORDER BY total_spent DESC LIMIT 10
```

### AI Rule Generation

Describe quality expectations in natural language and DataGuard generates executable quality rules:

```
"Email addresses should be in valid format and unique across all rows"
→ Generates: Uniqueness check on 'email' column + Validity check with regex pattern
```

### Auto-Fix Workflow

AI suggests fixes for detected quality issues with a human-in-the-loop approval process:

1. **Detect** — Quality check identifies issues (e.g., 500 rows with invalid dates)
2. **Propose** — AI generates fix suggestions (e.g., "Convert DD/MM/YYYY to YYYY-MM-DD")
3. **Review** — Human reviews the proposed fix and affected rows
4. **Approve/Reject** — Human approves or rejects the fix
5. **Apply** — Fix is applied to the data with a snapshot for rollback
6. **Rollback** — If needed, revert to the pre-fix state with one click

### LLM Fallback Chain

Configure up to 5 LLM providers with automatic fallback. If the primary provider fails (rate limit, timeout, error), DataGuard automatically tries the next provider in the chain:

```
Groq (primary) → NVIDIA NIM (fallback 1) → OpenRouter (fallback 2)
```

---

## 📊 Screenshots

### Overview Dashboard
Real-time quality scores, service health, recent alerts, and quality trend charts.

### Quality Forecasting
Historical quality score trends with exponential smoothing and linear trend projections.

### Auto-EDA
Automated exploratory data analysis with column distributions, correlations, and AI-generated insights.

### AI Copilot
Chat with your data using natural language. Get suggestions, insights, and SQL queries.

### SQL Playground
Execute SQL directly against your data with AI-assisted query writing and result visualization.

### Data Connectors
Connect to PostgreSQL, MySQL, MongoDB, S3, BigQuery, Snowflake, and more.

---

## 🚢 Production Deployment

### Using PM2

```bash
# Install PM2
npm install -g pm2

# Create ecosystem file
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [
    {
      name: 'dataguard-backend',
      script: 'venv/bin/python',
      args: '-m uvicorn index:app --host 0.0.0.0 --port 3001',
      cwd: './mini-services/backend',
    },
    {
      name: 'dataguard-frontend',
      script: 'npm',
      args: 'start',
      env: { PORT: 3000 },
    },
  ],
}
EOF

# Start
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

### Using Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name dataguard.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:3001/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 100M;
    }
}
```

### Using Docker (Coming Soon)

Docker support is planned. The architecture is designed to be containerized with separate frontend and backend containers sharing a volume for the SQLite database, or connecting to an external PostgreSQL instance.

---

## 🧪 Testing

The backend includes 30 test files covering all major modules:

```bash
cd mini-services/backend
source venv/bin/activate

# Run all tests
python -m pytest tests/ -v

# Run specific test module
python -m pytest tests/test_quality_checks.py -v
python -m pytest tests/test_statistical_tests.py -v
python -m pytest tests/test_integration.py -v
```

---

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Linux
lsof -i :3000
kill -9 <PID>

# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

### PostgreSQL Connection Refused

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql    # Linux
Get-Service -Name postgresql*       # Windows

# Start if stopped
sudo systemctl start postgresql     # Linux
Start-Service -Name postgresql-x64-16  # Windows
```

### psycopg2 Installation Fails

```bash
# Use the pre-built binary (recommended)
pip install psycopg2-binary

# Linux: Install dev headers if building from source
sudo apt install -y libpq-dev gcc
pip install psycopg2
```

### Virtual Environment Activation on Windows

```powershell
# If you get a script execution error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Or use CMD instead of PowerShell:
venv\Scripts\activate.bat
```

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Setup

```bash
# Start backend in development mode (auto-reload)
cd mini-services/backend
source venv/bin/activate
python -m uvicorn index:app --host 0.0.0.0 --port 3001 --reload

# Start frontend in development mode
bun run dev
```

### Code Style

- **Frontend:** TypeScript with ESLint, Prettier formatting
- **Backend:** Python with PEP 8 conventions
- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`)

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ for data teams who care about quality**

[Report Bug](https://github.com/your-org/dataguard/issues) · [Request Feature](https://github.com/your-org/dataguard/issues) · [Documentation](https://github.com/your-org/dataguard/wiki)

</div>