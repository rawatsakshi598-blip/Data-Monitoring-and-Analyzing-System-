'use client'

import { useEffect, useState } from 'react'
import { GitBranch, Search } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'

interface LineageEdge {
  id: string
  fromTable: { name: string; fullyQualifiedName: string }
  toTable: { name: string; fullyQualifiedName: string }
  lineageType: string
  description: string | null
  pipelineName: string | null
}

const typeColors: Record<string, string> = {
  transformation: 'bg-violet-100 text-violet-700',
  copy: 'bg-blue-100 text-blue-700',
  reference: 'bg-emerald-100 text-emerald-700',
  derivation: 'bg-amber-100 text-amber-700',
}

export default function Lineage() {
  const [edges, setEdges] = useState<LineageEdge[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    fetch('/api/lineage')
      .then((r) => r.json())
      .then((data) => setEdges(Array.isArray(data) ? data : []))
      .catch(() => setEdges([]))
      .finally(() => setLoading(false))
  }, [])

  const filtered = edges.filter(
    (e) =>
      (e.fromTable?.name || '').toLowerCase().includes(search.toLowerCase()) ||
      (e.toTable?.name || '').toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Data Lineage</h2>
        <p className="text-sm text-slate-500">
          {edges.length} lineage relationships tracked
        </p>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input
          placeholder="Search lineage..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-5 animate-pulse">
                <div className="flex items-center gap-4">
                  <div className="h-5 w-32 rounded bg-slate-200" />
                  <div className="h-5 w-8 rounded bg-slate-200" />
                  <div className="h-5 w-32 rounded bg-slate-200" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((edge) => (
            <Card key={edge.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-5">
                <div className="flex items-center gap-4 flex-wrap">
                  <div className="flex items-center gap-2">
                    <div className="rounded-lg bg-slate-100 p-2">
                      <GitBranch className="h-4 w-4 text-slate-600" />
                    </div>
                    <div>
                      <p className="font-medium text-slate-900">{edge.fromTable?.name || 'Unknown'}</p>
                      <p className="text-xs text-slate-400">{edge.fromTable?.fullyQualifiedName || ''}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <div className="h-px w-8 bg-slate-300" />
                    <Badge className={typeColors[edge.lineageType] || ''}>
                      {edge.lineageType}
                    </Badge>
                    <div className="h-px w-8 bg-slate-300" />
                  </div>

                  <div className="flex items-center gap-2">
                    <div>
                      <p className="font-medium text-slate-900">{edge.toTable?.name || 'Unknown'}</p>
                      <p className="text-xs text-slate-400">{edge.toTable?.fullyQualifiedName || ''}</p>
                    </div>
                  </div>

                  {edge.pipelineName && (
                    <Badge variant="outline" className="text-xs ml-auto">
                      {edge.pipelineName}
                    </Badge>
                  )}
                </div>
                {edge.description && (
                  <p className="text-sm text-slate-500 mt-2">{edge.description}</p>
                )}
              </CardContent>
            </Card>
          ))}
          {filtered.length === 0 && (
            <div className="text-center py-12 text-slate-400">
              No lineage relationships found.
            </div>
          )}
        </div>
      )}
    </div>
  )
}
