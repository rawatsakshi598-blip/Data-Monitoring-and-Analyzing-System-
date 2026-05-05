'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Database, Download, Trash2, RefreshCw, Eye, Loader2,
  CheckCircle2, AlertTriangle, Table2,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { toast } from 'sonner'

interface FixedTable {
  id: string
  name: string
  description: string | null
  rowCount: number
  columnCount: number
  qualityScore: number
  createdAt: string
  service?: { name: string; platform: string } | null
}

export default function FixedDatasets() {
  const [tables, setTables] = useState<FixedTable[]>([])
  const [loading, setLoading] = useState(true)
  const [previewData, setPreviewData] = useState<{ columns: string[]; rows: any[]; totalRows: number } | null>(null)
  const [previewName, setPreviewName] = useState('')
  const [showPreview, setShowPreview] = useState(false)
  const [previewLoading, setPreviewLoading] = useState(false)

  const fetchTables = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/tables/fixed')
      if (res.ok) {
        const data = await res.json()
        setTables(Array.isArray(data) ? data : [])
      } else {
        setTables([])
      }
    } catch {
      setTables([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchTables() }, [fetchTables])

  const handlePreview = async (table: FixedTable) => {
    setPreviewLoading(true)
    setPreviewName(table.name)
    setShowPreview(true)
    try {
      const res = await fetch(`/api/table-data/${table.id}?limit=20`)
      if (res.ok) {
        const data = await res.json()
        setPreviewData(data)
      } else {
        setPreviewData(null)
        toast.error('Failed to load preview')
      }
    } catch {
      setPreviewData(null)
      toast.error('Failed to load preview')
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleDownload = async (table: FixedTable) => {
    try {
      const res = await fetch(`/api/table-data/${table.id}?limit=100000`)
      if (res.ok) {
        const data = await res.json()
        if (data.rows && data.columns) {
          // Convert to CSV
          const header = data.columns.join(',')
          const rows = data.rows.map((row: any) =>
            data.columns.map((col: string) => {
              const val = row[col]
              if (val === null || val === undefined) return ''
              const str = String(val)
              return str.includes(',') || str.includes('"') || str.includes('\n')
                ? `"${str.replace(/"/g, '""')}"`
                : str
            }).join(',')
          )
          const csv = [header, ...rows].join('\n')
          const blob = new Blob([csv], { type: 'text/csv' })
          const url = URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = `${table.name}.csv`
          a.click()
          URL.revokeObjectURL(url)
          toast.success(`Downloaded ${table.name}.csv`)
        }
      } else {
        toast.error('Failed to download')
      }
    } catch {
      toast.error('Failed to download')
    }
  }

  const handleDelete = async (table: FixedTable) => {
    if (!confirm(`Delete ${table.name}? This cannot be undone.`)) return
    try {
      const res = await fetch(`/api/tables/${table.id}`, { method: 'DELETE' })
      if (res.ok) {
        toast.success(`Deleted ${table.name}`)
        fetchTables()
      } else {
        toast.error('Failed to delete')
      }
    } catch {
      toast.error('Failed to delete')
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map(i => <Skeleton key={i} className="h-40 rounded-xl" />)}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Fixed Datasets</h2>
          <p className="text-sm text-slate-500 mt-1">Auto-fixed copies created by the Data Copilot</p>
        </div>
        <Button variant="outline" className="gap-2" onClick={fetchTables}>
          <RefreshCw className="h-4 w-4" /> Refresh
        </Button>
      </div>

      {tables.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <Database className="h-12 w-12 text-slate-300 mx-auto mb-4" />
            <h3 className="font-semibold text-slate-700 mb-1">No Fixed Datasets Yet</h3>
            <p className="text-sm text-slate-400">
              Use the AI Data Copilot to auto-analyze and fix your datasets.
              Fixed copies will appear here.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {tables.map((table) => (
            <Card key={table.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="rounded-lg bg-emerald-100 p-2 shrink-0">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    </div>
                    <div className="min-w-0">
                      <CardTitle className="text-sm truncate">{table.name}</CardTitle>
                      <p className="text-xs text-slate-400 truncate">{table.description}</p>
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="rounded bg-slate-50 p-2">
                    <p className="text-[10px] text-slate-400">Rows</p>
                    <p className="text-sm font-semibold">{table.rowCount?.toLocaleString() ?? '-'}</p>
                  </div>
                  <div className="rounded bg-slate-50 p-2">
                    <p className="text-[10px] text-slate-400">Columns</p>
                    <p className="text-sm font-semibold">{table.columnCount ?? '-'}</p>
                  </div>
                  <div className="rounded bg-slate-50 p-2">
                    <p className="text-[10px] text-slate-400">Score</p>
                    <p className="text-sm font-semibold">{table.qualityScore ?? '-'}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="outline" className="flex-1 gap-1.5" onClick={() => handlePreview(table)}>
                    <Eye className="h-3.5 w-3.5" /> Preview
                  </Button>
                  <Button size="sm" variant="outline" className="gap-1.5" onClick={() => handleDownload(table)}>
                    <Download className="h-3.5 w-3.5" />
                  </Button>
                  <Button size="sm" variant="ghost" className="text-red-500 hover:text-red-700 hover:bg-red-50 gap-1.5" onClick={() => handleDelete(table)}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
                <p className="text-[10px] text-slate-300">
                  Created: {new Date(table.createdAt).toLocaleString()}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Preview Dialog */}
      <Dialog open={showPreview} onOpenChange={setShowPreview}>
        <DialogContent className="max-w-4xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Table2 className="h-4 w-4" />
              {previewName} — Preview
            </DialogTitle>
          </DialogHeader>
          {previewLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            </div>
          ) : previewData ? (
            <ScrollArea className="max-h-[60vh]">
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b">
                      {previewData.columns.map((col) => (
                        <th key={col} className="text-left p-2 font-medium text-slate-600 whitespace-nowrap">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {previewData.rows.map((row, i) => (
                      <tr key={i} className="border-b hover:bg-slate-50">
                        {previewData.columns.map((col) => (
                          <td key={col} className="p-2 text-slate-700 whitespace-nowrap max-w-[200px] truncate">
                            {row[col] ?? '-'}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-slate-400 mt-2">
                Showing {previewData.rows.length} of {previewData.totalRows} rows
              </p>
            </ScrollArea>
          ) : (
            <div className="text-center py-8 text-slate-400">
              <AlertTriangle className="h-8 w-8 mx-auto mb-2" />
              <p className="text-sm">Failed to load preview</p>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
