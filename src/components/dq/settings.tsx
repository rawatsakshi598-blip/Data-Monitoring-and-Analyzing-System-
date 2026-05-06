'use client'

import { useState } from 'react'
import {
  Users,
  Mail,
  Building2,
  Plus,
  Search,
  Terminal,
  Copy,
  CheckCircle2,
  AlertTriangle,
  BookOpen,
  Upload,
  FileText,
  HardDrive,
  Settings2,
  Wrench,
  Zap,
  FolderOpen,
  Database,
  Monitor,
  Apple,
  Download,
  Server,
  Plug,
  Shield,
  Play,
  RotateCcw,
  FileCode,
  Braces,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Separator } from '@/components/ui/separator'
import { toast } from 'sonner'

// ─── Helpers ─────────────────────────────────────────────────────────────────

const copyToClipboard = (text: string) => {
  navigator.clipboard.writeText(text).then(
    () => toast.success('Copied to clipboard!'),
    () => toast.error('Failed to copy')
  )
}

// ─── CodeBlock Component ────────────────────────────────────────────────────

function CodeBlock({ code, language }: { code: string; language?: string }) {
  return (
    <div className="relative group mt-2">
      <div className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-slate-400 hover:text-slate-100 bg-slate-800/60 hover:bg-slate-700/60 backdrop-blur-sm"
          onClick={() => copyToClipboard(code)}
        >
          <Copy className="h-3.5 w-3.5 mr-1" />
          Copy
        </Button>
      </div>
      {language && (
        <div className="text-xs text-slate-500 mb-1 font-medium">{language}</div>
      )}
      <pre className="bg-slate-900 text-slate-100 rounded-lg p-4 font-mono text-sm overflow-x-auto whitespace-pre-wrap break-all leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  )
}

// ─── OS Badge ───────────────────────────────────────────────────────────────

function OSBadge({ os }: { os: 'linux' | 'windows' | 'both' }) {
  const cfg = {
    linux: { icon: <Terminal className="h-3 w-3" />, label: 'Linux', cls: 'bg-slate-100 text-slate-700 border-slate-200' },
    windows: { icon: <Monitor className="h-3 w-3" />, label: 'Windows', cls: 'bg-blue-50 text-blue-700 border-blue-200' },
    both: { icon: <Play className="h-3 w-3" />, label: 'Both', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  }
  const c = cfg[os]
  return (
    <Badge variant="outline" className={`gap-1 text-[10px] ${c.cls}`}>
      {c.icon} {c.label}
    </Badge>
  )
}

// ─── Prerequisites Tab ──────────────────────────────────────────────────────

function PrerequisitesTab() {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
          <CheckCircle2 className="h-5 w-5 text-emerald-500" />
          Prerequisites
        </h3>
        <p className="text-sm text-slate-500 mt-1">
          Ensure your system meets these requirements before installing DataGuard and PostgreSQL.
        </p>
      </div>

      {/* System Requirements */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Server className="h-4 w-4 text-slate-600" />
            System Requirements
          </CardTitle>
          <CardDescription>Minimum hardware and software requirements for both platforms.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-2 sm:grid-cols-2">
            {[
              { label: 'Operating System', value: 'Linux (Ubuntu 20.04+, Debian 11+, Fedora 36+) or Windows 10/11' },
              { label: 'Python', value: 'Python 3.10+ (for FastAPI backend)' },
              { label: 'Node.js', value: 'Node.js 18+ or Bun runtime (for Next.js frontend)' },
              { label: 'PostgreSQL', value: 'PostgreSQL 14+ (for production database)' },
              { label: 'Git', value: 'Git 2.30+ for cloning the repository' },
              { label: 'RAM', value: '4GB minimum (8GB recommended with PostgreSQL)' },
              { label: 'Disk Space', value: '5GB minimum (includes PostgreSQL + data storage)' },
              { label: 'Network', value: 'Internet access for dependency installation' },
            ].map((item) => (
              <div key={item.label} className="flex flex-col rounded-lg border border-slate-200 p-3 gap-1">
                <span className="text-xs font-medium text-slate-500">{item.label}</span>
                <span className="text-sm text-slate-800">{item.value}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Linux Verify */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Terminal className="h-4 w-4 text-slate-700" />
            Verify Prerequisites — Linux
          </CardTitle>
        </CardHeader>
        <CardContent>
          <CodeBlock
            code={`# Verify your Linux system
python3 --version  # 3.10+ required (for backend)
node --version     # v18+ required (for frontend)
bun --version      # or use Bun instead of npm
git --version      # Git 2.30+ required
free -h            # check available RAM (4GB+)
df -h /            # check available disk space

# Check if PostgreSQL is already installed
psql --version     # should show 14+
pg_isready         # check if PostgreSQL service is running`}
            language="bash"
          />
        </CardContent>
      </Card>

      {/* Windows Verify */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Monitor className="h-4 w-4 text-blue-600" />
            Verify Prerequisites — Windows
          </CardTitle>
        </CardHeader>
        <CardContent>
          <CodeBlock
            code={`# Verify your Windows system (PowerShell or CMD)
python --version   # 3.10+ required (for backend)
node --version     # v18+ required (for frontend)
git --version      # Git 2.30+ required

# Check if PostgreSQL is already installed
psql --version     # should show 14+

# Check system info
systeminfo | findstr /C:"Total Physical Memory"
wmic logicaldisk get size,freespace,caption`}
            language="powershell"
          />
        </CardContent>
      </Card>
    </div>
  )
}

// ─── PostgreSQL Setup Tab ───────────────────────────────────────────────────

function PostgreSQLTab() {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
          <Database className="h-5 w-5 text-blue-600" />
          PostgreSQL Setup
        </h3>
        <p className="text-sm text-slate-500 mt-1">
          Install and configure PostgreSQL as your production database for DataGuard. This replaces the default SQLite
          database with a robust, scalable relational database suitable for production workloads, concurrent access,
          and large datasets. PostgreSQL provides superior performance for complex queries, better concurrency handling
          through MVCC, and advanced features like full-text search, JSONB support, and extensibility through extensions.
        </p>
      </div>

      {/* Linux Installation */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Terminal className="h-4 w-4 text-slate-700" />
            Install PostgreSQL — Linux (Ubuntu/Debian)
            <OSBadge os="linux" />
          </CardTitle>
          <CardDescription>
            PostgreSQL is available through the default apt repositories on Ubuntu and Debian. The following commands
            install PostgreSQL 16 along with its contribution packages which provide additional utilities and data types.
            After installation, the PostgreSQL service starts automatically and is configured to launch on boot.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <CodeBlock
            code={`# ── Step 1: Update package lists ──
sudo apt update && sudo apt upgrade -y

# ── Step 2: Install PostgreSQL and contrib utilities ──
sudo apt install -y postgresql postgresql-contrib

# ── Step 3: Verify installation ──
psql --version
# Expected output: psql (PostgreSQL) 16.x

# ── Step 4: Start and enable PostgreSQL service ──
sudo systemctl start postgresql
sudo systemctl enable postgresql
sudo systemctl status postgresql
# Should show "active (exiting)" status

# ── Step 5: Verify the service is listening on port 5432 ──
sudo ss -tlnp | grep 5432
# Should show: LISTEN 0 244 127.0.0.1:5432`}
            language="bash"
          />
        </CardContent>
      </Card>

      {/* Fedora / RHEL */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Terminal className="h-4 w-4 text-slate-700" />
            Install PostgreSQL — Linux (Fedora/RHEL)
            <OSBadge os="linux" />
          </CardTitle>
          <CardDescription>
            On Fedora and RHEL-based distributions, PostgreSQL is available through dnf. RHEL 8 and 9 also provide
            PostgreSQL through application streams, allowing you to install specific versions side by side. The
            installation process uses systemd for service management, similar to Debian-based systems.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <CodeBlock
            code={`# ── Fedora ──
sudo dnf install -y postgresql-server postgresql-contrib
sudo postgresql-setup --initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql

# ── RHEL / Rocky Linux / AlmaLinux ──
sudo dnf install -y postgresql-server
sudo postgresql-setup --initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verify
psql --version`}
            language="bash"
          />
        </CardContent>
      </Card>

      {/* Windows Installation */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Monitor className="h-4 w-4 text-blue-600" />
            Install PostgreSQL — Windows
            <OSBadge os="windows" />
          </CardTitle>
          <CardDescription>
            PostgreSQL provides a native Windows installer via EnterpriseDB. The installer includes the database server,
            pgAdmin (a graphical management tool), Stack Builder (for installing additional drivers and tools), and
            command-line utilities. During installation, you will be prompted to set a password for the postgres
            superuser and choose a port number (default 5432).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Method 1: GUI Installer */}
          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-2 flex items-center gap-2">
              <Badge variant="outline" className="text-xs">Method 1</Badge>
              GUI Installer (Recommended)
            </h4>
            <div className="space-y-2 text-sm text-slate-600">
              <p>
                1. Download the PostgreSQL installer from{' '}
                <span className="font-mono text-blue-600">https://www.postgresql.org/download/windows/</span>
              </p>
              <p>
                2. Run the installer and follow the setup wizard. During installation, make note of the
                superuser password you set for the <code className="rounded bg-slate-100 px-1 py-0.5 text-xs font-mono">postgres</code> account.
              </p>
              <p>
                3. Keep the default port <code className="rounded bg-slate-100 px-1 py-0.5 text-xs font-mono">5432</code> unless you have a conflict.
              </p>
              <p>
                4. Select the components to install: PostgreSQL Server, pgAdmin 4, and Command Line Tools should all be checked.
              </p>
              <p>
                5. After installation completes, PostgreSQL starts automatically as a Windows service.
              </p>
            </div>
          </div>

          <Separator />

          {/* Method 2: Chocolatey */}
          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-2 flex items-center gap-2">
              <Badge variant="outline" className="text-xs">Method 2</Badge>
              Chocolatey (CLI Install)
            </h4>
            <CodeBlock
              code={`# Install Chocolatey first (if not already installed)
# Run in an elevated PowerShell (Run as Administrator)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = \\
  [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString(\\
  'https://community.chocolatey.org/install.ps1'))

# Install PostgreSQL via Chocolatey
choco install postgresql -y

# Verify installation
psql --version

# The service should auto-start. Check it:
Get-Service -Name postgresql*`}
              language="powershell"
            />
          </div>

          <Separator />

          {/* Method 3: winget */}
          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-2 flex items-center gap-2">
              <Badge variant="outline" className="text-xs">Method 3</Badge>
              Winget (Windows Package Manager)
            </h4>
            <CodeBlock
              code={`# Install PostgreSQL via winget
winget install -e --id PostgreSQL.PostgreSQL

# Verify
psql --version`}
              language="powershell"
            />
          </div>

          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
            <span>
              On Windows, after installation you may need to add PostgreSQL to your PATH.
              The default install path is{' '}
              <code className="font-mono">C:\\Program Files\\PostgreSQL\\16\\bin</code>.
              Add this to your System Environment Variables if <code className="font-mono">psql</code> is not recognized.
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Create Database and User */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Shield className="h-4 w-4 text-emerald-600" />
            Create Database & User for DataGuard
            <OSBadge os="both" />
          </CardTitle>
          <CardDescription>
            After installing PostgreSQL, create a dedicated database and user for DataGuard. Using a separate user
            instead of the postgres superuser is a security best practice — it follows the principle of least privilege
            and limits the potential damage if the application credentials are compromised. The dataguard user will
            only have permissions on the dataguard_db database, not the entire PostgreSQL cluster.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-1 flex items-center gap-2">
              <Terminal className="h-3.5 w-3.5" /> Linux
            </h4>
            <CodeBlock
              code={`# Switch to the postgres system user and open psql
sudo -u postgres psql

# Inside the psql shell, run:
CREATE USER dataguard WITH PASSWORD 'your_secure_password_here';
CREATE DATABASE dataguard_db OWNER dataguard;
GRANT ALL PRIVILEGES ON DATABASE dataguard_db TO dataguard;

# Connect to the new database and grant schema permissions
\\c dataguard_db
GRANT ALL ON SCHEMA public TO dataguard;

# Verify the user was created
\\du dataguard

# Exit psql
\\q`}
              language="sql"
            />
          </div>

          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-1 flex items-center gap-2">
              <Monitor className="h-3.5 w-3.5" /> Windows
            </h4>
            <CodeBlock
              code={`# Open SQL Shell (psql) from Start Menu, or run in CMD/PowerShell:
# The default postgres password was set during installation

"C:\\Program Files\\PostgreSQL\\16\\bin\\psql" -U postgres

# Inside the psql shell, run the same commands:
CREATE USER dataguard WITH PASSWORD 'your_secure_password_here';
CREATE DATABASE dataguard_db OWNER dataguard;
GRANT ALL PRIVILEGES ON DATABASE dataguard_db TO dataguard;

\\c dataguard_db
GRANT ALL ON SCHEMA public TO dataguard;

\\du dataguard
\\q`}
              language="sql"
            />
          </div>

          <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800 flex items-start gap-2">
            <Shield className="h-4 w-4 mt-0.5 shrink-0" />
            <span>
              Replace <code className="font-mono">your_secure_password_here</code> with a strong, unique password.
              For production, use a password manager to generate a 20+ character password with mixed case, numbers, and symbols.
              Never commit database credentials to version control.
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Configure PostgreSQL for Remote Access */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Settings2 className="h-4 w-4 text-slate-600" />
            Configure Remote Access (Optional)
            <OSBadge os="both" />
          </CardTitle>
          <CardDescription>
            By default, PostgreSQL only accepts connections from localhost. If you need to connect from another
            machine (for example, a separate application server or a data engineering workstation), you must
            configure PostgreSQL to listen on external interfaces and update the client authentication file. This
            is common in production deployments where the database runs on a dedicated server.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-1">Step 1: Edit postgresql.conf</h4>
            <CodeBlock
              code={`# Linux: /etc/postgresql/16/main/postgresql.conf
# Windows: C:\\Program Files\\PostgreSQL\\16\\data\\postgresql.conf

# Find the "listen_addresses" line and change it:
listen_addresses = '*'          # Listen on all interfaces
# OR for specific IPs:
listen_addresses = 'localhost, 192.168.1.100'

# Also verify the port:
port = 5432`}
              language="conf"
            />
          </div>

          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-1">Step 2: Edit pg_hba.conf</h4>
            <CodeBlock
              code={`# Linux: /etc/postgresql/16/main/pg_hba.conf
# Windows: C:\\Program Files\\PostgreSQL\\16\\data\\pg_hba.conf

# Add this line to allow password-authenticated connections
# from your local network (adjust the CIDR to match your network):
host    dataguard_db    dataguard    192.168.1.0/24    md5

# For development only (NOT for production), you can allow all:
host    dataguard_db    dataguard    0.0.0.0/0         md5

# Save the file, then restart PostgreSQL:`}
              language="conf"
            />
          </div>

          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-1">Step 3: Restart PostgreSQL</h4>
            <CodeBlock
              code={`# ── Linux ──
sudo systemctl restart postgresql

# ── Windows ──
# Option 1: Services Manager
#   Press Win+R → services.msc → Find PostgreSQL → Right-click → Restart

# Option 2: PowerShell (Run as Administrator)
Restart-Service -Name postgresql-x64-16`}
              language="bash"
            />
          </div>

          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800 flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
            <span>
              Exposing PostgreSQL to the internet (0.0.0.0/0) is dangerous. Always restrict access to specific
              IP ranges in production. Use SSH tunnels or VPNs when possible for an additional layer of security.
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Test Connection */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Plug className="h-4 w-4 text-violet-600" />
            Test the PostgreSQL Connection
            <OSBadge os="both" />
          </CardTitle>
          <CardDescription>
            Before connecting DataGuard to PostgreSQL, verify that the database and user are working correctly
            by connecting with the psql command-line tool. This confirms the server is running, the credentials
            are correct, and the database is accessible.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <CodeBlock
            code={`# Connect as the dataguard user
psql -h localhost -U dataguard -d dataguard_db -p 5432

# You will be prompted for the password you set earlier.
# After connecting, test with a simple query:

SELECT version();

# You should see something like:
# PostgreSQL 16.x on x86_64-pc-linux-gnu...

# Check available tables (should be empty initially):
\\dt

# Exit
\\q`}
            language="bash"
          />
        </CardContent>
      </Card>
    </div>
  )
}

// ─── DataGuard Setup Tab ────────────────────────────────────────────────────

function DataGuardSetupTab() {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
          <Zap className="h-5 w-5 text-amber-500" />
          DataGuard Installation
        </h3>
        <p className="text-sm text-slate-500 mt-1">
          Get DataGuard up and running on your machine with the FastAPI Python backend and Next.js frontend. The
          entire setup takes about 10 minutes depending on your internet speed and whether you already have Python
          and Node.js installed.
        </p>
      </div>

      {/* Linux Quick Start */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Terminal className="h-4 w-4 text-slate-700" />
            Quick Start — Linux
            <OSBadge os="linux" />
          </CardTitle>
          <CardDescription>Get DataGuard running on Linux in 6 steps.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {[
            {
              step: 1,
              title: 'Clone the Repository',
              code: `git clone https://github.com/your-org/dataguard.git dataguard
cd dataguard`,
            },
            {
              step: 2,
              title: 'Install Frontend Dependencies',
              code: `bun install   # recommended — or use: npm install`,
            },
            {
              step: 3,
              title: 'Setup Python Backend',
              code: `cd mini-services/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install PostgreSQL adapter (required for PostgreSQL mode)
pip install psycopg2-binary`,
              note: 'The psycopg2-binary package is the pre-compiled PostgreSQL adapter. If you prefer to compile from source (for custom Python builds), use pip install psycopg2 instead, but you will need libpq-dev and gcc installed.',
            },
            {
              step: 4,
              title: 'Configure Backend for PostgreSQL',
              code: `# Create/edit mini-services/backend/.env
# ─────────────────────────────────────
# Database Configuration
# ─────────────────────────────────────

# Option A: Use PostgreSQL (recommended for production)
DB_TYPE=postgresql
DATABASE_URL=postgresql://dataguard:your_secure_password_here@localhost:5432/dataguard_db

# Option B: Use SQLite (default, for quick testing only)
DB_TYPE=sqlite
DATABASE_URL=sqlite:///../../db/custom.db

# ─────────────────────────────────────
# LLM Provider (for AI features)
# ─────────────────────────────────────
LLM_API_KEY=gsk_your-key
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.3-70b-versatile

# ─────────────────────────────────────
# Server Configuration
# ─────────────────────────────────────
SERVER_PORT=3001
MAX_FILE_SIZE=104857600
MAX_COLUMNS=1000
MAX_ROWS=10000000`,
            },
            {
              step: 5,
              title: 'Start the Backend',
              code: `cd mini-services/backend
source venv/bin/activate
python -m uvicorn index:app --host 0.0.0.0 --port 3001 --reload`,
              note: 'The backend must be running before the frontend. The --reload flag enables auto-restart on code changes during development.',
            },
            {
              step: 6,
              title: 'Start the Frontend',
              code: `# From the project root directory
npm run dev   # or: bun run dev

# Open in browser:
# http://localhost:3000`,
            },
          ].map((s) => (
            <div key={s.step}>
              <div className="flex items-center gap-2 mb-2">
                <Badge variant="secondary" className="font-mono">Step {s.step}</Badge>
                <span className="text-sm font-medium text-slate-800">{s.title}</span>
              </div>
              <CodeBlock code={s.code} language="bash" />
              {s.note && <p className="text-xs text-slate-500 mt-1">{s.note}</p>}
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Windows Quick Start */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Monitor className="h-4 w-4 text-blue-600" />
            Quick Start — Windows
            <OSBadge os="windows" />
          </CardTitle>
          <CardDescription>Get DataGuard running on Windows in 6 steps.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {[
            {
              step: 1,
              title: 'Clone the Repository',
              code: `git clone https://github.com/your-org/dataguard.git dataguard
cd dataguard`,
            },
            {
              step: 2,
              title: 'Install Frontend Dependencies',
              code: `npm install   # or: bun install`,
            },
            {
              step: 3,
              title: 'Setup Python Backend',
              code: `cd mini-services\\backend
python -m venv venv
venv\\Scripts\\activate
pip install -r requirements.txt

# Install PostgreSQL adapter
pip install psycopg2-binary`,
              note: 'On Windows, use venv\\Scripts\\activate instead of source venv/bin/activate. If you get an execution policy error, run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser',
            },
            {
              step: 4,
              title: 'Configure Backend for PostgreSQL',
              code: `# Create/edit mini-services\\backend\\.env
# Same configuration as Linux (see Linux tab for full .env)
# The DATABASE_URL format is the same on both platforms:

DB_TYPE=postgresql
DATABASE_URL=postgresql://dataguard:your_secure_password_here@localhost:5432/dataguard_db

# For SQLite fallback:
# DB_TYPE=sqlite
# DATABASE_URL=sqlite:///../../db/custom.db`,
            },
            {
              step: 5,
              title: 'Start the Backend',
              code: `cd mini-services\\backend
venv\\Scripts\\activate
python -m uvicorn index:app --host 0.0.0.0 --port 3001 --reload`,
            },
            {
              step: 6,
              title: 'Start the Frontend',
              code: `# From the project root directory
npm run dev

# Open in browser:
# http://localhost:3000`,
            },
          ].map((s) => (
            <div key={s.step}>
              <div className="flex items-center gap-2 mb-2">
                <Badge variant="secondary" className="font-mono">Step {s.step}</Badge>
                <span className="text-sm font-medium text-slate-800">{s.title}</span>
              </div>
              <CodeBlock code={s.code} language="bash" />
              {s.note && <p className="text-xs text-slate-500 mt-1">{s.note}</p>}
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Connect PostgreSQL via DataGuard Connector */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Plug className="h-4 w-4 text-violet-600" />
            Connect PostgreSQL via DataGuard Connector
            <OSBadge os="both" />
          </CardTitle>
          <CardDescription>
            After setting up PostgreSQL, add it as a data connector in DataGuard. Navigate to the Connectors page
            in the sidebar, click &quot;Add Connector&quot;, and fill in your PostgreSQL connection details. The connector
            allows DataGuard to discover tables, run quality checks, and ingest data from your PostgreSQL database.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="flex flex-col rounded-lg border border-slate-200 p-3 gap-1">
              <span className="text-xs font-medium text-slate-500">Connector Type</span>
              <span className="text-sm text-slate-800">PostgreSQL</span>
            </div>
            <div className="flex flex-col rounded-lg border border-slate-200 p-3 gap-1">
              <span className="text-xs font-medium text-slate-500">Connection Name</span>
              <span className="text-sm text-slate-800">My PostgreSQL Database</span>
            </div>
            <div className="flex flex-col rounded-lg border border-slate-200 p-3 gap-1">
              <span className="text-xs font-medium text-slate-500">Host</span>
              <span className="text-sm text-slate-800 font-mono">localhost</span>
            </div>
            <div className="flex flex-col rounded-lg border border-slate-200 p-3 gap-1">
              <span className="text-xs font-medium text-slate-500">Port</span>
              <span className="text-sm text-slate-800 font-mono">5432</span>
            </div>
            <div className="flex flex-col rounded-lg border border-slate-200 p-3 gap-1">
              <span className="text-xs font-medium text-slate-500">Database</span>
              <span className="text-sm text-slate-800 font-mono">dataguard_db</span>
            </div>
            <div className="flex flex-col rounded-lg border border-slate-200 p-3 gap-1">
              <span className="text-xs font-medium text-slate-500">Username</span>
              <span className="text-sm text-slate-800 font-mono">dataguard</span>
            </div>
          </div>

          <Separator />

          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-1">Or use the API to create the connector:</h4>
            <CodeBlock
              code={`# Create a PostgreSQL connector via API
curl -X POST http://localhost:3000/api/connectors \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "My PostgreSQL Database",
    "type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "dataguard_db",
    "username": "dataguard"
  }'

# Test the connector connection
curl -X POST http://localhost:3000/api/connectors/{connector_id}/test`}
              language="bash"
            />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// ─── Data Upload Tab ────────────────────────────────────────────────────────

function DataUploadTab() {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
          <Upload className="h-5 w-5 text-blue-500" />
          Data Upload Methods
        </h3>
        <p className="text-sm text-slate-500 mt-1">
          Three ways to ingest data into DataGuard for quality monitoring, profiling, and analysis.
        </p>
      </div>

      {/* Method 1: UI Upload */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Upload className="h-4 w-4 text-blue-500" />
            Method 1: UI Upload (Drag-and-Drop)
          </CardTitle>
          <CardDescription>
            Navigate to the Ingest Data page in the sidebar. Drag and drop your files or click to browse.
            Supports CSV, JSON, and Excel files up to 100MB. The upload is processed on the FastAPI backend
            which parses the file, infers column types, and stores the data in your configured database
            (SQLite or PostgreSQL).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 flex-wrap">
            <Badge variant="secondary">.csv</Badge>
            <Badge variant="secondary">.json</Badge>
            <Badge variant="secondary">.xlsx</Badge>
            <Badge variant="secondary">.xls</Badge>
            <Badge className="bg-slate-100 text-slate-600 hover:bg-slate-100">Max 100MB</Badge>
          </div>
        </CardContent>
      </Card>

      {/* Method 2: API Upload */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <FileCode className="h-4 w-4 text-emerald-500" />
            Method 2: API Upload (curl)
          </CardTitle>
          <CardDescription>
            Use the REST API to upload files programmatically. This is useful for automated pipelines,
            scheduled uploads from external systems, or when integrating DataGuard into your existing
            data workflow. The API accepts multipart form data and returns a JSON response with the
            created table metadata.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <CodeBlock
            code={`curl -X POST http://localhost:3000/api/ingest \\
  -F "file=@/path/to/your/data.csv" \\
  -F "tableName=my_dataset" \\
  -F "serviceName=My Data"

# Windows PowerShell equivalent:
Invoke-RestMethod -Uri "http://localhost:3000/api/ingest" \\
  -Method Post \\
  -Form @{ file = Get-Item -Path "C:\\data\\my_dataset.csv"; tableName = "my_dataset" }`}
            language="bash"
          />
        </CardContent>
      </Card>

      {/* Method 3: Bulk Upload */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Braces className="h-4 w-4 text-purple-500" />
            Method 3: Bulk Upload Script
          </CardTitle>
          <CardDescription>
            Upload multiple files at once using a shell loop. This script iterates over all CSV and JSON files
            in a directory and uploads them one by one, using the filename (without extension) as the table name.
            This is particularly useful when you have a collection of exported datasets from another system.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <CodeBlock
            code={`#!/bin/bash
# bulk-upload.sh — Upload all CSV/JSON files in a directory

DATA_DIR="./data"
API_URL="http://localhost:3000/api/ingest"

for file in "\${DATA_DIR}"/*.{csv,json}; do
  [ -f "\$file" ] || continue

  BASENAME=\$(basename "\$file")
  TABLE_NAME=\$(echo "\$BASENAME" | sed 's/\\.[^.]*$//')

  echo "Uploading: \$BASENAME -> \$TABLE_NAME"

  curl -s -X POST "\$API_URL" \\
    -F "file=@\$file" \\
    -F "tableName=\$TABLE_NAME" \\
    -F "serviceName=Bulk Import"
done

echo "Done!"`}
            language="bash"
          />
        </CardContent>
      </Card>

      {/* Data Formats */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="h-4 w-4 text-green-500" />
            Supported Data Formats
          </CardTitle>
          <CardDescription>Examples of the supported file formats and their structure.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-1 flex items-center gap-2">
              <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 text-xs">CSV</Badge>
            </h4>
            <CodeBlock
              code={`id,name,email,department,salary,join_date
1,Alice Chen,alice@example.com,Engineering,95000,2022-03-15
2,Bob Smith,bob@example.com,Marketing,72000,2021-08-01
3,Carol Davis,carol@example.com,Engineering,88000,2023-01-10`}
              language="csv"
            />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-1 flex items-center gap-2">
              <Badge className="bg-amber-100 text-amber-700 hover:bg-amber-100 text-xs">JSON</Badge>
            </h4>
            <CodeBlock
              code={`[
  { "id": 1, "name": "Alice Chen", "email": "alice@example.com", "salary": 95000 },
  { "id": 2, "name": "Bob Smith", "email": "bob@example.com", "salary": 72000 }
]`}
              language="json"
            />
          </div>
          <div className="flex gap-2 flex-wrap">
            <Badge variant="secondary">.xlsx</Badge>
            <Badge variant="secondary">.xls</Badge>
            <Badge className="bg-slate-100 text-slate-600 hover:bg-slate-100">First row = headers</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// ─── Configuration Tab ──────────────────────────────────────────────────────

function ConfigurationTab() {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
          <Settings2 className="h-5 w-5 text-slate-600" />
          Configuration Reference
        </h3>
        <p className="text-sm text-slate-500 mt-1">
          Environment variables and configuration files for customizing your DataGuard instance. These settings
          control database connections, LLM providers, upload limits, and server behavior.
        </p>
      </div>

      {/* Frontend .env */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <FileCode className="h-4 w-4 text-slate-600" />
            Frontend Configuration
          </CardTitle>
          <CardDescription>
            Create a <code className="rounded bg-slate-100 px-1 py-0.5 text-xs font-mono">.env</code> file in the project root.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <CodeBlock
            code={`# .env — DataGuard Frontend Configuration (project root)

# Database URL (for legacy seeder only — runtime uses Python backend)
DATABASE_URL="file:./db/custom.db"

# Application
NEXT_PUBLIC_APP_NAME="DataGuard"
PORT=3000

# Optional: Authentication
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="your-secret-key-here"`}
            language="env"
          />
        </CardContent>
      </Card>

      {/* Backend .env */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <FileCode className="h-4 w-4 text-emerald-600" />
            Backend Configuration
          </CardTitle>
          <CardDescription>
            Located at <code className="rounded bg-slate-100 px-1 py-0.5 text-xs font-mono">mini-services/backend/.env</code>.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <CodeBlock
            code={`# .env — DataGuard Python Backend Configuration

# ── Database ──
# PostgreSQL (recommended for production)
DB_TYPE=postgresql
DATABASE_URL=postgresql://dataguard:your_secure_password@localhost:5432/dataguard_db

# SQLite (default, for quick testing)
# DB_TYPE=sqlite
# DATABASE_URL=sqlite:///../../db/custom.db

# ── Primary LLM Provider ──
LLM_API_KEY=gsk_your-key
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.3-70b-versatile

# ── Fallback Provider 1 ──
LLM_FALLBACK_1_API_KEY=nvapi_your-key
LLM_FALLBACK_1_BASE_URL=https://integrate.api.nvidia.com/v1
LLM_FALLBACK_1_MODEL=minimaxai/minimax-m2.7

# ── Fallback Provider 2 ──
LLM_FALLBACK_2_API_KEY=sk-or_your-key
LLM_FALLBACK_2_BASE_URL=https://openrouter.ai/api/v1
LLM_FALLBACK_2_MODEL=z-ai/glm-4.5-air:free

# ── Upload Limits ──
MAX_FILE_SIZE=104857600    # 100MB
MAX_COLUMNS=1000
MAX_ROWS=10000000

# ── Server ──
SERVER_PORT=3001`}
            language="env"
          />
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800 flex items-start gap-2 mt-3">
            <FolderOpen className="h-4 w-4 mt-0.5 shrink-0" />
            <span>
              The <code className="font-mono">.env</code> file is not committed to Git. Use{' '}
              <code className="font-mono">.env.example</code> as a template for team setups. Never share
              your LLM API keys or database passwords in plain text.
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Production Deployment */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Server className="h-4 w-4 text-violet-600" />
            Production Deployment
          </CardTitle>
          <CardDescription>
            Deploy DataGuard for production use using PM2 for process management and Nginx as a reverse proxy.
            PM2 provides automatic restarts, cluster mode for utilizing all CPU cores, log management, and
            zero-downtime reloads. Nginx handles SSL termination, static file serving, and request buffering.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-1">Build and Start</h4>
            <CodeBlock
              code={`# Build the optimized production bundle
bun run build

# Start the production server
bun run start`}
              language="bash"
            />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-1">Process Management with PM2</h4>
            <CodeBlock
              code={`# Install PM2 globally
npm install -g pm2

# Create ecosystem file for both backend and frontend
# ecosystem.config.js
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

# Start all processes
pm2 start ecosystem.config.js

# Save for auto-restart on reboot
pm2 save
pm2 startup

# Monitor
pm2 monit
pm2 logs`}
              language="bash"
            />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-1">Nginx Reverse Proxy</h4>
            <CodeBlock
              code={`# /etc/nginx/sites-available/dataguard
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
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API (direct access optional)
    location /api/ {
        proxy_pass http://127.0.0.1:3001/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 100M;
    }
}`}
              language="nginx"
            />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// ─── Troubleshooting Tab ────────────────────────────────────────────────────

function TroubleshootingTab() {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
          <Wrench className="h-5 w-5 text-red-500" />
          Troubleshooting
        </h3>
        <p className="text-sm text-slate-500 mt-1">
          Common issues and how to resolve them on both Linux and Windows.
        </p>
      </div>

      {/* Issue 1: Port in use */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            Port 3000 or 3001 is already in use
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-slate-600">
            Another process is using the port DataGuard needs. Kill the conflicting process or start DataGuard on a different port.
          </p>
          <div>
            <h4 className="text-xs font-semibold text-slate-500 mb-1 flex items-center gap-1"><Terminal className="h-3 w-3" /> Linux</h4>
            <CodeBlock
              code={`# Find the process using port 3000
lsof -i :3000
# or
ss -tlnp | grep 3000

# Kill the process
kill -9 <PID>

# Or start on a different port
PORT=3002 bun run dev`}
              language="bash"
            />
          </div>
          <div>
            <h4 className="text-xs font-semibold text-slate-500 mb-1 flex items-center gap-1"><Monitor className="h-3 w-3" /> Windows</h4>
            <CodeBlock
              code={`# Find the process using port 3000
netstat -ano | findstr :3000

# Kill the process (replace <PID> with the actual PID)
taskkill /PID <PID> /F

# Or start on a different port
set PORT=3002 && npm run dev`}
              language="powershell"
            />
          </div>
        </CardContent>
      </Card>

      {/* Issue 2: PostgreSQL connection refused */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            PostgreSQL Connection Refused
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-slate-600">
            This error means the backend cannot reach PostgreSQL. Common causes include the PostgreSQL service not running,
            incorrect host/port in the connection string, or firewall rules blocking the connection.
          </p>
          <CodeBlock
            code={`# ── Linux ──
# Check if PostgreSQL is running
sudo systemctl status postgresql

# If not running, start it
sudo systemctl start postgresql

# Check it's listening on port 5432
sudo ss -tlnp | grep 5432

# Check PostgreSQL logs for errors
sudo tail -50 /var/log/postgresql/postgresql-16-main.log


# ── Windows ──
# Check if PostgreSQL service is running
Get-Service -Name postgresql*

# Start it if stopped
Start-Service -Name postgresql-x64-16

# Check if port 5432 is open
Test-NetConnection -ComputerName localhost -Port 5432`}
            language="bash"
          />
        </CardContent>
      </Card>

      {/* Issue 3: psycopg2 install fails */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            psycopg2 Installation Fails
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-slate-600">
            Building psycopg2 from source requires the PostgreSQL development headers and a C compiler.
            On most systems, using the pre-built binary package avoids this entirely.
          </p>
          <CodeBlock
            code={`# ── Linux ──
# Option 1: Use the binary package (recommended)
pip install psycopg2-binary

# Option 2: Install dev headers and build from source
sudo apt install -y libpq-dev gcc
pip install psycopg2


# ── Windows ──
# Option 1: Use the binary package (recommended)
pip install psycopg2-binary

# Option 2: If building from source fails, install Microsoft C++ Build Tools
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
# Select "Desktop development with C++" workload`}
            language="bash"
          />
        </CardContent>
      </Card>

      {/* Issue 4: Database locked */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            SQLite Database Locked Errors
          </CardTitle>
          <CardDescription>
            If you are using SQLite (the default) instead of PostgreSQL, you may encounter database locked errors
            under concurrent access. SQLite uses file-level locking which limits write concurrency. This is one
            of the main reasons to switch to PostgreSQL for production use.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <CodeBlock
            code={`# Check for stale lock files
ls -la db/*.db-journal
ls -la db/*.db-wal
ls -la db/*.db-shm

# Remove stale locks (ensure no processes are running first)
rm -f db/*.db-journal db/*.db-wal db/*.db-shm

# Restart the Python backend
cd mini-services/backend
source venv/bin/activate   # Linux
# venv\\Scripts\\activate    # Windows
python -m uvicorn index:app --host 0.0.0.0 --port 3001 --reload`}
            language="bash"
          />
        </CardContent>
      </Card>

      {/* Issue 5: Large file upload */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            Large File Upload Failures
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-slate-600">
            Uploads may fail due to body size limits, timeouts, or memory constraints. Adjust your configuration
            to handle larger files. Files over 10MB are automatically chunked into 5MB pieces by the frontend
            uploader, but server-side limits may still need adjustment.
          </p>
          <CodeBlock
            code={`# ── next.config.ts — increase the body size limit ──
module.exports = {
  experimental: {
    serverActions: {
      bodySizeLimit: '100mb',
    },
  },
}

# ── Nginx reverse proxy ──
# /etc/nginx/nginx.conf
# client_max_body_size 100M;

# ── Increase Node.js memory for large datasets ──
# Linux:
export NODE_OPTIONS="--max-old-space-size=4096"

# Windows:
set NODE_OPTIONS=--max-old-space-size=4096`}
            language="bash"
          />
        </CardContent>
      </Card>

      {/* Issue 6: venv activation on Windows */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            Virtual Environment Activation Fails on Windows
          </CardTitle>
        </CardHeader>
        <CardContent>
          <CodeBlock
            code={`# If you get "cannot be loaded because running scripts is disabled"

# Option 1: Change execution policy for current user
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Option 2: Activate with a one-time bypass
powershell -ExecutionPolicy Bypass -File venv\\Scripts\\activate.ps1

# Option 3: Use CMD instead of PowerShell
venv\\Scripts\\activate.bat`}
            language="powershell"
          />
        </CardContent>
      </Card>
    </div>
  )
}

// ─── Teams Tab Content ──────────────────────────────────────────────────────

interface Team {
  id: string
  name: string
  displayName: string | null
  description: string | null
  email: string | null
  teamType: string
  users: string
  isJoinable: boolean
}

function TeamsTab() {
  const [teams, setTeams] = useState<Team[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useState(() => {
    fetch('/api/teams')
      .then((r) => r.json())
      .then((data) => setTeams(Array.isArray(data) ? data : []))
      .catch(() => setTeams([]))
      .finally(() => setLoading(false))
  })

  const filtered = teams.filter(
    (t) =>
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      (t.displayName || '').toLowerCase().includes(search.toLowerCase())
  )

  const parseUsers = (usersJson: string): string[] => {
    try {
      return JSON.parse(usersJson)
    } catch {
      return []
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Teams</h2>
          <p className="text-sm text-slate-500">{teams.length} teams configured</p>
        </div>
        <Button><Plus className="h-4 w-4 mr-2" />Add Team</Button>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input placeholder="Search teams..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
      </div>

      {loading ? (
        <div className="space-y-3">{[...Array(3)].map((_, i) => (
          <Card key={i}><CardContent className="p-5 animate-pulse"><div className="h-5 w-32 rounded bg-slate-200 mb-3" /><div className="h-3 w-48 rounded bg-slate-200" /></CardContent></Card>
        ))}</div>
      ) : (
        <div className="space-y-4">
          {filtered.map((team) => {
            const members = parseUsers(team.users)
            return (
              <Card key={team.id} className="hover:shadow-md transition-shadow">
                <CardContent className="p-5">
                  <div className="flex items-start gap-4">
                    <div className="rounded-lg bg-slate-100 p-2.5 text-slate-600"><Building2 className="h-5 w-5" /></div>
                    <div>
                      <h3 className="font-semibold text-slate-900">{team.displayName || team.name}</h3>
                      {team.description && <p className="text-sm text-slate-500 mt-0.5">{team.description}</p>}
                      <div className="flex items-center gap-3 mt-2 flex-wrap text-xs text-slate-400">
                        <Badge variant="outline" className="text-xs">{team.teamType}</Badge>
                        {team.email && <span className="flex items-center gap-1"><Mail className="h-3 w-3" />{team.email}</span>}
                        <span className="flex items-center gap-1"><Users className="h-3 w-3" />{members.length} members</span>
                        <Badge variant={team.isJoinable ? 'secondary' : 'outline'} className="text-xs">{team.isJoinable ? 'Joinable' : 'Invite only'}</Badge>
                      </div>
                      {members.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">{members.map((m) => <Badge key={m} variant="secondary" className="text-xs">{m}</Badge>)}</div>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
          {filtered.length === 0 && <div className="text-center py-12 text-slate-400">No teams found.</div>}
        </div>
      )}
    </div>
  )
}

// ─── Main Local Setup Component ─────────────────────────────────────────────

export default function Settings() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-900 flex items-center gap-2">
            <Wrench className="h-5 w-5" />
            Local Setup
          </h2>
          <p className="text-sm text-slate-500">
            Install, configure, and deploy DataGuard locally with PostgreSQL integration.
          </p>
        </div>
      </div>

      <Tabs defaultValue="dataguard" className="w-full">
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="dataguard" className="flex items-center gap-1.5">
            <Zap className="h-4 w-4" />
            DataGuard Setup
          </TabsTrigger>
          <TabsTrigger value="postgresql" className="flex items-center gap-1.5">
            <Database className="h-4 w-4" />
            PostgreSQL Setup
          </TabsTrigger>
          <TabsTrigger value="prerequisites" className="flex items-center gap-1.5">
            <CheckCircle2 className="h-4 w-4" />
            Prerequisites
          </TabsTrigger>
          <TabsTrigger value="upload" className="flex items-center gap-1.5">
            <Upload className="h-4 w-4" />
            Data Upload
          </TabsTrigger>
          <TabsTrigger value="config" className="flex items-center gap-1.5">
            <Settings2 className="h-4 w-4" />
            Configuration
          </TabsTrigger>
          <TabsTrigger value="troubleshoot" className="flex items-center gap-1.5">
            <Wrench className="h-4 w-4" />
            Troubleshooting
          </TabsTrigger>
          <TabsTrigger value="teams" className="flex items-center gap-1.5">
            <Users className="h-4 w-4" />
            Teams
          </TabsTrigger>
        </TabsList>

        <TabsContent value="dataguard"><DataGuardSetupTab /></TabsContent>
        <TabsContent value="postgresql"><PostgreSQLTab /></TabsContent>
        <TabsContent value="prerequisites"><PrerequisitesTab /></TabsContent>
        <TabsContent value="upload"><DataUploadTab /></TabsContent>
        <TabsContent value="config"><ConfigurationTab /></TabsContent>
        <TabsContent value="troubleshoot"><TroubleshootingTab /></TabsContent>
        <TabsContent value="teams"><TeamsTab /></TabsContent>
      </Tabs>
    </div>
  )
}