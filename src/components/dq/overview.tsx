'use client'

import { useEffect, useState } from 'react'
import {
  Database,
  Table2,
  TestTubes,
  AlertTriangle,
  TrendingUp,
  Clock,
  Users,
  CheckCircle2,
  XCircle,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  Activity,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface Stats {
  totalServices: number
  totalTables: number
  totalTests: number
  totalAlerts: number
  averageQualityScore: number
  testsPassRate: number
  freshTables: number
  staleTables: number
  totalTeams: number
  recentActivityCount: number
  recentTestResults: { date: string; passed: number; failed: number }[]
  failedTests: number
  totalDQTestResults: number
}

const defaultStats: Stats = {
  totalServices: 0,
  totalTables: 0,
  totalTests: 0,
  totalAlerts: 0,
  averageQualityScore: 0,
  testsPassRate: 0,
  freshTables: 0,
  staleTables: 0,
  totalTeams: 0,
  recentActivityCount: 0,
  recentTestResults: [],
  failedTests: 0,
  totalDQTestResults: 0,
}

function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  color,
}: {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ElementType
  trend?: 'up' | 'down'
  color?: string
}) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-sm text-slate-500">{title}</p>
            <p className="text-2xl font-bold text-slate-900">{value}</p>
            {subtitle && (
              <p className="text-xs text-slate-400 flex items-center gap-1">
                {trend === 'up' ? (
                  <ArrowUpRight className="h-3 w-3 text-emerald-500" />
                ) : trend === 'down' ? (
                  <ArrowDownRight className="h-3 w-3 text-red-500" />
                ) : null}
                {subtitle}
              </p>
            )}
          </div>
          <div className={`rounded-lg p-2.5 ${color || 'bg-slate-100'}`}>
            <Icon className="h-5 w-5 text-slate-600" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function TestResultsChart({ data }: { data: { date: string; passed: number; failed: number }[] }) {
  const [hoveredBar, setHoveredBar] = useState<number | null>(null)

  if (data.length === 0) return null

  // SVG dimensions
  const W = 700, H = 240
  const padL = 48, padR = 16, padT = 20, padB = 32
  const chartW = W - padL - padR
  const chartH = H - padT - padB

  const maxVal = Math.max(...data.map((d) => Math.max(d.passed, d.failed)), 1)
  const niceMax = Math.ceil(maxVal / 5) * 5 || 5
  const gridLines = 5
  const groupW = chartW / data.length
  const barW = Math.min(groupW * 0.3, 28)
  const barGap = Math.min(barW * 0.15, 4)

  const toY = (v: number) => padT + chartH - (v / niceMax) * chartH

  return (
    <div className="w-full">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" preserveAspectRatio="xMidYMid meet">
        {/* Y-axis grid lines and labels */}
        {Array.from({ length: gridLines + 1 }, (_, i) => {
          const val = Math.round((niceMax / gridLines) * i)
          const y = toY(val)
          return (
            <g key={`grid-${i}`}>
              <line
                x1={padL} y1={y} x2={W - padR} y2={y}
                stroke="#e2e8f0" strokeWidth="1"
                strokeDasharray={i === 0 ? '0' : '4,3'}
              />
              <text
                x={padL - 8} y={y}
                textAnchor="end" dominantBaseline="middle"
                fill="#94a3b8" fontSize="10"
              >
                {val}
              </text>
            </g>
          )
        })}

        {/* X-axis line */}
        <line x1={padL} y1={padT + chartH} x2={W - padR} y2={padT + chartH} stroke="#cbd5e1" strokeWidth="1.5" />

        {/* Bar groups */}
        {data.map((day, i) => {
          const cx = padL + (i + 0.5) * groupW  // center of group
          const pX = cx - barW - barGap / 2       // passed bar left x
          const fX = cx + barGap / 2               // failed bar left x
          const pH = (day.passed / niceMax) * chartH
          const fH = (day.failed / niceMax) * chartH
          const baseline = padT + chartH
          const isHovered = hoveredBar === i

          return (
            <g
              key={day.date}
              onMouseEnter={() => setHoveredBar(i)}
              onMouseLeave={() => setHoveredBar(null)}
              style={{ cursor: 'pointer' }}
            >
              {/* Hover highlight column */}
              {isHovered && (
                <rect
                  x={cx - groupW / 2} y={padT}
                  width={groupW} height={chartH}
                  fill="#f1f5f9" rx="4"
                />
              )}

              {/* Passed bar */}
              {day.passed > 0 && (
                <rect
                  x={pX} y={baseline - pH}
                  width={barW} height={pH}
                  fill={isHovered ? '#059669' : '#34d399'}
                  rx="3" ry="3"
                />
              )}

              {/* Failed bar */}
              {day.failed > 0 && (
                <rect
                  x={fX} y={baseline - fH}
                  width={barW} height={fH}
                  fill={isHovered ? '#dc2626' : '#f87171'}
                  rx="3" ry="3"
                />
              )}

              {/* Value labels on top of bars when hovered */}
              {isHovered && day.passed > 0 && (
                <text x={pX + barW / 2} y={baseline - pH - 6} textAnchor="middle" fontSize="10" fontWeight="600" fill="#059669">
                  {day.passed}
                </text>
              )}
              {isHovered && day.failed > 0 && (
                <text x={fX + barW / 2} y={baseline - fH - 6} textAnchor="middle" fontSize="10" fontWeight="600" fill="#dc2626">
                  {day.failed}
                </text>
              )}

              {/* Tooltip card */}
              {isHovered && (
                <g>
                  <rect
                    x={cx - 50} y={padT - 4}
                    width={100} height={50}
                    fill="white" stroke="#e2e8f0" strokeWidth="1"
                    rx="6" ry="6"
                  />
                  <text x={cx} y={padT + 12} textAnchor="middle" fontSize="10" fontWeight="600" fill="#334155">
                    {day.date.slice(5)}
                  </text>
                  <text x={cx} y={padT + 26} textAnchor="middle" fontSize="9" fill="#059669">
                    {day.passed} passed
                  </text>
                  <text x={cx} y={padT + 38} textAnchor="middle" fontSize="9" fill="#dc2626">
                    {day.failed} failed
                  </text>
                </g>
              )}

              {/* X-axis label */}
              <text x={cx} y={baseline + 18} textAnchor="middle" fontSize="9" fill="#94a3b8">
                {day.date.slice(5)}
              </text>
            </g>
          )
        })}
      </svg>

      {/* Summary row */}
      <div className="flex items-center justify-center gap-6 mt-1 text-xs text-slate-500">
        <span>Total: <strong className="text-slate-700">{data.reduce((s, d) => s + d.passed + d.failed, 0)}</strong></span>
        <span>Passed: <strong className="text-emerald-600">{data.reduce((s, d) => s + d.passed, 0)}</strong></span>
        <span>Failed: <strong className="text-red-500">{data.reduce((s, d) => s + d.failed, 0)}</strong></span>
        {(() => {
          const tp = data.reduce((s, d) => s + d.passed, 0)
          const ta = data.reduce((s, d) => s + d.passed + d.failed, 0)
          return <span>Pass Rate: <strong className="text-violet-600">{ta > 0 ? ((tp / ta) * 100).toFixed(1) : '0'}%</strong></span>
        })()}
      </div>
    </div>
  )
}

export default function Overview() {
  const [stats, setStats] = useState<Stats>(defaultStats)
  const [loading, setLoading] = useState(true)

  const safeFixed = (val: number | undefined | null, digits = 1) => (val ?? 0).toFixed(digits)

  useEffect(() => {
    fetch('/api/stats')
      .then((r) => r.json())
      .then((data) => {
        if (data && typeof data.totalServices !== 'undefined') {
          setStats({ ...defaultStats, ...data, recentTestResults: Array.isArray(data.recentTestResults) ? data.recentTestResults : [] })
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(8)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-5">
                <div className="space-y-2 animate-pulse">
                  <div className="h-3 w-24 rounded bg-slate-200" />
                  <div className="h-7 w-16 rounded bg-slate-200" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Stats grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Services"
          value={stats.totalServices}
          subtitle={`${stats.totalTables} tables total`}
          icon={Database}
          color="bg-blue-50"
        />
        <StatCard
          title="Quality Score"
          value={stats.totalTables > 0 ? `${safeFixed(stats.averageQualityScore)}%` : 'N/A'}
          subtitle={stats.totalTables > 0 ? 'Average across tables' : 'No tables yet'}
          icon={TrendingUp}
          trend={stats.totalTables > 0 ? 'up' : undefined}
          color="bg-emerald-50"
        />
        <StatCard
          title="Test Pass Rate"
          value={stats.totalDQTestResults > 0 ? `${safeFixed(stats.testsPassRate)}%` : 'N/A'}
          subtitle={stats.totalDQTestResults > 0 ? `${stats.totalTests} tests defined` : 'No test results yet'}
          icon={CheckCircle2}
          trend={stats.totalDQTestResults > 0 && stats.testsPassRate >= 90 ? 'up' : stats.totalDQTestResults > 0 ? 'down' : undefined}
          color="bg-violet-50"
        />
        <StatCard
          title="Active Alerts"
          value={stats.totalAlerts}
          subtitle="Requires attention"
          icon={AlertTriangle}
          trend={stats.totalAlerts > 5 ? 'down' : undefined}
          color="bg-amber-50"
        />
        <StatCard
          title="Fresh Tables"
          value={stats.freshTables}
          subtitle={`${stats.staleTables} stale`}
          icon={Clock}
          trend="up"
          color="bg-emerald-50"
        />
        <StatCard
          title="Failed Tests"
          value={stats.failedTests || 0}
          subtitle={`${stats.totalDQTestResults || 0} total test results`}
          icon={XCircle}
          trend={stats.failedTests > 0 ? 'down' : undefined}
          color="bg-red-50"
        />
        <StatCard
          title="Teams"
          value={stats.totalTeams}
          subtitle="Active collaborators"
          icon={Users}
          color="bg-sky-50"
        />
        <StatCard
          title="Recent Activity"
          value={stats.recentActivityCount}
          subtitle="Events in last 24h"
          icon={Activity}
          color="bg-orange-50"
        />
      </div>

      {/* Test Results Chart */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              Test Results (Last 14 Days)
            </CardTitle>
            {stats.recentTestResults.length > 0 && (
              <div className="flex items-center gap-4 text-xs text-slate-500">
                <span className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-sm bg-emerald-500" />
                  Passed
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-sm bg-red-400" />
                  Failed
                </span>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {stats.recentTestResults.length > 0 ? (
            <TestResultsChart data={stats.recentTestResults} />
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400">
              <BarChart3 className="h-10 w-10 mb-2 opacity-30" />
              <p className="text-sm">No test results in the last 14 days</p>
              <p className="text-xs mt-1">Run quality checks to see results here</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
