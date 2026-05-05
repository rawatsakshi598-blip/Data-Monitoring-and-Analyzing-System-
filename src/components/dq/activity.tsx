'use client'

import { useEffect, useState } from 'react'
import {
  Activity,
  User,
  Table2,
  Database,
  Tag,
  GitBranch,
  Bell,
  BookOpen,
  Search,
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'

interface ActivityItem {
  id: string
  entityType: string
  entityName: string | null
  action: string
  userName: string | null
  description: string | null
  timestamp: string
}

const typeIcons: Record<string, React.ReactNode> = {
  table: <Table2 className="h-4 w-4" />,
  service: <Database className="h-4 w-4" />,
  test: <Activity className="h-4 w-4" />,
  tag: <Tag className="h-4 w-4" />,
  glossaryTerm: <BookOpen className="h-4 w-4" />,
  team: <User className="h-4 w-4" />,
  lineage: <GitBranch className="h-4 w-4" />,
  alert: <Bell className="h-4 w-4" />,
}

const actionColors: Record<string, string> = {
  created: 'bg-emerald-100 text-emerald-700',
  updated: 'bg-blue-100 text-blue-700',
  deleted: 'bg-red-100 text-red-700',
  ingested: 'bg-violet-100 text-violet-700',
  tested: 'bg-amber-100 text-amber-700',
  tagged: 'bg-sky-100 text-sky-700',
}

export default function ActivityView() {
  const [activities, setActivities] = useState<ActivityItem[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    fetch('/api/activity?limit=50')
      .then((r) => r.json())
      .then((data) => setActivities(Array.isArray(data) ? data : []))
      .catch(() => setActivities([]))
      .finally(() => setLoading(false))
  }, [])

  const filtered = activities.filter(
    (a) =>
      (a.entityName || '').toLowerCase().includes(search.toLowerCase()) ||
      (a.userName || '').toLowerCase().includes(search.toLowerCase()) ||
      (a.description || '').toLowerCase().includes(search.toLowerCase())
  )

  const formatTime = (ts: string) => {
    const d = new Date(ts)
    const now = new Date()
    const diff = now.getTime() - d.getTime()
    if (diff < 60000) return 'Just now'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`
    return d.toLocaleDateString()
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Activity Feed</h2>
        <p className="text-sm text-slate-500">
          {activities.length} events recorded
        </p>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input
          placeholder="Search activity..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(8)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-4 animate-pulse">
                <div className="h-4 w-48 rounded bg-slate-200 mb-2" />
                <div className="h-3 w-32 rounded bg-slate-200" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((item) => (
            <Card key={item.id} className="hover:shadow-sm transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 rounded-lg bg-slate-100 p-2 text-slate-500">
                    {typeIcons[item.entityType] || <Activity className="h-4 w-4" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      {item.userName && (
                        <span className="text-sm font-medium text-slate-900">{item.userName}</span>
                      )}
                      <Badge className={actionColors[item.action] || ''}>{item.action}</Badge>
                      <span className="text-sm text-slate-600">
                        {item.entityType}
                        {item.entityName && (
                          <span className="font-medium"> {item.entityName}</span>
                        )}
                      </span>
                    </div>
                    {item.description && (
                      <p className="text-sm text-slate-400 mt-0.5 line-clamp-1">{item.description}</p>
                    )}
                  </div>
                  <span className="text-xs text-slate-400 whitespace-nowrap">{formatTime(item.timestamp)}</span>
                </div>
              </CardContent>
            </Card>
          ))}
          {filtered.length === 0 && (
            <div className="text-center py-12 text-slate-400">No activity found.</div>
          )}
        </div>
      )}
    </div>
  )
}
