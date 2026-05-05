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
          value={`${safeFixed(stats.averageQualityScore)}%`}
          subtitle="Average across tables"
          icon={TrendingUp}
          trend="up"
          color="bg-emerald-50"
        />
        <StatCard
          title="Test Pass Rate"
          value={`${safeFixed(stats.testsPassRate)}%`}
          subtitle={`${stats.totalTests} tests defined`}
          icon={CheckCircle2}
          trend={stats.testsPassRate >= 90 ? 'up' : 'down'}
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
          value={stats.totalTests - Math.round((stats.totalTests * stats.testsPassRate) / 100)}
          subtitle="Last 24 hours"
          icon={XCircle}
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
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            Test Results (Last 14 Days)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {stats.recentTestResults.length > 0 ? (
            <div className="flex items-end gap-1 h-40">
              {stats.recentTestResults.map((day) => {
                const maxVal = Math.max(
                  ...stats.recentTestResults.map((d) => d.passed + d.failed),
                  1
                )
                const total = day.passed + day.failed
                const passHeight = total > 0 ? (day.passed / maxVal) * 100 : 0
                const failHeight = total > 0 ? (day.failed / maxVal) * 100 : 0
                return (
                  <div
                    key={day.date}
                    className="flex-1 flex flex-col items-center gap-0.5"
                    title={`${day.date}: ${day.passed} passed, ${day.failed} failed`}
                  >
                    <div className="w-full flex flex-col gap-0.5" style={{ height: '140px' }}>
                      <div className="mt-auto flex flex-col gap-0.5" style={{ height: '100%' }}>
                        <div
                          className="w-full rounded-t bg-emerald-400 transition-all"
                          style={{ height: `${passHeight}%` }}
                        />
                        <div
                          className="w-full rounded-b bg-red-400 transition-all"
                          style={{ height: `${failHeight}%` }}
                        />
                      </div>
                    </div>
                    <span className="text-[9px] text-slate-400 mt-1">
                      {day.date.slice(5)}
                    </span>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="text-sm text-slate-400 text-center py-8">
              No test results in the last 14 days
            </p>
          )}
          <div className="flex items-center gap-4 mt-4 text-xs text-slate-500">
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm bg-emerald-400" />
              Passed
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm bg-red-400" />
              Failed
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
