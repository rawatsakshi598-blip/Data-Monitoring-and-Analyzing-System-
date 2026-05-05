'use client'

import { useEffect, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { formatDistanceToNow } from 'date-fns'
import {
  Plus,
  Database,
  HardDrive,
  Cloud,
  Server,
  Globe,
  ExternalLink,
  Table2,
  Rows3,
  Clock,
  ShieldCheck,
  Search,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Skeleton } from '@/components/ui/skeleton'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { MoreVertical, Eye } from 'lucide-react'
import type { Dataset, QualityCheck } from '@/lib/store'

const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.06 },
  },
}

const datasetTypes: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  postgresql: { label: 'PostgreSQL', icon: Database, color: 'text-sky-600 bg-sky-500/15' },
  mysql: { label: 'MySQL', icon: Database, color: 'text-orange-600 bg-orange-500/15' },
  mongodb: { label: 'MongoDB', icon: Database, color: 'text-green-600 bg-green-500/15' },
  snowflake: { label: 'Snowflake', icon: Cloud, color: 'text-sky-500 bg-sky-500/15' },
  bigquery: { label: 'BigQuery', icon: HardDrive, color: 'text-emerald-600 bg-emerald-500/15' },
  s3: { label: 'S3', icon: Cloud, color: 'text-amber-600 bg-amber-500/15' },
  api: { label: 'API', icon: Globe, color: 'text-violet-600 bg-violet-500/15' },
}

function getScoreColor(score: number) {
  if (score >= 90) return 'text-emerald-600'
  if (score >= 70) return 'text-amber-600'
  return 'text-red-600'
}

function getScoreBarColor(score: number) {
  if (score >= 90) return '[&>div]:bg-emerald-500'
  if (score >= 70) return '[&>div]:bg-amber-500'
  return '[&>div]:bg-red-500'
}

function getStatusDot(status: string) {
  switch (status) {
    case 'active':
      return 'bg-emerald-500'
    case 'warning':
      return 'bg-amber-500'
    case 'error':
    case 'inactive':
      return 'bg-red-500'
    default:
      return 'bg-muted-foreground'
  }
}

function getStatusLabel(status: string) {
  switch (status) {
    case 'active':
      return 'Active'
    case 'warning':
      return 'Warning'
    case 'error':
      return 'Error'
    case 'inactive':
      return 'Inactive'
    default:
      return status
  }
}

interface DatasetWithMeta extends Dataset {
  rulesCount?: number
  recentChecks?: QualityCheck[]
}

export default function DatasetsView() {
  const [datasets, setDatasets] = useState<DatasetWithMeta[]>([])

  const safeFixed = (val: number | undefined | null, d = 1) => (val ?? 0).toFixed(d)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [detailDialogOpen, setDetailDialogOpen] = useState(false)
  const [selectedDataset, setSelectedDataset] = useState<DatasetWithMeta | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // Form state
  const [formName, setFormName] = useState('')
  const [formDescription, setFormDescription] = useState('')
  const [formType, setFormType] = useState('postgresql')

  const fetchDatasets = useCallback(async () => {
    try {
      setLoading(true)
      const res = await fetch('/api/datasets')
      if (!res.ok) throw new Error('Failed to fetch datasets')
      const data = await res.json()
      setDatasets(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Failed to fetch datasets:', err)
      setError('Failed to load datasets')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchDatasets()
  }, [fetchDatasets])

  const handleSubmit = async () => {
    if (!formName.trim()) return
    try {
      setSubmitting(true)
      const res = await fetch('/api/datasets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: formName.trim(),
          description: formDescription.trim() || null,
          type: formType,
        }),
      })
      if (!res.ok) throw new Error('Failed to create dataset')
      setDialogOpen(false)
      setFormName('')
      setFormDescription('')
      setFormType('postgresql')
      fetchDatasets()
    } catch (err) {
      console.error('Failed to create dataset:', err)
    } finally {
      setSubmitting(false)
    }
  }

  const openDetail = async (dataset: DatasetWithMeta) => {
    setSelectedDataset(dataset)
    setDetailDialogOpen(true)
    // Fetch additional details
    try {
      const res = await fetch(`/api/datasets/${dataset.id}`)
      if (res.ok) {
        const data = await res.json()
        setSelectedDataset({ ...dataset, ...data })
      }
    } catch {
      // Use basic data
    }
  }

  const formatNumber = (n: number) => {
    if (n == null) return '0'
    if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
    return n.toString()
  }

  if (loading) {
    return (
      <div className="space-y-6 p-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-10 w-36" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-52 rounded-xl" />
          ))}
        </div>
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Datasets</h1>
          <p className="text-sm text-muted-foreground">{datasets.length} datasets registered</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Add Dataset
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Dataset</DialogTitle>
              <DialogDescription>
                Register a new data source for quality monitoring.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  placeholder="e.g., customer_orders_db"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Brief description of the dataset..."
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  className="min-h-[80px]"
                />
              </div>
              <div className="space-y-2">
                <Label>Type</Label>
                <Select value={formType} onValueChange={setFormType}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(datasetTypes).map(([key, val]) => (
                      <SelectItem key={key} value={key}>
                        {val.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleSubmit} disabled={!formName.trim() || submitting}>
                {submitting ? 'Creating...' : 'Create Dataset'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {error && (
        <div className="text-center py-8">
          <p className="text-muted-foreground">{error}</p>
        </div>
      )}

      {/* Dataset Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {datasets.map((dataset) => {
          const typeInfo = datasetTypes[dataset.type] || { label: dataset.type, icon: Database, color: 'text-muted-foreground bg-muted' }
          const TypeIcon = typeInfo.icon

          return (
            <motion.div key={dataset.id} variants={fadeInUp}>
              <Card className="shadow-sm hover:shadow-md transition-shadow cursor-pointer group" onClick={() => openDetail(dataset)}>
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className={`rounded-lg p-2 ${typeInfo.color}`}>
                        <TypeIcon className="h-5 w-5" />
                      </div>
                      <div className="min-w-0">
                        <CardTitle className="text-base truncate">{dataset.name}</CardTitle>
                        <CardDescription className="text-xs truncate mt-0.5">
                          {dataset.description || 'No description'}
                        </CardDescription>
                      </div>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                        <Button variant="ghost" size="icon" className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={(e) => { e.stopPropagation(); openDetail(dataset) }}>
                          <Eye className="h-4 w-4 mr-2" />
                          View Details
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4 pt-0">
                  <div className="flex items-center gap-3">
                    <Badge variant="outline" className={typeInfo.color}>
                      {typeInfo.label}
                    </Badge>
                    <div className="flex items-center gap-1.5">
                      <span className={`h-2 w-2 rounded-full ${getStatusDot(dataset.status)}`} />
                      <span className="text-xs text-muted-foreground">{getStatusLabel(dataset.status)}</span>
                    </div>
                  </div>

                  {/* Quality Score */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">Quality Score</span>
                      <span className={`font-semibold ${getScoreColor(dataset.qualityScore ?? 0)}`}>
                        {safeFixed(dataset.qualityScore)}%
                      </span>
                    </div>
                    <Progress value={dataset.qualityScore} className={`h-2 ${getScoreBarColor(dataset.qualityScore)}`} />
                  </div>

                  <Separator />

                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="flex items-center gap-1.5 text-muted-foreground">
                      <Rows3 className="h-3.5 w-3.5" />
                      <span>{formatNumber(dataset.rowCount)} rows</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-muted-foreground">
                      <Table2 className="h-3.5 w-3.5" />
                      <span>{dataset.columnCount} columns</span>
                    </div>
                  </div>

                  {dataset.lastChecked && (
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      <Clock className="h-3.5 w-3.5" />
                      <span>Checked {formatDistanceToNow(new Date(dataset.lastChecked), { addSuffix: true })}</span>
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          )
        })}
      </div>

      {/* Detail Dialog */}
      <Dialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
        <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
          {selectedDataset && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-3">
                  {(() => {
                    const t = datasetTypes[selectedDataset.type] || { label: selectedDataset.type, icon: Database, color: 'text-muted-foreground bg-muted' }
                    const Icon = t.icon
                    return (
                      <div className={`rounded-lg p-2 ${t.color}`}>
                        <Icon className="h-5 w-5" />
                      </div>
                    )
                  })()}
                  {selectedDataset.name}
                </DialogTitle>
                <DialogDescription>{selectedDataset.description || 'No description'}</DialogDescription>
              </DialogHeader>

              <div className="space-y-6">
                {/* Info Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Type</p>
                    <p className="text-sm font-medium">{datasetTypes[selectedDataset.type]?.label || selectedDataset.type}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Status</p>
                    <div className="flex items-center gap-1.5">
                      <span className={`h-2 w-2 rounded-full ${getStatusDot(selectedDataset.status)}`} />
                      <span className="text-sm font-medium">{getStatusLabel(selectedDataset.status)}</span>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Quality Score</p>
                    <p className={`text-sm font-semibold ${getScoreColor(selectedDataset.qualityScore ?? 0)}`}>
                      {safeFixed(selectedDataset.qualityScore)}%
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Rows</p>
                    <p className="text-sm font-medium">{formatNumber(selectedDataset.rowCount)}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Columns</p>
                    <p className="text-sm font-medium">{selectedDataset.columnCount}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Last Checked</p>
                    <p className="text-sm font-medium">
                      {selectedDataset.lastChecked
                        ? formatDistanceToNow(new Date(selectedDataset.lastChecked), { addSuffix: true })
                        : 'Never'}
                    </p>
                  </div>
                </div>

                <Separator />

                {/* Connection Info */}
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold flex items-center gap-2">
                    <Server className="h-4 w-4" />
                    Connection Info
                  </h3>
                  <div className="bg-muted/50 rounded-lg p-3 text-xs font-mono break-all">
                    {selectedDataset.connectionInfo || 'No connection info available'}
                  </div>
                </div>

                {/* Associated Rules */}
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4" />
                    Associated Rules
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {(selectedDataset as DatasetWithMeta).rulesCount ?? '-'} rules configured
                  </p>
                </div>

                {/* Recent Checks */}
                {(selectedDataset as DatasetWithMeta).recentChecks && (selectedDataset as DatasetWithMeta).recentChecks!.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="text-sm font-semibold flex items-center gap-2">
                      <Clock className="h-4 w-4" />
                      Recent Checks
                    </h3>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Status</TableHead>
                          <TableHead>Score</TableHead>
                          <TableHead>Records</TableHead>
                          <TableHead>Time</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {(selectedDataset as DatasetWithMeta).recentChecks!.slice(0, 5).map((check) => (
                          <TableRow key={check.id}>
                            <TableCell>
                              <Badge
                                variant={
                                  check.status === 'passed'
                                    ? 'outline'
                                    : check.status === 'failed'
                                      ? 'destructive'
                                      : 'secondary'
                                }
                                className={
                                  check.status === 'passed'
                                    ? 'bg-emerald-500/15 text-emerald-700 border-emerald-500/30'
                                    : check.status === 'warning'
                                      ? 'bg-amber-500/15 text-amber-700 border-amber-500/30'
                                      : ''
                                }
                              >
                                {check.status}
                              </Badge>
                            </TableCell>
                            <TableCell className={getScoreColor(check.score ?? 0)}>
                              {safeFixed(check.score)}
                            </TableCell>
                            <TableCell className="text-muted-foreground">
                              {formatNumber(check.recordsChecked)}
                            </TableCell>
                            <TableCell className="text-muted-foreground text-xs">
                              {formatDistanceToNow(new Date(check.createdAt), { addSuffix: true })}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </motion.div>
  )
}
