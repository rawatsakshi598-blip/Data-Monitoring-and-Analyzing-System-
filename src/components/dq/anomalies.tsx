'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, Search, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

interface Anomaly {
  id: string
  datasetId: string
  datasetName?: string
  column: string
  anomalyType: string
  value: string | number | null
  expectedRange: string
  zScore: number
  detectedAt: string
}

export default function Anomalies() {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    fetch('/api/anomaly')
      .then(r => r.json())
      .then(data => setAnomalies(Array.isArray(data) ? data : []))
      .catch(() => setAnomalies([]))
      .finally(() => setLoading(false))
  }, [])

  const filtered = anomalies.filter(a =>
    a.column?.toLowerCase().includes(search.toLowerCase()) ||
    a.datasetName?.toLowerCase().includes(search.toLowerCase()) ||
    a.anomalyType?.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Anomalies</h2>
        <p className="text-sm text-slate-500">{anomalies.length} anomalies detected via statistical analysis</p>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input placeholder="Search anomalies..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
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
                  <TableHead>Dataset</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Value</TableHead>
                  <TableHead>Expected</TableHead>
                  <TableHead>Z-Score</TableHead>
                  <TableHead>Detected</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.length === 0 ? (
                  <TableRow><TableCell colSpan={7} className="text-center py-8 text-slate-400"><AlertTriangle className="h-8 w-8 mx-auto mb-2 opacity-50" />No anomalies found</TableCell></TableRow>
                ) : filtered.map(a => (
                  <TableRow key={a.id}>
                    <TableCell className="font-medium">{a.column}</TableCell>
                    <TableCell className="text-muted-foreground">{a.datasetName || a.datasetId?.slice(0, 8)}</TableCell>
                    <TableCell><Badge variant="outline">{a.anomalyType}</Badge></TableCell>
                    <TableCell className="font-mono text-sm">{String(a.value ?? '—')}</TableCell>
                    <TableCell className="text-muted-foreground text-sm">{a.expectedRange}</TableCell>
                    <TableCell><Badge className={Math.abs(a.zScore) > 3 ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}>{a.zScore.toFixed(2)}</Badge></TableCell>
                    <TableCell className="text-xs text-muted-foreground">{new Date(a.detectedAt).toLocaleString()}</TableCell>
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
