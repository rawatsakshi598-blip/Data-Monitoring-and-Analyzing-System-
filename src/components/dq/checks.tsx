'use client'

import { useEffect, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { formatDistanceToNow, format } from 'date-fns'
import {
  ClipboardCheck,
  TrendingUp,
  Gauge,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  AlertOctagon,
  Filter,
  Play,
  RefreshCw,
  Loader2,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { QualityCheck, Dataset } from '@/lib/store'
import { toast } from 'sonner'

const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
}

interface CheckWithNames extends QualityCheck {
  ruleName?: string
  datasetName?: string
}

function getStatusBadge(status: string) {
  switch (status) {
    case 'passed':
      return <Badge className="bg-emerald-500/15 text-emerald-700 border-emerald-500/30">Passed</Badge>
    case 'failed':
      return <Badge variant="destructive">Failed</Badge>
    case 'warning':
      return <Badge className="bg-amber-500/15 text-amber-700 border-amber-500/30">Warning</Badge>
    case 'error':
      return <Badge variant="destructive">Error</Badge>
    case 'running':
      return <Badge className="bg-sky-500/15 text-sky-700 border-sky-500/30">Running</Badge>
    default:
      return <Badge variant="secondary">{status}</Badge>
  }
}

function getScoreColor(score: number) {
  if (score >= 90) return 'text-emerald-600'
  if (score >= 70) return 'text-amber-600'
  return 'text-red-600'
}

function formatDuration(ms: number | undefined | null) {
  if (ms == null) return '0ms'
  if (ms >= 1000) {
    const secs = (ms / 1000).toFixed(1)
    return `${secs}s`
  }
  return `${ms}ms`
}

function formatNumber(n: number | undefined | null) {
  return (n ?? 0).toLocaleString()
}

export default function ChecksView() {
  const [checks, setChecks] = useState<CheckWithNames[]>([])

  const safeFixed = (val: number | undefined | null, d = 1) => (val ?? 0).toFixed(d)
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [runningAll, setRunningAll] = useState(false)

  // Filters
  const [datasetFilter, setDatasetFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [limit, setLimit] = useState('25')

  const fetchChecks = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const params = new URLSearchParams({ limit })
      if (datasetFilter !== 'all') params.set('datasetId', datasetFilter)
      if (statusFilter !== 'all') params.set('status', statusFilter)
      const res = await fetch(`/api/checks?${params.toString()}`)
      if (!res.ok) throw new Error('Failed to fetch checks')
      const data = await res.json()
      // Backend returns { rule: { name }, dataset: { name } } — map to flat fields
      const mapped = (Array.isArray(data) ? data : []).map((c: any) => ({
        ...c,
        ruleName: c.ruleName || c.rule?.name || '',
        datasetName: c.datasetName || c.dataset?.name || '',
      }))
      setChecks(mapped)
    } catch (err) {
      console.error('Failed to fetch checks:', err)
      setError('Failed to load checks')
    } finally {
      setLoading(false)
    }
  }, [datasetFilter, statusFilter, limit])

  const fetchDatasets = useCallback(async () => {
    try {
      const res = await fetch('/api/datasets')
      if (res.ok) {
        const data = await res.json()
        setDatasets(Array.isArray(data) ? data : [])
      }
    } catch {
      // datasets optional
    }
  }, [])

  const handleRunAllChecks = useCallback(async () => {
    setRunningAll(true)
    try {
      // Fetch all rules first
      const rulesRes = await fetch('/api/rules')
      if (!rulesRes.ok) throw new Error('Failed to fetch rules')
      const rules = await rulesRes.json()
      const ruleList = Array.isArray(rules) ? rules : []

      if (ruleList.length === 0) {
        toast.error('No quality rules found. Create rules first, then run checks.')
        return
      }

      // Run each rule
      let passed = 0
      let failed = 0
      for (const rule of ruleList) {
        try {
          const res = await fetch('/api/run-check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ruleId: rule.id }),
          })
          if (res.ok) passed++
          else failed++
        } catch {
          failed++
        }
      }

      toast.success(`Ran ${ruleList.length} checks: ${passed} passed, ${failed} failed`)

      // Refresh the checks list
      await fetchChecks()
    } catch (err: any) {
      toast.error(err.message || 'Failed to run checks')
    } finally {
      setRunningAll(false)
    }
  }, [fetchChecks])

  useEffect(() => {
    fetchDatasets()
  }, [fetchDatasets])

  useEffect(() => {
    fetchChecks()
  }, [fetchChecks])

  // Summary stats
  const totalChecks = checks.length
  const passedChecks = checks.filter((c) => c.status === 'passed').length
  const passRate = totalChecks > 0 ? Math.round((passedChecks / totalChecks) * 1000) / 10 : 0
  const avgScore = totalChecks > 0
    ? Math.round((checks.reduce((sum, c) => sum + (c.score ?? 0), 0) / totalChecks) * 10) / 10
    : 0
  const avgDuration = totalChecks > 0
    ? Math.round(checks.reduce((sum, c) => sum + c.duration, 0) / totalChecks)
    : 0

  const getDatasetName = (id: string) => {
    const ds = datasets.find((d) => d.id === id)
    if (ds) return ds.name
    // Also try matching by tableId field (some datasetIds are Table UUIDs)
    const byTableId = datasets.find((d) => (d as any).tableId === id)
    if (byTableId) return byTableId.name
    // Try matching by name
    const byName = datasets.find((d) => d.name === id)
    if (byName) return byName.name
    return id.length > 16 ? id.slice(0, 8) + '…' : id
  }

  if (loading && checks.length === 0) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-40" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-96 rounded-xl" />
      </div>
    )
  }

  return (
    <motion.div
      className="space-y-6 p-6"
      variants={staggerContainer}
      initial="hidden"
      animate="visible"
    >
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold">Quality Checks</h1>
          <p className="text-sm text-muted-foreground">
            View historical quality check results and trends
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={fetchChecks}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button
            size="sm"
            className="gap-2"
            onClick={handleRunAllChecks}
            disabled={runningAll}
          >
            {runningAll ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            {runningAll ? 'Running...' : 'Run All Checks'}
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <motion.div variants={fadeInUp}>
          <Card className="shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Checks
              </CardTitle>
            </CardHeader>
            <CardContent className="flex items-center gap-3 pt-0">
              <div className="rounded-full bg-sky-500/15 p-2.5">
                <ClipboardCheck className="h-5 w-5 text-sky-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{formatNumber(totalChecks)}</p>
                <p className="text-xs text-muted-foreground">In current view</p>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={fadeInUp}>
          <Card className="shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Pass Rate
              </CardTitle>
            </CardHeader>
            <CardContent className="flex items-center gap-3 pt-0">
              <div className={`rounded-full p-2.5 ${passRate >= 90 ? 'bg-emerald-500/15' : passRate >= 70 ? 'bg-amber-500/15' : 'bg-red-500/15'}`}>
                <TrendingUp className={`h-5 w-5 ${passRate >= 90 ? 'text-emerald-600' : passRate >= 70 ? 'text-amber-600' : 'text-red-600'}`} />
              </div>
              <div>
                <p className={`text-2xl font-bold ${passRate >= 90 ? 'text-emerald-600' : passRate >= 70 ? 'text-amber-600' : 'text-red-600'}`}>
                  {passRate}%
                </p>
                <p className="text-xs text-muted-foreground">
                  {passedChecks} of {totalChecks} passed
                </p>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={fadeInUp}>
          <Card className="shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Average Score
              </CardTitle>
            </CardHeader>
            <CardContent className="flex items-center gap-3 pt-0">
              <div className="rounded-full bg-violet-500/15 p-2.5">
                <Gauge className="h-5 w-5 text-violet-600" />
              </div>
              <div>
                <p className={`text-2xl font-bold ${getScoreColor(avgScore)}`}>
                  {avgScore}
                </p>
                <p className="text-xs text-muted-foreground">Out of 100</p>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={fadeInUp}>
          <Card className="shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Avg Duration
              </CardTitle>
            </CardHeader>
            <CardContent className="flex items-center gap-3 pt-0">
              <div className="rounded-full bg-orange-500/15 p-2.5">
                <Clock className="h-5 w-5 text-orange-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{formatDuration(avgDuration)}</p>
                <p className="text-xs text-muted-foreground">Per check</p>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Filter Bar */}
      <motion.div variants={fadeInUp} className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Filter className="h-4 w-4" />
          <span>Filters:</span>
        </div>
        <Select value={datasetFilter} onValueChange={setDatasetFilter}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="All Datasets" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Datasets</SelectItem>
            {datasets.map((ds) => (
              <SelectItem key={ds.id} value={ds.id}>
                {ds.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="All Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="passed">Passed</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
            <SelectItem value="warning">Warning</SelectItem>
            <SelectItem value="error">Error</SelectItem>
          </SelectContent>
        </Select>
        <Select value={limit} onValueChange={setLimit}>
          <SelectTrigger className="w-[100px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="25">25</SelectItem>
            <SelectItem value="50">50</SelectItem>
            <SelectItem value="100">100</SelectItem>
          </SelectContent>
        </Select>
      </motion.div>

      {error ? (
        <div className="text-center py-12">
          <AlertOctagon className="h-10 w-10 text-muted-foreground mx-auto mb-2" />
          <p className="text-muted-foreground">{error}</p>
        </div>
      ) : (
        /* Checks Table */
        <motion.div variants={fadeInUp}>
          <Card className="shadow-sm">
            <CardContent className="p-0">
              <ScrollArea className="max-h-[600px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Timestamp</TableHead>
                      <TableHead>Rule</TableHead>
                      <TableHead>Dataset</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Score</TableHead>
                      <TableHead className="text-right">Records Checked</TableHead>
                      <TableHead className="text-right">Records Failed</TableHead>
                      <TableHead>Duration</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {checks.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center py-12 text-muted-foreground">
                          <CheckCircle2 className="h-8 w-8 mx-auto mb-2 opacity-50" />
                          No checks found for the selected filters
                        </TableCell>
                      </TableRow>
                    ) : (
                      checks.map((check) => (
                        <TableRow key={check.id}>
                          <TableCell className="text-sm text-muted-foreground min-w-[140px]">
                            <div className="flex flex-col">
                              <span>
                                {format(new Date(check.createdAt), 'MMM d, HH:mm')}
                              </span>
                              <span className="text-xs">
                                {formatDistanceToNow(new Date(check.createdAt), { addSuffix: true })}
                              </span>
                            </div>
                          </TableCell>
                          <TableCell className="font-medium max-w-[180px] truncate">
                            {check.ruleName || (check.ruleId || '').slice(0, 8)}
                          </TableCell>
                          <TableCell className="text-muted-foreground max-w-[150px] truncate">
                            {check.datasetName || getDatasetName(check.datasetId)}
                          </TableCell>
                          <TableCell>{getStatusBadge(check.status)}</TableCell>
                          <TableCell>
                            <span className={`font-semibold ${getScoreColor(check.score ?? 0)}`}>
                              {safeFixed(check.score ?? 0)}
                            </span>
                          </TableCell>
                          <TableCell className="text-right font-mono text-sm">
                            {formatNumber(check.recordsChecked)}
                          </TableCell>
                          <TableCell className="text-right">
                            <span className={`font-mono text-sm ${check.recordsFailed > 0 ? 'text-red-600 font-semibold' : 'text-muted-foreground'}`}>
                              {formatNumber(check.recordsFailed)}
                            </span>
                          </TableCell>
                          <TableCell className="text-muted-foreground text-sm font-mono">
                            {formatDuration(check.duration)}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </motion.div>
  )
}