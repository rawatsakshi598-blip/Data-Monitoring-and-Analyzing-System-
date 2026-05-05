'use client'

import { useEffect, useState } from 'react'
import { Database, Plus, Search, RefreshCw, MoreHorizontal } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface Service {
  id: string
  name: string
  description: string | null
  serviceType: string
  platform: string
  status: string
  owner: string | null
  lastIngested: string | null
  _count?: { tables: number }
}

const statusColors: Record<string, string> = {
  active: 'bg-emerald-100 text-emerald-700',
  inactive: 'bg-slate-100 text-slate-600',
  error: 'bg-red-100 text-red-700',
  deprecated: 'bg-amber-100 text-amber-700',
}

export default function Services() {
  const [services, setServices] = useState<Service[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    fetch('/api/services')
      .then((r) => r.json())
      .then((data) => setServices(Array.isArray(data) ? data : []))
      .catch(() => setServices([]))
      .finally(() => setLoading(false))
  }, [])

  const filtered = services.filter(
    (s) =>
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.platform.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Services</h2>
          <p className="text-sm text-slate-500">
            {services.length} data services registered
          </p>
        </div>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Add Service
        </Button>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input
          placeholder="Search services..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9 max-w-sm"
        />
      </div>

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
            <Card key={service.id} className="hover:shadow-md transition-shadow cursor-pointer">
              <CardContent className="p-5">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-slate-100 p-2">
                      <Database className="h-5 w-5 text-slate-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-900">{service.name}</h3>
                      <p className="text-xs text-slate-500">{service.platform}</p>
                    </div>
                  </div>
                  <Badge variant="outline" className={statusColors[service.status] || ''}>
                    {service.status}
                  </Badge>
                </div>
                {service.description && (
                  <p className="text-sm text-slate-500 line-clamp-2 mb-3">
                    {service.description}
                  </p>
                )}
                <div className="flex items-center gap-4 text-xs text-slate-400">
                  <Badge variant="secondary" className="text-xs">
                    {service.serviceType}
                  </Badge>
                  {service._count && (
                    <span>{service._count.tables} tables</span>
                  )}
                  {service.owner && <span>Owner: {service.owner}</span>}
                </div>
              </CardContent>
            </Card>
          ))}
          {filtered.length === 0 && (
            <div className="col-span-full text-center py-12 text-slate-400">
              No services found.
            </div>
          )}
        </div>
      )}
    </div>
  )
}
