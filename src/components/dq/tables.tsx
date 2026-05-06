'use client'

import { useEffect, useState } from 'react'
import {
  Table2,
  Search,
  ArrowUpDown,
  Database,
  Loader2,
  X,
  FileUp,
} from 'lucide-react'
import {
  Table as ShadTable,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

interface Tbl {
  id: string
  name: string
  fullyQualifiedName: string
  description: string | null
  database: string | null
  schema: string | null
  service: { name: string }
  columnCount: number
  rowCount: number
  qualityScore: number
  freshnessStatus: string
  tier: number
  lastProfiled: string | null
  _count?: { tests: number }
}

interface ColumnInfo {
  cid: number
  name: string
  type: string
  notnull: boolean
  defaultValue: string | null
  primaryKey: boolean
}

interface TablePreview {
  id: string
  name: string
  fullyQualifiedName: string
  columns: ColumnInfo[]
  resultColumns: string[]
  rows: Record<string, unknown>[]
  rowCount: number
  totalRows: number
  truncated: boolean
}

const freshnessColors: Record<string, string> = {
  fresh: 'bg-emerald-100 text-emerald-700',
  stale: 'bg-amber-100 text-amber-700',
  missing: 'bg-red-100 text-red-700',
}

const tierLabels: Record<number, string> = {
  0: 'PII',
  1: 'Sensitive',
  2: 'Internal',
  3: 'Public',
}

export default function Tables() {
  const [tables, setTables] = useState<Tbl[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<string>('name')

  // Single table detail preview
  const [detailTable, setDetailTable] = useState<TablePreview | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [detailError, setDetailError] = useState<string | null>(null)

  const safeFixed = (val: number | undefined | null, d = 1) => (val ?? 0).toFixed(d)

  useEffect(() => {
    const params = new URLSearchParams()
    if (sort) params.set('sort', sort)
    fetch(`/api/tables?${params}`)
      .then((r) => r.json())
      .then((data) => setTables(Array.isArray(data) ? data : []))
      .catch(() => setTables([]))
      .finally(() => setLoading(false))
  }, [sort])

  // Sanitize a table name the same way Python's _csv_to_sqlite does:
  // - Replace non-alphanumeric/underscore chars with '_'
  // - Prepend 't_' if the name starts with a digit
  const sanitizeTableName = (name: string): string => {
    let safe = name.replace(/[^a-zA-Z0-9_]/g, '_')
    if (!safe || /^\d/.test(safe)) {
      safe = 't_' + safe
    }
    return safe
  }

  // Load single table with all rows — backend now tries CSV then SQLite fallback automatically
  const loadTableDetail = async (table: Tbl) => {
    setLoadingDetail(true)
    setDetailError(null)
    setDetailTable(null)
    setDetailOpen(true)

    try {
      // Backend endpoint tries CSV file first, then falls back to uploaded_data.db SQLite
      const res = await fetch(`/api/table-data/${encodeURIComponent(table.id)}?limit=5000`)
      const data = await res.json()
      if (!data.error && data.rows && data.rows.length > 0) {
        setDetailTable(data)
        return
      }

      // FALLBACK: Try SQL endpoint with sanitized table name (in case backend fallback missed it)
      const safeName = sanitizeTableName(table.name)
      try {
        const sqlRes = await fetch(`/api/sql/table-preview?database=uploaded_data&table=${encodeURIComponent(safeName)}&limit=5000`)
        const sqlData = await sqlRes.json()
        if (!sqlData.error && sqlData.rows && sqlData.rows.length > 0) {
          setDetailTable({
            id: table.id,
            name: sqlData.table || table.name,
            fullyQualifiedName: `uploaded_data.${sqlData.table || table.name}`,
            columns: sqlData.columns || [],
            resultColumns: sqlData.resultColumns || [],
            rows: sqlData.rows,
            rowCount: sqlData.rowCount,
            totalRows: sqlData.totalRows,
            truncated: sqlData.truncated,
          })
          return
        }
      } catch {
        // SQL endpoint failed
      }

      // Show error from primary endpoint
      if (data.error) {
        setDetailError(data.error)
      } else {
        setDetailError(`No data found for table "${table.name}". The data file may not have been saved during upload.`)
      }
    } catch {
      setDetailError('Failed to load table detail. Is the backend running?')
    } finally {
      setLoadingDetail(false)
    }
  }

  // Handle table row click
  const handleRowClick = (t: Tbl) => {
    loadTableDetail(t)
  }

  const filtered = tables.filter(
    (t) =>
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.fullyQualifiedName.toLowerCase().includes(search.toLowerCase())
  )

  const scoreBadge = (score: number) => {
    if (score >= 90) return 'bg-emerald-100 text-emerald-700'
    if (score >= 70) return 'bg-amber-100 text-amber-700'
    return 'bg-red-100 text-red-700'
  }

  const formatCellValue = (value: unknown): string => {
    if (value === null || value === undefined) return 'NULL'
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Tables</h2>
          <p className="text-sm text-slate-500">
            {tables.length} tables across all services — click any table to view data
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={sort === 'qualityScore' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSort('qualityScore')}
          >
            <ArrowUpDown className="h-3 w-3 mr-1" />
            By Quality
          </Button>
          <Button
            variant={sort === 'rowCount' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSort('rowCount')}
          >
            <ArrowUpDown className="h-3 w-3 mr-1" />
            By Rows
          </Button>
          <Button
            variant={sort === 'name' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSort('name')}
          >
            A-Z
          </Button>
        </div>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input
          placeholder="Search tables by name..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9 max-w-sm"
        />
      </div>

      {loading ? (
        <Card>
          <CardContent className="p-5">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-12 bg-slate-100 rounded mb-2 animate-pulse" />
            ))}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <ShadTable>
              <TableHeader>
                <TableRow>
                  <TableHead>Table</TableHead>
                  <TableHead className="hidden md:table-cell">Service</TableHead>
                  <TableHead className="hidden sm:table-cell">Columns</TableHead>
                  <TableHead className="hidden sm:table-cell">Rows</TableHead>
                  <TableHead>Quality</TableHead>
                  <TableHead className="hidden lg:table-cell">Freshness</TableHead>
                  <TableHead className="hidden lg:table-cell">Tier</TableHead>
                  <TableHead className="hidden lg:table-cell">Tests</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((t) => (
                  <TableRow
                    key={t.id}
                    className="cursor-pointer hover:bg-indigo-50/60 transition-colors"
                    onClick={() => handleRowClick(t)}
                  >
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Table2 className="h-4 w-4 text-indigo-500 shrink-0" />
                        <div>
                          <div className="font-medium text-slate-900">{t.name}</div>
                          <div className="text-xs text-slate-400">{t.fullyQualifiedName}</div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="hidden md:table-cell">
                      <Badge variant="outline" className="text-xs">
                        <Database className="h-3 w-3 mr-1" />
                        {t.service?.name || 'Unknown'}
                      </Badge>
                    </TableCell>
                    <TableCell className="hidden sm:table-cell text-sm text-slate-600">
                      {t.columnCount}
                    </TableCell>
                    <TableCell className="hidden sm:table-cell text-sm text-slate-600">
                      {(t.rowCount ?? 0).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Badge className={scoreBadge(t.qualityScore)}>
                        {safeFixed(t.qualityScore)}%
                      </Badge>
                    </TableCell>
                    <TableCell className="hidden lg:table-cell">
                      <Badge variant="outline" className={freshnessColors[t.freshnessStatus]}>
                        {t.freshnessStatus}
                      </Badge>
                    </TableCell>
                    <TableCell className="hidden lg:table-cell">
                      <Badge variant="secondary">{tierLabels[t.tier] || `T${t.tier}`}</Badge>
                    </TableCell>
                    <TableCell className="hidden lg:table-cell text-sm text-slate-600">
                      {t._count?.tests || 0}
                    </TableCell>
                  </TableRow>
                ))}
                {filtered.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8 text-slate-400">
                      No tables found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </ShadTable>
          </CardContent>
        </Card>
      )}

      {/* ════════════════════════════════════════════════════════════
          TABLE DETAIL DIALOG — Full data view (all rows & columns)
          Both scrollbars visible from the start via single scroll container
          ════════════════════════════════════════════════════════════ */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-[95vw] w-full max-h-[90vh] flex flex-col p-0">
          <DialogHeader className="px-6 pt-6 pb-3 border-b shrink-0">
            <DialogTitle className="flex items-center gap-2">
              <Table2 className="h-5 w-5 text-indigo-600" />
              {detailTable?.name || 'Table Data'}
              {detailTable && (
                <>
                  <Badge variant="secondary" className="text-xs ml-2">
                    {detailTable.columns.length} columns
                  </Badge>
                  <Badge variant="outline" className="text-xs">
                    {detailTable.totalRows.toLocaleString()} rows
                  </Badge>
                </>
              )}
            </DialogTitle>
          </DialogHeader>

          {loadingDetail ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
              <span className="ml-3 text-sm text-slate-500">Loading table data...</span>
            </div>
          ) : detailError ? (
            <div className="m-6 p-4 rounded-lg bg-red-50 border border-red-200 flex items-center gap-2 text-sm text-red-700">
              <X className="h-4 w-4 shrink-0" />
              {detailError}
              <Button variant="ghost" size="sm" className="ml-auto" onClick={() => setDetailError(null)}>
                Dismiss
              </Button>
            </div>
          ) : detailTable ? (
            <>
              {/* Column info */}
              <div className="px-6 py-2 bg-slate-50/80 border-b shrink-0">
                <div className="flex flex-wrap gap-1.5">
                  {detailTable.columns.map(col => (
                    <Badge
                      key={col.name}
                      variant="outline"
                      className={`text-[10px] font-mono ${col.primaryKey ? 'bg-amber-50 border-amber-300 text-amber-700' : 'bg-white'}`}
                    >
                      {col.primaryKey && <span className="mr-0.5">PK</span>}
                      {col.name}
                      <span className="ml-1 text-slate-400">{col.type || 'ANY'}</span>
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Data rows — single scroll container for both axes so both scrollbars are always visible */}
              <div className="flex-1 min-h-0 table-scroll-both">
                {detailTable.rows.length > 0 ? (
                  <table className="w-full caption-bottom text-sm border-collapse">
                    <thead className="sticky top-0 z-10">
                      <tr className="bg-slate-100 border-b">
                        <th className="h-10 px-2 text-center text-[11px] font-medium text-slate-600 whitespace-nowrap bg-slate-100 sticky left-0 z-20">
                          #
                        </th>
                        {detailTable.resultColumns.map(col => (
                          <th key={col} className="h-10 px-2 text-left text-[11px] font-medium font-mono whitespace-nowrap bg-slate-100">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {detailTable.rows.map((row, i) => (
                        <tr key={i} className={`border-b ${i % 2 === 0 ? '' : 'bg-slate-50/50'}`}>
                          <td className="p-2 text-center text-[11px] text-muted-foreground font-mono sticky left-0 bg-inherit z-[1] whitespace-nowrap">
                            {i + 1}
                          </td>
                          {detailTable.resultColumns.map(col => {
                            const val = row[col]
                            const isNull = val === null || val === undefined
                            return (
                              <td key={col} className={`p-2 font-mono text-[11px] max-w-[300px] truncate whitespace-nowrap ${isNull ? 'text-red-400 italic' : ''}`}>
                                {isNull ? 'NULL' : formatCellValue(val)}
                              </td>
                            )
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="py-16 text-center text-sm text-slate-400">
                    <FileUp className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                    No data file found for this table.
                  </div>
                )}
              </div>

              {detailTable.truncated && (
                <div className="px-6 py-2 border-t bg-amber-50 text-center text-xs text-amber-700 shrink-0">
                  Showing first {detailTable.rowCount} of {detailTable.totalRows.toLocaleString()} rows. Use SQL Playground to query more data.
                </div>
              )}
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  )
}
