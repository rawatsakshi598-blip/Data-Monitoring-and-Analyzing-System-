'use client'

import { useEffect, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { formatDistanceToNow } from 'date-fns'
import {
  ShieldCheck,
  ClipboardCheck,
  AlertTriangle,
  Activity,
  TrendingUp,
  Clock,
  ArrowUpRight,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  AreaChart,
  BarChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Area,
  Bar,
} from 'recharts'
import type { QualityCheck, Alert } from '@/lib/store'

interface DashboardStats {
  totalDatasets: number
  averageQualityScore: number
  enabledRulesCount: number
  checksToday: number
  criticalAlerts: number
  passRate: number
  recentChecks: { date: string; passed: number; failed: number }[]
}

interface RecentCheckRow extends QualityCheck {
  ruleName?: string
  datasetName?: string
}

interface StatsResponse extends DashboardStats {
  recentChecksList?: RecentCheckRow[]
  activeAlerts?: Alert[]
}

const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
}

function getScoreColor(score: number) {
  if (score > 90) return { text: 'text-emerald-600', bg: 'bg-emerald-500/20', border: 'border-emerald-500', ring: 'ring-emerald-500' }
  if (score > 70) return { text: 'text-amber-600', bg: 'bg-amber-500/20', border: 'border-amber-500', ring: 'ring-amber-500' }
  return { text: 'text-red-600', bg: 'bg-red-500/20', border: 'border-red-500', ring: 'ring-red-500' }
}

function getStatusBadge(status: string) {
  switch (status) {
    case 'passed':
      return <Badge className="bg-emerald-500/15 text-emerald-700 border-emerald-500/30 hover:bg-emerald-500/25">Passed</Badge>
    case 'failed':
      return <Badge className="bg-red-500/15 text-red-700 border-red-500/30 hover:bg-red-500/25">Failed</Badge>
    case 'warning':
      return <Badge className="bg-amber-500/15 text-amber-700 border-amber-500/30 hover:bg-amber-500/25">Warning</Badge>
    case 'error':
      return <Badge variant="destructive">Error</Badge>
    case 'running':
      return <Badge className="bg-sky-500/15 text-sky-700 border-sky-500/30 hover:bg-sky-500/25">Running</Badge>
    default:
      return <Badge variant="secondary">{status}</Badge>
  }
}

function CircularScore({ score }: { score: number }) {
  const colors = getScoreColor(score)
  const circumference = 2 * Math.PI * 54
  const offset = circumference - (score / 100) * circumference
  const clampedScore = Math.round(Math.min(100, Math.max(0, score)))

  return (
    <div className="relative flex items-center justify-center">
      <svg className="w-32 h-32 -rotate-90" viewBox="0 0 120 120">
        <circle
          cx="60"
          cy="60"
          r="54"
          fill="none"
          className="stroke-muted"
          strokeWidth="8"
        />
        <circle
          cx="60"
          cy="60"
          r="54"
          fill="none"
          className={colors.border}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 1s ease-in-out' }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className={`text-3xl font-bold ${colors.text}`}>
          {clampedScore}
        </span>
        <span className="text-xs text-muted-foreground">/ 100</span>
      </div>
    </div>
  )
}

export default function DashboardView() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [recentChecks, setRecentChecks] = useState<RecentCheckRow[]>([])
  const [activeAlerts, setActiveAlerts] = useState<Alert[]>([])
  const [trendData, setTrendData] = useState<{ date: string; score: number }[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const safeFixed = (val: number | undefined | null, d = 1) => (val ?? 0).toFixed(d)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const [statsRes, checksRes, alertsRes] = await Promise.all([
        fetch('/api/stats'),
        fetch('/api/checks?limit=5'),
        fetch('/api/alerts?status=active'),
      ])

      if (!statsRes.ok || !checksRes.ok) throw new Error('Failed to fetch data')

      const statsData: DashboardStats = await statsRes.json()
      const checksRaw = await checksRes.json()
      const checksData: RecentCheckRow[] = Array.isArray(checksRaw) ? checksRaw : []
      const alertsRaw = alertsRes.ok ? await alertsRes.json() : []
      const alertsData: Alert[] = Array.isArray(alertsRaw) ? alertsRaw : []

      setStats(statsData)
      setRecentChecks(checksData)
      setActiveAlerts(alertsData)

      // Generate trend data from recent checks
      const scoreTrend = statsData.recentChecks.map((day) => {
        const total = day.passed + day.failed
        const score = total > 0 ? Math.round((day.passed / total) * 100 * 10) / 10 : 0
        return {
          date: new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
          score,
        }
      })
      setTrendData(scoreTrend)
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err)
      setError('Failed to load dashboard data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  if (loading) {
    return (
      <div className="space-y-6 p-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-40 rounded-xl" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Skeleton className="h-80 rounded-xl" />
          <Skeleton className="h-80 rounded-xl" />
        </div>
      </div>
    )
  }

  if (error || !stats) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="h-10 w-10 text-muted-foreground mx-auto mb-2" />
          <p className="text-muted-foreground">{error || 'No data available'}</p>
        </div>
      </div>
    )
  }

  const chartData = stats.recentChecks.map((day) => ({
    date: new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    passed: day.passed,
    failed: day.failed,
    warning: Math.floor(day.failed * 0.2),
  }))

  const scoreColors = getScoreColor(stats.averageQualityScore)

  return (
    <motion.div
      className="space-y-6 p-6"
      variants={staggerContainer}
      initial="hidden"
      animate="visible"
    >
      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <motion.div variants={fadeInUp}>
          <Card className="shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Overall Quality Score
              </CardTitle>
            </CardHeader>
            <CardContent className="flex items-center justify-center pt-0">
              <CircularScore score={stats.averageQualityScore} />
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={fadeInUp}>
          <Card className="shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Active Rules
              </CardTitle>
            </CardHeader>
            <CardContent className="flex items-center gap-4 pt-0">
              <div className={`rounded-full p-3 ${scoreColors.bg}`}>
                <ShieldCheck className={`h-6 w-6 ${scoreColors.text}`} />
              </div>
              <div>
                <p className="text-3xl font-bold">{stats.enabledRulesCount}</p>
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <TrendingUp className="h-3 w-3" />
                  Quality rules running
                </p>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={fadeInUp}>
          <Card className="shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Checks Today
              </CardTitle>
            </CardHeader>
            <CardContent className="flex items-center gap-4 pt-0">
              <div className="rounded-full bg-emerald-500/20 p-3">
                <ClipboardCheck className="h-6 w-6 text-emerald-600" />
              </div>
              <div>
                <p className="text-3xl font-bold">{stats.checksToday}</p>
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <Activity className="h-3 w-3" />
                  {stats.passRate}% pass rate
                </p>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={fadeInUp}>
          <Card className={`shadow-sm ${stats.criticalAlerts > 0 ? 'border-red-200 bg-red-50/50' : ''}`}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Critical Alerts
              </CardTitle>
            </CardHeader>
            <CardContent className="flex items-center gap-4 pt-0">
              <div className={`rounded-full p-3 ${stats.criticalAlerts > 0 ? 'bg-red-500/20' : 'bg-emerald-500/20'}`}>
                <AlertTriangle className={`h-6 w-6 ${stats.criticalAlerts > 0 ? 'text-red-600' : 'text-emerald-600'}`} />
              </div>
              <div>
                <p className={`text-3xl font-bold ${stats.criticalAlerts > 0 ? 'text-red-600' : ''}`}>
                  {stats.criticalAlerts}
                </p>
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  {stats.criticalAlerts > 0 ? (
                    <>
                      <ArrowUpRight className="h-3 w-3 text-red-500" />
                      Requires attention
                    </>
                  ) : (
                    'All clear'
                  )}
                </p>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <motion.div variants={fadeInUp}>
          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle className="text-base">Quality Score Trend</CardTitle>
              <p className="text-xs text-muted-foreground">Last 14 days</p>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trendData}>
                    <defs>
                      <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#10b981" stopOpacity={0.2} />
                        <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11 }}
                      className="text-muted-foreground"
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      domain={[0, 100]}
                      tick={{ fontSize: 11 }}
                      className="text-muted-foreground"
                      tickLine={false}
                      axisLine={false}
                    />
                    <RechartsTooltip
                      contentStyle={{
                        backgroundColor: 'hsl(var(--popover))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px',
                        fontSize: '12px',
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="score"
                      stroke="#10b981"
                      strokeWidth={2}
                      fill="url(#scoreGradient)"
                      name="Quality Score"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={fadeInUp}>
          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle className="text-base">Check Results</CardTitle>
              <p className="text-xs text-muted-foreground">Pass/Fail per day</p>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11 }}
                      className="text-muted-foreground"
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 11 }}
                      className="text-muted-foreground"
                      tickLine={false}
                      axisLine={false}
                    />
                    <RechartsTooltip
                      contentStyle={{
                        backgroundColor: 'hsl(var(--popover))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px',
                        fontSize: '12px',
                      }}
                    />
                    <Bar dataKey="passed" fill="#10b981" radius={[2, 2, 0, 0]} name="Passed" />
                    <Bar dataKey="warning" fill="#f59e0b" radius={[2, 2, 0, 0]} name="Warning" />
                    <Bar dataKey="failed" fill="#ef4444" radius={[2, 2, 0, 0]} name="Failed" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Bottom Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Checks */}
        <motion.div variants={fadeInUp}>
          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle className="text-base">Recent Checks</CardTitle>
              <p className="text-xs text-muted-foreground">Last 5 quality checks</p>
            </CardHeader>
            <CardContent>
              {recentChecks.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground text-sm">
                  No checks available
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Rule</TableHead>
                      <TableHead>Dataset</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Score</TableHead>
                      <TableHead>Time</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {recentChecks.map((check) => (
                      <TableRow key={check.id}>
                        <TableCell className="font-medium max-w-[150px] truncate">
                          {check.ruleName || check.ruleId.slice(0, 8)}
                        </TableCell>
                        <TableCell className="max-w-[120px] truncate">
                          {check.datasetName || check.datasetId.slice(0, 8)}
                        </TableCell>
                        <TableCell>{getStatusBadge(check.status)}</TableCell>
                        <TableCell>
                          <span className={`font-medium ${getScoreColor(check.score ?? 0).text}`}>
                            {safeFixed(check.score)}
                          </span>
                        </TableCell>
                        <TableCell className="text-muted-foreground text-xs">
                          {formatDistanceToNow(new Date(check.createdAt), { addSuffix: true })}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Active Alerts */}
        <motion.div variants={fadeInUp}>
          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle className="text-base">Active Alerts</CardTitle>
              <p className="text-xs text-muted-foreground">Unresolved alerts</p>
            </CardHeader>
            <CardContent>
              <ScrollArea className="max-h-80">
                <div className="space-y-3">
                  {activeAlerts.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground text-sm">
                      <ShieldCheck className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      No active alerts
                    </div>
                  ) : (
                    activeAlerts.map((alert) => (
                      <div
                        key={alert.id}
                        className={`border-l-4 rounded-md p-3 bg-muted/30 ${
                          alert.severity === 'critical'
                            ? 'border-l-red-500'
                            : alert.severity === 'warning'
                              ? 'border-l-amber-500'
                              : 'border-l-sky-500'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <Badge
                                variant={
                                  alert.severity === 'critical'
                                    ? 'destructive'
                                    : alert.severity === 'warning'
                                      ? 'outline'
                                      : 'secondary'
                                }
                                className={
                                  alert.severity === 'warning'
                                    ? 'bg-amber-500/15 text-amber-700 border-amber-500/30'
                                    : ''
                                }
                              >
                                {alert.severity}
                              </Badge>
                              <span className="text-sm font-medium truncate">
                                {alert.title}
                              </span>
                            </div>
                            <p className="text-xs text-muted-foreground line-clamp-2">
                              {alert.message}
                            </p>
                          </div>
                          <span className="text-xs text-muted-foreground whitespace-nowrap flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {formatDistanceToNow(new Date(alert.createdAt), { addSuffix: true })}
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </motion.div>
  )
}
