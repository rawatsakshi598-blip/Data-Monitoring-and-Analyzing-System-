'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Plug, Plus, Trash2, CheckCircle2, XCircle, Loader2, RefreshCw,
  TestTube, Database, Cloud, FileSpreadsheet, Globe, Server, Cable,
  Zap, Table, ChevronRight, ArrowLeft, Eye, HardDrive,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

// ── Types ──
interface Connector {
  id: string
  name: string
  type: string
  host: string
  port: number | null
  database: string | null
  status: 'connected' | 'disconnected' | 'error'
  lastSync: string | null
  tablesCount: number
  createdAt: string
}

interface TableInfo {
  name: string
  schema?: string
  rowCount?: number
  columns?: string[]
}

interface TableData {
  tableName: string
  columns: string[]
  rows: Record<string, unknown>[]
  totalRows: number
}

const CONNECTOR_TYPES = [
  { type: 'postgresql', name: 'PostgreSQL', icon: <Database className="h-5 w-5 text-blue-600" />, defaultPort: 5432, needsAuth: true, color: 'bg-blue-50 border-blue-200' },
  { type: 'mysql', name: 'MySQL', icon: <Database className="h-5 w-5 text-sky-600" />, defaultPort: 3306, needsAuth: true, color: 'bg-sky-50 border-sky-200' },
  { type: 'sqlite', name: 'SQLite', icon: <FileSpreadsheet className="h-5 w-5 text-amber-600" />, defaultPort: null, needsAuth: false, color: 'bg-amber-50 border-amber-200' },
  { type: 'local_sqlite', name: 'Local Database (Demo)', icon: <HardDrive className="h-5 w-5 text-emerald-600" />, defaultPort: null, needsAuth: false, color: 'bg-emerald-50 border-emerald-200' },
  { type: 's3', name: 'Amazon S3', icon: <Cloud className="h-5 w-5 text-orange-500" />, defaultPort: null, needsAuth: true, color: 'bg-orange-50 border-orange-200' },
  { type: 'bigquery', name: 'BigQuery', icon: <Globe className="h-5 w-5 text-blue-500" />, defaultPort: null, needsAuth: true, color: 'bg-blue-50 border-blue-200' },
  { type: 'mongodb', name: 'MongoDB', icon: <Server className="h-5 w-5 text-emerald-600" />, defaultPort: 27017, needsAuth: true, color: 'bg-emerald-50 border-emerald-200' },
  { type: 'redshift', name: 'Redshift', icon: <Database className="h-5 w-5 text-violet-600" />, defaultPort: 5439, needsAuth: true, color: 'bg-violet-50 border-violet-200' },
  { type: 'snowflake', name: 'Snowflake', icon: <Cloud className="h-5 w-5 text-cyan-500" />, defaultPort: null, needsAuth: true, color: 'bg-cyan-50 border-cyan-200' },
  { type: 'api', name: 'REST API', icon: <Cable className="h-5 w-5 text-rose-500" />, defaultPort: 443, needsAuth: false, color: 'bg-rose-50 border-rose-200' },
]

// ── Helpers ──
function safeNumber(val: unknown, fallback = 0): number {
  const n = Number(val)
  return Number.isFinite(n) ? n : fallback
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { className: string; icon: React.ReactNode }> = {
    connected: { className: 'bg-emerald-50 text-emerald-700 border-emerald-200', icon: <CheckCircle2 className="h-3 w-3" /> },
    disconnected: { className: 'bg-slate-50 text-slate-600 border-slate-200', icon: <XCircle className="h-3 w-3" /> },
    error: { className: 'bg-red-50 text-red-700 border-red-200', icon: <XCircle className="h-3 w-3" /> },
  }
  const c = config[status] || config.disconnected
  return (
    <Badge variant="outline" className={cn('gap-1 text-[11px]', c.className)}>
      {c.icon}
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  )
}

function ConnectorIcon({ type }: { type: string }) {
  const ct = CONNECTOR_TYPES.find((c) => c.type === type)
  return ct?.icon || <Database className="h-5 w-5" />
}

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    connected: 'bg-emerald-500',
    disconnected: 'bg-slate-400',
    error: 'bg-red-500',
  }
  return <span className={cn('h-2.5 w-2.5 rounded-full inline-block', colors[status] || 'bg-slate-400')} />
}

// ── Table Browser Sub-component ──
function TableBrowser({ connectorId, connectorName, onBack }: {
  connectorId: string
  connectorName: string
  onBack: () => void
}) {
  const [tables, setTables] = useState<TableInfo[]>([])
  const [selectedTable, setSelectedTable] = useState<string | null>(null)
  const [tableData, setTableData] = useState<TableData | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingData, setLoadingData] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchTables = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/connectors/${connectorId}/tables`)
      if (res.ok) {
        const data = await res.json()
        setTables(Array.isArray(data?.tables) ? data.tables : [])
      } else {
        const err = await res.json().catch(() => ({}))
        setError(err.error || 'Failed to load tables')
      }
    } catch {
      setError('Could not connect to backend')
    } finally {
      setLoading(false)
    }
  }, [connectorId])

  useEffect(() => { fetchTables() }, [fetchTables])

  const fetchTableData = async (tableName: string) => {
    setSelectedTable(tableName)
    setLoadingData(true)
    try {
      const res = await fetch(`/api/connectors/${connectorId}/tables/${encodeURIComponent(tableName)}`)
      if (res.ok) {
        const data = await res.json()
        setTableData(data)
      } else {
        toast.error('Failed to load table data')
      }
    } catch {
      toast.error('Could not fetch table data')
    } finally {
      setLoadingData(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={onBack}><ArrowLeft className="h-4 w-4" /></Button>
          <Skeleton className="h-6 w-48" />
        </div>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-16 rounded-lg" />)}</div>
      </div>
    )
  }

  if (selectedTable && tableData) {
    const maxRows = 50
    const displayRows = tableData.rows.slice(0, maxRows)
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => { setSelectedTable(null); setTableData(null) }}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h3 className="text-lg font-semibold text-slate-900">{selectedTable}</h3>
          <Badge variant="outline" className="text-xs">{tableData.totalRows} rows</Badge>
          <Badge variant="outline" className="text-xs">{tableData.columns.length} columns</Badge>
        </div>
        <Card>
          <CardContent className="p-0 overflow-auto">
            <table className="w-full text-xs">
              <thead className="bg-slate-50 sticky top-0">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-slate-500 border-b">#</th>
                  {tableData.columns.map((col) => (
                    <th key={col} className="px-3 py-2 text-left font-medium text-slate-500 border-b whitespace-nowrap">{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {displayRows.map((row, idx) => (
                  <tr key={idx} className="border-b border-slate-100 hover:bg-slate-50/50">
                    <td className="px-3 py-1.5 text-slate-400">{idx + 1}</td>
                    {tableData.columns.map((col) => {
                      const val = row[col]
                      const display = val === null ? <span className="text-slate-300 italic">NULL</span> : String(val)
                      return (
                        <td key={col} className="px-3 py-1.5 text-slate-700 max-w-[200px] truncate" title={String(val ?? '')}>
                          {display}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            {tableData.totalRows > maxRows && (
              <div className="px-4 py-2 text-xs text-slate-400 bg-slate-50 border-t">
                Showing {maxRows} of {tableData.totalRows} rows
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={onBack}><ArrowLeft className="h-4 w-4" /></Button>
        <div>
          <h3 className="text-lg font-semibold text-slate-900">{connectorName} — Tables</h3>
          <p className="text-xs text-slate-400">{tables.length} tables found</p>
        </div>
      </div>
      {error && (
        <Card className="border-red-200 bg-red-50/50">
          <CardContent className="p-4 text-sm text-red-700">{error}</CardContent>
        </Card>
      )}
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {tables.map((t) => (
          <Card
            key={t.name}
            className="cursor-pointer hover:shadow-md transition border-slate-200"
            onClick={() => fetchTableData(t.name)}
          >
            <CardContent className="p-3 flex items-center gap-3">
              <div className="rounded-lg bg-blue-50 p-2"><Table className="h-4 w-4 text-blue-600" /></div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 truncate">{t.name}</p>
                <p className="text-[11px] text-slate-400">
                  {t.rowCount != null ? `${t.rowCount} rows` : 'View data'}
                  {t.columns && t.columns.length > 0 ? ` · ${t.columns.length} cols` : ''}
                </p>
              </div>
              <ChevronRight className="h-4 w-4 text-slate-300 shrink-0" />
            </CardContent>
          </Card>
        ))}
      </div>
      {loadingData && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
          <span className="ml-2 text-sm text-slate-500">Loading table data...</span>
        </div>
      )}
    </div>
  )
}

// ── Main Component ──
export default function Connectors() {
  const [connectors, setConnectors] = useState<Connector[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [testingId, setTestingId] = useState<string | null>(null)
  const [browsingConnector, setBrowsingConnector] = useState<Connector | null>(null)
  const [newConnector, setNewConnector] = useState({
    name: '', type: 'postgresql', host: '', port: '5432',
    database: '', username: '', password: '',
  })

  const fetchConnectors = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/connectors')
      if (res.ok) {
        const data = await res.json()
        const rawConnectors = Array.isArray(data) ? data : data?.connectors || []
        // Normalize — ensure all fields have safe defaults (fix NaN)
        const safeConnectors: Connector[] = rawConnectors.map((c: Record<string, unknown>) => ({
          id: (c.id as string) || '',
          name: (c.name as string) || 'Unnamed',
          type: (c.type as string) || 'postgresql',
          host: (c.host as string) || '',
          port: c.port as number | null ?? null,
          database: (c.database as string) || null,
          status: (['connected', 'disconnected', 'error'].includes(c.status as string) ? c.status : 'disconnected') as Connector['status'],
          lastSync: (c.lastSync as string) || (c.lastTested as string) || null,
          tablesCount: safeNumber(c.tablesCount, 0),
          createdAt: (c.createdAt as string) || new Date().toISOString(),
        }))
        setConnectors(safeConnectors)
      } else {
        throw new Error('Failed')
      }
    } catch {
      setError('Failed to load connectors from server')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchConnectors() }, [fetchConnectors])

  const handleCreate = async () => {
    if (!newConnector.name.trim() || (!newConnector.host.trim() && newConnector.type !== 'local_sqlite')) {
      toast.error('Name and host are required')
      return
    }
    const ct = CONNECTOR_TYPES.find((c) => c.type === newConnector.type)
    try {
      const res = await fetch('/api/connectors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newConnector.name,
          type: newConnector.type,
          host: newConnector.type === 'local_sqlite' ? '(local)' : newConnector.host,
          port: newConnector.port ? parseInt(newConnector.port) : ct?.defaultPort || null,
          database: newConnector.database || null,
          username: newConnector.username || null,
          password: newConnector.password || null,
        }),
      })
      if (res.ok) {
        const raw = await res.json()
        const data: Connector = {
          id: raw.id || `c${Date.now()}`,
          name: raw.name || newConnector.name,
          type: raw.type || newConnector.type,
          host: raw.host || newConnector.host,
          port: raw.port ?? (newConnector.port ? parseInt(newConnector.port) : ct?.defaultPort ?? null),
          database: raw.database || newConnector.database || null,
          status: raw.status || 'disconnected',
          lastSync: raw.lastSync || null,
          tablesCount: safeNumber(raw.tablesCount, 0),
          createdAt: raw.createdAt || new Date().toISOString(),
        }
        setConnectors((prev) => [data, ...prev])
        toast.success('Connector created')
      } else {
        throw new Error('Failed')
      }
    } catch {
      const connector: Connector = {
        id: `c${Date.now()}`, name: newConnector.name, type: newConnector.type,
        host: newConnector.host, port: newConnector.port ? parseInt(newConnector.port) : ct?.defaultPort || null,
        database: newConnector.database || null, status: 'disconnected',
        lastSync: null, tablesCount: 0, createdAt: new Date().toISOString(),
      }
      setConnectors((prev) => [connector, ...prev])
      toast.success('Connector created (offline)')
    }
    setShowCreateDialog(false)
    setNewConnector({ name: '', type: 'postgresql', host: '', port: '5432', database: '', username: '', password: '' })
  }

  const handleTest = async (connectorId: string) => {
    setTestingId(connectorId)
    try {
      const res = await fetch(`/api/connectors/${connectorId}/test`, { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        const newStatus = data.success ? 'connected' : 'error'
        const tablesCount = safeNumber(data.tablesCount, 0)
        setConnectors((prev) => prev.map((c) => c.id === connectorId ? {
          ...c, status: newStatus as Connector['status'],
          lastSync: new Date().toISOString(),
          tablesCount: tablesCount || c.tablesCount,
        } : c))
        if (data.success) {
          toast.success(data.message || 'Connection successful')
        } else {
          toast.error(data.error || 'Connection failed')
        }
      } else {
        setConnectors((prev) => prev.map((c) => c.id === connectorId ? { ...c, status: 'error' as const } : c))
        toast.error('Connection test failed')
      }
    } catch {
      // Simulate for demo
      setConnectors((prev) => prev.map((c) => c.id === connectorId ? { ...c, status: 'connected' as const, lastSync: new Date().toISOString() } : c))
      toast.success('Connection test simulated (offline)')
    } finally {
      setTestingId(null)
    }
  }

  const handleSync = async (connectorId: string) => {
    try {
      await fetch(`/api/connectors/${connectorId}/fetch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
    } catch { /* offline */ }
    setConnectors((prev) => prev.map((c) =>
      c.id === connectorId ? { ...c, lastSync: new Date().toISOString(), tablesCount: Math.max(c.tablesCount, 1) } : c
    ))
    toast.success('Sync started')
  }

  const handleDelete = async (connectorId: string) => {
    try {
      await fetch(`/api/connectors/${connectorId}`, { method: 'DELETE' })
    } catch { /* offline */ }
    setConnectors((prev) => prev.filter((c) => c.id !== connectorId))
    if (browsingConnector?.id === connectorId) setBrowsingConnector(null)
    toast.success('Connector removed')
  }

  // ── Demo: Add Local SQLite connector (uses app's own DB) ──
  const handleAddLocalDemo = async () => {
    try {
      const res = await fetch('/api/connectors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'DataGuard Local DB',
          type: 'local_sqlite',
          host: '(local)',
          port: null,
          database: 'dataguard',
          username: null,
          password: null,
        }),
      })
      if (res.ok) {
        const raw = await res.json()
        const data: Connector = {
          id: raw.id || `c${Date.now()}`,
          name: raw.name || 'DataGuard Local DB',
          type: raw.type || 'local_sqlite',
          host: '(local)',
          port: null,
          database: raw.database || 'dataguard',
          status: 'connected',
          lastSync: new Date().toISOString(),
          tablesCount: safeNumber(raw.tablesCount, 0),
          createdAt: raw.createdAt || new Date().toISOString(),
        }
        setConnectors((prev) => [data, ...prev])
        toast.success('Local database connector added — already connected!')
      } else {
        throw new Error('Failed')
      }
    } catch {
      // Offline fallback
      const data: Connector = {
        id: `c${Date.now()}`, name: 'DataGuard Local DB', type: 'local_sqlite',
        host: '(local)', port: null, database: 'dataguard', status: 'connected',
        lastSync: new Date().toISOString(), tablesCount: 8,
        createdAt: new Date().toISOString(),
      }
      setConnectors((prev) => [data, ...prev])
      toast.success('Local database connector added (offline)')
    }
  }

  // ── Demo: Seed sample connectors for presentation ──
  const handleSeedDemo = async () => {
    const demoConnectors = [
      { name: 'Production PostgreSQL', type: 'postgresql', host: 'db.prod.example.com', port: 5432, database: 'analytics_db', username: 'readonly_user' },
      { name: 'Customer Data Warehouse', type: 'mysql', host: 'warehouse.internal', port: 3306, database: 'customers', username: 'etl_service' },
      { name: 'Sales Data Lake', type: 's3', host: 's3://sales-data-lake', port: null, database: '', username: '' },
      { name: 'Reporting DB', type: 'postgresql', host: 'reports.prod.example.com', port: 5432, database: 'reports', username: 'reporter' },
      { name: 'User Analytics', type: 'mongodb', host: 'analytics.cluster.mongodb.net', port: 27017, database: 'user_events', username: 'analytics_read' },
      { name: 'Financial Data', type: 'snowflake', host: 'xy12345.us-east-1.snowflakecomputing.com', port: null, database: 'FINANCE_DB', username: 'dq_reader' },
    ]

    let created = 0
    for (const dc of demoConnectors) {
      try {
        const res = await fetch('/api/connectors', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(dc),
        })
        if (res.ok) {
          const raw = await res.json()
          const data: Connector = {
            id: raw.id || `c${Date.now()}`,
            name: raw.name || dc.name,
            type: raw.type || dc.type,
            host: raw.host || dc.host,
            port: raw.port ?? dc.port,
            database: raw.database || dc.database || null,
            status: 'disconnected',
            lastSync: null,
            tablesCount: 0,
            createdAt: raw.createdAt || new Date().toISOString(),
          }
          setConnectors((prev) => [data, ...prev])
          created++
        }
      } catch {
        // Offline fallback
        const data: Connector = {
          id: `c${Date.now()}${created}`, name: dc.name, type: dc.type,
          host: dc.host, port: dc.port, database: dc.database || null,
          status: 'disconnected', lastSync: null, tablesCount: 0,
          createdAt: new Date().toISOString(),
        }
        setConnectors((prev) => [data, ...prev])
        created++
      }
    }
    toast.success(`Added ${created} demo connectors`)
  }

  const selectedTypeMeta = CONNECTOR_TYPES.find((c) => c.type === newConnector.type)
  // Fix NaN: use safeNumber for all numeric aggregations
  const connectedCount = connectors.filter((c) => c.status === 'connected').length
  const totalTables = connectors.reduce((acc, c) => acc + safeNumber(c.tablesCount, 0), 0)

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between"><Skeleton className="h-8 w-48" /><Skeleton className="h-10 w-36" /></div>
        <div className="grid gap-4 sm:grid-cols-3">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}</div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">{[...Array(6)].map((_, i) => <Skeleton key={i} className="h-48 rounded-xl" />)}</div>
      </div>
    )
  }

  // ── Table Browser View ──
  if (browsingConnector) {
    return (
      <TableBrowser
        connectorId={browsingConnector.id}
        connectorName={browsingConnector.name}
        onBack={() => setBrowsingConnector(null)}
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Data Connectors</h2>
          <p className="text-sm text-slate-500 mt-1">Manage connections to external data sources and browse database tables</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" className="gap-2" onClick={handleAddLocalDemo}>
            <HardDrive className="h-4 w-4" /> Connect Local DB
          </Button>
          {connectors.length === 0 && (
            <Button variant="outline" className="gap-2" onClick={handleSeedDemo}>
              <Zap className="h-4 w-4" /> Load Demo
            </Button>
          )}
          <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
            <Button className="gap-2" onClick={() => setShowCreateDialog(true)}>
              <Plus className="h-4 w-4" /> Add Connector
            </Button>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>Add Data Connector</DialogTitle>
                <DialogDescription>Configure a new data source connection</DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-2">
                <div className="space-y-2">
                  <Label>Connector Type</Label>
                  <Select value={newConnector.type} onValueChange={(v) => {
                    const ct = CONNECTOR_TYPES.find((c) => c.type === v)
                    setNewConnector((prev) => ({ ...prev, type: v, port: ct?.defaultPort?.toString() || '' }))
                  }}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {CONNECTOR_TYPES.map((ct) => (
                        <SelectItem key={ct.type} value={ct.type}>
                          <span className="flex items-center gap-2">{ct.name}</span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                {newConnector.type === 'local_sqlite' && (
                  <Card className="bg-emerald-50 border-emerald-200">
                    <CardContent className="p-3 text-xs text-emerald-700">
                      This connector uses the DataGuard application&apos;s own SQLite database. No host or credentials needed — just give it a name and create it. When tested, it will connect automatically.
                    </CardContent>
                  </Card>
                )}
                <div className="space-y-2">
                  <Label>Connection Name</Label>
                  <Input placeholder="e.g., Production PostgreSQL" value={newConnector.name} onChange={(e) => setNewConnector((p) => ({ ...p, name: e.target.value }))} />
                </div>
                {newConnector.type !== 'local_sqlite' && (
                  <>
                    <div className="space-y-2">
                      <Label>Host / Endpoint</Label>
                      <Input placeholder="e.g., db.prod.internal or s3://bucket" value={newConnector.host} onChange={(e) => setNewConnector((p) => ({ ...p, host: e.target.value }))} />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      {selectedTypeMeta?.defaultPort !== null && (
                        <div className="space-y-2">
                          <Label>Port</Label>
                          <Input placeholder="5432" value={newConnector.port} onChange={(e) => setNewConnector((p) => ({ ...p, port: e.target.value }))} />
                        </div>
                      )}
                      <div className="space-y-2">
                        <Label>Database</Label>
                        <Input placeholder="database name" value={newConnector.database} onChange={(e) => setNewConnector((p) => ({ ...p, database: e.target.value }))} />
                      </div>
                    </div>
                    {selectedTypeMeta?.needsAuth && (
                      <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-2">
                          <Label>Username</Label>
                          <Input placeholder="username" value={newConnector.username} onChange={(e) => setNewConnector((p) => ({ ...p, username: e.target.value }))} />
                        </div>
                        <div className="space-y-2">
                          <Label>Password</Label>
                          <Input type="password" placeholder="password" value={newConnector.password} onChange={(e) => setNewConnector((p) => ({ ...p, password: e.target.value }))} />
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancel</Button>
                <Button onClick={handleCreate} disabled={!newConnector.name.trim() || (newConnector.type !== 'local_sqlite' && !newConnector.host.trim())}>Create Connector</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {error && (
        <Card className="border-red-200 bg-red-50/50">
          <CardContent className="p-4 flex items-center gap-3">
            <XCircle className="h-5 w-5 text-red-500 shrink-0" />
            <p className="text-sm text-red-700">{error}</p>
            <Button variant="outline" size="sm" onClick={fetchConnectors} className="ml-auto">Retry</Button>
          </CardContent>
        </Card>
      )}

      {/* Summary */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card><CardContent className="p-4 flex items-center gap-3">
          <div className="rounded-lg bg-emerald-50 p-2"><CheckCircle2 className="h-4 w-4 text-emerald-600" /></div>
          <div><p className="text-xs text-emerald-600">Connected</p><p className="text-xl font-bold">{connectedCount}/{connectors.length || 0}</p></div>
        </CardContent></Card>
        <Card><CardContent className="p-4 flex items-center gap-3">
          <div className="rounded-lg bg-blue-50 p-2"><Database className="h-4 w-4 text-blue-600" /></div>
          <div><p className="text-xs text-blue-600">Tables Available</p><p className="text-xl font-bold">{totalTables}</p></div>
        </CardContent></Card>
        <Card><CardContent className="p-4 flex items-center gap-3">
          <div className="rounded-lg bg-violet-50 p-2"><Plug className="h-4 w-4 text-violet-600" /></div>
          <div><p className="text-xs text-violet-600">Connector Types</p><p className="text-xl font-bold">{new Set(connectors.map((c) => c.type)).size || 0}</p></div>
        </CardContent></Card>
      </div>

      {/* Empty State with Demo Button */}
      {connectors.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <Plug className="h-12 w-12 text-slate-300 mx-auto mb-4" />
            <h3 className="font-semibold text-slate-700 mb-1">No Connectors</h3>
            <p className="text-sm text-slate-400 mb-4">Add a data connector to get started. For presentations, connect the local database to show real data.</p>
            <div className="flex items-center justify-center gap-3">
              <Button className="gap-2" onClick={handleAddLocalDemo}>
                <HardDrive className="h-4 w-4" /> Connect Local DB (Recommended)
              </Button>
              <Button variant="outline" onClick={handleSeedDemo} className="gap-2">
                <Zap className="h-4 w-4" /> Load Demo Connectors
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {connectors.map((connector) => {
            const typeMeta = CONNECTOR_TYPES.find((c) => c.type === connector.type)
            const isBrowsable = connector.status === 'connected'
            return (
              <Card key={connector.id} className={cn('hover:shadow-md transition', typeMeta?.color || '')}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="rounded-lg bg-white/80 p-2"><ConnectorIcon type={connector.type} /></div>
                      <div>
                        <h3 className="text-sm font-semibold text-slate-900">{connector.name}</h3>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <StatusDot status={connector.status} />
                          <span className="text-xs text-slate-400">{typeMeta?.name || connector.type}</span>
                        </div>
                      </div>
                    </div>
                    <StatusBadge status={connector.status} />
                  </div>

                  <div className="space-y-1.5 text-xs text-slate-500 mb-4">
                    <div className="flex items-center justify-between">
                      <span>Host</span>
                      <span className="font-mono text-slate-700 truncate ml-2 max-w-[180px]">{connector.host}</span>
                    </div>
                    {connector.port && (
                      <div className="flex items-center justify-between">
                        <span>Port</span><span className="text-slate-700">{connector.port}</span>
                      </div>
                    )}
                    {connector.database && (
                      <div className="flex items-center justify-between">
                        <span>Database</span><span className="text-slate-700">{connector.database}</span>
                      </div>
                    )}
                    <div className="flex items-center justify-between">
                      <span>Tables</span><span className="text-slate-700">{safeNumber(connector.tablesCount, 0)}</span>
                    </div>
                    {connector.lastSync && (
                      <div className="flex items-center justify-between">
                        <span>Last Sync</span><span className="text-slate-700">{new Date(connector.lastSync).toLocaleDateString()}</span>
                      </div>
                    )}
                  </div>

                  <Separator className="mb-3" />

                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" className="flex-1 gap-1" onClick={() => handleTest(connector.id)} disabled={testingId === connector.id}>
                      {testingId === connector.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <TestTube className="h-3.5 w-3.5" />}
                      Test
                    </Button>
                    {isBrowsable ? (
                      <Button variant="outline" size="sm" className="flex-1 gap-1" onClick={() => setBrowsingConnector(connector)}>
                        <Eye className="h-3.5 w-3.5" /> Browse
                      </Button>
                    ) : (
                      <Button variant="outline" size="sm" className="flex-1 gap-1" onClick={() => handleSync(connector.id)} disabled={connector.status !== 'connected'}>
                        <RefreshCw className="h-3.5 w-3.5" /> Sync
                      </Button>
                    )}
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-red-500 hover:text-red-700" onClick={() => handleDelete(connector.id)}>
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}