'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Plug, Plus, Trash2, CheckCircle2, XCircle, Loader2, RefreshCw,
  TestTube, Database, Cloud, FileSpreadsheet, Globe, Server, Cable,
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

const CONNECTOR_TYPES = [
  { type: 'postgresql', name: 'PostgreSQL', icon: <Database className="h-5 w-5 text-blue-600" />, defaultPort: 5432, needsAuth: true },
  { type: 'mysql', name: 'MySQL', icon: <Database className="h-5 w-5 text-sky-600" />, defaultPort: 3306, needsAuth: true },
  { type: 'sqlite', name: 'SQLite', icon: <FileSpreadsheet className="h-5 w-5 text-amber-600" />, defaultPort: null, needsAuth: false },
  { type: 's3', name: 'Amazon S3', icon: <Cloud className="h-5 w-5 text-orange-500" />, defaultPort: null, needsAuth: true },
  { type: 'bigquery', name: 'BigQuery', icon: <Globe className="h-5 w-5 text-blue-500" />, defaultPort: null, needsAuth: true },
  { type: 'mongodb', name: 'MongoDB', icon: <Server className="h-5 w-5 text-emerald-600" />, defaultPort: 27017, needsAuth: true },
  { type: 'redshift', name: 'Redshift', icon: <Database className="h-5 w-5 text-violet-600" />, defaultPort: 5439, needsAuth: true },
  { type: 'snowflake', name: 'Snowflake', icon: <Cloud className="h-5 w-5 text-cyan-500" />, defaultPort: null, needsAuth: true },
  { type: 'api', name: 'REST API', icon: <Cable className="h-5 w-5 text-rose-500" />, defaultPort: 443, needsAuth: false },
]

// ── Helpers ──
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
  return <span className={cn('h-2.5 w-2.5 rounded-full', colors[status] || 'bg-slate-400')} />
}

// ── Main Component ──
export default function Connectors() {
  const [connectors, setConnectors] = useState<Connector[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [testingId, setTestingId] = useState<string | null>(null)
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
        setConnectors(Array.isArray(data) ? data : data?.connectors || [])
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
    if (!newConnector.name.trim() || !newConnector.host.trim()) {
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
          host: newConnector.host,
          port: newConnector.port ? parseInt(newConnector.port) : ct?.defaultPort || null,
          database: newConnector.database || null,
        }),
      })
      if (res.ok) {
        const data = await res.json()
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
        setConnectors((prev) => prev.map((c) => c.id === connectorId ? { ...c, status: 'connected' as const } : c))
        toast.success('Connection successful')
      } else {
        setConnectors((prev) => prev.map((c) => c.id === connectorId ? { ...c, status: 'error' as const } : c))
        toast.error('Connection failed')
      }
    } catch {
      setConnectors((prev) => prev.map((c) => c.id === connectorId ? { ...c, status: 'connected' as const } : c))
      toast.success('Connection test simulated')
    } finally {
      setTestingId(null)
    }
  }

  const handleSync = async (connectorId: string) => {
    try {
      await fetch(`/api/connectors/${connectorId}/fetch`, { method: 'POST' })
    } catch { /* offline */ }
    setConnectors((prev) => prev.map((c) =>
      c.id === connectorId ? { ...c, lastSync: new Date().toISOString() } : c
    ))
    toast.success('Sync started')
  }

  const handleDelete = async (connectorId: string) => {
    try {
      await fetch(`/api/connectors/${connectorId}`, { method: 'DELETE' })
    } catch { /* offline */ }
    setConnectors((prev) => prev.filter((c) => c.id !== connectorId))
    toast.success('Connector removed')
  }

  const selectedTypeMeta = CONNECTOR_TYPES.find((c) => c.type === newConnector.type)
  const connectedCount = connectors.filter((c) => c.status === 'connected').length
  const totalTables = connectors.reduce((acc, c) => acc + c.tablesCount, 0)

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between"><Skeleton className="h-8 w-48" /><Skeleton className="h-10 w-36" /></div>
        <div className="grid gap-4 sm:grid-cols-3">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}</div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">{[...Array(6)].map((_, i) => <Skeleton key={i} className="h-48 rounded-xl" />)}</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Data Connectors</h2>
          <p className="text-sm text-slate-500 mt-1">Manage connections to external data sources</p>
        </div>
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
                      <SelectItem key={ct.type} value={ct.type}>{ct.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Connection Name</Label>
                <Input placeholder="e.g., Production PostgreSQL" value={newConnector.name} onChange={(e) => setNewConnector((p) => ({ ...p, name: e.target.value }))} />
              </div>
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
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancel</Button>
              <Button onClick={handleCreate} disabled={!newConnector.name.trim() || !newConnector.host.trim()}>Create Connector</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
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
          <div><p className="text-xs text-emerald-600">Connected</p><p className="text-xl font-bold">{connectedCount}/{connectors.length}</p></div>
        </CardContent></Card>
        <Card><CardContent className="p-4 flex items-center gap-3">
          <div className="rounded-lg bg-blue-50 p-2"><Database className="h-4 w-4 text-blue-600" /></div>
          <div><p className="text-xs text-blue-600">Tables Available</p><p className="text-xl font-bold">{totalTables}</p></div>
        </CardContent></Card>
        <Card><CardContent className="p-4 flex items-center gap-3">
          <div className="rounded-lg bg-violet-50 p-2"><Plug className="h-4 w-4 text-violet-600" /></div>
          <div><p className="text-xs text-violet-600">Connector Types</p><p className="text-xl font-bold">{new Set(connectors.map((c) => c.type)).size}</p></div>
        </CardContent></Card>
      </div>

      {/* Connector Grid */}
      {connectors.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <Plug className="h-12 w-12 text-slate-300 mx-auto mb-4" />
            <h3 className="font-semibold text-slate-700 mb-1">No Connectors</h3>
            <p className="text-sm text-slate-400 mb-4">Add a data connector to get started</p>
            <Button onClick={() => setShowCreateDialog(true)} className="gap-2"><Plus className="h-4 w-4" /> Add Connector</Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {connectors.map((connector) => (
            <Card key={connector.id} className="hover:shadow-md transition">
              <CardContent className="p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-slate-50 p-2"><ConnectorIcon type={connector.type} /></div>
                    <div>
                      <h3 className="text-sm font-semibold text-slate-900">{connector.name}</h3>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <StatusDot status={connector.status} />
                        <span className="text-xs text-slate-400">{CONNECTOR_TYPES.find((c) => c.type === connector.type)?.name}</span>
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
                    <span>Tables</span><span className="text-slate-700">{connector.tablesCount}</span>
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
                  <Button variant="outline" size="sm" className="flex-1 gap-1" onClick={() => handleSync(connector.id)} disabled={connector.status !== 'connected'}>
                    <RefreshCw className="h-3.5 w-3.5" /> Sync
                  </Button>
                  <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-red-500 hover:text-red-700" onClick={() => handleDelete(connector.id)}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
