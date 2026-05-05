'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Workflow, Plus, Play, Trash2, GripVertical, X, ChevronRight, Clock,
  CheckCircle2, XCircle, Loader2, RotateCcw, Save, Settings2,
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

interface Pipeline {
  id: string
  name: string
  description: string
  tableName: string
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
  error?: string
}

const STEP_TYPES = [
  { type: 'imputation', name: 'Imputation', category: 'Cleaning', description: 'Fill missing values' },
  { type: 'outlier_removal', name: 'Outlier Removal', category: 'Cleaning', description: 'Remove statistical outliers' },
  { type: 'deduplication', name: 'Deduplication', category: 'Cleaning', description: 'Remove duplicate records' },
  { type: 'encoding', name: 'One-Hot Encoding', category: 'Transform', description: 'Encode categorical variables' },
  { type: 'scaling', name: 'Feature Scaling', category: 'Transform', description: 'Normalize or standardize features' },
  { type: 'binning', name: 'Discretization', category: 'Transform', description: 'Bin continuous variables' },
  { type: 'aggregation', name: 'Aggregation', category: 'Transform', description: 'Aggregate by group' },
  { type: 'filter', name: 'Filter Rows', category: 'Transform', description: 'Filter rows by condition' },
  { type: 'join', name: 'Join Tables', category: 'Combine', description: 'Join with another table' },
  { type: 'pivot', name: 'Pivot / Melt', category: 'Reshape', description: 'Reshape data structure' },
  { type: 'date_parse', name: 'Date Parsing', category: 'Transform', description: 'Parse and format dates' },
  { type: 'text_clean', name: 'Text Cleaning', category: 'Cleaning', description: 'Normalize text fields' },
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
    failed: { icon: <XCircle className="h-3 w-3" />, className: 'bg-red-50 text-red-700 border-red-200' },
    running: { icon: <Loader2 className="h-3 w-3 animate-spin" />, className: 'bg-blue-50 text-blue-700 border-blue-200' },
    active: { icon: <CheckCircle2 className="h-3 w-3" />, className: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
    draft: { icon: <Clock className="h-3 w-3" />, className: 'bg-slate-50 text-slate-600 border-slate-200' },
  }
  const c = config[status] || config.draft
  return (
    <Badge variant="outline" className={cn('gap-1 text-[11px]', c.className)}>
      {c.icon}
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  )
}

// ── Main Component ──
export default function PipelineBuilder() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [runs, setRuns] = useState<PipelineRun[]>([])
  const [datasets, setDatasets] = useState<{ id: string; name: string }[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedPipeline, setSelectedPipeline] = useState<Pipeline | null>(null)

  // Dialog state
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showStepDialog, setShowStepDialog] = useState(false)
  const [newPipelineName, setNewPipelineName] = useState('')
  const [newPipelineDesc, setNewPipelineDesc] = useState('')
  const [newPipelineTable, setNewPipelineTable] = useState('')
  const [newStepType, setNewStepType] = useState('')
  const [newStepConfig, setNewStepConfig] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [pRes, rRes, dRes] = await Promise.all([
        fetch('/api/pipelines'),
        fetch('/api/pipelines/runs'),
        fetch('/api/datasets'),
      ])
      const pData = pRes.ok ? await pRes.json() : []
      const rData = rRes.ok ? await rRes.json() : []
      const dData = dRes.ok ? await dRes.json() : []
      setPipelines(Array.isArray(pData) ? pData : pData?.pipelines || [])
      setRuns(Array.isArray(rData) ? rData : rData?.runs || [])
      setDatasets(Array.isArray(dData) ? dData.map((d: { id: string; name: string }) => ({ id: d.id, name: d.name })) : [])
    } catch {
      setError('Failed to load pipeline data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const handleCreatePipeline = async () => {
    if (!newPipelineName.trim()) { toast.error('Pipeline name is required'); return }
    setSubmitting(true)
    try {
      const res = await fetch('/api/pipelines', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newPipelineName, description: newPipelineDesc, tableName: newPipelineTable }),
      })
      if (!res.ok) throw new Error('Failed')
      const data = await res.json()
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
        tableName: newPipelineTable, steps: [], status: 'draft',
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
    if (newStepConfig.trim()) {
      newStepConfig.split(',').forEach((pair) => {
        const [k, v] = pair.split(':').map((s) => s.trim())
        if (k && v) configObj[k] = v
      })
    }
    const newStep: TransformStep = {
      id: `s${Date.now()}`, type: newStepType, name: stepInfo?.name || newStepType, config: configObj,
    }
    const updated = { ...selectedPipeline, steps: [...selectedPipeline.steps, newStep], updatedAt: new Date().toISOString() }
    setSelectedPipeline(updated)
    setPipelines((prev) => prev.map((p) => (p.id === updated.id ? updated : p)))
    setShowStepDialog(false)
    setNewStepType('')
    setNewStepConfig('')
    toast.success(`Added ${stepInfo?.name} step`)
  }

  const handleRemoveStep = (stepId: string) => {
    if (!selectedPipeline) return
    const updated = { ...selectedPipeline, steps: selectedPipeline.steps.filter((s) => s.id !== stepId), updatedAt: new Date().toISOString() }
    setSelectedPipeline(updated)
    setPipelines((prev) => prev.map((p) => (p.id === updated.id ? updated : p)))
  }

  const handleRunPipeline = async (pipeline: Pipeline) => {
    try {
      const res = await fetch(`/api/pipelines/${pipeline.id}/run`, { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        setRuns((prev) => [data, ...prev])
        toast.success(`Pipeline "${pipeline.name}" started`)
      } else { throw new Error('Failed') }
    } catch {
      const newRun: PipelineRun = {
        id: `r${Date.now()}`, pipelineId: pipeline.id, pipelineName: pipeline.name,
        status: 'running', startedAt: new Date().toISOString(),
      }
      setRuns((prev) => [newRun, ...prev])
      toast.success(`Pipeline "${pipeline.name}" started (offline)`)
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

  const activeCount = pipelines.filter((p) => p.status === 'active').length
  const draftCount = pipelines.filter((p) => p.status === 'draft').length
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
                    {datasets.map((d) => <SelectItem key={d.id} value={d.name}>{d.name}</SelectItem>)}
                    <SelectItem value="customers">customers</SelectItem>
                    <SelectItem value="orders">orders</SelectItem>
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
      <div className="grid gap-4 sm:grid-cols-3">
        <Card><CardContent className="p-4 flex items-center gap-3">
          <div className="rounded-lg bg-emerald-50 p-2"><CheckCircle2 className="h-5 w-5 text-emerald-600" /></div>
          <div><p className="text-xs text-slate-500">Active</p><p className="text-2xl font-bold">{activeCount}</p></div>
        </CardContent></Card>
        <Card><CardContent className="p-4 flex items-center gap-3">
          <div className="rounded-lg bg-slate-50 p-2"><Clock className="h-5 w-5 text-slate-600" /></div>
          <div><p className="text-xs text-slate-500">Drafts</p><p className="text-2xl font-bold">{draftCount}</p></div>
        </CardContent></Card>
        <Card><CardContent className="p-4 flex items-center gap-3">
          <div className="rounded-lg bg-blue-50 p-2"><Settings2 className="h-5 w-5 text-blue-600" /></div>
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
            <Card key={pipeline.id} className={cn('cursor-pointer transition-all hover:shadow-md', selectedPipeline?.id === pipeline.id ? 'ring-2 ring-emerald-500' : '')} onClick={() => setSelectedPipeline(pipeline)}>
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
                      <span className="flex items-center gap-1"><Settings2 className="h-3 w-3" />{pipeline.steps.length} steps</span>
                      <span className="flex items-center gap-1"><Play className="h-3 w-3" />{pipeline.runCount} runs</span>
                      {pipeline.tableName && <Badge variant="outline" className="text-[10px]">{pipeline.tableName}</Badge>}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); handleRunPipeline(pipeline) }} className="h-8 w-8 p-0">
                      <Play className="h-4 w-4 text-emerald-600" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); handleDeletePipeline(pipeline.id) }} className="h-8 w-8 p-0">
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                </div>
                <div className="flex items-center gap-2 mt-3 flex-wrap">
                  {pipeline.steps.map((step, i) => (
                    <div key={step.id} className="flex items-center gap-2">
                      <Badge variant="secondary" className="text-[11px] gap-1">{step.name}</Badge>
                      {i < pipeline.steps.length - 1 && <ChevronRight className="h-3 w-3 text-slate-300" />}
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
                      <Button variant="outline" size="sm" onClick={() => handleRunPipeline(selectedPipeline)} className="gap-1">
                        <Play className="h-3.5 w-3.5" /> Run
                      </Button>
                      <Button variant="outline" size="sm" className="gap-1">
                        <Save className="h-3.5 w-3.5" /> Save
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {selectedPipeline.steps.map((step, index) => (
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
                    {selectedPipeline.steps.length === 0 && (
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
                    {STEP_TYPES.map((stepType) => (
                      <button key={stepType.type} onClick={() => { setNewStepType(stepType.type); setShowStepDialog(true) }} className="flex items-center gap-3 rounded-lg border bg-white p-3 text-left hover:shadow-sm hover:border-emerald-300 transition">
                        <div className="flex h-8 w-8 items-center justify-center rounded bg-slate-50">
                          <span className="text-xs font-bold text-slate-500">{index => STEP_TYPES.indexOf(stepType) + 1}</span>
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
                      <Label>Configuration (key:value pairs, comma-separated)</Label>
                      <Input placeholder="e.g., strategy:mean, columns:age,income" value={newStepConfig} onChange={(e) => setNewStepConfig(e.target.value)} />
                      <p className="text-[10px] text-slate-400">Example: strategy:mean, columns:age,income</p>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setShowStepDialog(false)}>Cancel</Button>
                    <Button onClick={handleAddStep} disabled={!newStepType}>Add Step</Button>
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
            <Card key={run.id}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <StatusBadge status={run.status} />
                    <div>
                      <p className="text-sm font-medium text-slate-900">{run.pipelineName}</p>
                      <div className="flex items-center gap-3 text-xs text-slate-400 mt-0.5">
                        <span>Started: {new Date(run.startedAt).toLocaleString()}</span>
                        {run.duration != null && <span>Duration: {run.duration}s</span>}
                        {run.recordsProcessed != null && <span>Records: {run.recordsProcessed.toLocaleString()}</span>}
                      </div>
                      {run.error && <p className="text-xs text-red-500 mt-1">Error: {run.error}</p>}
                    </div>
                  </div>
                  {run.status === 'failed' && (
                    <Button variant="outline" size="sm" className="gap-1"><RotateCcw className="h-3 w-3" /> Retry</Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </TabsContent>
      </Tabs>
    </div>
  )
}
