'use client'

import { useEffect, useState } from 'react'
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
  ExternalLink,
  BookOpen,
  Upload,
  FileText,
  HardDrive,
  Settings2,
  Wrench,
  Zap,
  FolderOpen,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { toast } from 'sonner'

// ─── Types ───────────────────────────────────────────────────────────────────

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

// ─── Teams Tab Content ──────────────────────────────────────────────────────

function TeamsTab() {
  const [teams, setTeams] = useState<Team[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    fetch('/api/teams')
      .then((r) => r.json())
      .then((data) => setTeams(Array.isArray(data) ? data : []))
      .catch(() => setTeams([]))
      .finally(() => setLoading(false))
  }, [])

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
          <h2 className="text-xl font-semibold text-slate-900">Teams & Settings</h2>
          <p className="text-sm text-slate-500">
            {teams.length} teams configured
          </p>
        </div>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Add Team
        </Button>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input
          placeholder="Search teams..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-5 animate-pulse">
                <div className="h-5 w-32 rounded bg-slate-200 mb-3" />
                <div className="h-3 w-48 rounded bg-slate-200" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((team) => {
            const members = parseUsers(team.users)
            return (
              <Card key={team.id} className="hover:shadow-md transition-shadow">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4">
                      <div className="rounded-lg bg-slate-100 p-2.5 text-slate-600">
                        <Building2 className="h-5 w-5" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-slate-900">
                          {team.displayName || team.name}
                        </h3>
                        {team.description && (
                          <p className="text-sm text-slate-500 mt-0.5">{team.description}</p>
                        )}
                        <div className="flex items-center gap-3 mt-2 flex-wrap text-xs text-slate-400">
                          <Badge variant="outline" className="text-xs">
                            {team.teamType}
                          </Badge>
                          {team.email && (
                            <span className="flex items-center gap-1">
                              <Mail className="h-3 w-3" />
                              {team.email}
                            </span>
                          )}
                          <span className="flex items-center gap-1">
                            <Users className="h-3 w-3" />
                            {members.length} members
                          </span>
                          <Badge
                            variant={team.isJoinable ? 'secondary' : 'outline'}
                            className="text-xs"
                          >
                            {team.isJoinable ? 'Joinable' : 'Invite only'}
                          </Badge>
                        </div>
                        {members.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {members.map((m) => (
                              <Badge key={m} variant="secondary" className="text-xs">
                                {m}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
          {filtered.length === 0 && (
            <div className="text-center py-12 text-slate-400">No teams found.</div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Local Setup Guide Tab Content ──────────────────────────────────────────

function LocalSetupGuideTab() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold text-slate-900 flex items-center gap-2">
          <BookOpen className="h-5 w-5" />
          Local Setup Guide
        </h2>
        <p className="text-sm text-slate-500 mt-1">
          Deploy DataGuard locally on your Linux machine with this step-by-step guide.
        </p>
      </div>

      {/* Section 1: Prerequisites */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            Section 1: Prerequisites
          </CardTitle>
          <CardDescription>Make sure your system meets these requirements before starting.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-2 sm:grid-cols-2">
            {[
              { label: 'Operating System', value: 'Linux (Ubuntu 20.04+, Debian 11+, Fedora 36+, Arch Linux)' },
              { label: 'Runtime', value: 'Node.js 18+ or Bun runtime' },
              { label: 'Version Control', value: 'Git' },
              { label: 'RAM (minimum)', value: '4GB (8GB recommended)' },
              { label: 'Disk Space', value: '2GB minimum' },
              { label: 'Network', value: 'Internet access for dependency installation' },
            ].map((item) => (
              <div
                key={item.label}
                className="flex flex-col rounded-lg border border-slate-200 p-3 gap-1"
              >
                <span className="text-xs font-medium text-slate-500">{item.label}</span>
                <span className="text-sm text-slate-800">{item.value}</span>
              </div>
            ))}
          </div>
          <CodeBlock
            code={`# Verify your system
node --version   # v18+ required
bun --version    # or use Bun
git --version
free -h          # check available RAM`}
            language="bash"
          />
        </CardContent>
      </Card>

      {/* Section 2: Quick Start */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Zap className="h-4 w-4 text-amber-500" />
            Section 2: Quick Start
          </CardTitle>
          <CardDescription>Get DataGuard up and running in 5 simple steps.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* Step 1 */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="secondary" className="font-mono">Step 1</Badge>
              <span className="text-sm font-medium text-slate-800">Clone and Setup</span>
            </div>
            <CodeBlock
              code={`git clone https://github.com/your-org/dataguard.git dataguard
cd dataguard`}
              language="bash"
            />
          </div>

          {/* Step 2 */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="secondary" className="font-mono">Step 2</Badge>
              <span className="text-sm font-medium text-slate-800">Install Dependencies</span>
            </div>
            <CodeBlock
              code={`bun install   # recommended — or use: npm install`}
              language="bash"
            />
          </div>

          {/* Step 3 */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="secondary" className="font-mono">Step 3</Badge>
              <span className="text-sm font-medium text-slate-800">Setup Database</span>
            </div>
            <CodeBlock
              code={`bun run db:push`}
              language="bash"
            />
            <p className="text-xs text-slate-500 mt-1">
              This creates the SQLite database and runs all migrations using Prisma.
            </p>
          </div>

          {/* Step 4 */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="secondary" className="font-mono">Step 4</Badge>
              <span className="text-sm font-medium text-slate-800">Start Development Server</span>
            </div>
            <CodeBlock
              code={`bun run dev`}
              language="bash"
            />
            <p className="text-xs text-slate-500 mt-1">
              The development server starts with hot-reload enabled.
            </p>
          </div>

          {/* Step 5 */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="secondary" className="font-mono">Step 5</Badge>
              <span className="text-sm font-medium text-slate-800">Open in Browser</span>
            </div>
            <CodeBlock
              code={`http://localhost:3000`}
              language="url"
            />
          </div>
        </CardContent>
      </Card>

      {/* Section 3: Data Upload Methods */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Upload className="h-4 w-4 text-blue-500" />
            Section 3: Data Upload Methods
          </CardTitle>
          <CardDescription>Three ways to ingest data into DataGuard.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* Method 1: UI Upload */}
          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-1 flex items-center gap-2">
              <Badge variant="outline" className="text-xs">Method 1</Badge>
              UI Upload (Drag-and-Drop)
            </h4>
            <p className="text-sm text-slate-600 mb-2">
              Navigate to the <span className="font-medium">Ingest Data</span> page in the sidebar. Drag and drop
              your files or click to browse. Supports <strong>CSV</strong>, <strong>JSON</strong>, and <strong>Excel</strong> files
              up to <strong>100MB</strong>.
            </p>
            <div className="flex gap-2 flex-wrap">
              <Badge variant="secondary">.csv</Badge>
              <Badge variant="secondary">.json</Badge>
              <Badge variant="secondary">.xlsx</Badge>
              <Badge variant="secondary">.xls</Badge>
              <Badge className="bg-slate-100 text-slate-600 hover:bg-slate-100">Max 100MB</Badge>
            </div>
          </div>

          {/* Method 2: API Upload */}
          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-1 flex items-center gap-2">
              <Badge variant="outline" className="text-xs">Method 2</Badge>
              API Upload (curl)
            </h4>
            <p className="text-sm text-slate-600 mb-2">
              Use the REST API to upload files programmatically.
            </p>
            <CodeBlock
              code={`curl -X POST http://localhost:3000/api/ingest \\
  -F "file=@/path/to/your/data.csv" \\
  -F "tableName=my_dataset" \\
  -F "serviceName=My Data"`}
              language="bash"
            />
          </div>

          {/* Method 3: Bulk Upload */}
          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-1 flex items-center gap-2">
              <Badge variant="outline" className="text-xs">Method 3</Badge>
              Bulk Upload (Multiple Files)
            </h4>
            <p className="text-sm text-slate-600 mb-2">
              Upload multiple files at once using a shell loop.
            </p>
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
          </div>
        </CardContent>
      </Card>

      {/* Section 4: Chunked Upload for Large Files */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <HardDrive className="h-4 w-4 text-purple-500" />
            Section 4: Chunked Upload for Large Files
          </CardTitle>
          <CardDescription>
            Files larger than 10MB are automatically chunked into 5MB pieces. The UI handles
            this transparently. For API usage, use the script below.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
            <span>
              The frontend automatically splits files &gt; 10MB into 5MB chunks. This section
              is only needed for programmatic API uploads.
            </span>
          </div>
          <CodeBlock
            code={`#!/bin/bash
# chunked-upload.sh — Upload large files in chunks

FILE="large_dataset.csv"
TABLE_NAME="large_data"
CHUNK_SIZE=5242880  # 5MB
TOTAL_SIZE=$(stat -c%s "$FILE")
CHUNKS=$(( (TOTAL_SIZE + CHUNK_SIZE - 1) / CHUNK_SIZE ))
FILE_ID=$(uuidgen)

echo "Uploading $FILE ($(( TOTAL_SIZE / 1048576 ))MB) in $CHUNKS chunks..."

for i in $(seq 0 $((CHUNKS - 1))); do
  OFFSET=$((i * CHUNK_SIZE))
  echo "  Chunk $(( i + 1 ))/$CHUNKS (offset: $OFFSET)"

  dd if="$FILE" bs=1 skip=$OFFSET count=$CHUNK_SIZE 2>/dev/null | \\
  curl -s -X POST http://localhost:3000/api/ingest \\
    -F "file=@-" \\
    -F "chunkIndex=$i" \\
    -F "totalChunks=$CHUNKS" \\
    -F "fileId=$FILE_ID" \\
    -F "fileName=$FILE" \\
    -F "tableName=$TABLE_NAME"
done

echo "Upload complete!"`}
            language="bash"
          />
        </CardContent>
      </Card>

      {/* Section 5: Data Format Examples */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="h-4 w-4 text-green-500" />
            Section 5: Data Format Examples
          </CardTitle>
          <CardDescription>Supported file formats and example structures.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* CSV */}
          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-1 flex items-center gap-2">
              <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 text-xs">CSV</Badge>
              Comma-Separated Values
            </h4>
            <CodeBlock
              code={`id,name,email,department,salary,join_date
1,Alice Chen,alice@example.com,Engineering,95000,2022-03-15
2,Bob Smith,bob@example.com,Marketing,72000,2021-08-01
3,Carol Davis,carol@example.com,Engineering,88000,2023-01-10
4,David Lee,david@example.com,Sales,67000,2020-11-20`}
              language="csv"
            />
          </div>

          {/* JSON */}
          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-1 flex items-center gap-2">
              <Badge className="bg-amber-100 text-amber-700 hover:bg-amber-100 text-xs">JSON</Badge>
              JSON Array of Objects
            </h4>
            <CodeBlock
              code={`[
  {
    "id": 1,
    "name": "Alice Chen",
    "email": "alice@example.com",
    "department": "Engineering",
    "salary": 95000,
    "join_date": "2022-03-15"
  },
  {
    "id": 2,
    "name": "Bob Smith",
    "email": "bob@example.com",
    "department": "Marketing",
    "salary": 72000,
    "join_date": "2021-08-01"
  },
  {
    "id": 3,
    "name": "Carol Davis",
    "email": "carol@example.com",
    "department": "Engineering",
    "salary": 88000,
    "join_date": "2023-01-10"
  }
]`}
              language="json"
            />
          </div>

          {/* Excel */}
          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-1 flex items-center gap-2">
              <Badge className="bg-teal-100 text-teal-700 hover:bg-teal-100 text-xs">Excel</Badge>
              Microsoft Excel Spreadsheets
            </h4>
            <p className="text-sm text-slate-600 mb-2">
              Both <strong>.xlsx</strong> (Excel 2007+) and <strong>.xls</strong> (legacy) formats are supported.
              The first row is treated as column headers, same as CSV.
            </p>
            <div className="flex gap-2 flex-wrap">
              <Badge variant="secondary">.xlsx</Badge>
              <Badge variant="secondary">.xls</Badge>
              <Badge className="bg-slate-100 text-slate-600 hover:bg-slate-100">First row = headers</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Section 6: Production Deployment */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Terminal className="h-4 w-4 text-slate-700" />
            Section 6: Production Deployment
          </CardTitle>
          <CardDescription>Deploy DataGuard for production use on your Linux server.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-1">Build for Production</h4>
            <CodeBlock
              code={`# Build the optimized production bundle
bun run build`}
              language="bash"
            />
          </div>

          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-1">Start Production Server</h4>
            <CodeBlock
              code={`# Start the production server
bun run start`}
              language="bash"
            />
          </div>

          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-1">Process Management with PM2</h4>
            <p className="text-sm text-slate-600 mb-2">
              Use PM2 for automatic restarts, logging, and process monitoring.
            </p>
            <CodeBlock
              code={`# Install PM2 globally
npm install -g pm2

# Start DataGuard as a managed process
pm2 start npm --name "dataguard" -- start

# Save the process list for auto-restart on reboot
pm2 save
pm2 startup

# Monitor the application
pm2 monit
pm2 logs dataguard`}
              language="bash"
            />
          </div>

          <div>
            <h4 className="text-sm font-semibold text-slate-800 mb-1">Reverse Proxy (Nginx)</h4>
            <CodeBlock
              code={`# /etc/nginx/sites-available/dataguard
server {
    listen 80;
    server_name dataguard.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_cache_bypass $http_upgrade;
    }
}`}
              language="nginx"
            />
          </div>
        </CardContent>
      </Card>

      {/* Section 7: Configuration */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Settings2 className="h-4 w-4 text-slate-600" />
            Section 7: Configuration
          </CardTitle>
          <CardDescription>Environment variables for customizing your DataGuard instance.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-slate-600">
            Create a <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs font-mono">.env</code> file
            in the project root or export these variables directly:
          </p>
          <CodeBlock
            code={`# .env — DataGuard Configuration

# Database (SQLite)
DATABASE_URL="file:./db/custom.db"

# Application
NEXT_PUBLIC_APP_NAME="DataGuard"
PORT=3000

# Optional: Authentication
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="your-secret-key-here"

# Optional: Logging
LOG_LEVEL="info"`}
            language="env"
          />
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800 flex items-start gap-2">
            <FolderOpen className="h-4 w-4 mt-0.5 shrink-0" />
            <span>
              The <code className="font-mono">.env</code> file is not committed to Git. Use{' '}
              <code className="font-mono">.env.example</code> as a template for team setups.
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Section 8: Troubleshooting */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Wrench className="h-4 w-4 text-red-500" />
            Section 8: Troubleshooting
          </CardTitle>
          <CardDescription>Common issues and how to resolve them.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Issue 1 */}
          <div className="rounded-lg border border-slate-200 p-4 space-y-2">
            <h4 className="text-sm font-semibold text-slate-800 flex items-center gap-2">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
              Port 3000 is already in use
            </h4>
            <p className="text-sm text-slate-600">
              Another process is using port 3000. Kill it or use a different port.
            </p>
            <CodeBlock
              code={`# Find the process using port 3000
lsof -i :3000
# or
ss -tlnp | grep 3000

# Kill the process
kill -9 <PID>

# Or start on a different port
PORT=3001 bun run dev`}
              language="bash"
            />
          </div>

          {/* Issue 2 */}
          <div className="rounded-lg border border-slate-200 p-4 space-y-2">
            <h4 className="text-sm font-semibold text-slate-800 flex items-center gap-2">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
              Database locked errors
            </h4>
            <p className="text-sm text-slate-600">
              SQLite uses file-level locking. These errors occur with concurrent writes.
            </p>
            <CodeBlock
              code={`# Check for stale lock files
ls -la db/*.db-journal
ls -la db/*.db-wal
ls -la db/*.db-shm

# Remove stale locks (make sure no processes are running)
rm -f db/*.db-journal db/*.db-wal db/*.db-shm

# Retry the operation
bun run db:push`}
              language="bash"
            />
          </div>

          {/* Issue 3 */}
          <div className="rounded-lg border border-slate-200 p-4 space-y-2">
            <h4 className="text-sm font-semibold text-slate-800 flex items-center gap-2">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
              Large file upload failures
            </h4>
            <p className="text-sm text-slate-600">
              Uploads may fail due to body size limits or timeouts. Adjust your configuration.
            </p>
            <CodeBlock
              code={`# In next.config.ts — increase the body size limit
module.exports = {
  experimental: {
    serverActions: {
      bodySizeLimit: '100mb',
    },
  },
}

# If using Nginx reverse proxy, also increase client_max_body_size
# /etc/nginx/nginx.conf
# client_max_body_size 100M;

# Restart nginx
sudo systemctl restart nginx`}
              language="bash"
            />
          </div>

          {/* Issue 4 */}
          <div className="rounded-lg border border-slate-200 p-4 space-y-2">
            <h4 className="text-sm font-semibold text-slate-800 flex items-center gap-2">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
              Memory issues with huge datasets
            </h4>
            <p className="text-sm text-slate-600">
              Processing very large files may exhaust memory. Use chunked uploads and limit batch sizes.
            </p>
            <CodeBlock
              code={`# Increase Node.js memory limit
export NODE_OPTIONS="--max-old-space-size=4096"  # 4GB

# Or with bun
bun run dev --max-old-space-size=4096

# Monitor memory usage
watch -n 1 'free -h && ps aux | grep node'

# For datasets > 1GB, consider:
# 1. Splitting into smaller files before upload
# 2. Using the chunked upload API (Section 4)
# 3. Upgrading to a machine with more RAM`}
              language="bash"
            />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// ─── Main Settings Component ────────────────────────────────────────────────

export default function Settings() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Settings</h2>
          <p className="text-sm text-slate-500">
            Manage teams and local deployment configuration.
          </p>
        </div>
      </div>

      <Tabs defaultValue="guide" className="w-full">
        <TabsList>
          <TabsTrigger value="guide" className="flex items-center gap-1.5">
            <BookOpen className="h-4 w-4" />
            Local Setup Guide
          </TabsTrigger>
          <TabsTrigger value="teams" className="flex items-center gap-1.5">
            <Users className="h-4 w-4" />
            Teams
          </TabsTrigger>
        </TabsList>

        <TabsContent value="guide">
          <LocalSetupGuideTab />
        </TabsContent>

        <TabsContent value="teams">
          <TeamsTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
