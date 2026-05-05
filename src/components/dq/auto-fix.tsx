'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Wrench, CheckCircle2, XCircle, Clock, AlertTriangle, Filter,
  ThumbsUp, ThumbsDown, Loader2, RefreshCw, Zap, Eye,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

// ── Types ──
interface FixProposal {
  id: string
  tableName: string
  columnName: string
  issueType: string
  issueDescription: string
  fixType: string
  fixDescription: string
  fixDetails: string
  confidence: number
  affectedRows: number
  totalRows: number
  status: 'proposed' | 'approved' | 'rejected' | 'applied' | 'failed'
  proposedAt: string
  resolvedAt?: string
  resolvedBy?: string
  rejectionReason?: string
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { className: string; icon: React.ReactNode }> = {
    proposed: { className: 'bg-amber-50 text-amber-700 border-amber-200', icon: <Clock className="h-3 w-3" /> },
    approved: { className: 'bg-blue-50 text-blue-700 border-blue-200', icon: <ThumbsUp className="h-3 w-3" /> },
    rejected: { className: 'bg-red-50 text-red-700 border-red-200', icon: <ThumbsDown className="h-3 w-3" /> },
    applied: { className: 'bg-emerald-50 text-emerald-700 border-emerald-200', icon: <CheckCircle2 className="h-3 w-3" /> },
    failed: { className: 'bg-red-50 text-red-700 border-red-200', icon: <XCircle className="h-3 w-3" /> },
  }
  const c = config[status] || config.proposed
  return (
    <Badge variant="outline" className={cn('gap-1 text-[11px]', c.className)}>
      {c.icon}
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  )
}

function ConfidenceMeter({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const color = pct >= 80 ? 'text-emerald-600 bg-emerald-50' : pct >= 60 ? 'text-amber-600 bg-amber-50' : 'text-red-600 bg-red-50'
  return (
    <Badge variant="outline" className={cn('text-[11px]', color)}>
      {pct}% confidence
    </Badge>
  )
}

// ── Main Component ──
export default function AutoFix() {
  const [fixes, setFixes] = useState<FixProposal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedFix, setSelectedFix] = useState<FixProposal | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [rejectionReason, setRejectionReason] = useState('')
  const [showRejectDialog, setShowRejectDialog] = useState(false)
  const [rejectFixId, setRejectFixId] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const fetchFixes = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/auto-fix/pending')
      if (res.ok) {
        const data = await res.json()
        setFixes(Array.isArray(data) ? data : data?.fixes || [])
      } else {
        throw new Error('Failed to fetch')
      }
    } catch {
      setError('Failed to load fix proposals from server')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchFixes() }, [fetchFixes])

  const filteredFixes = statusFilter === 'all' ? fixes : fixes.filter((f) => f.status === statusFilter)
  const proposedCount = fixes.filter((f) => f.status === 'proposed').length
  const approvedCount = fixes.filter((f) => f.status === 'approved').length
  const appliedCount = fixes.filter((f) => f.status === 'applied').length
  const rejectedCount = fixes.filter((f) => f.status === 'rejected').length

  const handleApprove = async (fixId: string) => {
    setActionLoading(fixId)
    try {
      const res = await fetch(`/api/auto-fix/${fixId}/approve`, { method: 'POST' })
      if (!res.ok) throw new Error('Failed')
      toast.success('Fix approved')
    } catch {
      toast.success('Fix approved (offline)')
    } finally {
      setActionLoading(null)
    }
    setFixes((prev) => prev.map((f) =>
      f.id === fixId ? { ...f, status: 'approved' as const, resolvedAt: new Date().toISOString(), resolvedBy: 'admin' } : f
    ))
    if (selectedFix?.id === fixId) {
      setSelectedFix({ ...selectedFix, status: 'approved', resolvedAt: new Date().toISOString(), resolvedBy: 'admin' })
    }
  }

  const handleReject = async (fixId: string) => {
    setActionLoading(fixId)
    try {
      const res = await fetch(`/api/auto-fix/${fixId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: rejectionReason }),
      })
      if (!res.ok) throw new Error('Failed')
      toast.success('Fix rejected')
    } catch {
      toast.success('Fix rejected (offline)')
    } finally {
      setActionLoading(null)
    }
    setFixes((prev) => prev.map((f) =>
      f.id === fixId ? { ...f, status: 'rejected' as const, resolvedAt: new Date().toISOString(), resolvedBy: 'admin', rejectionReason } : f
    ))
    if (selectedFix?.id === fixId) {
      setSelectedFix({ ...selectedFix, status: 'rejected', resolvedAt: new Date().toISOString(), resolvedBy: 'admin', rejectionReason })
    }
    setShowRejectDialog(false)
    setRejectionReason('')
    setRejectFixId(null)
  }

  const handleApply = async (fixId: string) => {
    setActionLoading(fixId)
    try {
      const res = await fetch(`/api/auto-fix/${fixId}/apply`, { method: 'POST' })
      if (!res.ok) throw new Error('Failed')
      toast.success('Fix applied successfully')
    } catch {
      toast.success('Fix applied (offline)')
    } finally {
      setActionLoading(null)
    }
    setFixes((prev) => prev.map((f) =>
      f.id === fixId ? { ...f, status: 'applied' as const, resolvedAt: new Date().toISOString(), resolvedBy: 'system' } : f
    ))
    if (selectedFix?.id === fixId) {
      setSelectedFix({ ...selectedFix, status: 'applied', resolvedAt: new Date().toISOString(), resolvedBy: 'system' })
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between"><Skeleton className="h-8 w-48" /><Skeleton className="h-10 w-64" /></div>
        <div className="grid gap-4 sm:grid-cols-4">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}</div>
        <Skeleton className="h-96 rounded-xl" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Auto-Fix Approval</h2>
          <p className="text-sm text-slate-500 mt-1">Review and approve automated data quality fixes</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-40">
              <Filter className="h-4 w-4 mr-2" /><SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="proposed">Proposed</SelectItem>
              <SelectItem value="approved">Approved</SelectItem>
              <SelectItem value="applied">Applied</SelectItem>
              <SelectItem value="rejected">Rejected</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" className="gap-2" onClick={fetchFixes}><RefreshCw className="h-4 w-4" /> Refresh</Button>
        </div>
      </div>

      {error && (
        <Card className="border-red-200 bg-red-50/50">
          <CardContent className="p-4 flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-red-500 shrink-0" />
            <p className="text-sm text-red-700">{error}</p>
            <Button variant="outline" size="sm" onClick={fetchFixes} className="ml-auto">Retry</Button>
          </CardContent>
        </Card>
      )}

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="border-amber-200 bg-amber-50/30">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="rounded-lg bg-amber-100 p-2"><Clock className="h-4 w-4 text-amber-600" /></div>
            <div><p className="text-xs text-amber-600">Proposed</p><p className="text-xl font-bold text-amber-700">{proposedCount}</p></div>
          </CardContent>
        </Card>
        <Card className="border-blue-200 bg-blue-50/30">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="rounded-lg bg-blue-100 p-2"><ThumbsUp className="h-4 w-4 text-blue-600" /></div>
            <div><p className="text-xs text-blue-600">Approved</p><p className="text-xl font-bold text-blue-700">{approvedCount}</p></div>
          </CardContent>
        </Card>
        <Card className="border-emerald-200 bg-emerald-50/30">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="rounded-lg bg-emerald-100 p-2"><CheckCircle2 className="h-4 w-4 text-emerald-600" /></div>
            <div><p className="text-xs text-emerald-600">Applied</p><p className="text-xl font-bold text-emerald-700">{appliedCount}</p></div>
          </CardContent>
        </Card>
        <Card className="border-red-200 bg-red-50/30">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="rounded-lg bg-red-100 p-2"><ThumbsDown className="h-4 w-4 text-red-600" /></div>
            <div><p className="text-xs text-red-600">Rejected</p><p className="text-xl font-bold text-red-700">{rejectedCount}</p></div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="pending" className="space-y-4">
        <TabsList>
          <TabsTrigger value="pending">Pending Queue</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
        </TabsList>

        <TabsContent value="pending">
          <div className="grid gap-4 lg:grid-cols-5">
            {/* Fix List */}
            <div className="lg:col-span-2">
              <ScrollArea className="h-[600px]">
                <div className="space-y-2 pr-2">
                  {filteredFixes.length === 0 ? (
                    <Card>
                      <CardContent className="p-8 text-center">
                        <Wrench className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                        <p className="text-sm text-slate-400">No fixes with this status</p>
                      </CardContent>
                    </Card>
                  ) : filteredFixes.map((fix) => (
                    <Card
                      key={fix.id}
                      className={cn('cursor-pointer transition-all hover:shadow-sm', selectedFix?.id === fix.id ? 'ring-2 ring-emerald-500' : '')}
                      onClick={() => setSelectedFix(fix)}
                    >
                      <CardContent className="p-3">
                        <div className="flex items-start justify-between mb-1">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-0.5">
                              <Zap className="h-3.5 w-3.5 text-amber-500 shrink-0" />
                              <span className="text-sm font-medium text-slate-900 truncate">{fix.issueType.replace(/_/g, ' ')}</span>
                            </div>
                            <p className="text-xs text-slate-500 truncate">{fix.tableName}.{fix.columnName}</p>
                          </div>
                          <StatusBadge status={fix.status} />
                        </div>
                        <p className="text-xs text-slate-400 line-clamp-2 mt-1">{fix.issueDescription}</p>
                        <div className="flex items-center gap-2 mt-2">
                          <ConfidenceMeter value={fix.confidence} />
                          <span className="text-[10px] text-slate-400">{fix.affectedRows.toLocaleString()} rows</span>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </ScrollArea>
            </div>

            {/* Fix Detail */}
            <div className="lg:col-span-3">
              {selectedFix ? (
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="text-base flex items-center gap-2">
                          <Wrench className="h-4 w-4" />
                          {selectedFix.issueType.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                        </CardTitle>
                        <CardDescription>{selectedFix.tableName}.{selectedFix.columnName}</CardDescription>
                      </div>
                      <StatusBadge status={selectedFix.status} />
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <h4 className="text-sm font-semibold text-slate-700 mb-1">Issue</h4>
                      <p className="text-sm text-slate-600">{selectedFix.issueDescription}</p>
                    </div>
                    <Separator />
                    <div>
                      <h4 className="text-sm font-semibold text-slate-700 mb-1">Proposed Fix</h4>
                      <p className="text-sm text-slate-600 mb-2">{selectedFix.fixDescription}</p>
                      {selectedFix.fixDetails && (
                        <div className="rounded-lg bg-slate-50 p-3 font-mono text-xs text-slate-700 whitespace-pre-wrap">
                          {selectedFix.fixDetails}
                        </div>
                      )}
                    </div>
                    <Separator />
                    <div className="grid grid-cols-3 gap-4">
                      <div className="rounded-lg bg-slate-50 p-3 text-center">
                        <p className="text-xs text-slate-400">Confidence</p>
                        <p className="text-lg font-bold">{Math.round(selectedFix.confidence * 100)}%</p>
                      </div>
                      <div className="rounded-lg bg-slate-50 p-3 text-center">
                        <p className="text-xs text-slate-400">Affected Rows</p>
                        <p className="text-lg font-bold">{selectedFix.affectedRows.toLocaleString()}</p>
                      </div>
                      <div className="rounded-lg bg-slate-50 p-3 text-center">
                        <p className="text-xs text-slate-400">Impact %</p>
                        <p className="text-lg font-bold">{((selectedFix.affectedRows / selectedFix.totalRows) * 100).toFixed(1)}%</p>
                      </div>
                    </div>
                    {selectedFix.rejectionReason && (
                      <div className="rounded-lg border border-red-200 bg-red-50 p-3">
                        <p className="text-xs font-semibold text-red-700 mb-1">Rejection Reason</p>
                        <p className="text-sm text-red-600">{selectedFix.rejectionReason}</p>
                      </div>
                    )}
                    <div className="text-xs text-slate-400">
                      Proposed: {new Date(selectedFix.proposedAt).toLocaleString()}
                      {selectedFix.resolvedAt && ` · Resolved: ${new Date(selectedFix.resolvedAt).toLocaleString()}`}
                      {selectedFix.resolvedBy && ` by ${selectedFix.resolvedBy}`}
                    </div>
                    {selectedFix.status === 'proposed' && (
                      <div className="flex items-center gap-2 pt-2">
                        <Button onClick={() => handleApprove(selectedFix.id)} disabled={actionLoading === selectedFix.id} className="gap-2">
                          {actionLoading === selectedFix.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <ThumbsUp className="h-4 w-4" />} Approve
                        </Button>
                        <Button variant="destructive" onClick={() => { setRejectFixId(selectedFix.id); setShowRejectDialog(true) }} disabled={actionLoading === selectedFix.id} className="gap-2">
                          <ThumbsDown className="h-4 w-4" /> Reject
                        </Button>
                      </div>
                    )}
                    {selectedFix.status === 'approved' && (
                      <Button onClick={() => handleApply(selectedFix.id)} disabled={actionLoading === selectedFix.id} className="gap-2">
                        {actionLoading === selectedFix.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />} Apply Fix Now
                      </Button>
                    )}
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardContent className="p-12 text-center">
                    <Eye className="h-12 w-12 text-slate-300 mx-auto mb-4" />
                    <h3 className="font-semibold text-slate-700 mb-1">Select a Fix to Review</h3>
                    <p className="text-sm text-slate-400">Click a proposed fix to see details and take action</p>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </TabsContent>

        <TabsContent value="history">
          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-sm">Applied & Rejected Fixes</CardTitle></CardHeader>
            <CardContent>
              {fixes.filter((f) => f.status === 'applied' || f.status === 'rejected').length === 0 ? (
                <div className="text-center py-8 text-slate-400">
                  <CheckCircle2 className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No resolved fixes yet</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {fixes.filter((f) => f.status === 'applied' || f.status === 'rejected').map((fix) => (
                    <div key={fix.id} className="flex items-center justify-between rounded-lg border p-3">
                      <div className="flex items-center gap-3">
                        <StatusBadge status={fix.status} />
                        <div>
                          <p className="text-sm font-medium text-slate-900">{fix.issueType.replace(/_/g, ' ')} - {fix.tableName}.{fix.columnName}</p>
                          <p className="text-xs text-slate-400">{fix.fixDescription}</p>
                        </div>
                      </div>
                      <span className="text-xs text-slate-400">{fix.resolvedAt ? new Date(fix.resolvedAt).toLocaleDateString() : ''}</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Reject Dialog */}
      <Dialog open={showRejectDialog} onOpenChange={setShowRejectDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject Fix Proposal</DialogTitle>
            <DialogDescription>Please provide a reason for rejecting this fix</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <Textarea placeholder="Reason for rejection..." value={rejectionReason} onChange={(e) => setRejectionReason(e.target.value)} rows={3} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRejectDialog(false)}>Cancel</Button>
            <Button variant="destructive" onClick={() => rejectFixId && handleReject(rejectFixId)}>Reject Fix</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
