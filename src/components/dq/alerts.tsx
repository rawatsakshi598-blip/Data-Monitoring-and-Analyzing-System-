'use client'

import { useEffect, useState } from 'react'
import {
  Bell,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Search,
  Filter,
  Clock,
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface Alert {
  id: string
  title: string
  message: string
  severity: string
  alertType: string
  source: string | null
  channel: string
  status: string
  assignedTo: string | null
  createdAt: string
  resolvedAt: string | null
}

const severityColors: Record<string, string> = {
  critical: 'bg-red-100 text-red-700',
  warning: 'bg-amber-100 text-amber-700',
  info: 'bg-blue-100 text-blue-700',
}

const statusColors: Record<string, string> = {
  active: 'bg-red-100 text-red-700',
  acknowledged: 'bg-amber-100 text-amber-700',
  resolved: 'bg-emerald-100 text-emerald-700',
  suppressed: 'bg-slate-100 text-slate-600',
}

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  useEffect(() => {
    const params = new URLSearchParams()
    if (statusFilter !== 'all') params.set('status', statusFilter)
    fetch(`/api/alerts?${params}`)
      .then((r) => r.json())
      .then((data) => setAlerts(Array.isArray(data) ? data : []))
      .catch(() => setAlerts([]))
      .finally(() => setLoading(false))
  }, [statusFilter])

  const filtered = alerts.filter(
    (a) =>
      a.title.toLowerCase().includes(search.toLowerCase()) ||
      a.message.toLowerCase().includes(search.toLowerCase())
  )

  const handleResolve = async (id: string) => {
    await fetch(`/api/alerts`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, status: 'resolved' }),
    })
    setAlerts((prev) =>
      prev.map((a) =>
        a.id === id
          ? { ...a, status: 'resolved', resolvedAt: new Date().toISOString() }
          : a
      )
    )
  }

  const formatTime = (ts: string) => {
    const d = new Date(ts)
    const now = new Date()
    const diff = now.getTime() - d.getTime()
    if (diff < 60000) return 'Just now'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
    return d.toLocaleDateString()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Alerts</h2>
          <p className="text-sm text-slate-500">
            {alerts.filter((a) => a.status === 'active').length} active &middot;{' '}
            {alerts.filter((a) => a.status === 'resolved').length} resolved
          </p>
        </div>
      </div>

      {/* Summary */}
      <div className="grid gap-4 sm:grid-cols-4">
        {(['active', 'acknowledged', 'resolved', 'suppressed'] as const).map((s) => (
          <Card key={s}>
            <CardContent className="p-4 flex items-center gap-3">
              <Badge className={statusColors[s] || ''}>{s}</Badge>
              <span className="text-lg font-bold text-slate-900">
                {alerts.filter((a) => a.status === s).length}
              </span>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input
            placeholder="Search alerts..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex gap-1">
          {['all', 'active', 'acknowledged', 'resolved'].map((s) => (
            <Button
              key={s}
              variant={statusFilter === s ? 'default' : 'outline'}
              size="sm"
              onClick={() => setStatusFilter(s)}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </Button>
          ))}
        </div>
      </div>

      {/* Alerts list */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-4 animate-pulse">
                <div className="h-4 w-48 rounded bg-slate-200 mb-2" />
                <div className="h-3 w-64 rounded bg-slate-200" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((alert) => (
            <Card
              key={alert.id}
              className={`hover:shadow-sm transition-shadow ${
                alert.status === 'active' ? 'border-l-2 border-l-red-400' : ''
              }`}
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-medium text-slate-900">{alert.title}</h3>
                      <Badge className={severityColors[alert.severity] || ''}>{alert.severity}</Badge>
                      <Badge variant="outline">{alert.alertType.replace(/_/g, ' ')}</Badge>
                      <Badge className={statusColors[alert.status] || ''}>{alert.status}</Badge>
                    </div>
                    <p className="text-sm text-slate-500">{alert.message}</p>
                    <div className="flex items-center gap-3 text-xs text-slate-400">
                      {alert.source && <span>Source: {alert.source}</span>}
                      {alert.assignedTo && <span>Assigned: {alert.assignedTo}</span>}
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatTime(alert.createdAt)}
                      </span>
                    </div>
                  </div>
                  {alert.status === 'active' || alert.status === 'acknowledged' ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleResolve(alert.id)}
                    >
                      <CheckCircle2 className="h-3 w-3 mr-1" />
                      Resolve
                    </Button>
                  ) : (
                    alert.resolvedAt && (
                      <span className="text-xs text-slate-400 flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                        {formatTime(alert.resolvedAt)}
                      </span>
                    )
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
          {filtered.length === 0 && (
            <div className="text-center py-12 text-slate-400">No alerts found.</div>
          )}
        </div>
      )}
    </div>
  )
}
