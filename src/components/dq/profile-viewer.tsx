'use client'

import { useEffect, useState } from 'react'
import { Eye, Search, BarChart3 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

interface ProfileColumn {
  name: string
  type: string
  nullCount: number
  uniqueCount: number
  min?: string | number | null
  max?: string | number | null
  avg?: string | number | null
  topValues?: string
}

interface Profile {
  datasetId: string
  datasetName?: string
  rowCount: number
  columnCount: number
  columns: ProfileColumn[]
  profiledAt: string
}

export default function ProfileViewer() {
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    fetch('/api/profile')
      .then(r => r.json())
      .then(data => {
        const list = Array.isArray(data) ? data : []
        setProfiles(list)
        if (list.length > 0 && !selectedId) setSelectedId(list[0].datasetId)
      })
      .catch(() => setProfiles([]))
      .finally(() => setLoading(false))
  }, [])

  const selected = profiles.find(p => p.datasetId === selectedId)
  const filteredCols = selected?.columns?.filter(c => c.name.toLowerCase().includes(search.toLowerCase())) || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Data Profiles</h2>
          <p className="text-sm text-slate-500">{profiles.length} datasets profiled</p>
        </div>
        <Select value={selectedId} onValueChange={setSelectedId}>
          <SelectTrigger className="w-[200px]"><SelectValue placeholder="Select dataset" /></SelectTrigger>
          <SelectContent>
            {profiles.map(p => <SelectItem key={p.datasetId} value={p.datasetId}>{p.datasetName || p.datasetId.slice(0, 8)}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {selected && (
        <div className="grid gap-4 sm:grid-cols-3">
          <Card><CardContent className="p-4"><p className="text-2xl font-bold">{selected.rowCount?.toLocaleString()}</p><p className="text-xs text-slate-500">Rows</p></CardContent></Card>
          <Card><CardContent className="p-4"><p className="text-2xl font-bold">{selected.columnCount}</p><p className="text-xs text-slate-500">Columns</p></CardContent></Card>
          <Card><CardContent className="p-4"><p className="text-2xl font-bold">{new Date(selected.profiledAt).toLocaleDateString()}</p><p className="text-xs text-slate-500">Profiled</p></CardContent></Card>
        </div>
      )}

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input placeholder="Search columns..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
      </div>

      {loading ? (
        <Card><CardContent className="p-5">{[...Array(5)].map((_, i) => <div key={i} className="h-10 bg-slate-100 rounded mb-2 animate-pulse" />)}</CardContent></Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Column</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Nulls</TableHead>
                  <TableHead className="text-right">Unique</TableHead>
                  <TableHead>Min</TableHead>
                  <TableHead>Max</TableHead>
                  <TableHead>Avg</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredCols.length === 0 ? (
                  <TableRow><TableCell colSpan={7} className="text-center py-8 text-slate-400"><BarChart3 className="h-8 w-8 mx-auto mb-2 opacity-50" />No profile data available</TableCell></TableRow>
                ) : filteredCols.map(col => (
                  <TableRow key={col.name}>
                    <TableCell className="font-medium">{col.name}</TableCell>
                    <TableCell><Badge variant="outline" className="text-xs font-mono">{col.type}</Badge></TableCell>
                    <TableCell className="text-right"><span className={col.nullCount > 0 ? 'text-red-600 font-semibold' : 'text-emerald-600'}>{col.nullCount}</span></TableCell>
                    <TableCell className="text-right text-muted-foreground">{col.uniqueCount?.toLocaleString()}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{String(col.min ?? '—')}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{String(col.max ?? '—')}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{String(col.avg ?? '—')}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
