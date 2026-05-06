'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Workflow, Plus, Play, Trash2, GripVertical, X, ChevronRight, Clock,
  CheckCircle2, XCircle, Loader2, RotateCcw, Save, Settings2, Square,
  AlertCircle, FileText, BarChart3, ArrowRight,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

// ── Types ──
interface TransformStep {
  id: string
  type: string
  name: string
  config: Record<string, string>
}

interface StepResult {
  step_id: string
  step_name: string
  status: string
  message?: string
  duration_ms?: number
  rows_affected?: number
  columns_affected?: string[]
  details?: Record<string, unknown>
}

interface Pipeline {
  id: string
  name: string
  description: string
  tableId: string
  tableName?: string
  steps: TransformStep[]
  status: string
  createdAt: string
  updatedAt: string
  lastRun?: string
  runCount: number
}

interface PipelineRun {
  id: string
  pipelineId: string
  pipelineName: string
  status: string
  startedAt: string
  completedAt?: string
  duration?: number
  recordsProcessed?: number
  totalSteps?: number
  completedSteps?: number
  failedSteps?: number
  stepResults?: StepResult[]
  finalShape?: number[]
  error?: string
}

const STEP_TYPES = [
  { type: 'imputation', name: 'Imputation', category: 'Cleaning', description: 'Fill missing values', methods: ['mean', 'median', 'mode', 'constant', 'forward_fill', 'backward_fill', 'knn', 'most_frequent'] },
  { type: 'outlier_removal', name: 'Outlier Removal', category: 'Cleaning', description: 'Remove statistical outliers', methods: ['iqr_remove', 'iqr_cap', 'zscore_remove', 'zscore_cap', 'winsorize', 'percentile_clip'] },
  { type: 'deduplication', name: 'Deduplication', category: 'Cleaning', description: 'Remove duplicate records', methods: ['exact', 'subset', 'keep_first', 'keep_last', 'keep_none'] },
  { type: 'encoding', name: 'One-Hot Encoding', category: 'Transform', description: 'Encode categorical variables', methods: ['one_hot', 'label', 'ordinal', 'target', 'frequency', 'binary'] },
  { type: 'scaling', name: 'Feature Scaling', category: 'Transform', description: 'Normalize or standardize features', methods: ['minmax', 'zscore', 'robust', 'log', 'max_abs'] },
  { type: 'date_parse', name: 'Date Parsing', category: 'Transform', description: 'Parse and format dates', methods: ['parse', 'extract_features', 'to_format', 'auto_detect'] },
  { type: 'text_clean', name: 'Text Cleaning', category: 'Cleaning', description: 'Normalize text fields', methods: ['trim', 'lowercase', 'uppercase', 'title_case', 'remove_special', 'standardize_whitespace'] },
  { type: 'type_conversion', name: 'Type Conversion', category: 'Transform', description: 'Convert column data types', methods: ['auto', 'to_numeric', 'to_string', 'to_datetime', 'to_category', 'to_boolean'] },
  { type: 'data_split', name: 'Train/Test Split', category: 'Transform', description: 'Split dataset for ML', methods: ['random', 'stratified', 'time_based'] },
]

const CATEGORY_COLORS: Record<string, string> = {
  Cleaning: 'bg-blue-100 text-blue-700 border-blue-200',
  Transform: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  Combine: 'bg-violet-100 text-violet-700 border-violet-200',
  Reshape: 'bg-amber-100 text-amber-700 border-amber-200',
}

// ── Sub-components ──
function StepTypeBadge({ type }: { type: string }) {
  const step = STEP_TYPES.find((s) => s.type === type)
  if (!step) return null
  return (
    <Badge variant="outline" className={cn('text-[10px]', CATEGORY_COLORS[step.category] || '')}>
      {step.category}
    </Badge>
  )
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { icon: React.ReactNode; className: string }> = {
    success: { icon: <CheckCircle2 className="h-3 w-3" />, className: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
    completed: { icon: <CheckCircle2 className="h-3 w-3" />, className: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
    active: { icon: <CheckCircle2 className="h-3 w-3" />, className: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
    failed: { icon: <XCircle className="h-3 w-3" />, className: 'bg-red-50 text-red-700 border-red-200' },
    error: { icon: <XCircle className="h-3 w-3" />, className: 'bg-red-50 text-red-700 border-red-200' },
    running: { icon: <Loader2 className="h-3 w-3 animate-spin" />, className: 'bg-blue-50 text-blue-700 border-blue-200' },
    draft: { icon: <Clock className="h-3 w-3" />, className: 'bg-slate-50 text-slate-600 border-slate-200' },
    cancelled: { icon: <AlertCircle className="h-3 w-3" />, className: 'bg-amber-50 text-amber-700 border-amber-200' },
  }
  const c = config[status] || config.draft
  return (
    <Badge variant="outline" className={cn('gap-1 text-[11px]', c.className)}>
      {c.icon}
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  )
}

function StepResultCard({ result, index }: { result: StepResult; index: number }) {
  const statusConfig: Record<string, { icon: React.ReactNode; color: string }> = {
    success: { icon: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />, color: 'border-emerald-200 bg-emerald-50/50' },
    failed: { icon: <XCircle className="h-3.5 w-3.5 text-red-500" />, color: 'border-red-200 bg-red-50/50' },
    error: { icon: <XCircle className="h-3.5 w-3.5 text-red-500" />, color: 'border-red-200 bg-red-50/50' },
    skipped: { icon: <Clock className="h-3.5 w-3.5 text-amber-500" />, color: 'border-amber-200 bg-amber-50/50' },
  }
  const sc = statusConfig[result.status] || statusConfig.skipped

  return (
    <div className={cn('flex items-start gap-3 rounded-lg border p-3', sc.color)}>
      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-white text-xs font-bold text-slate-500 shrink-0">
        {index + 1}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          {sc.icon}
          <span className="text-sm font-medium text-slate-900">{result.step_name || result.step_id}</span>
          <Badge variant="outline" className="text-[10px]">{result.status}</Badge>
        </div>
        {result.message && <p className="text-xs text-slate-600 mb-1">{result.message}</p>}
        <div className="flex items-center gap-3 text-[11px] text-slate-400">
          {result.duration_ms != null && <span>{result.duration_ms}ms</span>}
          {result.rows_affected != null && result.rows_affected > 0 && <span>{result.rows_affected} rows affected</span>}
          {result.columns_affected && result.columns_affected.length > 0 && (
            <span>{result.columns_affected.length} columns</span>
          )}
        </div>
        {result.details && Object.keys(result.details).length > 0 && (
          <div className="mt-1 text-[10px] text-slate-400">
            {Object.entries(result.details).slice(0, 4).map(([k, v]) => (
              <span key={k} className="mr-3">{k}: <span className="text-slate-600">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span></span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Main Component ──
export default function PipelineBuilder() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [runs, setRuns] = useState<PipelineRun[]>([])
  const [tables, setTables] = useState<{ id: string; name: string }[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedPipeline, setSelectedPipeline] = useState<Pipeline | null>(null)
  const [selectedRun, setSelectedRun] = useState<PipelineRun | null>(null)

  // Dialog state
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showStepDialog, setShowStepDialog] = useState(false)
  const [newPipelineName, setNewPipelineName] = useState('')
  const [newPipelineDesc, setNewPipelineDesc] = useState('')
  const [newPipelineTable, setNewPipelineTable] = useState('')
  const [newStepType, setNewStepType] = useState('')
  const [newStepConfig, setNewStepConfig] = useState('')
  const [newStepMethod, setNewStepMethod] = useState('')
  const [newStepColumns, setNewStepColumns] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // Running state tracking
  const [runningPipelineId, setRunningPipelineId] = useState<string | null>(null)
  const pollRef = useRef<NodeJS.Timeout | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [pResult, rResult, tResult] = await Promise.allSettled([
        fetch('/api/pipelines'),
        fetch('/api/pipelines/runs'),
        fetch('/api/tables'),
      ])
      const pData = pResult.status === 'fulfilled' && pResult.value.ok ? await pResult.value.json() : []
      const rData = rResult.status === 'fulfilled' && rResult.value.ok ? await rResult.value.json() : []
      const tData = tResult.status === 'fulfilled' && tResult.value.ok ? await tResult.value.json() : []
      // Normalize pipelines — ensure steps and runCount are always defined
      const rawPipelines = Array.isArray(pData) ? pData : pData?.pipelines || []
      const safePipelines: Pipeline[] = rawPipelines.map((p: Record<string, unknown>) => ({
        id: (p.id as string) || '',
        name: (p.name as string) || 'Untitled',
        description: (p.description as string) || '',
        tableId: (p.tableId as string) || '',
        tableName: (p.tableName as string) || undefined,
        steps: Array.isArray(p.steps) ? p.steps as TransformStep[] : [],
        status: (p.status as string) || 'draft',
        createdAt: (p.createdAt as string) || new Date().toISOString(),
        updatedAt: (p.updatedAt as string) || new Date().toISOString(),
        runCount: (p.runCount as number) ?? ((p._count as Record<string, unknown>)?.runs as number) ?? 0,
      }))
      setPipelines(safePipelines)
      // Map backend run fields to frontend PipelineRun interface
      const mappedRuns: PipelineRun[] = Array.isArray(rData)
        ? rData.map((r: Record<string, unknown>) => ({
            id: r.id as string,
            pipelineId: (r.pipelineId as string) || '',
            pipelineName: (r.pipelineName as string) || 'Unknown',
            status: (r.status as string) || 'unknown',
            startedAt: (r.createdAt as string) || new Date().toISOString(),
            completedAt: r.completedAt as string | undefined,
            duration: (r.totalDurationMs as number) ? Math.round((r.totalDurationMs as number) / 1000 * 10) / 10 : undefined,
            recordsProcessed: (r.completedSteps as number) || undefined,
            totalSteps: (r.totalSteps as number) || undefined,
            completedSteps: (r.completedSteps as number) || undefined,
            failedSteps: (r.failedSteps as number) || undefined,
            stepResults: Array.isArray(r.stepResults) ? r.stepResults as StepResult[] : undefined,
            finalShape: Array.isArray(r.finalShape) ? r.finalShape as number[] : undefined,
            error: r.error as string | undefined,
          }))
        : []
      setRuns(mappedRuns)
      setTables(Array.isArray(tData) ? tData.map((t: { id: string; name: string }) => ({ id: t.id, name: t.name })) : [])
    } catch {
      setError('Failed to load pipeline data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  // Poll for updates when a pipeline is running
  useEffect(() => {
    if (runningPipelineId) {
      pollRef.current = setInterval(async () => {
        try {
          const res = await fetch('/api/pipelines/runs')
          if (res.ok) {
            const data = await res.json()
            const currentRun = Array.isArray(data)
              ? data.find((r: Record<string, unknown>) => r.pipelineId === runningPipelineId && r.status === 'running')
              : null
            if (!currentRun) {
              // Run completed — stop polling and refresh
              setRunningPipelineId(null)
              if (pollRef.current) clearInterval(pollRef.current)
              fetchData()
            }
          }
        } catch { /* ignore poll errors */ }
      }, 2000)
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [runningPipelineId, fetchData])

  const handleCreatePipeline = async () => {
    if (!newPipelineName.trim()) { toast.error('Pipeline name is required'); return }
    setSubmitting(true)
    try {
      const res = await fetch('/api/pipelines', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newPipelineName, description: newPipelineDesc, tableId: newPipelineTable, steps: [] }),
      })
      if (!res.ok) throw new Error('Failed')
      const raw = await res.json()
      const data: Pipeline = {
        id: raw.id || `p${Date.now()}`,
        name: raw.name || newPipelineName,
        description: raw.description || '',
        tableId: raw.tableId || newPipelineTable,
        tableName: raw.tableName || undefined,
        steps: Array.isArray(raw.steps) ? raw.steps : [],
        status: raw.status || 'draft',
        createdAt: raw.createdAt || new Date().toISOString(),
        updatedAt: raw.updatedAt || new Date().toISOString(),
        runCount: raw.runCount ?? raw._count?.runs ?? 0,
      }
      setPipelines((prev) => [data, ...prev])
      setSelectedPipeline(data)
      setShowCreateDialog(false)
      setNewPipelineName('')
      setNewPipelineDesc('')
      setNewPipelineTable('')
      toast.success('Pipeline created')
    } catch {
      const newPipeline: Pipeline = {
        id: `p${Date.now()}`, name: newPipelineName, description: newPipelineDesc,
        tableId: newPipelineTable, steps: [], status: 'draft',
        createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), runCount: 0,
      }
      setPipelines((prev) => [newPipeline, ...prev])
      setSelectedPipeline(newPipeline)
      setShowCreateDialog(false)
      toast.success('Pipeline created (offline)')
    } finally {
      setSubmitting(false)
    }
  }

  const handleAddStep = () => {
    if (!selectedPipeline || !newStepType) return
    const stepInfo = STEP_TYPES.find((s) => s.type === newStepType)
    const configObj: Record<string, string> = {}
    if (newStepMethod) configObj['method'] = newStepMethod
    if (newStepColumns.trim()) configObj['columns'] = newStepColumns.trim()
    if (newStepConfig.trim()) {
      newStepConfig.split(',').forEach((pair) => {
        const [k, v] = pair.split(':').map((s) => s.trim())
        if (k && v) configObj[k] = v
      })
    }
    const newStep: TransformStep = {
      id: `s${Date.now()}`, type: newStepType, name: stepInfo?.name || newStepType, config: configObj,
    }
    const updated = { ...selectedPipeline, steps: [...(selectedPipeline.steps ?? []), newStep], updatedAt: new Date().toISOString() }
    setSelectedPipeline(updated)
    setPipelines((prev) => prev.map((p) => (p.id === updated.id ? updated : p)))
    setShowStepDialog(false)
    setNewStepType('')
    setNewStepConfig('')
    setNewStepMethod('')
    setNewStepColumns('')
    toast.success(`Added ${stepInfo?.name} step`)
  }

  const handleRemoveStep = (stepId: string) => {
    if (!selectedPipeline) return
    const updated = { ...selectedPipeline, steps: (selectedPipeline.steps ?? []).filter((s) => s.id !== stepId), updatedAt: new Date().toISOString() }
    setSelectedPipeline(updated)
    setPipelines((prev) => prev.map((p) => (p.id === updated.id ? updated : p)))
  }

  const handleRunPipeline = async (pipeline: Pipeline) => {
    if (runningPipelineId) {
      toast.error('Another pipeline is already running. Please wait or cancel it first.')
      return
    }

    // Check if pipeline has steps
    if ((pipeline.steps ?? []).length === 0) {
      toast.error('Cannot run a pipeline with no steps. Add steps first, then Save, then Run.')
      return
    }

    // Check if pipeline has a table
    if (!pipeline.tableId) {
      toast.error('Cannot run pipeline without a target table. Select a table when creating the pipeline.')
      return
    }

    setRunningPipelineId(pipeline.id)

    // Immediately show a "running" state
    setPipelines((prev) => prev.map((p) => p.id === pipeline.id ? { ...p, status: 'running' } : p))
    if (selectedPipeline?.id === pipeline.id) {
      setSelectedPipeline((prev) => prev ? { ...prev, status: 'running' } : prev)
    }

    // Add a temporary run entry
    const tempRunId = `r${Date.now()}`
    const tempRun: PipelineRun = {
      id: tempRunId, pipelineId: pipeline.id, pipelineName: pipeline.name,
      status: 'running', startedAt: new Date().toISOString(),
      totalSteps: (pipeline.steps ?? []).length,
      completedSteps: 0, failedSteps: 0,
    }
    setRuns((prev) => [tempRun, ...prev])
    toast.info(`Pipeline "${pipeline.name}" is running...`)

    try {
      const res = await fetch(`/api/pipelines/${pipeline.id}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })

      if (res.ok) {
        const data = await res.json()
        const finalStatus = data.status === 'cancelled' ? 'cancelled'
          : data.success ? 'completed' : 'failed'

        // Update the temporary run with real data
        setRuns((prev) => prev.map((r) => r.id === tempRunId ? {
          ...r,
          id: data.run_id || r.id,
          status: finalStatus,
          duration: data.total_duration_ms ? Math.round(data.total_duration_ms / 1000 * 10) / 10 : undefined,
          totalSteps: data.total_steps,
          completedSteps: data.completed_steps,
          failedSteps: data.failed_steps,
          recordsProcessed: data.completed_steps || undefined,
          stepResults: data.step_results || [],
          finalShape: data.final_shape,
          error: data.success ? undefined : (data.step_results?.find((sr: StepResult) => sr.status === 'error' || sr.status === 'failed')?.message || 'Pipeline execution failed'),
        } : r))

        // Update pipeline status
        setPipelines((prev) => prev.map((p) => p.id === pipeline.id ? { ...p, status: finalStatus === 'completed' ? 'active' : finalStatus, runCount: p.runCount + 1 } : p))
        if (selectedPipeline?.id === pipeline.id) {
          setSelectedPipeline((prev) => prev ? { ...prev, status: finalStatus === 'completed' ? 'active' : finalStatus, runCount: prev.runCount + 1 } : prev)
        }

        if (finalStatus === 'completed') {
          toast.success(`Pipeline "${pipeline.name}" completed successfully! ${data.completed_steps}/${data.total_steps} steps passed.`)
        } else if (finalStatus === 'cancelled') {
          toast.warning(`Pipeline "${pipeline.name}" was cancelled.`)
        } else {
          toast.error(`Pipeline "${pipeline.name}" failed. ${data.failed_steps} step(s) had errors.`)
        }

        // Refresh data to get updated state
        setTimeout(() => fetchData(), 500)
      } else {
        const errData = await res.json().catch(() => ({}))
        // Update temp run to failed
        setRuns((prev) => prev.map((r) => r.id === tempRunId ? { ...r, status: 'failed', error: errData.error || `Server error (${res.status})` } : r))
        setPipelines((prev) => prev.map((p) => p.id === pipeline.id ? { ...p, status: 'failed' } : p))
        toast.error(`Pipeline run failed: ${errData.error || res.statusText}`)
      }
    } catch (err) {
      // Update temp run to failed
      setRuns((prev) => prev.map((r) => r.id === tempRunId ? { ...r, status: 'failed', error: 'Network error — is the backend running?' } : r))
      setPipelines((prev) => prev.map((p) => p.id === pipeline.id ? { ...p, status: 'failed' } : p))
      toast.error('Failed to run pipeline — backend may be down')
    } finally {
      setRunningPipelineId(null)
    }
  }

  const handleStopPipeline = async (pipelineId: string) => {
    try {
      await fetch(`/api/pipelines/${pipelineId}/run`, { method: 'DELETE' })
      toast.info('Pipeline stop requested')
      setRunningPipelineId(null)
      // Refresh after a short delay
      setTimeout(() => fetchData(), 1000)
    } catch {
      toast.error('Failed to stop pipeline')
    }
  }

  const handleDeletePipeline = async (pipelineId: string) => {
    try {
      await fetch(`/api/pipelines/${pipelineId}`, { method: 'DELETE' })
    } catch { /* offline */ }
    setPipelines((prev) => prev.filter((p) => p.id !== pipelineId))
    if (selectedPipeline?.id === pipelineId) setSelectedPipeline(null)
    toast.success('Pipeline deleted')
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-36" />
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
        </div>
        <Skeleton className="h-96 rounded-xl" />
      </div>
    )
  }

  const activeCount = pipelines.filter((p) => p.status === 'active' || p.status === 'completed').length
  const draftCount = pipelines.filter((p) => p.status === 'draft').length
  const runningCount = pipelines.filter((p) => p.status === 'running').length
  const totalRuns = runs.length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Pipeline Builder</h2>
          <p className="text-sm text-slate-500 mt-1">Build transform pipelines with configurable steps</p>
        </div>
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <Button className="gap-2" onClick={() => setShowCreateDialog(true)}>
            <Plus className="h-4 w-4" /> New Pipeline
          </Button>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Pipeline</DialogTitle>
              <DialogDescription>Configure a new data transformation pipeline</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label>Pipeline Name</Label>
                <Input placeholder="e.g., Customer Data Cleaning" value={newPipelineName} onChange={(e) => setNewPipelineName(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea placeholder="Describe what this pipeline does..." value={newPipelineDesc} onChange={(e) => setNewPipelineDesc(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Target Table</Label>
                <Select value={newPipelineTable} onValueChange={setNewPipelineTable}>
                  <SelectTrigger><SelectValue placeholder="Select table" /></SelectTrigger>
                  <SelectContent>
                    {tables.map((t) => <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancel</Button>
              <Button onClick={handleCreatePipeline} disabled={!newPipelineName.trim() || submitting}>
                {submitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                Create Pipeline
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {error && <p className="text-sm text-red-500">{error}</p>}

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-4">
        <Card><CardContent className="p-4 flex items-center gap-3">
          <div className="rounded-lg bg-emerald-50 p-2"><CheckCircle2 className="h-5 w-5 text-emerald-600" /></div>
          <div><p className="text-xs text-slate-500">Active</p><p className="text-2xl font-bold">{activeCount}</p></div>
        </CardContent></Card>
        <Card><CardContent className="p-4 flex items-center gap-3">
          <div className="rounded-lg bg-slate-50 p-2"><Clock className="h-5 w-5 text-slate-600" /></div>
          <div><p className="text-xs text-slate-500">Drafts</p><p className="text-2xl font-bold">{draftCount}</p></div>
        </CardContent></Card>
        <Card><CardContent className="p-4 flex items-center gap-3">
          <div className={cn('rounded-lg p-2', runningCount > 0 ? 'bg-blue-50' : 'bg-slate-50')}>
            {runningCount > 0 ? <Loader2 className="h-5 w-5 text-blue-600 animate-spin" /> : <Settings2 className="h-5 w-5 text-slate-600" />}
          </div>
          <div><p className="text-xs text-slate-500">Running</p><p className="text-2xl font-bold">{runningCount}</p></div>
        </CardContent></Card>
        <Card><CardContent className="p-4 flex items-center gap-3">
          <div className="rounded-lg bg-violet-50 p-2"><BarChart3 className="h-5 w-5 text-violet-600" /></div>
          <div><p className="text-xs text-slate-500">Total Runs</p><p className="text-2xl font-bold">{totalRuns}</p></div>
        </CardContent></Card>
      </div>

      {/* Main Tabs */}
      <Tabs defaultValue="pipelines" className="space-y-4">
        <TabsList>
          <TabsTrigger value="pipelines">Pipelines</TabsTrigger>
          <TabsTrigger value="builder">Builder</TabsTrigger>
          <TabsTrigger value="runs">Run History</TabsTrigger>
        </TabsList>

        {/* Pipelines Tab */}
        <TabsContent value="pipelines" className="space-y-3">
          {pipelines.length === 0 ? (
            <Card>
              <CardContent className="p-12 text-center">
                <Workflow className="h-12 w-12 text-slate-300 mx-auto mb-4" />
                <h3 className="font-semibold text-slate-700 mb-1">No Pipelines Yet</h3>
                <p className="text-sm text-slate-400 mb-4">Create your first transform pipeline</p>
                <Button onClick={() => setShowCreateDialog(true)} className="gap-2"><Plus className="h-4 w-4" /> New Pipeline</Button>
              </CardContent>
            </Card>
          ) : pipelines.map((pipeline) => (
            <Card key={pipeline.id} className={cn('cursor-pointer transition-all hover:shadow-md', selectedPipeline?.id === pipeline.id ? 'ring-2 ring-emerald-500' : '', pipeline.status === 'running' ? 'ring-2 ring-blue-400 animate-pulse' : '')} onClick={() => setSelectedPipeline(pipeline)}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Workflow className="h-4 w-4 text-slate-500 shrink-0" />
                      <h3 className="font-semibold text-slate-900 truncate">{pipeline.name}</h3>
                      <StatusBadge status={pipeline.status} />
                    </div>
                    <p className="text-sm text-slate-500 mb-2 truncate">{pipeline.description}</p>
                    <div className="flex items-center gap-4 text-xs text-slate-400">
                      <span className="flex items-center gap-1"><Settings2 className="h-3 w-3" />{(pipeline.steps ?? []).length} steps</span>
                      <span className="flex items-center gap-1"><Play className="h-3 w-3" />{pipeline.runCount ?? 0} runs</span>
                      {pipeline.tableName && <Badge variant="outline" className="text-[10px]">{pipeline.tableName}</Badge>}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    {pipeline.status === 'running' ? (
                      <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); handleStopPipeline(pipeline.id) }} className="h-8 w-8 p-0">
                        <Square className="h-4 w-4 text-red-500" />
                      </Button>
                    ) : (
                      <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); handleRunPipeline(pipeline) }} className="h-8 w-8 p-0" disabled={!!runningPipelineId}>
                        <Play className="h-4 w-4 text-emerald-600" />
                      </Button>
                    )}
                    <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); handleDeletePipeline(pipeline.id) }} className="h-8 w-8 p-0">
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                </div>
                <div className="flex items-center gap-2 mt-3 flex-wrap">
                  {(pipeline.steps ?? []).map((step, i) => (
                    <div key={step.id} className="flex items-center gap-2">
                      <Badge variant="secondary" className="text-[11px] gap-1">{step.name}</Badge>
                      {i < (pipeline.steps ?? []).length - 1 && <ChevronRight className="h-3 w-3 text-slate-300" />}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        {/* Builder Tab */}
        <TabsContent value="builder" className="space-y-4">
          {selectedPipeline ? (
            <>
              <Card>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-base">{selectedPipeline.name}</CardTitle>
                      <CardDescription>{selectedPipeline.description || 'No description'}</CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      {selectedPipeline.status === 'running' ? (
                        <Button variant="destructive" size="sm" onClick={() => handleStopPipeline(selectedPipeline.id)} className="gap-1">
                          <Square className="h-3.5 w-3.5" /> Stop
                        </Button>
                      ) : (
                        <Button variant="outline" size="sm" onClick={() => handleRunPipeline(selectedPipeline)} className="gap-1" disabled={!!runningPipelineId}>
                          <Play className="h-3.5 w-3.5" /> Run
                        </Button>
                      )}
                      <Button variant="outline" size="sm" className="gap-1" onClick={async () => {
                        if (!selectedPipeline) return
                        try {
                          const backendSteps = (selectedPipeline.steps ?? []).map((s, i) => ({
                            id: s.id,
                            transform_type: s.type,
                            name: s.name,
                            config: s.config,
                            stepOrder: i,
                          }))
                          await fetch(`/api/pipelines/${selectedPipeline.id}`, {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ steps: backendSteps, name: selectedPipeline.name, description: selectedPipeline.description, tableId: selectedPipeline.tableId }),
                          })
                          toast.success('Pipeline saved')
                        } catch { toast.error('Failed to save pipeline') }
                      }}>
                        <Save className="h-3.5 w-3.5" /> Save
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {(selectedPipeline.steps ?? []).map((step, index) => (
                      <div key={step.id} className="flex items-center gap-3 rounded-lg border bg-white p-3 hover:shadow-sm transition group">
                        <GripVertical className="h-4 w-4 text-slate-300 cursor-grab" />
                        <div className="flex h-7 w-7 items-center justify-center rounded bg-slate-100 text-xs font-bold text-slate-500">
                          {index + 1}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-slate-900">{step.name}</span>
                            <StepTypeBadge type={step.type} />
                          </div>
                          <div className="flex gap-2 mt-0.5 flex-wrap">
                            {Object.entries(step.config).map(([key, value]) => (
                              <span key={key} className="text-[11px] text-slate-400">{key}: <span className="text-slate-600">{value}</span></span>
                            ))}
                          </div>
                        </div>
                        <Button variant="ghost" size="sm" onClick={() => handleRemoveStep(step.id)} className="h-7 w-7 p-0 opacity-0 group-hover:opacity-100 transition-opacity">
                          <X className="h-3.5 w-3.5 text-red-500" />
                        </Button>
                      </div>
                    ))}
                    {(selectedPipeline.steps ?? []).length === 0 && (
                      <div className="rounded-lg border-2 border-dashed border-slate-200 p-8 text-center">
                        <p className="text-sm text-slate-400">No steps yet. Add transform steps below.</p>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Add Step */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Available Steps</CardTitle>
                  <CardDescription>Click to add a step to the pipeline</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                    {STEP_TYPES.map((stepType, idx) => (
                      <button key={stepType.type} onClick={() => { setNewStepType(stepType.type); setShowStepDialog(true) }} className="flex items-center gap-3 rounded-lg border bg-white p-3 text-left hover:shadow-sm hover:border-emerald-300 transition">
                        <div className="flex h-8 w-8 items-center justify-center rounded bg-slate-50">
                          <span className="text-xs font-bold text-slate-500">{idx + 1}</span>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-slate-900">{stepType.name}</p>
                          <p className="text-[11px] text-slate-400">{stepType.description}</p>
                        </div>
                      </button>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Step Config Dialog */}
              <Dialog open={showStepDialog} onOpenChange={setShowStepDialog}>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Add Step: {STEP_TYPES.find((s) => s.type === newStepType)?.name}</DialogTitle>
                    <DialogDescription>Configure the step parameters</DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-2">
                    <div className="rounded-lg bg-slate-50 p-3 text-xs text-slate-500">
                      {STEP_TYPES.find((s) => s.type === newStepType)?.description}
                    </div>
                    <div className="space-y-2">
                      <Label>Method</Label>
                      <Select value={newStepMethod} onValueChange={setNewStepMethod}>
                        <SelectTrigger><SelectValue placeholder="Select method" /></SelectTrigger>
                        <SelectContent>
                          {STEP_TYPES.find((s) => s.type === newStepType)?.methods?.map((m) => (
                            <SelectItem key={m} value={m}>{m}</SelectItem>
                          )) || []}
                        </SelectContent>
                      </Select>
                      <p className="text-[10px] text-slate-400">Choose the transformation method to use</p>
                    </div>
                    <div className="space-y-2">
                      <Label>Columns (comma-separated, leave empty for all)</Label>
                      <Input placeholder="e.g., age, income, city" value={newStepColumns} onChange={(e) => setNewStepColumns(e.target.value)} />
                    </div>
                    <div className="space-y-2">
                      <Label>Extra Config (key:value pairs, comma-separated)</Label>
                      <Input placeholder="e.g., threshold:0.5, fill_value:0" value={newStepConfig} onChange={(e) => setNewStepConfig(e.target.value)} />
                      <p className="text-[10px] text-slate-400">Optional extra parameters</p>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setShowStepDialog(false)}>Cancel</Button>
                    <Button onClick={handleAddStep} disabled={!newStepType || !newStepMethod}>Add Step</Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </>
          ) : (
            <Card>
              <CardContent className="p-12 text-center">
                <Workflow className="h-12 w-12 text-slate-300 mx-auto mb-4" />
                <h3 className="font-semibold text-slate-700 mb-1">No Pipeline Selected</h3>
                <p className="text-sm text-slate-400">Select a pipeline from the list to start building</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Run History Tab */}
        <TabsContent value="runs" className="space-y-3">
          {runs.length === 0 ? (
            <Card><CardContent className="p-12 text-center">
              <Clock className="h-12 w-12 text-slate-300 mx-auto mb-4" />
              <h3 className="font-semibold text-slate-700">No Run History</h3>
              <p className="text-sm text-slate-400">Run a pipeline to see results here</p>
            </CardContent></Card>
          ) : runs.map((run) => (
            <Card key={run.id} className={cn('transition-all', selectedRun?.id === run.id ? 'ring-2 ring-blue-400' : '', run.status === 'running' ? 'border-blue-300' : '')}>
              <CardContent className="p-4">
                {/* Run Header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <StatusBadge status={run.status} />
                    <div>
                      <p className="text-sm font-medium text-slate-900">{run.pipelineName}</p>
                      <div className="flex items-center gap-3 text-xs text-slate-400 mt-0.5">
                        <span>Started: {new Date(run.startedAt).toLocaleString()}</span>
                        {run.duration != null && <span>Duration: {run.duration}s</span>}
                        {run.finalShape && <span>Shape: {run.finalShape.join(' x ')}</span>}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {/* Progress indicator for running */}
                    {run.status === 'running' && (
                      <div className="flex items-center gap-2">
                        <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
                        <span className="text-xs text-blue-600">Running...</span>
                        <Button variant="destructive" size="sm" onClick={() => handleStopPipeline(run.pipelineId)} className="h-7 gap-1 text-xs">
                          <Square className="h-3 w-3" /> Stop
                        </Button>
                      </div>
                    )}
                    {/* Expand to see step details */}
                    {run.stepResults && run.stepResults.length > 0 && (
                      <Button variant="ghost" size="sm" onClick={() => setSelectedRun(selectedRun?.id === run.id ? null : run)} className="h-7 gap-1 text-xs">
                        <FileText className="h-3 w-3" />
                        {selectedRun?.id === run.id ? 'Hide' : 'Details'}
                      </Button>
                    )}
                    {run.status === 'failed' && (
                      <Button variant="outline" size="sm" className="gap-1 h-7 text-xs" onClick={() => {
                        const pipeline = pipelines.find((p) => p.id === run.pipelineId)
                        if (pipeline) handleRunPipeline(pipeline)
                      }}><RotateCcw className="h-3 w-3" /> Retry</Button>
                    )}
                  </div>
                </div>

                {/* Progress bar for running */}
                {run.status === 'running' && run.totalSteps != null && run.totalSteps > 0 && (
                  <div className="mt-3">
                    <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                      <span>Step {(run.completedSteps ?? 0) + 1} of {run.totalSteps}</span>
                      <span>{Math.round(((run.completedSteps ?? 0) / run.totalSteps) * 100)}%</span>
                    </div>
                    <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500 rounded-full transition-all duration-500" style={{ width: `${((run.completedSteps ?? 0) / run.totalSteps) * 100}%` }} />
                    </div>
                  </div>
                )}

                {/* Step summary for completed/failed */}
                {(run.status === 'completed' || run.status === 'failed' || run.status === 'cancelled') && run.totalSteps != null && (
                  <div className="flex items-center gap-3 mt-2 text-xs">
                    {run.completedSteps != null && run.completedSteps > 0 && (
                      <span className="flex items-center gap-1 text-emerald-600"><CheckCircle2 className="h-3 w-3" />{run.completedSteps} passed</span>
                    )}
                    {run.failedSteps != null && run.failedSteps > 0 && (
                      <span className="flex items-center gap-1 text-red-600"><XCircle className="h-3 w-3" />{run.failedSteps} failed</span>
                    )}
                    {run.totalSteps != null && (
                      <span className="text-slate-400">{run.totalSteps} total steps</span>
                    )}
                  </div>
                )}

                {/* Error message */}
                {run.error && <p className="text-xs text-red-500 mt-2 bg-red-50 p-2 rounded">Error: {run.error}</p>}

                {/* Step-by-step results (expandable) */}
                {selectedRun?.id === run.id && run.stepResults && run.stepResults.length > 0 && (
                  <div className="mt-3 space-y-2">
                    <Separator />
                    <p className="text-xs font-medium text-slate-500 mt-2 flex items-center gap-1">
                      <ArrowRight className="h-3 w-3" /> Step-by-Step Results
                    </p>
                    {run.stepResults.map((sr, idx) => (
                      <StepResultCard key={sr.step_id || idx} result={sr} index={idx} />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </TabsContent>
      </Tabs>
    </div>
  )
} 