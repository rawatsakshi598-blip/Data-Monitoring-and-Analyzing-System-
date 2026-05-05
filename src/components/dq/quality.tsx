'use client'

import { useEffect, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  TestTubes, CheckCircle2, XCircle, AlertTriangle, Search, Play,
  Loader2, Sparkles, FileText, Wrench, BarChart3,
  ChevronRight, Eye, RefreshCw, Zap, MoreVertical
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ScrollArea } from '@/components/ui/scroll-area'
import { type Dataset, type QualityRule, type QualityCheck } from '@/lib/store'
import { toast } from 'sonner'

// ── Helpers ──
const safeFixed = (val: number | undefined | null, d = 1) => (val ?? 0).toFixed(d)

function getScoreColor(score: number) {
  if (score >= 90) return 'text-emerald-600'
  if (score >= 70) return 'text-amber-600'
  return 'text-red-600'
}

function getScoreBg(score: number) {
  if (score >= 90) return 'bg-emerald-100 text-emerald-700'
  if (score >= 70) return 'bg-amber-100 text-amber-700'
  return 'bg-red-100 text-red-700'
}

function getStatusBadge(status: string) {
  switch (status) {
    case 'passed':  return <Badge className="bg-emerald-500/15 text-emerald-700 border-emerald-500/30">Passed</Badge>
    case 'failed':  return <Badge variant="destructive">Failed</Badge>
    case 'warning': return <Badge className="bg-amber-500/15 text-amber-700 border-amber-500/30">Warning</Badge>
    case 'error':   return <Badge variant="destructive">Error</Badge>
    default:        return <Badge variant="secondary">{status}</Badge>
  }
}

function getSeverityBadge(severity: string) {
  switch (severity) {
    case 'critical': return <Badge className="bg-red-500/15 text-red-700 border-red-500/30">critical</Badge>
    case 'warning':  return <Badge className="bg-amber-500/15 text-amber-700 border-amber-500/30">warning</Badge>
    case 'info':     return <Badge className="bg-sky-500/15 text-sky-700 border-sky-500/30">info</Badge>
    default:         return <Badge variant="secondary">{severity}</Badge>
  }
}

function getDimensionBadge(dimension: string) {
  const colors: Record<string, string> = {
    completeness: 'bg-emerald-500/15 text-emerald-700 border-emerald-500/30',
    accuracy:     'bg-sky-500/15 text-sky-700 border-sky-500/30',
    consistency:  'bg-violet-500/15 text-violet-700 border-violet-500/30',
    timeliness:   'bg-amber-500/15 text-amber-700 border-amber-500/30',
    uniqueness:   'bg-orange-500/15 text-orange-700 border-orange-500/30',
    validity:     'bg-pink-500/15 text-pink-700 border-pink-500/30',
    integrity:    'bg-teal-500/15 text-teal-700 border-teal-500/30',
    conformity:   'bg-indigo-500/15 text-indigo-700 border-indigo-500/30',
  }
  return <Badge variant="outline" className={colors[dimension] || ''}>{dimension}</Badge>
}

// ── Check Result Card (shared) ──
function CheckResultCard({ result }: { result: Record<string, unknown> }) {
  const chk    = (result.check || result) as Record<string, unknown>
  const status  = String(chk.status  || '')
  const score   = Number(chk.score   || 0)
  const mode    = String(result.executionMode || result.mode || '')
  const message = String(chk.message || '')
  const failed  = Number(chk.recordsFailed || chk.records_failed || 0)
  const isPassed = status === 'passed'

  return (
    <div className={`rounded-lg border p-4 ${isPassed ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
      <div className="flex items-center gap-3 mb-2">
        {isPassed
          ? <CheckCircle2 className="h-5 w-5 text-emerald-600" />
          : <XCircle className="h-5 w-5 text-red-600" />
        }
        <span className="font-semibold">{status.toUpperCase()}</span>
        <Badge className={getScoreBg(score)}>{safeFixed(score)}%</Badge>
        {mode && <Badge variant="outline">{mode}</Badge>}
      </div>
      {message && <p className="text-sm text-slate-600">{message}</p>}
      {failed > 0 && (
        <p className="text-xs text-red-500 mt-1">{failed.toLocaleString()} records failed</p>
      )}
    </div>
  )
}

// ── NL Rule Creator ──
function NLRuleCreator({ datasets, onCreated }: { datasets: Dataset[]; onCreated: () => void }) {
  const [prompt,    setPrompt]    = useState('')
  const [datasetId, setDatasetId] = useState('')
  const [loading,   setLoading]   = useState(false)
  const [result,    setResult]    = useState<Record<string, unknown> | null>(null)

  async function handleGenerate() {
    if (!prompt.trim() || !datasetId) return
    setLoading(true)
    setResult(null)
    try {
      const res = await fetch('/api/nl-rule', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ prompt: prompt.trim(), datasetId }),
      })
      if (!res.ok) throw new Error('Failed')
      const data = await res.json()
      setResult(data)
      onCreated()
      toast.success('Rule generated!', {
        description: `${String(data.generationMethod ?? '').toUpperCase()} — ${String(data.name ?? '')}`,
      })
    } catch {
      toast.error('Generation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="border-dashed border-2 border-primary/20">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-amber-500" />
          AI Rule Creator
        </CardTitle>
        <CardDescription>Describe your rule in plain English</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>Rule Description</Label>
          <Textarea
            placeholder="e.g. email should not be null and must contain @ symbol..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="min-h-[80px]"
          />
        </div>
        <div className="flex items-end gap-3">
          <div className="flex-1 space-y-2">
            <Label>Dataset</Label>
            <Select value={datasetId} onValueChange={setDatasetId}>
              <SelectTrigger><SelectValue placeholder="Select dataset" /></SelectTrigger>
              <SelectContent>
                {datasets.map((ds) => (
                  <SelectItem key={ds.id} value={ds.id}>{ds.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button
            onClick={handleGenerate}
            disabled={!prompt.trim() || !datasetId || loading}
            className="min-w-[160px]"
          >
            {loading
              ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Generating...</>
              : <><Sparkles className="h-4 w-4 mr-2" />Generate Rule</>
            }
          </Button>
        </div>

        <AnimatePresence>
          {result && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
            >
              <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 space-y-2">
                <div className="flex items-center gap-2 text-emerald-700">
                  <CheckCircle2 className="h-4 w-4" />
                  <span className="font-semibold text-sm">
                    Rule Generated ({String(result.generationMethod ?? '').toUpperCase()})
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                  <div>
                    <p className="text-xs text-muted-foreground">Name</p>
                    <p className="font-medium">{String(result.name ?? '')}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Type</p>
                    <p className="font-medium capitalize">{String(result.type ?? '')}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Dimension</p>
                    {getDimensionBadge(String(result.dimension ?? ''))}
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Severity</p>
                    {getSeverityBadge(String(result.severity ?? ''))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </CardContent>
    </Card>
  )
}

// ── Run Check Panel ──
function RunCheckPanel({
  datasets, rules, onDone, preselectedRuleId, onRuleConsumed,
}: {
  datasets: Dataset[]
  rules: QualityRule[]
  onDone: () => void
  preselectedRuleId: string
  onRuleConsumed: () => void
}) {
  const [datasetId, setDatasetId] = useState('')
  const [ruleId,    setRuleId]    = useState('')
  const [loading,   setLoading]   = useState(false)
  const [result,    setResult]    = useState<Record<string, unknown> | null>(null)

  useEffect(() => {
    if (!preselectedRuleId) return
    setRuleId(preselectedRuleId)
    const rule = rules.find((r) => r.id === preselectedRuleId)
    if (rule?.datasetId) setDatasetId(rule.datasetId)
    onRuleConsumed()
  }, [preselectedRuleId, rules, onRuleConsumed])

  async function handleRun() {
    if (!datasetId || !ruleId) return
    setLoading(true)
    setResult(null)
    try {
      const res = await fetch('/api/run-check', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ datasetId, ruleId }),
      })
      if (!res.ok) throw new Error('Failed')
      const data = await res.json()
      setResult(data)
      onDone()
      const chk = (data.check || data) as Record<string, unknown>
      toast.success('Check complete!', {
        description: `Status: ${String(chk.status ?? '')}, Score: ${String(chk.score ?? '')}`,
      })
    } catch {
      toast.error('Check failed')
    } finally {
      setLoading(false)
    }
  }

  const filteredRules = rules.filter((r) => !datasetId || r.datasetId === datasetId)

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Play className="h-4 w-4 text-emerald-500" />
          Run Quality Check
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label>Dataset</Label>
            <Select value={datasetId} onValueChange={(v) => { setDatasetId(v); setRuleId('') }}>
              <SelectTrigger><SelectValue placeholder="Select dataset" /></SelectTrigger>
              <SelectContent>
                {datasets.map((ds) => (
                  <SelectItem key={ds.id} value={ds.id}>{ds.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Rule</Label>
            <Select value={ruleId} onValueChange={setRuleId}>
              <SelectTrigger><SelectValue placeholder="Select rule" /></SelectTrigger>
              <SelectContent>
                {filteredRules.map((r) => (
                  <SelectItem key={r.id} value={r.id}>{r.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <Button onClick={handleRun} disabled={!datasetId || !ruleId || loading}>
          {loading
            ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Running...</>
            : <><Play className="h-4 w-4 mr-2" />Run Check</>
          }
        </Button>

        <AnimatePresence>
          {result && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <CheckResultCard result={result} />
            </motion.div>
          )}
        </AnimatePresence>
      </CardContent>
    </Card>
  )
}

// ── AI Report Panel ──
function AIReportPanel({ datasets }: { datasets: Dataset[] }) {
  const [datasetId, setDatasetId] = useState('')
  const [report,    setReport]    = useState<Record<string, unknown> | null>(null)
  const [loading,   setLoading]   = useState(false)

  async function generate() {
    if (!datasetId) return
    setLoading(true)
    try {
      const res = await fetch('/api/ai/generate-report', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ datasetId }),
      })
      if (!res.ok) throw new Error('Failed')
      const data = await res.json()
      setReport(data.report || data)
    } catch {
      toast.error('Report generation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <FileText className="h-4 w-4 text-blue-500" />
          AI Quality Report
        </CardTitle>
        <CardDescription>Generate an AI-powered quality analysis</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-end gap-3">
          <div className="flex-1 space-y-2">
            <Label>Dataset</Label>
            <Select value={datasetId} onValueChange={setDatasetId}>
              <SelectTrigger><SelectValue placeholder="Select dataset" /></SelectTrigger>
              <SelectContent>
                {datasets.map((ds) => (
                  <SelectItem key={ds.id} value={ds.id}>{ds.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button onClick={generate} disabled={!datasetId || loading}>
            {loading
              ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Analyzing...</>
              : <><Sparkles className="h-4 w-4 mr-2" />Generate Report</>
            }
          </Button>
        </div>

        {report && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant="outline">{String(report.generationMethod || 'generated')}</Badge>
              {report.average_score != null && (
                <Badge className={getScoreBg(Number(report.average_score))}>
                  Score: {safeFixed(Number(report.average_score))}%
                </Badge>
              )}
              {report.passed != null && (
                <Badge variant="secondary">{String(report.passed)}/{String(report.total)} passed</Badge>
              )}
            </div>
            {report.summary && (
              <div>
                <h4 className="text-sm font-semibold text-slate-700 mb-1">Summary</h4>
                <p className="text-sm text-slate-600">{String(report.summary)}</p>
              </div>
            )}
            {report.diagnosis && (
              <div>
                <h4 className="text-sm font-semibold text-slate-700 mb-1">Diagnosis</h4>
                <p className="text-sm text-slate-600 whitespace-pre-line">{String(report.diagnosis)}</p>
              </div>
            )}
            {report.action_plan && (
              <div>
                <h4 className="text-sm font-semibold text-slate-700 mb-1">Action Plan</h4>
                <p className="text-sm text-slate-600 whitespace-pre-line">{String(report.action_plan)}</p>
              </div>
            )}
            {report.fix_code && (
              <div>
                <h4 className="text-sm font-semibold text-slate-700 mb-1">Suggested Fix</h4>
                <pre className="bg-slate-900 text-slate-100 rounded-lg p-3 text-xs font-mono overflow-x-auto">
                  {String(report.fix_code)}
                </pre>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ── AI Fix Panel ──
function AIFixPanel({ rules }: { rules: QualityRule[] }) {
  const [ruleName, setRuleName] = useState('')
  const [score,    setScore]    = useState('80')
  const [message,  setMessage]  = useState('')
  const [fix,      setFix]      = useState<Record<string, unknown> | null>(null)
  const [loading,  setLoading]  = useState(false)

  async function generate() {
    if (!ruleName) return
    setLoading(true)
    try {
      const res = await fetch('/api/ai/generate-fix', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          ruleName,
          checkResult: {
            status:  'failed',
            score:   Number(score),
            message: message || `${ruleName}: score ${score}%`,
          },
        }),
      })
      if (!res.ok) throw new Error('Failed')
      const data = await res.json()
      setFix(data.fix || data)
    } catch {
      toast.error('Fix generation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Wrench className="h-4 w-4 text-orange-500" />
          AI Fix Suggestion
        </CardTitle>
        <CardDescription>Get AI-powered fix code for failed checks</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="space-y-2">
            <Label>Rule</Label>
            <Select value={ruleName} onValueChange={setRuleName}>
              <SelectTrigger><SelectValue placeholder="Select rule" /></SelectTrigger>
              <SelectContent>
                {rules.map((r) => (
                  <SelectItem key={r.id} value={r.name}>{r.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Score</Label>
            <Input
              type="number"
              value={score}
              onChange={(e) => setScore(e.target.value)}
              min="0"
              max="100"
            />
          </div>
          <div className="space-y-2">
            <Label>Message (optional)</Label>
            <Input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="e.g. 20% null values"
            />
          </div>
        </div>

        <Button onClick={generate} disabled={!ruleName || loading} size="sm">
          {loading
            ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Generating...</>
            : <><Wrench className="h-4 w-4 mr-2" />Suggest Fix</>
          }
        </Button>

        {fix && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Badge variant="outline">{String(fix.generationMethod || 'generated')}</Badge>
            </div>
            {fix.explanation && (
              <p className="text-sm text-slate-600">{String(fix.explanation)}</p>
            )}
            {fix.fix_code && (
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-semibold text-slate-700">Fix Code</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      navigator.clipboard.writeText(String(fix.fix_code))
                      toast.success('Copied!')
                    }}
                  >
                    Copy
                  </Button>
                </div>
                <pre className="bg-slate-900 text-slate-100 rounded-lg p-3 text-xs font-mono overflow-x-auto">
                  {String(fix.fix_code)}
                </pre>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ── Main Quality Component ──
export default function Quality() {
  const [rules,    setRules]    = useState<QualityRule[]>([])
  const [checks,   setChecks]   = useState<QualityCheck[]>([])
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [loading,  setLoading]  = useState(true)
  const [search,   setSearch]   = useState('')
  const [activeTab,      setActiveTab]      = useState('rules')
  const [showCreator,    setShowCreator]    = useState(false)
  const [preselectedRuleId, setPreselectedRuleId] = useState('')

  const fetchData = useCallback(async () => {
    try {
      const [rulesRes, checksRes, dsRes] = await Promise.all([
        fetch('/api/rules'),
        fetch('/api/checks?limit=20'),
        fetch('/api/datasets'),
      ])
      const rulesData  = rulesRes.ok  ? await rulesRes.json()  : []
      const checksData = checksRes.ok ? await checksRes.json() : []
      const dsData     = dsRes.ok     ? await dsRes.json()     : []
      setRules(Array.isArray(rulesData)  ? rulesData  : [])
      setChecks(Array.isArray(checksData) ? checksData : [])
      setDatasets(Array.isArray(dsData)  ? dsData     : [])
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const toggleRule = async (ruleId: string, enabled: boolean) => {
    await fetch(`/api/rules/${ruleId}`, {
      method:  'PUT',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ enabled: !enabled }),
    })
    setRules((prev) => prev.map((r) => r.id === ruleId ? { ...r, enabled: !enabled } : r))
  }

  const deleteRule = async (ruleId: string) => {
    await fetch(`/api/rules/${ruleId}`, { method: 'DELETE' })
    setRules((prev) => prev.filter((r) => r.id !== ruleId))
    toast.success('Rule deleted')
  }

  const passed   = checks.filter((c) => c.status === 'passed').length
  const failed   = checks.filter((c) => c.status === 'failed').length
  const passRate = checks.length > 0
    ? Math.round((passed / checks.length) * 1000) / 10
    : 0
  const avgScore = checks.length > 0
    ? Math.round((checks.reduce((s, c) => s + (c.score || 0), 0) / checks.length) * 10) / 10
    : 0

  const filteredRules  = rules.filter((r) => r.name.toLowerCase().includes(search.toLowerCase()))
  const getDatasetName = (id: string | null) =>
    datasets.find((d) => d.id === id)?.name || (id || '').slice(0, 8)

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
        </div>
        <Skeleton className="h-96 rounded-xl" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Data Quality</h2>
          <p className="text-sm text-slate-500">
            {rules.length} rules &middot; {checks.length} checks &middot; {passRate}% pass rate
          </p>
        </div>
        <Button
          variant={showCreator ? 'outline' : 'default'}
          onClick={() => setShowCreator(!showCreator)}
        >
          <Sparkles className="h-4 w-4 mr-2" />
          {showCreator ? 'Close Creator' : 'AI Create Rule'}
        </Button>
      </div>

      {/* Summary cards */}
      <div className="grid gap-4 sm:grid-cols-4">
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="rounded-lg bg-sky-50 p-2"><TestTubes className="h-5 w-5 text-sky-600" /></div>
            <div><p className="text-2xl font-bold">{rules.length}</p><p className="text-xs text-slate-500">Rules</p></div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="rounded-lg bg-emerald-50 p-2"><CheckCircle2 className="h-5 w-5 text-emerald-600" /></div>
            <div><p className="text-2xl font-bold text-emerald-600">{passed}</p><p className="text-xs text-slate-500">Passed</p></div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="rounded-lg bg-red-50 p-2"><XCircle className="h-5 w-5 text-red-600" /></div>
            <div><p className="text-2xl font-bold text-red-600">{failed}</p><p className="text-xs text-slate-500">Failed</p></div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="rounded-lg bg-violet-50 p-2"><BarChart3 className="h-5 w-5 text-violet-600" /></div>
            <div>
              <p className={`text-2xl font-bold ${getScoreColor(avgScore)}`}>{avgScore}</p>
              <p className="text-xs text-slate-500">Avg Score</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* AI Rule Creator */}
      <AnimatePresence>
        {showCreator && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
          >
            <NLRuleCreator datasets={datasets} onCreated={fetchData} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="rules"><TestTubes className="h-4 w-4 mr-1.5" />Rules</TabsTrigger>
          <TabsTrigger value="checks"><CheckCircle2 className="h-4 w-4 mr-1.5" />Checks</TabsTrigger>
          <TabsTrigger value="run"><Play className="h-4 w-4 mr-1.5" />Run</TabsTrigger>
          <TabsTrigger value="report"><FileText className="h-4 w-4 mr-1.5" />AI Report</TabsTrigger>
          <TabsTrigger value="fix"><Wrench className="h-4 w-4 mr-1.5" />AI Fix</TabsTrigger>
        </TabsList>

        {/* Rules Tab */}
        <TabsContent value="rules" className="space-y-4">
          <div className="relative max-w-sm">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input
              placeholder="Search rules..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Dimension</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Dataset</TableHead>
                    <TableHead>Enabled</TableHead>
                    <TableHead className="w-[50px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRules.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8 text-slate-400">
                        <Zap className="h-8 w-8 mx-auto mb-2 opacity-50" />
                        No rules found
                      </TableCell>
                    </TableRow>
                  ) : filteredRules.map((rule) => (
                    <TableRow key={rule.id} className={!rule.enabled ? 'opacity-60' : ''}>
                      <TableCell>
                        <div className="max-w-[200px]">
                          <p className="font-medium truncate">{rule.name}</p>
                          {rule.description && (
                            <p className="text-xs text-muted-foreground truncate">{rule.description}</p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="capitalize">
                          {rule.type?.replace(/_/g, ' ')}
                        </Badge>
                      </TableCell>
                      <TableCell>{getDimensionBadge(rule.dimension || '')}</TableCell>
                      <TableCell>{getSeverityBadge(rule.severity || '')}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {getDatasetName(rule.datasetId)}
                      </TableCell>
                      <TableCell>
                        <Switch
                          checked={rule.enabled}
                          onCheckedChange={() => toggleRule(rule.id, rule.enabled)}
                        />
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" className="h-8 w-8">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem
                              onClick={() => {
                                setPreselectedRuleId(rule.id)
                                setActiveTab('run')
                              }}
                            >
                              Run Check
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              className="text-red-600"
                              onClick={() => deleteRule(rule.id)}
                            >
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Checks Tab */}
        <TabsContent value="checks" className="space-y-4">
          <Card>
            <CardContent className="p-0">
              <ScrollArea className="max-h-[500px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Time</TableHead>
                      <TableHead>Rule</TableHead>
                      <TableHead>Dataset</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Score</TableHead>
                      <TableHead className="text-right">Failed</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {checks.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-8 text-slate-400">
                          No checks yet. Run a check to see results.
                        </TableCell>
                      </TableRow>
                    ) : checks.map((check) => (
                      <TableRow key={check.id}>
                        <TableCell className="text-xs text-muted-foreground">
                          {new Date(check.createdAt).toLocaleString()}
                        </TableCell>
                        <TableCell className="font-medium max-w-[150px] truncate">
                          {(check as Record<string, unknown> & typeof check).rule
                            ? String(((check as Record<string, unknown>).rule as Record<string, unknown>).name ?? '')
                            : check.ruleId?.slice(0, 8)}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {(check as Record<string, unknown> & typeof check).dataset
                            ? String(((check as Record<string, unknown>).dataset as Record<string, unknown>).name ?? '')
                            : getDatasetName(check.datasetId)}
                        </TableCell>
                        <TableCell>{getStatusBadge(check.status)}</TableCell>
                        <TableCell>
                          <span className={`font-semibold ${getScoreColor(check.score || 0)}`}>
                            {safeFixed(check.score)}
                          </span>
                        </TableCell>
                        <TableCell className="text-right">
                          <span className={check.recordsFailed > 0 ? 'text-red-600 font-semibold' : 'text-muted-foreground'}>
                            {(check.recordsFailed || 0).toLocaleString()}
                          </span>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Run Tab */}
        <TabsContent value="run">
          <RunCheckPanel
            datasets={datasets}
            rules={rules}
            onDone={fetchData}
            preselectedRuleId={preselectedRuleId}
            onRuleConsumed={() => setPreselectedRuleId('')}
          />
        </TabsContent>

        {/* AI Report Tab */}
        <TabsContent value="report">
          <AIReportPanel datasets={datasets} />
        </TabsContent>

        {/* AI Fix Tab */}
        <TabsContent value="fix">
          <AIFixPanel rules={rules} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
