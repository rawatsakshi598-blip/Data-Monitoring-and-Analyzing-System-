'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  BarChart3, FileSearch, AlertTriangle, CheckCircle2, Loader2, Download,
  RefreshCw, Info, Sparkles, Columns, Hash, Type, Calendar, BarChart2,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

// ── Types ──
interface ColumnProfile {
  name: string
  type: 'numeric' | 'categorical' | 'datetime' | 'boolean'
  missingCount: number
  missingPct: number
  uniqueCount: number
  totalCount: number
  mean?: number
  std?: number
  min?: number
  max?: number
  median?: number
  topValues?: { value: string; count: number; pct: number }[]
}

interface EDAReport {
  tableName: string
  totalRows: number
  totalColumns: number
  memoryUsage: string
  duplicateRows: number
  duplicatePct: number
  numericCols: number
  categoricalCols: number
  datetimeCols: number
  booleanCols: number
  overallMissing: number
  columnProfiles: ColumnProfile[]
  correlations: { col1: string; col2: string; value: number }[]
  insights: { type: string; message: string; severity: 'info' | 'warning' | 'critical' }[]
}

// ── Helpers ──
function TypeIcon({ type }: { type: string }) {
  switch (type) {
    case 'numeric': return <Hash className="h-3.5 w-3.5 text-blue-500" />
    case 'categorical': return <Type className="h-3.5 w-3.5 text-emerald-500" />
    case 'datetime': return <Calendar className="h-3.5 w-3.5 text-amber-500" />
    case 'boolean': return <BarChart2 className="h-3.5 w-3.5 text-violet-500" />
    default: return <Columns className="h-3.5 w-3.5" />
  }
}

function SeverityIcon({ severity }: { severity: string }) {
  switch (severity) {
    case 'critical': return <AlertTriangle className="h-4 w-4 text-red-500" />
    case 'warning': return <AlertTriangle className="h-4 w-4 text-amber-500" />
    default: return <Info className="h-4 w-4 text-blue-500" />
  }
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: 'bg-red-500/15 text-red-700 border-red-500/30',
    warning: 'bg-amber-500/15 text-amber-700 border-amber-500/30',
    info: 'bg-sky-500/15 text-sky-700 border-sky-500/30',
  }
  return <Badge variant="outline" className={cn('text-[10px]', colors[severity] || '')}>{severity}</Badge>
}

const missingColor = (pct: number) =>
  pct === 0 ? 'text-emerald-600' : pct < 5 ? 'text-amber-600' : 'text-red-600'

// ── Main Component ──
export default function AutoEDA() {
  const [report, setReport] = useState<EDAReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedTable, setSelectedTable] = useState('')
  const [tables, setTables] = useState<string[]>([])
  const [selectedColumn, setSelectedColumn] = useState<ColumnProfile | null>(null)

  const fetchTables = useCallback(async () => {
    try {
      const res = await fetch('/api/tables')
      if (res.ok) {
        const data = await res.json()
        const tableList = Array.isArray(data) ? data.map((t: { name?: string; tableName?: string }) => t.name || t.tableName || '').filter(Boolean) : []
        setTables(tableList)
        if (tableList.length > 0) setSelectedTable(tableList[0])
      } else {
        setTables([])
      }
    } catch {
      setTables([])
    } finally {
      setInitialLoading(false)
    }
  }, [])

  useEffect(() => { fetchTables() }, [fetchTables])

  const generateReport = async () => {
    if (!selectedTable) return
    setLoading(true)
    setError(null)
    setReport(null)
    try {
      const res = await fetch(`/api/auto-eda/${encodeURIComponent(selectedTable)}`)
      if (res.ok) {
        const data = await res.json()
        setReport(data)
        toast.success('EDA report generated')
      } else {
        throw new Error('Failed to generate report')
      }
    } catch {
      setError('Failed to generate EDA report. Please try again.')
      toast.error('EDA report generation failed')
    } finally {
      setLoading(false)
    }
  }

  const handleExport = () => {
    if (!report) return
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `eda-report-${report.tableName}.json`; a.click()
    URL.revokeObjectURL(url)
    toast.success('Report exported')
  }

  if (initialLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between"><Skeleton className="h-8 w-48" /><Skeleton className="h-10 w-64" /></div>
        <div className="grid gap-4 sm:grid-cols-4">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}</div>
        <Skeleton className="h-96 rounded-xl" />
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <Loader2 className="h-10 w-10 animate-spin text-emerald-500" />
        <div className="text-center">
          <p className="font-semibold text-slate-700">Generating EDA Report...</p>
          <p className="text-sm text-slate-400">Analyzing column profiles, correlations, and distributions</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Auto-EDA Report</h2>
          <p className="text-sm text-slate-500 mt-1">One-click exploratory data analysis with insights</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={selectedTable} onValueChange={setSelectedTable}>
            <SelectTrigger className="w-48"><SelectValue placeholder="Select table" /></SelectTrigger>
            <SelectContent>
              {tables.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
            </SelectContent>
          </Select>
          <Button onClick={generateReport} className="gap-2"><Sparkles className="h-4 w-4" />Generate Report</Button>
          {report && <Button variant="outline" className="gap-2" onClick={handleExport}><Download className="h-4 w-4" />Export</Button>}
        </div>
      </div>

      {error && (
        <Card className="border-red-200 bg-red-50/50">
          <CardContent className="p-4 flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-red-500 shrink-0" />
            <p className="text-sm text-red-700">{error}</p>
            <Button variant="outline" size="sm" onClick={generateReport} className="ml-auto"><RefreshCw className="h-3.5 w-3.5 mr-1" />Retry</Button>
          </CardContent>
        </Card>
      )}

      {report && (
        <>
          {/* Overview Stats */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card><CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-blue-50 p-2"><FileSearch className="h-4 w-4 text-blue-600" /></div>
                <div><p className="text-xs text-slate-500">Total Rows</p><p className="text-lg font-bold text-slate-900">{report.totalRows.toLocaleString()}</p></div>
              </div>
            </CardContent></Card>
            <Card><CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-emerald-50 p-2"><Columns className="h-4 w-4 text-emerald-600" /></div>
                <div><p className="text-xs text-slate-500">Total Columns</p><p className="text-lg font-bold text-slate-900">{report.totalColumns}</p></div>
              </div>
            </CardContent></Card>
            <Card><CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-amber-50 p-2"><AlertTriangle className="h-4 w-4 text-amber-600" /></div>
                <div><p className="text-xs text-slate-500">Missing Overall</p><p className="text-lg font-bold text-slate-900">{report.overallMissing}%</p></div>
              </div>
            </CardContent></Card>
            <Card><CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-red-50 p-2"><BarChart3 className="h-4 w-4 text-red-600" /></div>
                <div><p className="text-xs text-slate-500">Duplicates</p><p className="text-lg font-bold text-slate-900">{report.duplicateRows} ({report.duplicatePct}%)</p></div>
              </div>
            </CardContent></Card>
          </div>

          {/* Column Type Summary */}
          <div className="grid gap-4 sm:grid-cols-4">
            <Card><CardContent className="p-3 flex items-center gap-2"><Hash className="h-4 w-4 text-blue-500" /><span className="text-sm">Numeric: <strong>{report.numericCols}</strong></span></CardContent></Card>
            <Card><CardContent className="p-3 flex items-center gap-2"><Type className="h-4 w-4 text-emerald-500" /><span className="text-sm">Categorical: <strong>{report.categoricalCols}</strong></span></CardContent></Card>
            <Card><CardContent className="p-3 flex items-center gap-2"><Calendar className="h-4 w-4 text-amber-500" /><span className="text-sm">Datetime: <strong>{report.datetimeCols}</strong></span></CardContent></Card>
            <Card><CardContent className="p-3 flex items-center gap-2"><BarChart2 className="h-4 w-4 text-violet-500" /><span className="text-sm">Boolean: <strong>{report.booleanCols}</strong></span></CardContent></Card>
          </div>

          {/* Insights */}
          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-sm">Key Insights</CardTitle></CardHeader>
            <CardContent>
              <ScrollArea className="h-[220px]">
                <div className="space-y-2">
                  {report.insights.map((insight, i) => (
                    <div key={i} className={cn(
                      'flex items-start gap-3 rounded-lg border p-3',
                      insight.severity === 'critical' ? 'border-red-200 bg-red-50/50' :
                      insight.severity === 'warning' ? 'border-amber-200 bg-amber-50/50' :
                      'border-blue-200 bg-blue-50/50'
                    )}>
                      <SeverityIcon severity={insight.severity} />
                      <div className="flex-1">
                        <p className="text-sm text-slate-700">{insight.message}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <SeverityBadge severity={insight.severity} />
                          <Badge variant="outline" className="text-[10px]">{insight.type}</Badge>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          <Tabs defaultValue="columns" className="space-y-4">
            <TabsList>
              <TabsTrigger value="columns">Column Profiles</TabsTrigger>
              <TabsTrigger value="correlations">Correlations</TabsTrigger>
            </TabsList>

            {/* Column Profiles */}
            <TabsContent value="columns">
              <Card>
                <CardContent className="p-0">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Column</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Null Count</TableHead>
                        <TableHead>Missing %</TableHead>
                        <TableHead>Unique</TableHead>
                        <TableHead>Min / Top</TableHead>
                        <TableHead>Max / Count</TableHead>
                        <TableHead>Mean</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {report.columnProfiles.map((col) => (
                        <TableRow key={col.name} className="cursor-pointer hover:bg-slate-50" onClick={() => setSelectedColumn(col)}>
                          <TableCell className="font-medium">{col.name}</TableCell>
                          <TableCell>
                            <Badge variant="outline" className="gap-1 text-[11px]"><TypeIcon type={col.type} />{col.type}</Badge>
                          </TableCell>
                          <TableCell className="text-slate-600">{col.missingCount.toLocaleString()}</TableCell>
                          <TableCell className={cn('font-medium', missingColor(col.missingPct))}>{col.missingPct}%</TableCell>
                          <TableCell className="text-slate-600">{col.uniqueCount.toLocaleString()}</TableCell>
                          <TableCell className="text-slate-600">
                            {col.type === 'numeric' ? (col.min?.toLocaleString() ?? '-') : (col.topValues?.[0]?.value ?? '-')}
                          </TableCell>
                          <TableCell className="text-slate-600">
                            {col.type === 'numeric' ? (col.max?.toLocaleString() ?? '-') : (col.topValues?.[0]?.count.toLocaleString() ?? '-')}
                          </TableCell>
                          <TableCell className="text-slate-600">{col.type === 'numeric' ? (col.mean?.toLocaleString(undefined, { maximumFractionDigits: 1 }) ?? '-') : '-'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>

              {selectedColumn && (
                <Card className="mt-4">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <TypeIcon type={selectedColumn.type} />
                      {selectedColumn.name}
                      <Badge variant="outline" className="text-[11px]">{selectedColumn.type}</Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {selectedColumn.type === 'numeric' && (
                      <div className="grid grid-cols-3 gap-4">
                        <div className="rounded-lg bg-slate-50 p-3 text-center">
                          <p className="text-xs text-slate-400">Mean</p>
                          <p className="font-semibold">{selectedColumn.mean?.toLocaleString()}</p>
                        </div>
                        <div className="rounded-lg bg-slate-50 p-3 text-center">
                          <p className="text-xs text-slate-400">Median</p>
                          <p className="font-semibold">{selectedColumn.median?.toLocaleString()}</p>
                        </div>
                        <div className="rounded-lg bg-slate-50 p-3 text-center">
                          <p className="text-xs text-slate-400">Std Dev</p>
                          <p className="font-semibold">{selectedColumn.std?.toLocaleString()}</p>
                        </div>
                      </div>
                    )}
                    {selectedColumn.topValues && (
                      <div className="space-y-2">
                        {selectedColumn.topValues.map((tv, i) => (
                          <div key={i} className="flex items-center gap-3">
                            <span className="w-28 text-sm text-slate-700 truncate">{tv.value}</span>
                            <div className="flex-1"><Progress value={tv.pct} className="h-2" /></div>
                            <span className="text-xs text-slate-500 w-16 text-right">{tv.pct}%</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* Correlations */}
            <TabsContent value="correlations">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm">Feature Correlations</CardTitle>
                  <CardDescription>Pearson correlation coefficients between numeric columns</CardDescription>
                </CardHeader>
                <CardContent>
                  {report.correlations.length > 0 ? (
                    <ScrollArea className="max-h-[400px]">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Column 1</TableHead>
                            <TableHead>Column 2</TableHead>
                            <TableHead>Correlation</TableHead>
                            <TableHead>Strength</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {report.correlations.map((c, i) => (
                            <TableRow key={i}>
                              <TableCell className="font-medium">{c.col1}</TableCell>
                              <TableCell className="font-medium">{c.col2}</TableCell>
                              <TableCell className={cn('font-semibold', Math.abs(c.value) > 0.5 ? 'text-red-600' : Math.abs(c.value) > 0.3 ? 'text-amber-600' : 'text-emerald-600')}>
                                {c.value.toFixed(3)}
                              </TableCell>
                              <TableCell>
                                <Badge variant="outline" className={cn('text-[10px]',
                                  Math.abs(c.value) > 0.5 ? 'bg-red-50 text-red-700 border-red-200' :
                                  Math.abs(c.value) > 0.3 ? 'bg-amber-50 text-amber-700 border-amber-200' :
                                  'bg-emerald-50 text-emerald-700 border-emerald-200'
                                )}>
                                  {Math.abs(c.value) > 0.5 ? 'High' : Math.abs(c.value) > 0.3 ? 'Medium' : 'Low'}
                                </Badge>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </ScrollArea>
                  ) : (
                    <div className="text-center py-8 text-slate-400">
                      <BarChart3 className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      No correlation data available
                    </div>
                  )}
                  <div className="flex items-center gap-4 mt-3 text-xs text-slate-500">
                    <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-emerald-500" /> Low (&lt;0.3)</span>
                    <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-amber-500" /> Medium (0.3-0.5)</span>
                    <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-red-500" /> High (&gt;0.5)</span>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </>
      )}

      {!report && !loading && !error && (
        <Card>
          <CardContent className="p-12 text-center">
            <BarChart3 className="h-12 w-12 text-slate-300 mx-auto mb-4" />
            <h3 className="font-semibold text-slate-700 mb-1">No EDA Report Generated</h3>
            <p className="text-sm text-slate-400 mb-4">Select a table and click Generate Report</p>
            <Button onClick={generateReport} className="gap-2"><Sparkles className="h-4 w-4" /> Generate Report</Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
