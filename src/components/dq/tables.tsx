'use client'

import { useEffect, useState } from 'react'
import {
  Table2,
  Search,
  ArrowUpDown,
  Database,
  AlertTriangle,
  Eye,
  ChevronDown,
  ChevronRight,
  Loader2,
  X,
  RefreshCw,
  FileUp,
} from 'lucide-react'
import {
  Table,
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

  // Show Table Data state
  const [showDataOpen, setShowDataOpen] = useState(false)
  const [previewTables, setPreviewTables] = useState<TablePreview[]>([])
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [expandedPreview, setExpandedPreview] = useState<string | null>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)

  // Single table detail preview
  const [detailTable, setDetailTable] = useState<TablePreview | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [loadingDetail, setLoadingDetail] = useState(false)

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

  // Load all uploaded tables preview — now also includes SQLite tables from uploaded_data.db
  const loadUploadedTablesPreview = async () => {
    setLoadingPreview(true)
    setPreviewError(null)
    setPreviewTables([])
    setExpandedPreview(null)
    try {
      // First, try to load from the uploaded_data SQLite database
      const sqlRes = await fetch('/api/sql/all-tables-preview?database=uploaded_data&limit=50')
      const sqlData = await sqlRes.json()

      if (sqlData.tables && sqlData.tables.length > 0) {
        // Data is in SQLite — convert to our preview format
        setPreviewTables(sqlData.tables.map((t: { name: string; columns: ColumnInfo[]; resultColumns: string[]; rows: Record<string, unknown>[]; rowCount: number; totalRows: number; truncated: boolean }) => ({
          id: t.name,
          name: t.name,
          fullyQualifiedName: `uploaded_data.${t.name}`,
          columns: t.columns,
          resultColumns: t.resultColumns,
          rows: t.rows,
          rowCount: t.rowCount,
          totalRows: t.totalRows,
          truncated: t.truncated,
        })))
      } else {
        // Fallback: load from CSV files (legacy support)
        const res = await fetch('/api/uploaded-tables-preview?limit=50')
        const data = await res.json()
        if (data.error) {
          setPreviewError(data.error)
        } else if (data.tables) {
          setPreviewTables(data.tables)
        }
      }
    } catch (err) {
      // Fallback: try CSV-based endpoint
      try {
        const res = await fetch('/api/uploaded-tables-preview?limit=50')
        const data = await res.json()
        if (data.error) {
          setPreviewError(data.error)
        } else if (data.tables) {
          setPreviewTables(data.tables)
        }
      } catch {
        setPreviewError('Failed to load table data. Is the backend running?')
      }
    } finally {
      setLoadingPreview(false)
    }
  }

  // Load single table with more rows — tries SQLite first, then CSV fallback
  const loadTableDetail = async (tableId: string) => {
    setLoadingDetail(true)
    try {
      // Try SQLite-based endpoint first (tableId might be a table name from uploaded_data db)
      const sqlRes = await fetch(`/api/sql/table-preview?database=uploaded_data&table=${encodeURIComponent(tableId)}&limit=200`)
      const sqlData = await sqlRes.json()
      if (!sqlData.error && sqlData.rows && sqlData.rows.length > 0) {
        setDetailTable({
          id: tableId,
          name: sqlData.table || tableId,
          fullyQualifiedName: `uploaded_data.${sqlData.table || tableId}`,
          columns: sqlData.columns || [],
          resultColumns: sqlData.resultColumns || [],
          rows: sqlData.rows,
          rowCount: sqlData.rowCount,
          totalRows: sqlData.totalRows,
          truncated: sqlData.truncated,
        })
        setDetailOpen(true)
      } else {
        // Fallback: CSV-based endpoint
        const res = await fetch(`/api/table-data/${tableId}?limit=200`)
        const data = await res.json()
        if (data.error) {
          setPreviewError(data.error)
        } else {
          setDetailTable(data)
          setDetailOpen(true)
        }
      }
    } catch (err) {
      // Fallback: try CSV-based endpoint
      try {
        const res = await fetch(`/api/table-data/${tableId}?limit=200`)
        const data = await res.json()
        if (data.error) {
          setPreviewError(data.error)
        } else {
          setDetailTable(data)
          setDetailOpen(true)
        }
      } catch {
        setPreviewError('Failed to load table detail.')
      }
    } finally {
      setLoadingDetail(false)
    }
  }

  const handleOpenShowData = () => {
    setShowDataOpen(true)
    loadUploadedTablesPreview()
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
            {tables.length} tables across all services
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* SHOW TABLE DATA BUTTON */}
          <Button
            variant="default"
            size="sm"
            className="gap-1.5 bg-indigo-600 hover:bg-indigo-700"
            onClick={handleOpenShowData}
          >
            <Eye className="h-3.5 w-3.5" />
            Show Table Data
          </Button>
          <div className="w-px h-6 bg-slate-200" />
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
            <Table>
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
                  <TableRow key={t.id} className="cursor-pointer hover:bg-slate-50">
                    <TableCell>
                      <div>
                        <div className="font-medium text-slate-900">{t.name}</div>
                        <div className="text-xs text-slate-400">{t.fullyQualifiedName}</div>
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
            </Table>
          </CardContent>
        </Card>
      )}

      {/* SHOW TABLE DATA DIALOG */}
      <Dialog open={showDataOpen} onOpenChange={setShowDataOpen}>
        <DialogContent className="max-w-[95vw] w-full max-h-[90vh] flex flex-col p-0">
          <DialogHeader className="px-6 pt-6 pb-3 border-b shrink-0">
            <DialogTitle className="flex items-center gap-2 text-lg">
              <Eye className="h-5 w-5 text-indigo-600" />
              Show Table Data
              {previewTables.length > 0 && (
                <Badge variant="secondary" className="text-xs ml-2">
                  {previewTables.length} tables
                </Badge>
              )}
            </DialogTitle>
          </DialogHeader>

          {/* Toolbar */}
          <div className="px-6 py-3 border-b bg-slate-50/50 flex items-center gap-3 shrink-0">
            <Button
              variant="outline"
              size="sm"
              className="h-9 gap-1.5"
              onClick={loadUploadedTablesPreview}
              disabled={loadingPreview}
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loadingPreview ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            {previewTables.length > 0 && (
              <span className="text-xs text-slate-500">
                Showing data from your uploaded tables (queryable in SQL Playground)
              </span>
            )}
          </div>

          {/* Error */}
          {previewError && (
            <div className="mx-6 mt-3 p-3 rounded-lg bg-red-50 border border-red-200 flex items-center gap-2 text-sm text-red-700">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              {previewError}
              <Button variant="ghost" size="icon" className="h-6 w-6 ml-auto" onClick={() => setPreviewError(null)}>
                <X className="h-3 w-3" />
              </Button>
            </div>
          )}

          {/* Loading */}
          {loadingPreview && (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
              <span className="ml-3 text-sm text-slate-500">Loading table data...</span>
            </div>
          )}

          {/* Tables preview content */}
          {!loadingPreview && previewTables.length > 0 && (
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
              {previewTables.map((tbl) => (
                <div key={tbl.id} className="rounded-lg border bg-white shadow-sm">
                  {/* Table header — div instead of button to avoid nested button error */}
                  <div
                    className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 transition cursor-pointer"
                    onClick={() => setExpandedPreview(expandedPreview === tbl.id ? null : tbl.id)}
                  >
                    <div className="flex items-center gap-3">
                      <Table2 className="h-4 w-4 text-indigo-500" />
                      <span className="font-semibold text-slate-800">{tbl.name}</span>
                      <Badge variant="outline" className="text-[10px]">
                        {tbl.columns.length} cols
                      </Badge>
                      <Badge variant="secondary" className="text-[10px]">
                        {tbl.totalRows.toLocaleString()} rows
                      </Badge>
                      {tbl.truncated && (
                        <Badge variant="outline" className="text-[10px] text-amber-600 border-amber-300">
                          Showing first {tbl.rowCount}
                        </Badge>
                      )}
                      {tbl.rows.length === 0 && (
                        <Badge variant="outline" className="text-[10px] text-slate-400 border-slate-200">
                          No CSV data found
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-[11px] px-2.5 gap-1"
                        onClick={(e) => {
                          e.stopPropagation()
                          loadTableDetail(tbl.id)
                        }}
                        disabled={loadingDetail}
                      >
                        <Eye className="h-3 w-3" />
                        View All
                      </Button>
                      {expandedPreview === tbl.id ? (
                        <ChevronDown className="h-4 w-4 text-slate-400" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-slate-400" />
                      )}
                    </div>
                  </div>

                  {/* Expanded: show data preview */}
                  {expandedPreview === tbl.id && (
                    <div className="border-t">
                      {/* Column info */}
                      <div className="px-4 py-2 bg-slate-50/80 border-b">
                        <p className="text-xs font-medium text-slate-500 mb-1.5">Columns</p>
                        <div className="flex flex-wrap gap-1.5">
                          {tbl.columns.map(col => (
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

                      {/* Data rows */}
                      {tbl.rows.length > 0 ? (
                        <div className="overflow-x-auto">
                          <Table>
                            <TableHeader>
                              <TableRow className="bg-slate-50 hover:bg-slate-50">
                                <TableHead className="w-10 text-center text-[11px]">#</TableHead>
                                {tbl.resultColumns.map(col => (
                                  <TableHead key={col} className="font-mono text-[11px] whitespace-nowrap">
                                    {col}
                                  </TableHead>
                                ))}
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {tbl.rows.map((row, i) => (
                                <TableRow key={i} className={i % 2 === 0 ? '' : 'bg-slate-50/50'}>
                                  <TableCell className="text-center text-[11px] text-muted-foreground font-mono">
                                    {i + 1}
                                  </TableCell>
                                  {tbl.resultColumns.map(col => {
                                    const val = row[col]
                                    const isNull = val === null || val === undefined
                                    return (
                                      <TableCell key={col} className={`font-mono text-[11px] max-w-[200px] truncate ${isNull ? 'text-red-400 italic' : ''}`}>
                                        {isNull ? 'NULL' : formatCellValue(val)}
                                      </TableCell>
                                    )
                                  })}
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      ) : (
                        <div className="py-8 text-center text-sm text-slate-400">
                          <FileUp className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                          No data file found for this table.
                          <br />
                          <span className="text-xs">Data may not have been saved during upload.</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Empty state */}
          {!loadingPreview && previewTables.length === 0 && !previewError && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Database className="h-12 w-12 text-slate-300 mb-3" />
              <p className="text-sm text-slate-500">No uploaded tables found</p>
              <p className="text-xs text-slate-400 mt-1">Upload a CSV or Excel file to see table data here</p>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* TABLE DETAIL DIALOG (View All - up to 200 rows) */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-[95vw] w-full max-h-[85vh] flex flex-col p-0">
          <DialogHeader className="px-6 pt-6 pb-3 border-b shrink-0">
            <DialogTitle className="flex items-center gap-2">
              <Table2 className="h-5 w-5 text-indigo-600" />
              {detailTable?.name || 'Table Data'}
              {detailTable && (
                <Badge variant="secondary" className="text-xs ml-2">
                  {detailTable.totalRows.toLocaleString()} total rows
                </Badge>
              )}
            </DialogTitle>
          </DialogHeader>

          {loadingDetail ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
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

              {/* Data rows */}
              <div className="flex-1 overflow-auto">
                {detailTable.rows.length > 0 ? (
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-slate-50 hover:bg-slate-50 sticky top-0">
                        <TableHead className="w-10 text-center text-[11px]">#</TableHead>
                        {detailTable.resultColumns.map(col => (
                          <TableHead key={col} className="font-mono text-[11px] whitespace-nowrap">
                            {col}
                          </TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {detailTable.rows.map((row, i) => (
                        <TableRow key={i} className={i % 2 === 0 ? '' : 'bg-slate-50/50'}>
                          <TableCell className="text-center text-[11px] text-muted-foreground font-mono">
                            {i + 1}
                          </TableCell>
                          {detailTable.resultColumns.map(col => {
                            const val = row[col]
                            const isNull = val === null || val === undefined
                            return (
                              <TableCell key={col} className={`font-mono text-[11px] max-w-[250px] truncate ${isNull ? 'text-red-400 italic' : ''}`}>
                                {isNull ? 'NULL' : formatCellValue(val)}
                              </TableCell>
                            )
                          })}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                ) : (
                  <div className="py-16 text-center text-sm text-slate-400">
                    <FileUp className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                    No data file found for this table.
                  </div>
                )}
              </div>

              {detailTable.truncated && (
                <div className="px-6 py-2 border-t bg-amber-50 text-center text-xs text-amber-700">
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
