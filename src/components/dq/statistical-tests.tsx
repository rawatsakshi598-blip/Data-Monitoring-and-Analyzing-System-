'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  FlaskConical, Play, Download, CheckCircle2, XCircle, Loader2,
  Minus, Info, BarChart3,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

// ── Types ──
interface TestResult {
  id: string
  testName: string
  testType: string
  nullHypothesis: string
  altHypothesis: string
  statistic: number
  pValue: number
  significant: boolean
  confidenceLevel: number
  effectSize?: number
  conclusion: string
  timestamp: string
  tableName: string
  columns: string[]
}

interface TestConfig {
  columns: string
  groupColumn: string
  confidence: string
  sampleSize: string
}

const TEST_TYPES = [
  { type: 't_test', name: 'Independent T-Test', description: 'Compare means of two groups', requiresGroup: true, icon: '📊' },
  { type: 'paired_t_test', name: 'Paired T-Test', description: 'Compare paired observations', requiresGroup: false, icon: '🔄' },
  { type: 'chi_square', name: 'Chi-Square Test', description: 'Test independence of categories', requiresGroup: true, icon: '🔲' },
  { type: 'anova', name: 'One-Way ANOVA', description: 'Compare means across groups', requiresGroup: true, icon: '📈' },
  { type: 'mann_whitney', name: 'Mann-Whitney U', description: 'Non-parametric group comparison', requiresGroup: true, icon: '📉' },
  { type: 'ks_test', name: 'Kolmogorov-Smirnov', description: 'Test distribution normality', requiresGroup: false, icon: '🔔' },
  { type: 'correlation', name: 'Correlation Test', description: 'Test linear relationship', requiresGroup: false, icon: '🔗' },
  { type: 'levene', name: "Levene's Test", description: 'Test equality of variances', requiresGroup: true, icon: '📐' },
]

// ── Helpers ──
function SignificanceBadge({ significant }: { significant: boolean }) {
  return (
    <Badge variant="outline" className={cn(
      'text-[10px]',
      significant ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-slate-50 text-slate-600 border-slate-200'
    )}>
      {significant ? 'Significant' : 'Not Significant'}
    </Badge>
  )
}

function PValueDisplay({ value }: { value: number }) {
  const isSmall = value < 0.001
  return (
    <span className={cn('font-mono', value < 0.05 ? 'text-emerald-600 font-semibold' : 'text-slate-600')}>
      {isSmall ? '< 0.001' : value.toFixed(4)}
    </span>
  )
}

// ── Main Component ──
export default function StatisticalTests() {
  const [results, setResults] = useState<TestResult[]>([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedTest, setSelectedTest] = useState('t_test')
  const [tableName, setTableName] = useState('customers')
  const [tables, setTables] = useState<string[]>([])
  const [config, setConfig] = useState<TestConfig>({
    columns: '', groupColumn: '', confidence: '95', sampleSize: '',
  })
  const [selectedResult, setSelectedResult] = useState<TestResult | null>(null)

  const fetchTables = useCallback(async () => {
    try {
      const res = await fetch('/api/tables')
      if (res.ok) {
        const data = await res.json()
        const tableList = Array.isArray(data) ? data.map((t: { name?: string; tableName?: string }) => t.name || t.tableName || '').filter(Boolean) : []
        setTables(tableList)
        if (tableList.length > 0 && !tables.includes(tableName)) setTableName(tableList[0])
      } else {
        setTables([])
      }
    } catch {
      setTables([])
    }
  }, [])

  const fetchHistory = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/statistical/results/${encodeURIComponent(tableName)}`)
      if (res.ok) {
        const data = await res.json()
        setResults(Array.isArray(data) ? data : data?.results || [])
      } else {
        setResults([])
      }
    } catch {
      setError('Failed to load test history')
    } finally {
      setLoading(false)
    }
  }, [tableName])

  useEffect(() => { fetchTables(); fetchHistory() }, [fetchTables, fetchHistory])

  const handleRunTest = async () => {
    if (!config.columns.trim()) {
      toast.error('Please specify columns for the test')
      return
    }
    setRunning(true)
    try {
      const res = await fetch('/api/statistical/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          testType: selectedTest,
          tableName,
          columns: config.columns.split(',').map((c) => c.trim()),
          groupColumn: config.groupColumn || undefined,
          confidenceLevel: parseInt(config.confidence),
          sampleSize: config.sampleSize ? parseInt(config.sampleSize) : undefined,
        }),
      })
      if (res.ok) {
        const data = await res.json()
        const newResult: TestResult = data.result || data
        setResults((prev) => [newResult, ...prev])
        setSelectedResult(newResult)
        toast.success('Statistical test completed')
      } else {
        throw new Error('Failed')
      }
    } catch {
      toast.error('Failed to run statistical test — backend unavailable. Please ensure the Python backend is running on port 3001.')
    } finally {
      setRunning(false)
    }
  }

  const handleExport = () => {
    if (results.length === 0) return
    const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `stat-tests-${tableName}.json`; a.click()
    URL.revokeObjectURL(url)
    toast.success('Results exported')
  }

  const currentTestMeta = TEST_TYPES.find((t) => t.type === selectedTest)

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between"><Skeleton className="h-8 w-48" /><Skeleton className="h-10 w-36" /></div>
        <div className="grid gap-6 lg:grid-cols-5"><Skeleton className="h-96 rounded-xl" /><Skeleton className="h-96 rounded-xl lg:col-span-3" /></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Statistical Tests</h2>
          <p className="text-sm text-slate-500 mt-1">Run statistical tests on your data for hypothesis validation</p>
        </div>
        <Button variant="outline" className="gap-2" onClick={handleExport} disabled={results.length === 0}>
          <Download className="h-4 w-4" /> Export All
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        {/* Test Configuration */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <FlaskConical className="h-4 w-4" /> Configure Test
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Test Type</Label>
                <Select value={selectedTest} onValueChange={setSelectedTest}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {TEST_TYPES.map((t) => (
                      <SelectItem key={t.type} value={t.type}>{t.icon} {t.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {currentTestMeta && (
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-xs text-slate-500 mb-1">{currentTestMeta.description}</p>
                  <p className="text-[10px] text-slate-400">
                    {currentTestMeta.requiresGroup ? 'Requires: group column' : 'Requires: numeric column(s)'}
                  </p>
                </div>
              )}

              <div className="space-y-2">
                <Label>Table</Label>
                <Select value={tableName} onValueChange={setTableName}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {tables.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Columns (comma-separated)</Label>
                <Input
                  placeholder="e.g., income, credit_score"
                  value={config.columns}
                  onChange={(e) => setConfig((p) => ({ ...p, columns: e.target.value }))}
                />
              </div>

              {currentTestMeta?.requiresGroup && (
                <div className="space-y-2">
                  <Label>Group Column</Label>
                  <Input
                    placeholder="e.g., segment, region"
                    value={config.groupColumn}
                    onChange={(e) => setConfig((p) => ({ ...p, groupColumn: e.target.value }))}
                  />
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label>Confidence Level</Label>
                  <Select value={config.confidence} onValueChange={(v) => setConfig((p) => ({ ...p, confidence: v }))}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="90">90%</SelectItem>
                      <SelectItem value="95">95%</SelectItem>
                      <SelectItem value="99">99%</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Sample Size (optional)</Label>
                  <Input
                    type="number"
                    placeholder="All rows"
                    value={config.sampleSize}
                    onChange={(e) => setConfig((p) => ({ ...p, sampleSize: e.target.value }))}
                  />
                </div>
              </div>

              <Button onClick={handleRunTest} disabled={running || !config.columns.trim()} className="w-full gap-2">
                {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                {running ? 'Running...' : 'Run Test'}
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Results */}
        <div className="lg:col-span-3 space-y-4">
          {error && (
            <Card className="border-red-200 bg-red-50/50">
              <CardContent className="p-4"><p className="text-sm text-red-700">{error}</p></CardContent>
            </Card>
          )}

          {/* Selected Result Detail */}
          {selectedResult && (
            <Card className="border-emerald-200">
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <FlaskConical className="h-4 w-4 text-emerald-500" />
                  {selectedResult.testName}
                </CardTitle>
                <CardDescription>{selectedResult.testType} · {selectedResult.tableName}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="rounded-lg bg-slate-50 p-3 text-center">
                    <p className="text-xs text-slate-400">Statistic</p>
                    <p className="text-lg font-bold">{selectedResult.statistic.toFixed(3)}</p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3 text-center">
                    <p className="text-xs text-slate-400">P-Value</p>
                    <PValueDisplay value={selectedResult.pValue} />
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3 text-center">
                    <p className="text-xs text-slate-400">Confidence</p>
                    <p className="text-lg font-bold">{selectedResult.confidenceLevel}%</p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-3 text-center">
                    <p className="text-xs text-slate-400">Result</p>
                    <SignificanceBadge significant={selectedResult.significant} />
                  </div>
                </div>

                {selectedResult.effectSize != null && (
                  <div className="rounded-lg bg-slate-50 p-3">
                    <p className="text-xs text-slate-400">Effect Size</p>
                    <p className="font-semibold">{selectedResult.effectSize.toFixed(3)}</p>
                  </div>
                )}

                <Separator />

                <div>
                  <p className="text-xs font-semibold text-slate-500 mb-1">H₀ (Null Hypothesis)</p>
                  <p className="text-sm text-slate-700">{selectedResult.nullHypothesis}</p>
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-500 mb-1">H₁ (Alternative Hypothesis)</p>
                  <p className="text-sm text-slate-700">{selectedResult.altHypothesis}</p>
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-500 mb-1">Conclusion</p>
                  <p className="text-sm text-slate-900 font-medium">{selectedResult.conclusion}</p>
                </div>
                <div className="text-xs text-slate-400">
                  Columns: {selectedResult.columns.join(', ')} · {new Date(selectedResult.timestamp).toLocaleString()}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Test History Table */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Test History for {tableName}</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {results.length === 0 ? (
                <div className="text-center py-8">
                  <FlaskConical className="h-8 w-8 text-slate-300 mx-auto mb-2 opacity-50" />
                  <p className="text-sm text-slate-400">No test results yet. Run a test to get started.</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Test</TableHead>
                      <TableHead>Columns</TableHead>
                      <TableHead>Statistic</TableHead>
                      <TableHead>P-Value</TableHead>
                      <TableHead>Result</TableHead>
                      <TableHead>Time</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {results.map((result) => (
                      <TableRow
                        key={result.id}
                        className={cn('cursor-pointer hover:bg-slate-50', selectedResult?.id === result.id ? 'bg-emerald-50' : '')}
                        onClick={() => setSelectedResult(result)}
                      >
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {result.significant ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> : <Minus className="h-3.5 w-3.5 text-slate-400" />}
                            <span className="text-sm font-medium">{result.testName}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-xs text-slate-500">{result.columns.join(', ')}</TableCell>
                        <TableCell className="font-mono text-sm">{result.statistic.toFixed(2)}</TableCell>
                        <TableCell><PValueDisplay value={result.pValue} /></TableCell>
                        <TableCell><SignificanceBadge significant={result.significant} /></TableCell>
                        <TableCell className="text-xs text-slate-400">{new Date(result.timestamp).toLocaleDateString()}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
