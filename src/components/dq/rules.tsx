'use client'

import { useEffect, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plus,
  Sparkles,
  Search,
  Filter,
  MoreVertical,
  Pencil,
  Trash2,
  Loader2,
  Zap,
  CheckCircle2,
  XCircle,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
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
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import type { QualityRule, Dataset } from '@/lib/store'

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

function getSeverityBadge(severity: string) {
  switch (severity) {
    case 'critical':
      return <Badge className="bg-red-500/15 text-red-700 border-red-500/30">critical</Badge>
    case 'warning':
      return <Badge className="bg-amber-500/15 text-amber-700 border-amber-500/30">warning</Badge>
    case 'info':
      return <Badge className="bg-sky-500/15 text-sky-700 border-sky-500/30">info</Badge>
    default:
      return <Badge variant="secondary">{severity}</Badge>
  }
}

function getDimensionBadge(dimension: string) {
  const colors: Record<string, string> = {
    completeness: 'bg-emerald-500/15 text-emerald-700 border-emerald-500/30',
    accuracy: 'bg-sky-500/15 text-sky-700 border-sky-500/30',
    consistency: 'bg-violet-500/15 text-violet-700 border-violet-500/30',
    timeliness: 'bg-amber-500/15 text-amber-700 border-amber-500/30',
    uniqueness: 'bg-orange-500/15 text-orange-700 border-orange-500/30',
    validity: 'bg-pink-500/15 text-pink-700 border-pink-500/30',
    integrity: 'bg-teal-500/15 text-teal-700 border-teal-500/30',
    conformity: 'bg-indigo-500/15 text-indigo-700 border-indigo-500/30',
  }
  return (
    <Badge variant="outline" className={colors[dimension] || ''}>
      {dimension}
    </Badge>
  )
}

function formatSchedule(schedule: string | null) {
  if (!schedule) return <span className="text-muted-foreground">Manual</span>
  const scheduleMap: Record<string, string> = {
    '0 */6 * * *': 'Every 6 hours',
    '0 * * * *': 'Every hour',
    '0 0 * * *': 'Daily',
    '*/5 * * * *': 'Every 5 min',
    '0 2 * * *': 'Daily 2:00 AM',
    '0 0 * * 0': 'Weekly',
    '0 */4 * * *': 'Every 4 hours',
    '0 */8 * * *': 'Every 8 hours',
    '0 0 1 * *': 'Monthly',
    '*/30 * * * *': 'Every 30 min',
  }
  return (
    <span className="font-mono text-xs">
      {scheduleMap[schedule] || schedule}
    </span>
  )
}

export default function RulesView() {
  const [rules, setRules] = useState<QualityRule[]>([])
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [datasetFilter, setDatasetFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')

  // NL Rule Creator
  const [nlPrompt, setNlPrompt] = useState('')
  const [nlDatasetId, setNlDatasetId] = useState('')
  const [nlLoading, setNlLoading] = useState(false)
  const [generatedRule, setGeneratedRule] = useState<QualityRule | null>(null)
  const [showNlCreator, setShowNlCreator] = useState(false)

  const fetchRules = useCallback(async () => {
    try {
      setLoading(true)
      const res = await fetch('/api/rules')
      if (!res.ok) throw new Error('Failed to fetch rules')
      const data = await res.json()
      setRules(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Failed to fetch rules:', err)
      setError('Failed to load rules')
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchDatasets = useCallback(async () => {
    try {
      const res = await fetch('/api/datasets')
      if (res.ok) {
        const data = await res.json()
        setDatasets(Array.isArray(data) ? data : [])
      }
    } catch {
      // datasets optional for rules view
    }
  }, [])

  useEffect(() => {
    Promise.all([fetchRules(), fetchDatasets()])
  }, [fetchRules, fetchDatasets])

  const toggleRule = async (ruleId: string, enabled: boolean) => {
    try {
      const res = await fetch(`/api/rules/${ruleId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !enabled }),
      })
      if (res.ok) {
        setRules((prev) =>
          prev.map((r) => (r.id === ruleId ? { ...r, enabled: !enabled } : r))
        )
      }
    } catch {
      console.error('Failed to toggle rule')
    }
  }

  const deleteRule = async (ruleId: string) => {
    try {
      const res = await fetch(`/api/rules/${ruleId}`, { method: 'DELETE' })
      if (res.ok) {
        setRules((prev) => prev.filter((r) => r.id !== ruleId))
      }
    } catch {
      console.error('Failed to delete rule')
    }
  }

  const handleGenerateRule = async () => {
    if (!nlPrompt.trim() || !nlDatasetId) return
    try {
      setNlLoading(true)
      setGeneratedRule(null)
      const selectedDataset = datasets.find((d) => d.id === nlDatasetId)
      const res = await fetch('/api/nl-rule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: nlPrompt.trim(),
          datasetId: nlDatasetId,
          datasetName: selectedDataset?.name || '',
        }),
      })
      if (!res.ok) throw new Error('Failed to generate rule')
      const rule = await res.json()
      setGeneratedRule(rule)
      setNlPrompt('')
      fetchRules()
    } catch (err) {
      console.error('Failed to generate rule:', err)
    } finally {
      setNlLoading(false)
    }
  }

  // Filter rules
  const filteredRules = rules.filter((rule) => {
    if (datasetFilter !== 'all' && rule.datasetId !== datasetFilter) return false
    if (statusFilter === 'enabled' && !rule.enabled) return false
    if (statusFilter === 'disabled' && rule.enabled) return false
    if (searchQuery && !rule.name.toLowerCase().includes(searchQuery.toLowerCase())) return false
    return true
  })

  // Get dataset name by id
  const getDatasetName = (id: string) => {
    const ds = datasets.find((d) => d.id === id)
    return ds?.name || id.slice(0, 8)
  }

  if (loading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-36" />
        <Skeleton className="h-48 rounded-xl" />
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Quality Rules</h1>
          <p className="text-sm text-muted-foreground">{rules.length} rules configured</p>
        </div>
        <Button
          variant={showNlCreator ? 'outline' : 'default'}
          onClick={() => setShowNlCreator(!showNlCreator)}
        >
          {showNlCreator ? (
            <>
              <XCircle className="h-4 w-4 mr-2" />
              Close Creator
            </>
          ) : (
            <>
              <Plus className="h-4 w-4 mr-2" />
              Create Rule
            </>
          )}
        </Button>
      </div>

      {/* NL Rule Creator */}
      <AnimatePresence>
        {showNlCreator && (
          <motion.div
            variants={fadeInUp}
            initial="hidden"
            animate="visible"
            exit={{ opacity: 0, y: -10 }}
          >
            <Card className="shadow-sm border-dashed border-2 border-primary/20">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-amber-500" />
                  Natural Language Rule Creator
                </CardTitle>
                <CardDescription>
                  Describe your data quality rule in plain English and let AI generate it.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="nl-prompt">Rule Description</Label>
                  <Textarea
                    id="nl-prompt"
                    placeholder="Alert me if customer_age is negative or greater than 150, or if email format is invalid..."
                    value={nlPrompt}
                    onChange={(e) => setNlPrompt(e.target.value)}
                    className="min-h-[100px]"
                  />
                </div>
                <div className="flex items-end gap-4">
                  <div className="flex-1 space-y-2">
                    <Label>Dataset</Label>
                    <Select value={nlDatasetId} onValueChange={setNlDatasetId}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select a dataset" />
                      </SelectTrigger>
                      <SelectContent>
                        {datasets.map((ds) => (
                          <SelectItem key={ds.id} value={ds.id}>
                            {ds.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <Button
                    onClick={handleGenerateRule}
                    disabled={!nlPrompt.trim() || !nlDatasetId || nlLoading}
                    className="min-w-[180px]"
                  >
                    {nlLoading ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-4 w-4 mr-2" />
                        Generate Rule with AI
                      </>
                    )}
                  </Button>
                </div>

                {/* Generated Rule Preview */}
                <AnimatePresence>
                  {generatedRule && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                    >
                      <Separator className="my-4" />
                      <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 space-y-3">
                        <div className="flex items-center gap-2 text-emerald-700">
                          <CheckCircle2 className="h-5 w-5" />
                          <span className="font-semibold text-sm">Rule Generated Successfully</span>
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                          <div>
                            <p className="text-xs text-muted-foreground">Name</p>
                            <p className="font-medium">{generatedRule.name}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Type</p>
                            <p className="font-medium capitalize">{generatedRule.type}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Dimension</p>
                            <p className="font-medium capitalize">{generatedRule.dimension}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Severity</p>
                            <p className="font-medium capitalize">{generatedRule.severity}</p>
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Filter Bar */}
      <motion.div variants={fadeInUp} className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search rules..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={datasetFilter} onValueChange={setDatasetFilter}>
          <SelectTrigger className="w-[180px]">
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
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="All Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="enabled">Enabled</SelectItem>
            <SelectItem value="disabled">Disabled</SelectItem>
          </SelectContent>
        </Select>
      </motion.div>

      {error && (
        <div className="text-center py-8">
          <p className="text-muted-foreground">{error}</p>
        </div>
      )}

      {/* Rules Table */}
      <motion.div variants={fadeInUp}>
        <Card className="shadow-sm">
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Dimension</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Dataset</TableHead>
                  <TableHead>Schedule</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="w-[50px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredRules.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-12 text-muted-foreground">
                      <Zap className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      No rules found
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredRules.map((rule) => (
                    <TableRow key={rule.id} className={!rule.enabled ? 'opacity-60' : ''}>
                      <TableCell>
                        <div className="max-w-[200px]">
                          <p className="font-medium truncate">{rule.name}</p>
                          {rule.description && (
                            <p className="text-xs text-muted-foreground truncate mt-0.5">
                              {rule.description}
                            </p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="capitalize">
                          {rule.type.replace(/_/g, ' ')}
                        </Badge>
                      </TableCell>
                      <TableCell>{getDimensionBadge(rule.dimension)}</TableCell>
                      <TableCell>{getSeverityBadge(rule.severity)}</TableCell>
                      <TableCell>
                        <span className="text-sm text-muted-foreground">
                          {getDatasetName(rule.datasetId)}
                        </span>
                      </TableCell>
                      <TableCell>{formatSchedule(rule.schedule)}</TableCell>
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
                            <DropdownMenuItem>
                              <Pencil className="h-4 w-4 mr-2" />
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              variant="destructive"
                              onClick={() => deleteRule(rule.id)}
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  )
}
