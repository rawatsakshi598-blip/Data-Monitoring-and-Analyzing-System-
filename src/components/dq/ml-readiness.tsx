'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Brain, CheckCircle2, AlertTriangle, XCircle, Target, Shield, Database,
  BarChart3, Cpu, Lightbulb, ArrowUpRight, RefreshCw, Download, Loader2,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

// ── Types ──
interface MLReadinessReport {
  tableName: string
  overallGrade: string
  overallScore: number
  dimensions: {
    completeness: number
    feature_quality: number
    encoding: number
    distribution: number
    data_size: number
    multicollinearity: number
  }
  issues: {
    id: string
    dimension: string
    severity: 'critical' | 'warning' | 'info'
    title: string
    description: string
    impact: string
    recommendation: string
  }[]
  recommendations: {
    id: string
    priority: 'high' | 'medium' | 'low'
    action: string
    expectedImprovement: number
    effort: string
  }[]
}

const DIMENSION_META: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  completeness: { label: 'Completeness', icon: CheckCircle2, color: 'text-emerald-600' },
  feature_quality: { label: 'Feature Quality', icon: Target, color: 'text-blue-600' },
  encoding: { label: 'Encoding', icon: Shield, color: 'text-violet-600' },
  distribution: { label: 'Distribution', icon: BarChart3, color: 'text-amber-600' },
  data_size: { label: 'Data Size', icon: Database, color: 'text-sky-600' },
  multicollinearity: { label: 'Multicollinearity', icon: Cpu, color: 'text-rose-600' },
}

// ── Helpers ──
function GradeBadge({ grade }: { grade: string }) {
  const colors: Record<string, string> = {
    'A+': 'bg-emerald-100 text-emerald-700 border-emerald-300',
    'A': 'bg-emerald-50 text-emerald-700 border-emerald-200',
    'B+': 'bg-blue-50 text-blue-700 border-blue-200',
    'B': 'bg-sky-50 text-sky-700 border-sky-200',
    'C+': 'bg-amber-50 text-amber-700 border-amber-200',
    'C': 'bg-amber-50 text-amber-700 border-amber-200',
    'D': 'bg-red-50 text-red-700 border-red-200',
    'F': 'bg-red-100 text-red-800 border-red-300',
  }
  return (
    <Badge variant="outline" className={cn('text-lg font-bold px-4 py-1', colors[grade] || colors['C'])}>
      {grade}
    </Badge>
  )
}

function SeverityIcon({ severity }: { severity: string }) {
  switch (severity) {
    case 'critical': return <XCircle className="h-4 w-4 text-red-500" />
    case 'warning': return <AlertTriangle className="h-4 w-4 text-amber-500" />
    default: return <Lightbulb className="h-4 w-4 text-blue-500" />
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

const scoreColor = (score: number) =>
  score >= 85 ? 'text-emerald-600' : score >= 70 ? 'text-amber-600' : 'text-red-600'

const scoreBarColor = (score: number) =>
  score >= 85 ? '[&>div]:bg-emerald-500' : score >= 70 ? '[&>div]:bg-amber-500' : '[&>div]:bg-red-500'

function getGradeFromScore(score: number): string {
  if (score >= 95) return 'A+'
  if (score >= 85) return 'A'
  if (score >= 80) return 'B+'
  if (score >= 70) return 'B'
  if (score >= 60) return 'C+'
  if (score >= 50) return 'C'
  if (score >= 35) return 'D'
  return 'F'
}

// ── Main Component ──
export default function MLReadiness() {
  const [report, setReport] = useState<MLReadinessReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedTable, setSelectedTable] = useState('')
  const [tables, setTables] = useState<string[]>([])

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

  const fetchReport = async () => {
    if (!selectedTable) return
    setLoading(true)
    setError(null)
    try {
      // GET endpoint auto-computes if no cached result exists
      const res = await fetch(`/api/ml-readiness/${encodeURIComponent(selectedTable)}`)
      if (res.ok) {
        const data = await res.json()
        setReport(data)
        toast.success('ML readiness analysis complete')
      } else {
        const errData = await res.json().catch(() => ({}))
        setError(errData.error || 'Failed to generate ML readiness report')
        toast.error(errData.error || 'Analysis failed')
      }
    } catch (err: any) {
      setError('Failed to generate ML readiness report')
      toast.error('Analysis failed — is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  const handleExport = () => {
    if (!report) return
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `ml-readiness-${report.tableName}.json`; a.click()
    URL.revokeObjectURL(url)
    toast.success('Report exported')
  }

  if (initialLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between"><Skeleton className="h-8 w-48" /><Skeleton className="h-10 w-64" /></div>
        <div className="grid gap-4 lg:grid-cols-3">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-64 rounded-xl" />)}</div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <Loader2 className="h-10 w-10 animate-spin text-emerald-500" />
        <div className="text-center">
          <p className="font-semibold text-slate-700">Analyzing ML Readiness...</p>
          <p className="text-sm text-slate-400">Evaluating completeness, feature quality, encoding, and more</p>
        </div>
      </div>
    )
  }

  const criticalCount = report?.issues.filter((i) => i.severity === 'critical').length || 0
  const warningCount = report?.issues.filter((i) => i.severity === 'warning').length || 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">ML Readiness Score</h2>
          <p className="text-sm text-slate-500 mt-1">Evaluate dataset readiness for machine learning</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={selectedTable} onValueChange={setSelectedTable}>
            <SelectTrigger className="w-48"><SelectValue placeholder="Select table" /></SelectTrigger>
            <SelectContent>
              {tables.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
            </SelectContent>
          </Select>
          <Button onClick={fetchReport} className="gap-2"><Brain className="h-4 w-4" /> Analyze</Button>
          {report && <Button variant="outline" className="gap-2" onClick={handleExport}><Download className="h-4 w-4" /> Export</Button>}
        </div>
      </div>

      {error && (
        <Card className="border-red-200 bg-red-50/50">
          <CardContent className="p-4 flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-red-500 shrink-0" />
            <p className="text-sm text-red-700">{error}</p>
            <Button variant="outline" size="sm" onClick={fetchReport} className="ml-auto"><RefreshCw className="h-3.5 w-3.5 mr-1" />Retry</Button>
          </CardContent>
        </Card>
      )}

      {report && (
        <>
          {/* Score Overview */}
          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-1">
              <CardContent className="p-6 flex flex-col items-center justify-center">
                <p className="text-sm font-medium text-slate-500 mb-2">Overall ML Readiness</p>
                <div className={cn('text-6xl font-black', scoreColor(report.overallScore))}>
                  {report.overallGrade}
                </div>
                <p className={cn('text-2xl font-bold mt-1', scoreColor(report.overallScore))}>
                  {report.overallScore}/100
                </p>
                <Progress value={report.overallScore} className={cn('h-2 w-full mt-3', scoreBarColor(report.overallScore))} />
                <p className="text-xs text-slate-400 mt-2">
                  {report.overallScore >= 85 ? 'Ready for ML' : report.overallScore >= 70 ? 'Minor improvements needed' : 'Significant issues found'}
                </p>
              </CardContent>
            </Card>

            <Card className="lg:col-span-2">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Dimension Scores</CardTitle>
                <CardDescription>Key readiness dimensions evaluated for ML</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 sm:grid-cols-2">
                  {Object.entries(report.dimensions).map(([key, value]) => {
                    const meta = DIMENSION_META[key]
                    if (!meta) return null
                    const Icon = meta.icon
                    return (
                      <div key={key} className="flex items-center gap-3 rounded-lg border p-3">
                        <div className={cn('rounded-lg p-2 bg-slate-50', meta.color)}>
                          <Icon className="h-4 w-4" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm font-medium text-slate-700">{meta.label}</span>
                            <span className={cn('text-sm font-bold', scoreColor(value))}>{value}</span>
                          </div>
                          <Progress value={value} className={cn('h-1.5', scoreBarColor(value))} />
                        </div>
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Quick Stats */}
          <div className="grid gap-4 sm:grid-cols-3">
            <Card className="border-red-100">
              <CardContent className="p-4 flex items-center gap-3">
                <div className="rounded-lg bg-red-50 p-2"><XCircle className="h-4 w-4 text-red-600" /></div>
                <div><p className="text-xs text-red-600">Critical Issues</p><p className="text-xl font-bold text-red-700">{criticalCount}</p></div>
              </CardContent>
            </Card>
            <Card className="border-amber-100">
              <CardContent className="p-4 flex items-center gap-3">
                <div className="rounded-lg bg-amber-50 p-2"><AlertTriangle className="h-4 w-4 text-amber-600" /></div>
                <div><p className="text-xs text-amber-600">Warnings</p><p className="text-xl font-bold text-amber-700">{warningCount}</p></div>
              </CardContent>
            </Card>
            <Card className="border-emerald-100">
              <CardContent className="p-4 flex items-center gap-3">
                <div className="rounded-lg bg-emerald-50 p-2"><CheckCircle2 className="h-4 w-4 text-emerald-600" /></div>
                <div>
                  <p className="text-xs text-emerald-600">Dimensions Ready</p>
                  <p className="text-xl font-bold text-emerald-700">
                    {Object.values(report.dimensions).filter((v) => v >= 80).length}/{Object.keys(report.dimensions).length}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          <Tabs defaultValue="issues" className="space-y-4">
            <TabsList>
              <TabsTrigger value="issues">Issues</TabsTrigger>
              <TabsTrigger value="recommendations">Recommendations</TabsTrigger>
            </TabsList>

            {/* Issues Tab */}
            <TabsContent value="issues" className="space-y-3">
              {report.issues.length === 0 ? (
                <Card><CardContent className="p-12 text-center">
                  <CheckCircle2 className="h-12 w-12 text-emerald-300 mx-auto mb-4" />
                  <h3 className="font-semibold text-slate-700">No Issues Found</h3>
                  <p className="text-sm text-slate-400">Your dataset looks great for ML!</p>
                </CardContent></Card>
              ) : report.issues.map((issue) => (
                <Card key={issue.id} className={cn(
                  issue.severity === 'critical' ? 'border-red-200' :
                  issue.severity === 'warning' ? 'border-amber-200' : 'border-blue-200'
                )}>
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <SeverityIcon severity={issue.severity} />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="text-sm font-semibold text-slate-900">{issue.title}</h4>
                          <Badge variant="outline" className="text-[10px]">{issue.dimension}</Badge>
                          <SeverityBadge severity={issue.severity} />
                        </div>
                        <p className="text-sm text-slate-600 mb-2">{issue.description}</p>
                        <div className="grid gap-2 sm:grid-cols-2">
                          <div className="rounded bg-slate-50 p-2">
                            <p className="text-[10px] font-semibold text-slate-400 uppercase">Impact</p>
                            <p className="text-xs text-slate-700">{issue.impact}</p>
                          </div>
                          <div className="rounded bg-emerald-50 p-2">
                            <p className="text-[10px] font-semibold text-emerald-600 uppercase">Recommendation</p>
                            <p className="text-xs text-emerald-700">{issue.recommendation}</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </TabsContent>

            {/* Recommendations Tab */}
            <TabsContent value="recommendations" className="space-y-3">
              {report.recommendations.length === 0 ? (
                <Card><CardContent className="p-12 text-center">
                  <Lightbulb className="h-12 w-12 text-slate-300 mx-auto mb-4" />
                  <p className="text-sm text-slate-400">No recommendations at this time</p>
                </CardContent></Card>
              ) : report.recommendations.map((rec) => (
                <Card key={rec.id}>
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <div className={cn(
                        'mt-0.5 rounded-full p-1',
                        rec.priority === 'high' ? 'bg-red-100' : rec.priority === 'medium' ? 'bg-amber-100' : 'bg-blue-100'
                      )}>
                        <ArrowUpRight className={cn(
                          'h-3.5 w-3.5',
                          rec.priority === 'high' ? 'text-red-600' : rec.priority === 'medium' ? 'text-amber-600' : 'text-blue-600'
                        )} />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-slate-900">{rec.action}</p>
                        <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                          <span>Priority: <span className={cn(
                            'font-medium',
                            rec.priority === 'high' ? 'text-red-600' : rec.priority === 'medium' ? 'text-amber-600' : 'text-blue-600'
                          )}>{rec.priority}</span></span>
                          <span>Effort: {rec.effort}</span>
                          <span className="text-emerald-600">+{rec.expectedImprovement} pts</span>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </TabsContent>
          </Tabs>
        </>
      )}

      {!report && !loading && !error && (
        <Card>
          <CardContent className="p-12 text-center">
            <Brain className="h-12 w-12 text-slate-300 mx-auto mb-4" />
            <h3 className="font-semibold text-slate-700 mb-1">No ML Readiness Report</h3>
            <p className="text-sm text-slate-400 mb-4">Select a table and click Analyze to evaluate ML readiness</p>
            <Button onClick={fetchReport} className="gap-2"><Brain className="h-4 w-4" /> Analyze</Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
