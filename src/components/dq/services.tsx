'use client'

import { useEffect, useState, useCallback } from 'react'
import {
  Database,
  Plus,
  Search,
  RefreshCw,
  Server,
  HardDrive,
  Wifi,
  Cloud,
  Activity,
  Table2,
  ChevronRight,
  Trash2,
  X,
  Loader2,
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useAppStore } from '@/lib/store'

interface Service {
  id: string
  name: string
  description: string | null
  serviceType: string
  platform: string
  connectionUrl: string | null
  status: string
  owner: string | null
  lastIngested: string | null
  createdAt: string | null
  _count?: { tables: number }
}

interface ServiceTable {
  id: string
  name: string
  fullyQualifiedName: string
  columnCount: number
  rowCount: number
  qualityScore: number
  freshnessStatus: string
}

const statusColors: Record<string, string> = {
  active: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  warning: 'bg-amber-100 text-amber-700 border-amber-200',
  inactive: 'bg-slate-100 text-slate-600 border-slate-200',
  error: 'bg-red-100 text-red-700 border-red-200',
  deprecated: 'bg-amber-100 text-amber-700 border-amber-200',
}

const platformIcons: Record<string, React.ReactNode> = {
  postgresql: <Database className="h-5 w-5 text-blue-600" />,
  mysql: <Database className="h-5 w-5 text-orange-500" />,
  mongodb: <Database className="h-5 w-5 text-green-600" />,
  kafka: <Wifi className="h-5 w-5 text-purple-600" />,
  s3: <Cloud className="h-5 w-5 text-amber-600" />,
  file_upload: <HardDrive className="h-5 w-5 text-teal-600" />,
}

function getPlatformIcon(platform: string) {
  return platformIcons[platform] || <Server className="h-5 w-5 text-slate-600" />
}

function formatRelativeTime(dateStr: string | null): string {
  if (!dateStr) return 'Never'
  try {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours}h ago`
    const diffDays = Math.floor(diffHours / 24)
    if (diffDays < 30) return `${diffDays}d ago`
    return date.toLocaleDateString()
  } catch {
    return dateStr
  }
}

export default function Services() {
  const [services, setServices] = useState<Service[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [addOpen, setAddOpen] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [selectedService, setSelectedService] = useState<(Service & { tables?: ServiceTable[] }) | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [addForm, setAddForm] = useState({
    name: '',
    description: '',
    serviceType: 'database',
    platform: 'postgresql',
    connectionUrl: '',
    owner: '',
  })
  const [addSubmitting, setAddSubmitting] = useState(false)
  const [addError, setAddError] = useState<string | null>(null)
  const { setCurrentView } = useAppStore()

  const fetchServices = useCallback(() => {
    setLoading(true)
    fetch('/api/services')
      .then((r) => r.json())
      .then((data) => setServices(Array.isArray(data) ? data : []))
      .catch(() => setServices([]))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    fetchServices()
  }, [fetchServices])

  const filtered = services.filter(
    (s) =>
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.platform.toLowerCase().includes(search.toLowerCase()) ||
      (s.description || '').toLowerCase().includes(search.toLowerCase()) ||
      (s.owner || '').toLowerCase().includes(search.toLowerCase())
  )

  const handleAddService = async () => {
    if (!addForm.name.trim()) {
      setAddError('Service name is required')
      return
    }
    setAddSubmitting(true)
    setAddError(null)
    try {
      const res = await fetch('/api/services', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: addForm.name,
          description: addForm.description || null,
          serviceType: addForm.serviceType,
          platform: addForm.platform,
          connectionUrl: addForm.connectionUrl || null,
          owner: addForm.owner || null,
          status: 'active',
        }),
      })
      const data = await res.json()
      if (data.error) {
        setAddError(data.error)
      } else {
        setAddOpen(false)
        setAddForm({ name: '', description: '', serviceType: 'database', platform: 'postgresql', connectionUrl: '', owner: '' })
        fetchServices()
      }
    } catch {
      setAddError('Failed to create service. Is the backend running?')
    } finally {
      setAddSubmitting(false)
    }
  }

  const handleServiceClick = async (service: Service) => {
    setSelectedService(service)
    setDetailOpen(true)
    setLoadingDetail(true)
    try {
      const res = await fetch(`/api/services/${service.id}`)
      const data = await res.json()
      if (data.error) {
        setSelectedService({ ...service, tables: [] })
      } else {
        setSelectedService(data)
      }
    } catch {
      setSelectedService({ ...service, tables: [] })
    } finally {
      setLoadingDetail(false)
    }
  }

  const handleDeleteService = async (serviceId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('Delete this service and all its tables?')) return
    try {
      await fetch(`/api/services/${serviceId}`, { method: 'DELETE' })
      setDetailOpen(false)
      fetchServices()
    } catch {
      // silently fail
    }
  }

  const totalTables = services.reduce((sum, s) => sum + (s._count?.tables || 0), 0)
  const activeCount = services.filter((s) => s.status === 'active').length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Services</h2>
          <p className="text-sm text-slate-500">
            {services.length} data services registered &middot; {totalTables} tables &middot; {activeCount} active
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchServices}>
            <RefreshCw className="h-4 w-4 mr-1" />
            Refresh
          </Button>
          <Button onClick={() => setAddOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Add Service
          </Button>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input
          placeholder="Search services by name, platform, owner..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9 max-w-sm"
        />
      </div>

      {/* Services Grid */}
      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-5 animate-pulse">
                <div className="h-5 w-32 rounded bg-slate-200 mb-3" />
                <div className="h-3 w-48 rounded bg-slate-200 mb-2" />
                <div className="h-3 w-24 rounded bg-slate-200" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((service) => (
            <Card
              key={service.id}
              className="hover:shadow-md transition-shadow cursor-pointer group"
              onClick={() => handleServiceClick(service)}
            >
              <CardContent className="p-5">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-slate-100 p-2 group-hover:bg-indigo-50 transition-colors">
                      {getPlatformIcon(service.platform)}
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-900">{service.name}</h3>
                      <p className="text-xs text-slate-500">{service.platform}</p>
                    </div>
                  </div>
                  <Badge variant="outline" className={statusColors[service.status] || statusColors.active}>
                    {service.status}
                  </Badge>
                </div>
                {service.description && (
                  <p className="text-sm text-slate-500 line-clamp-2 mb-3">
                    {service.description}
                  </p>
                )}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 text-xs text-slate-400">
                    <Badge variant="secondary" className="text-xs">
                      {service.serviceType}
                    </Badge>
                    <span className="flex items-center gap-1">
                      <Table2 className="h-3 w-3" />
                      {service._count?.tables || 0} tables
                    </span>
                    {service.owner && <span>{service.owner}</span>}
                  </div>
                  <ChevronRight className="h-4 w-4 text-slate-300 group-hover:text-indigo-500 transition-colors" />
                </div>
                {service.lastIngested && (
                  <div className="mt-2 pt-2 border-t border-slate-100 text-xs text-slate-400 flex items-center gap-1">
                    <Activity className="h-3 w-3" />
                    Last ingested {formatRelativeTime(service.lastIngested)}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
          {filtered.length === 0 && (
            <div className="col-span-full text-center py-12 text-slate-400">
              <Server className="h-12 w-12 mx-auto mb-3 text-slate-300" />
              <p className="text-lg font-medium mb-1">No services found</p>
              <p className="text-sm">Try adjusting your search or add a new service.</p>
            </div>
          )}
        </div>
      )}

      {/* ════════════════════════════════════════════════════════════
          ADD SERVICE DIALOG
          ════════════════════════════════════════════════════════════ */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Plus className="h-5 w-5 text-indigo-600" />
              Add New Service
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            <div>
              <label className="text-sm font-medium text-slate-700 mb-1 block">Name *</label>
              <Input
                placeholder="e.g. PostgreSQL Production"
                value={addForm.name}
                onChange={(e) => setAddForm({ ...addForm, name: e.target.value })}
              />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 mb-1 block">Description</label>
              <Input
                placeholder="Brief description of this service"
                value={addForm.description}
                onChange={(e) => setAddForm({ ...addForm, description: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-slate-700 mb-1 block">Type</label>
                <select
                  className="w-full h-9 rounded-md border border-slate-200 bg-white px-3 text-sm"
                  value={addForm.serviceType}
                  onChange={(e) => setAddForm({ ...addForm, serviceType: e.target.value })}
                >
                  <option value="database">Database</option>
                  <option value="storage">Storage</option>
                  <option value="messaging">Messaging</option>
                  <option value="api">API</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700 mb-1 block">Platform</label>
                <select
                  className="w-full h-9 rounded-md border border-slate-200 bg-white px-3 text-sm"
                  value={addForm.platform}
                  onChange={(e) => setAddForm({ ...addForm, platform: e.target.value })}
                >
                  <option value="postgresql">PostgreSQL</option>
                  <option value="mysql">MySQL</option>
                  <option value="mongodb">MongoDB</option>
                  <option value="kafka">Kafka</option>
                  <option value="s3">S3</option>
                  <option value="file_upload">File Upload</option>
                </select>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 mb-1 block">Connection URL</label>
              <Input
                placeholder="e.g. postgresql://host:5432/db"
                value={addForm.connectionUrl}
                onChange={(e) => setAddForm({ ...addForm, connectionUrl: e.target.value })}
              />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 mb-1 block">Owner</label>
              <Input
                placeholder="e.g. Data Team"
                value={addForm.owner}
                onChange={(e) => setAddForm({ ...addForm, owner: e.target.value })}
              />
            </div>
            {addError && (
              <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700 flex items-center gap-2">
                <X className="h-4 w-4 shrink-0" />
                {addError}
              </div>
            )}
            <div className="flex justify-end gap-3 pt-2">
              <Button variant="outline" onClick={() => setAddOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleAddService} disabled={addSubmitting}>
                {addSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4 mr-2" />
                    Create Service
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* ════════════════════════════════════════════════════════════
          SERVICE DETAIL DIALOG
          ════════════════════════════════════════════════════════════ */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col p-0">
          {selectedService ? (
            <>
              <DialogHeader className="px-6 pt-6 pb-3 border-b shrink-0">
                <DialogTitle className="flex items-center gap-3">
                  <div className="rounded-lg bg-slate-100 p-2">
                    {getPlatformIcon(selectedService.platform)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      {selectedService.name}
                      <Badge variant="outline" className={statusColors[selectedService.status] || ''}>
                        {selectedService.status}
                      </Badge>
                    </div>
                    <p className="text-sm font-normal text-slate-500 mt-0.5">
                      {selectedService.platform} &middot; {selectedService.serviceType}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-red-500 hover:text-red-700 hover:bg-red-50"
                    onClick={(e) => handleDeleteService(selectedService.id, e)}
                  >
                    <Trash2 className="h-4 w-4 mr-1" />
                    Delete
                  </Button>
                </DialogTitle>
              </DialogHeader>

              <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
                {/* Service Info */}
                {selectedService.description && (
                  <p className="text-sm text-slate-600">{selectedService.description}</p>
                )}
                <div className="grid grid-cols-2 gap-3 text-sm">
                  {selectedService.owner && (
                    <div className="bg-slate-50 rounded-lg p-3">
                      <span className="text-slate-400 text-xs">Owner</span>
                      <p className="font-medium text-slate-700">{selectedService.owner}</p>
                    </div>
                  )}
                  {selectedService.connectionUrl && (
                    <div className="bg-slate-50 rounded-lg p-3">
                      <span className="text-slate-400 text-xs">Connection</span>
                      <p className="font-medium text-slate-700 font-mono text-xs truncate">{selectedService.connectionUrl}</p>
                    </div>
                  )}
                  <div className="bg-slate-50 rounded-lg p-3">
                    <span className="text-slate-400 text-xs">Tables</span>
                    <p className="font-medium text-slate-700">{selectedService._count?.tables || selectedService.tables?.length || 0}</p>
                  </div>
                  <div className="bg-slate-50 rounded-lg p-3">
                    <span className="text-slate-400 text-xs">Last Ingested</span>
                    <p className="font-medium text-slate-700">{formatRelativeTime(selectedService.lastIngested)}</p>
                  </div>
                </div>

                {/* Tables List */}
                <div>
                  <h4 className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-1">
                    <Table2 className="h-4 w-4" />
                    Tables ({selectedService.tables?.length || selectedService._count?.tables || 0})
                  </h4>
                  {loadingDetail ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin text-indigo-500" />
                    </div>
                  ) : selectedService.tables && selectedService.tables.length > 0 ? (
                    <div className="space-y-2">
                      {selectedService.tables.map((t) => (
                        <div
                          key={t.id}
                          className="flex items-center justify-between p-3 rounded-lg border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/50 cursor-pointer transition-colors"
                          onClick={() => {
                            setDetailOpen(false)
                            setCurrentView('tables')
                          }}
                        >
                          <div className="flex items-center gap-3">
                            <Table2 className="h-4 w-4 text-indigo-500" />
                            <div>
                              <p className="text-sm font-medium text-slate-900">{t.name}</p>
                              <p className="text-xs text-slate-400">{t.fullyQualifiedName}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-3 text-xs">
                            <span className="text-slate-500">{t.columnCount} cols</span>
                            <span className="text-slate-500">{(t.rowCount ?? 0).toLocaleString()} rows</span>
                            <Badge
                              variant="outline"
                              className={
                                t.qualityScore >= 90
                                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                  : t.qualityScore >= 70
                                  ? 'bg-amber-50 text-amber-700 border-amber-200'
                                  : 'bg-red-50 text-red-700 border-red-200'
                              }
                            >
                              {(t.qualityScore ?? 0).toFixed(1)}%
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-6 text-slate-400 text-sm">
                      <Table2 className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                      No tables registered for this service yet.
                      <br />
                      Upload data to create tables automatically.
                    </div>
                  )}
                </div>
              </div>

              <div className="px-6 py-3 border-t bg-slate-50 flex justify-end shrink-0">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setDetailOpen(false)
                    setCurrentView('tables')
                  }}
                >
                  View All Tables
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  )
}