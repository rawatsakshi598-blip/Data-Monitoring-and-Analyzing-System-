'use client'

import { useEffect, useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { format } from 'date-fns'
import {
  Shield,
  Heart,
  Scale,
  CreditCard,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Progress } from '@/components/ui/progress'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { ComplianceReport, Dataset } from '@/lib/store'

// ── Types ──────────────────────────────────────────────────────────

interface Finding {
  id: string
  field: string
  type: 'PII' | 'Sensitive' | 'Prohibited'
  recommendation: string
  status: 'Compliant' | 'Non-Compliant' | 'Needs Review'
}

interface FrameworkData {
  name: string
  icon: React.ReactNode
  score: number
  status: 'Compliant' | 'Non-Compliant' | 'Needs Review'
  findings: Finding[]
  lastScan: string
}

// ── Helpers ────────────────────────────────────────────────────────

function statusBadgeClass(status: string) {
  switch (status) {
    case 'Compliant':
      return 'bg-green-500/15 text-green-700 dark:text-green-400 border-green-500/30'
    case 'Non-Compliant':
      return 'bg-red-500/15 text-red-700 dark:text-red-400 border-red-500/30'
    case 'Needs Review':
      return 'bg-yellow-500/15 text-yellow-700 dark:text-yellow-400 border-yellow-500/30'
    default:
      return ''
  }
}

function findingStatusDot(status: string) {
  switch (status) {
    case 'Compliant':
      return <CheckCircle2 className="size-4 text-green-500" />
    case 'Non-Compliant':
      return <XCircle className="size-4 text-red-500" />
    case 'Needs Review':
      return <AlertTriangle className="size-4 text-yellow-500" />
    default:
      return null
  }
}

function typeBadge(type: string) {
  switch (type) {
    case 'PII':
      return 'bg-red-500/15 text-red-700 dark:text-red-400 border-red-500/30'
    case 'Sensitive':
      return 'bg-orange-500/15 text-orange-700 dark:text-orange-400 border-orange-500/30'
    case 'Prohibited':
      return 'bg-purple-500/15 text-purple-700 dark:text-purple-400 border-purple-500/30'
    default:
      return ''
  }
}

function scoreColor(score: number): string {
  if (score >= 90) return '#22c55e'
  if (score >= 70) return '#f97316'
  return '#ef4444'
}

// ── No mock data — all data comes from the Python backend ──

// ── Circular Score Indicator ───────────────────────────────────────

function CircularScore({ score, size = 80 }: { score: number; size?: number }) {
  const strokeWidth = 6
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference
  const color = scoreColor(score)

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          className="stroke-muted"
          strokeWidth={strokeWidth}
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1, ease: 'easeOut' }}
        />
      </svg>
      <span className="absolute text-sm font-bold" style={{ color }}>
        {score}%
      </span>
    </div>
  )
}

// ── Component ──────────────────────────────────────────────────────

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.07 } },
}
const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.35 } },
}

export default function ComplianceView() {
  const [reports, setReports] = useState<ComplianceReport[]>([])
  const [frameworks, setFrameworks] = useState<FrameworkData[]>([])
  const [loading, setLoading] = useState(true)
  const [complianceError, setComplianceError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('')

  // Fetch compliance reports and frameworks
  useEffect(() => {
    async function fetchCompliance() {
      try {
        const res = await fetch('/api/compliance')
        if (res.ok) {
          const data = await res.json()
          setReports(Array.isArray(data?.reports) ? data.reports : Array.isArray(data) ? data : [])
          if (Array.isArray(data?.frameworks) && data.frameworks.length > 0) {
            setFrameworks(data.frameworks)
            setActiveTab(data.frameworks[0].name)
          }
        } else {
          setComplianceError('Failed to load compliance data from backend')
        }
      } catch {
        setComplianceError('Backend unavailable — please ensure the Python backend is running on port 3001')
      } finally {
        setLoading(false)
      }
    }
    fetchCompliance()
  }, [])

  // Summary stats
  const summaryStats = useMemo(() => {
    const totalFindings = frameworks.reduce((sum, fw) => sum + fw.findings.length, 0)
    const compliant = frameworks.reduce(
      (sum, fw) => sum + fw.findings.filter((f) => f.status === 'Compliant').length,
      0,
    )
    const nonCompliant = frameworks.reduce(
      (sum, fw) => sum + fw.findings.filter((f) => f.status === 'Non-Compliant').length,
      0,
    )
    const needsReview = frameworks.reduce(
      (sum, fw) => sum + fw.findings.filter((f) => f.status === 'Needs Review').length,
      0,
    )
    return { totalFindings, compliant, nonCompliant, needsReview }
  }, [frameworks])

  const avgScore = frameworks.length > 0 ? Math.round(
    frameworks.reduce((sum, fw) => sum + fw.score, 0) / frameworks.length,
  ) : 0

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6 p-6"
    >
      {/* Header */}
      <motion.div variants={itemVariants}>
        <h1 className="text-2xl font-bold tracking-tight">Compliance Monitoring</h1>
        <p className="text-muted-foreground mt-1">
          GDPR, HIPAA, SOX, PCI-DSS compliance tracking
        </p>
      </motion.div>

      {/* Error state */}
      {complianceError && (
        <Card className="border-amber-200 bg-amber-50/50">
          <CardContent className="p-6 text-center">
            <Shield className="h-10 w-10 text-amber-400 mx-auto mb-3" />
            <p className="text-sm text-amber-700 font-medium">{complianceError}</p>
          </CardContent>
        </Card>
      )}

      {/* Empty state when no frameworks */}
      {!complianceError && frameworks.length === 0 && !loading && (
        <Card>
          <CardContent className="p-12 text-center">
            <Shield className="h-12 w-12 text-slate-300 mx-auto mb-4" />
            <h3 className="font-semibold text-slate-700 mb-1">No Compliance Data</h3>
            <p className="text-sm text-slate-400">Compliance data will appear after uploading data and running quality checks.</p>
          </CardContent>
        </Card>
      )}

      {/* Framework cards */}
      {frameworks.length > 0 && (
      <motion.div variants={itemVariants} className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {frameworks.map((fw) => {
          const nonCompliantCount = fw.findings.filter((f) => f.status === 'Non-Compliant').length
          return (
            <Card key={fw.name} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      {fw.icon}
                    </div>
                    <div>
                      <p className="font-semibold text-sm">{fw.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {fw.findings.length} findings
                      </p>
                    </div>
                  </div>
                  <Badge className={statusBadgeClass(fw.status)}>
                    {fw.status}
                  </Badge>
                </div>
                <div className="flex items-center justify-center py-2">
                  <CircularScore score={fw.score} size={72} />
                </div>
                {nonCompliantCount > 0 && (
                  <p className="text-xs text-red-500 text-center mt-1">
                    {nonCompliantCount} non-compliant finding{nonCompliantCount !== 1 ? 's' : ''}
                  </p>
                )}
              </CardContent>
            </Card>
          )
        })}
      </motion.div>
      )}

      {/* Compliance Details Tabs */}
      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Compliance Details</CardTitle>
            <CardDescription>
              Detailed findings and recommendations per framework
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="mb-4">
                {frameworks.map((fw) => (
                  <TabsTrigger key={fw.name} value={fw.name} className="gap-1.5">
                    <span className="hidden sm:inline">{fw.icon}</span>
                    {fw.name}
                  </TabsTrigger>
                ))}
              </TabsList>

              {frameworks.map((fw) => (
                <TabsContent key={fw.name} value={fw.name}>
                  <div className="space-y-4">
                    {/* Score + status */}
                    <div className="flex flex-col sm:flex-row items-center gap-6 p-4 rounded-lg bg-muted/50">
                      <CircularScore score={fw.score} size={96} />
                      <div className="text-center sm:text-left">
                        <p className="text-lg font-semibold">{fw.name} Compliance Score</p>
                        <div className="flex items-center gap-3 mt-2 justify-center sm:justify-start">
                          <Badge className={statusBadgeClass(fw.status)}>
                            {fw.status}
                          </Badge>
                          <span className="text-xs text-muted-foreground flex items-center gap-1">
                            <Clock className="size-3" />
                            Last scanned {formatDistanceToNowCompat(fw.lastScan)}
                          </span>
                        </div>
                        <Progress
                          value={fw.score}
                          className="mt-3 h-2 w-full max-w-xs"
                        />
                      </div>
                    </div>

                    {/* Findings table */}
                    <div className="rounded-lg border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-[40px]" />
                            <TableHead>Field</TableHead>
                            <TableHead>Type</TableHead>
                            <TableHead className="hidden md:table-cell">Recommendation</TableHead>
                            <TableHead>Status</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {fw.findings.map((finding) => (
                            <TableRow key={finding.id}>
                              <TableCell>{findingStatusDot(finding.status)}</TableCell>
                              <TableCell className="font-mono text-sm">{finding.field}</TableCell>
                              <TableCell>
                                <Badge className={typeBadge(finding.type)} variant="outline">
                                  {finding.type}
                                </Badge>
                              </TableCell>
                              <TableCell className="hidden md:table-cell text-sm text-muted-foreground max-w-[300px]">
                                {finding.recommendation}
                              </TableCell>
                              <TableCell>
                                <Badge className={statusBadgeClass(finding.status)}>
                                  {finding.status}
                                </Badge>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                </TabsContent>
              ))}
            </Tabs>
          </CardContent>
        </Card>
      </motion.div>

      {/* Bottom section: Overview + Recent Activity */}
      <motion.div variants={itemVariants} className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Compliance Overview */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Compliance Overview</CardTitle>
            <CardDescription>
              Aggregate compliance status across all frameworks
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Score */}
            <div className="flex items-center gap-4">
              <CircularScore score={avgScore} size={72} />
              <div>
                <p className="text-lg font-semibold">Average Score</p>
                <p className="text-sm text-muted-foreground">
                  Across {frameworks.length} frameworks
                </p>
              </div>
            </div>

            {/* Stacked bar */}
            <div>
              <p className="text-sm font-medium mb-2">Finding Status Distribution</p>
              <div className="flex rounded-full overflow-hidden h-4">
                <motion.div
                  className="bg-green-500 h-full"
                  style={{ width: `${(summaryStats.compliant / summaryStats.totalFindings) * 100}%` }}
                  initial={{ width: 0 }}
                  animate={{ width: `${(summaryStats.compliant / summaryStats.totalFindings) * 100}%` }}
                  transition={{ duration: 0.8 }}
                />
                <motion.div
                  className="bg-red-500 h-full"
                  style={{ width: `${(summaryStats.nonCompliant / summaryStats.totalFindings) * 100}%` }}
                  initial={{ width: 0 }}
                  animate={{ width: `${(summaryStats.nonCompliant / summaryStats.totalFindings) * 100}%` }}
                  transition={{ duration: 0.8, delay: 0.2 }}
                />
                <motion.div
                  className="bg-yellow-500 h-full"
                  style={{ width: `${(summaryStats.needsReview / summaryStats.totalFindings) * 100}%` }}
                  initial={{ width: 0 }}
                  animate={{ width: `${(summaryStats.needsReview / summaryStats.totalFindings) * 100}%` }}
                  transition={{ duration: 0.8, delay: 0.4 }}
                />
              </div>
              <div className="flex flex-wrap gap-4 mt-2 text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  <span className="inline-block size-2.5 rounded-full bg-green-500" />
                  Compliant ({summaryStats.compliant})
                </span>
                <span className="flex items-center gap-1">
                  <span className="inline-block size-2.5 rounded-full bg-red-500" />
                  Non-Compliant ({summaryStats.nonCompliant})
                </span>
                <span className="flex items-center gap-1">
                  <span className="inline-block size-2.5 rounded-full bg-yellow-500" />
                  Needs Review ({summaryStats.needsReview})
                </span>
              </div>
            </div>

            {/* Framework breakdown */}
            <div className="space-y-2 pt-2">
              {frameworks.map((fw) => (
                <div key={fw.name} className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2 text-muted-foreground">
                    <span className="w-4 text-center">{fw.icon}</span>
                    {fw.name}
                  </span>
                  <div className="flex items-center gap-2">
                    <div className="w-24">
                      <Progress value={fw.score} className="h-1.5" />
                    </div>
                    <span className="font-medium w-10 text-right" style={{ color: scoreColor(fw.score) }}>
                      {fw.score}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent Activity</CardTitle>
            <CardDescription>
              Latest compliance scan results
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="max-h-[380px]">
              <div className="space-y-3 pr-4">
                {/* Use reports for activity feed, sorted by date */}
                {([...reports].sort((a, b) =>
                  new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
                )).map((report, i) => (
                  <motion.div
                    key={report.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="flex items-center gap-3 rounded-lg border p-3 hover:bg-muted/30 transition-colors"
                  >
                    <div className="shrink-0">
                      {report.status === 'Compliant' ? (
                        <CheckCircle2 className="size-5 text-green-500" />
                      ) : report.status === 'Non-Compliant' ? (
                        <XCircle className="size-5 text-red-500" />
                      ) : (
                        <AlertTriangle className="size-5 text-yellow-500" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">{report.framework}</span>
                        <Badge className={statusBadgeClass(report.status)} variant="outline">
                          {report.status}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Score: <span style={{ color: scoreColor(report.score) }}>{report.score}%</span>
                        {' · '}
                        Dataset: {report.datasetId}
                      </p>
                    </div>
                    <span className="text-xs text-muted-foreground shrink-0">
                      {format(new Date(report.createdAt), 'MMM d, HH:mm')}
                    </span>
                  </motion.div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  )
}

// Simple helper since we want to use it inline without importing formatDistanceToNow everywhere
function formatDistanceToNowCompat(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  const diffHr = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHr / 24)

  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  if (diffHr < 24) return `${diffHr}h ago`
  return `${diffDay}d ago`
}
