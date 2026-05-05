'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  CalendarClock, Plus, Play, Trash2, Clock, CheckCircle2, XCircle,
  Loader2, RefreshCw, Timer, Calendar, Repeat, Zap,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

// ── Types ──
interface ScheduledJob {
  id: string
  name: string
  type: string
  schedule: string
  scheduleType: 'cron' | 'interval'
  enabled: boolean
  status: 'idle' | 'running' | 'success' | 'failed'
  lastRun: string | null
  nextRun: string | null
  lastDuration: number | null
  successCount: number
  failureCount: number
  createdAt: string
}

const JOB_TYPES = [
  { type: 'quality_check', name: 'Quality Check', icon: <CheckCircle2 className="h-4 w-4 text-emerald-500" /> },
  { type: 'sync', name: 'Data Sync', icon: <RefreshCw className="h-4 w-4 text-blue-500" /> },
  { type: 'profile', name: 'Data Profiling', icon: <Zap className="h-4 w-4 text-amber-500" /> },
  { type: 'ml_readiness', name: 'ML Readiness', icon: <Zap className="h-4 w-4 text-violet-500" /> },
  { type: 'auto_fix', name: 'Auto-Fix Scan', icon: <Zap className="h-4 w-4 text-rose-500" /> },
  { type: 'contract_check', name: 'Contract Check', icon: <Zap className="h-4 w-4 text-cyan-500" /> },
]

const CRON_DESCRIPTIONS: Record<string, string> = {
  '0 8 * * *': 'Every day at 8:00 AM',
  '0 * * * *': 'Every hour',
  '0 2 * * 1': 'Every Monday at 2:00 AM',
  '*/30 * * * *': 'Every 30 minutes',
  '0 0 * * *': 'Every day at midnight',
  '0 6 * * *': 'Every day at 6:00 AM',
  '0 */4 * * *': 'Every 4 hours',
}

// ── Helpers ──
function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { className: string; icon: React.ReactNode }> = {
    idle: { className: 'bg-slate-50 text-slate-600 border-slate-200', icon: <Clock className="h-3 w-3" /> },
    running: { className: 'bg-blue-50 text-blue-700 border-blue-200', icon: <Loader2 className="h-3 w-3 animate-spin" /> },
    success: { className: 'bg-emerald-50 text-emerald-700 border-emerald-200', icon: <CheckCircle2 className="h-3 w-3" /> },
    failed: { className: 'bg-red-50 text-red-700 border-red-200', icon: <XCircle className="h-3 w-3" /> },
  }
  const c = config[status] || config.idle
  return (
    <Badge variant="outline" className={cn('gap-1 text-[11px]', c.className)}>
      {c.icon}
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  )
}

function CronDescription({ schedule, scheduleType }: { schedule: string; scheduleType: string }) {
  return (
    <Badge variant="secondary" className="text-[10px] gap-1">
      {scheduleType === 'interval' ? <Timer className="h-3 w-3" /> : <Calendar className="h-3 w-3" />}
      {CRON_DESCRIPTIONS[schedule] || schedule}
    </Badge>
  )
}

// ── Main Component ──
export default function Scheduler() {
  const [jobs, setJobs] = useState<ScheduledJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [newJob, setNewJob] = useState({
    name: '', type: 'quality_check', scheduleType: 'cron' as 'cron' | 'interval',
    cronExpression: '0 8 * * *', intervalMinutes: '60', target: '',
  })

  const fetchJobs = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/schedules')
      if (res.ok) {
        const data = await res.json()
        setJobs(Array.isArray(data) ? data : data?.jobs || [])
      } else {
        throw new Error('Failed')
      }
    } catch {
      setError('Failed to load scheduled jobs from server')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchJobs() }, [fetchJobs])

  const handleCreate = async () => {
    if (!newJob.name.trim()) { toast.error('Job name is required'); return }
    const schedule = newJob.scheduleType === 'cron' ? newJob.cronExpression : `every ${newJob.intervalMinutes}m`
    try {
      const res = await fetch('/api/schedules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newJob.name, type: newJob.type, schedule,
          scheduleType: newJob.scheduleType, target: newJob.target,
        }),
      })
      if (res.ok) {
        const data = await res.json()
        setJobs((prev) => [data, ...prev])
        toast.success('Scheduled job created')
      } else {
        throw new Error('Failed')
      }
    } catch {
      const job: ScheduledJob = {
        id: `j${Date.now()}`, name: newJob.name, type: newJob.type,
        schedule, scheduleType: newJob.scheduleType, enabled: true, status: 'idle',
        lastRun: null, nextRun: null, lastDuration: null,
        successCount: 0, failureCount: 0, createdAt: new Date().toISOString(),
      }
      setJobs((prev) => [job, ...prev])
      toast.success('Scheduled job created (offline)')
    }
    setShowCreateDialog(false)
    setNewJob({ name: '', type: 'quality_check', scheduleType: 'cron', cronExpression: '0 8 * * *', intervalMinutes: '60', target: '' })
  }

  const handleToggle = async (jobId: string) => {
    const job = jobs.find((j) => j.id === jobId)
    if (!job) return
    try {
      await fetch(`/api/schedules/${jobId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !job.enabled }),
      })
    } catch { /* offline */ }
    setJobs((prev) => prev.map((j) => j.id === jobId ? { ...j, enabled: !j.enabled } : j))
    toast.success(job.enabled ? 'Job disabled' : 'Job enabled')
  }

  const handleRunNow = async (jobId: string) => {
    try {
      await fetch(`/api/schedules/${jobId}/run`, { method: 'POST' })
    } catch { /* offline */ }
    setJobs((prev) => prev.map((j) => j.id === jobId ? { ...j, status: 'running' as const } : j))
    toast.success('Job triggered')
  }

  const handleDelete = async (jobId: string) => {
    try {
      await fetch(`/api/schedules/${jobId}`, { method: 'DELETE' })
    } catch { /* offline */ }
    setJobs((prev) => prev.filter((j) => j.id !== jobId))
    toast.success('Job deleted')
  }

  const enabledCount = jobs.filter((j) => j.enabled).length
  const runningCount = jobs.filter((j) => j.status === 'running').length

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between"><Skeleton className="h-8 w-48" /><Skeleton className="h-10 w-36" /></div>
        <div className="grid gap-4 sm:grid-cols-3">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}</div>
        {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Job Scheduler</h2>
          <p className="text-sm text-slate-500 mt-1">Manage scheduled data quality and maintenance jobs</p>
        </div>
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <Button className="gap-2" onClick={() => setShowCreateDialog(true)}><Plus className="h-4 w-4" /> New Job</Button>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Scheduled Job</DialogTitle>
              <DialogDescription>Set up a recurring data quality task</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label>Job Name</Label>
                <Input placeholder="e.g., Daily Quality Scan" value={newJob.name} onChange={(e) => setNewJob((p) => ({ ...p, name: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>Job Type</Label>
                <Select value={newJob.type} onValueChange={(v) => setNewJob((p) => ({ ...p, type: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {JOB_TYPES.map((jt) => <SelectItem key={jt.type} value={jt.type}>{jt.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Target (table/dataset)</Label>
                <Input placeholder="e.g., customers" value={newJob.target} onChange={(e) => setNewJob((p) => ({ ...p, target: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>Schedule Type</Label>
                <div className="flex gap-2">
                  <Button variant={newJob.scheduleType === 'cron' ? 'default' : 'outline'} size="sm" onClick={() => setNewJob((p) => ({ ...p, scheduleType: 'cron' }))} className="gap-1">
                    <Calendar className="h-3.5 w-3.5" /> Cron
                  </Button>
                  <Button variant={newJob.scheduleType === 'interval' ? 'default' : 'outline'} size="sm" onClick={() => setNewJob((p) => ({ ...p, scheduleType: 'interval' }))} className="gap-1">
                    <Repeat className="h-3.5 w-3.5" /> Interval
                  </Button>
                </div>
              </div>
              {newJob.scheduleType === 'cron' ? (
                <div className="space-y-2">
                  <Label>Cron Expression</Label>
                  <Input placeholder="0 8 * * *" value={newJob.cronExpression} onChange={(e) => setNewJob((p) => ({ ...p, cronExpression: e.target.value }))} className="font-mono" />
                  <p className="text-xs text-slate-400">Format: minute hour day month weekday</p>
                </div>
              ) : (
                <div className="space-y-2">
                  <Label>Interval (minutes)</Label>
                  <Input type="number" placeholder="60" value={newJob.intervalMinutes} onChange={(e) => setNewJob((p) => ({ ...p, intervalMinutes: e.target.value }))} />
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancel</Button>
              <Button onClick={handleCreate} disabled={!newJob.name.trim()}>Create Job</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {error && (
        <Card className="border-red-200 bg-red-50/50">
          <CardContent className="p-4 flex items-center gap-3">
            <XCircle className="h-5 w-5 text-red-500 shrink-0" />
            <p className="text-sm text-red-700">{error}</p>
            <Button variant="outline" size="sm" onClick={fetchJobs} className="ml-auto">Retry</Button>
          </CardContent>
        </Card>
      )}

      {/* Summary */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card><CardContent className="p-4 flex items-center gap-3">
          <div className="rounded-lg bg-emerald-50 p-2"><CheckCircle2 className="h-4 w-4 text-emerald-600" /></div>
          <div><p className="text-xs text-emerald-600">Enabled Jobs</p><p className="text-xl font-bold">{enabledCount}/{jobs.length}</p></div>
        </CardContent></Card>
        <Card><CardContent className="p-4 flex items-center gap-3">
          <div className="rounded-lg bg-blue-50 p-2"><Loader2 className="h-4 w-4 text-blue-600" /></div>
          <div><p className="text-xs text-blue-600">Running</p><p className="text-xl font-bold">{runningCount}</p></div>
        </CardContent></Card>
        <Card><CardContent className="p-4 flex items-center gap-3">
          <div className="rounded-lg bg-amber-50 p-2"><CalendarClock className="h-4 w-4 text-amber-600" /></div>
          <div><p className="text-xs text-amber-600">Next Run</p><p className="text-lg font-bold">
            {jobs.find((j) => j.enabled && j.nextRun) ? new Date(jobs.find((j) => j.enabled && j.nextRun)!.nextRun!).toLocaleTimeString() : 'N/A'}
          </p></div>
        </CardContent></Card>
      </div>

      {/* Jobs List */}
      {jobs.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <CalendarClock className="h-12 w-12 text-slate-300 mx-auto mb-4" />
            <h3 className="font-semibold text-slate-700 mb-1">No Scheduled Jobs</h3>
            <p className="text-sm text-slate-400 mb-4">Create your first scheduled job</p>
            <Button onClick={() => setShowCreateDialog(true)} className="gap-2"><Plus className="h-4 w-4" /> New Job</Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {jobs.map((job) => (
            <Card key={job.id} className={cn(!job.enabled && 'opacity-60')}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-4 flex-1 min-w-0">
                    <Switch checked={job.enabled} onCheckedChange={() => handleToggle(job.id)} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                        <h3 className="text-sm font-semibold text-slate-900 truncate">{job.name}</h3>
                        <StatusBadge status={job.status} />
                        <Badge variant="outline" className="text-[10px]">
                          {JOB_TYPES.find((jt) => jt.type === job.type)?.name || job.type}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-slate-400 flex-wrap">
                        <CronDescription schedule={job.schedule} scheduleType={job.scheduleType} />
                        {job.lastRun && <span>Last: {new Date(job.lastRun).toLocaleString()}</span>}
                        {job.nextRun && job.enabled && <span>Next: {new Date(job.nextRun).toLocaleString()}</span>}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 shrink-0">
                    <div className="text-right text-xs">
                      <div className="flex items-center gap-2">
                        <span className="text-emerald-600">{job.successCount} ok</span>
                        <span className="text-red-500">{job.failureCount} fail</span>
                      </div>
                      {job.lastDuration != null && <span className="text-slate-400">{job.lastDuration}s</span>}
                    </div>
                    <Button variant="outline" size="sm" className="gap-1" onClick={() => handleRunNow(job.id)} disabled={!job.enabled}>
                      <Play className="h-3.5 w-3.5" /> Run Now
                    </Button>
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-red-500" onClick={() => handleDelete(job.id)}>
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
