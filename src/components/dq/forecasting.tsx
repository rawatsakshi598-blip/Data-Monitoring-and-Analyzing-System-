'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  TrendingUp, BarChart3, Calendar, ArrowUpRight, ArrowDownRight,
  Loader2, AlertTriangle, Activity, Shield, Info
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'

interface TableOption {
  id: string
  name: string
}

interface ForecastData {
  success: boolean
  trend: string
  current_score: number
  predicted_score_7d: number
  predicted_change: number
  will_degrade: boolean
  degradation_risk: string
  method: string
  tableId: string
  tableName: string
  historical: { date: string; score: number }[]
  forecasts: {
    exponential_smoothing: { date: string; predicted_score: number }[]
    linear_trend: { date: string; predicted_score: number }[]
  }
  note?: string
  error?: string
}

export default function ForecastingView() {
  const [forecastData, setForecastData] = useState<ForecastData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selectedTable, setSelectedTable] = useState('')
  const [tables, setTables] = useState<TableOption[]>([])
  const [loading, setLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)

  const fetchTables = useCallback(async () => {
    try {
      const res = await fetch('/api/tables')
      if (res.ok) {
        const data = await res.json()
        const tableList = Array.isArray(data)
          ? data.map((t: { id?: string; name?: string }) => ({
              id: t.id || '',
              name: t.name || '',
            })).filter((t: TableOption) => t.id && t.name)
          : []
        setTables(tableList)
        if (tableList.length > 0) setSelectedTable(tableList[0].id)
      } else {
        setError('Failed to load tables from backend')
      }
    } catch {
      setError('Backend unavailable — ensure Python backend is running on port 3001')
    } finally {
      setInitialLoading(false)
    }
  }, [])

  useEffect(() => { fetchTables() }, [fetchTables])

  const fetchForecast = useCallback(async () => {
    if (!selectedTable) return
    setLoading(true)
    setError(null)
    setForecastData(null)
    try {
      const res = await fetch(`/api/forecast/${encodeURIComponent(selectedTable)}?periods=7`)
      if (res.ok) {
        const data = await res.json()
        if (data.error) {
          setError(data.error)
        } else {
          setForecastData(data)
        }
      } else {
        setError('Failed to load forecast from backend')
      }
    } catch {
      setError('Backend unavailable — ensure Python backend is running on port 3001')
    } finally {
      setLoading(false)
    }
  }, [selectedTable])

  useEffect(() => {
    if (selectedTable) fetchForecast()
  }, [selectedTable, fetchForecast])

  const selectedTableName = tables.find(t => t.id === selectedTable)?.name || selectedTable

  if (initialLoading) {
    return (
      <div className="space-y-6 p-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="h-8 w-64 bg-slate-200 rounded animate-pulse" />
            <div className="h-4 w-96 bg-slate-100 rounded animate-pulse mt-2" />
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 bg-slate-100 rounded-xl animate-pulse" />
          ))}
        </div>
        <div className="h-64 bg-slate-100 rounded-xl animate-pulse" />
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Quality Forecasting</h1>
          <p className="text-sm text-slate-500">
            Predict future data quality scores and identify potential issues before they occur
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={selectedTable} onValueChange={setSelectedTable}>
            <SelectTrigger className="w-56">
              <SelectValue placeholder="Select table" />
            </SelectTrigger>
            <SelectContent>
              {tables.map((t) => (
                <SelectItem key={t.id} value={t.id}>
                  {t.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={fetchForecast} disabled={loading || !selectedTable} variant="outline" className="gap-2">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Activity className="h-4 w-4" />}
            Refresh
          </Button>
        </div>
      </div>

      {/* Error State */}
      {error && !loading && (
        <Card className="border-amber-200 bg-amber-50/50">
          <CardContent className="p-5 flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-500 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm text-amber-800 font-medium">{error}</p>
              <p className="text-xs text-amber-600 mt-1">Make sure the backend is running and quality checks have been executed.</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Loading Spinner */}
      {loading && (
        <div className="flex flex-col items-center justify-center h-48 gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
          <p className="text-sm text-slate-500">Analyzing quality trends...</p>
        </div>
      )}

      {/* Forecast Results */}
      {forecastData && !loading && (
        <>
          {/* Profile estimate notice */}
          {forecastData.note && (
            <Card className="border-blue-200 bg-blue-50/50">
              <CardContent className="p-4 flex items-start gap-3">
                <Info className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" />
                <p className="text-xs text-blue-700">{forecastData.note}</p>
              </CardContent>
            </Card>
          )}

          {/* Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              title="Current Score"
              value={`${forecastData.current_score.toFixed(1)}%`}
              icon={Shield}
              color="bg-blue-50"
              iconColor="text-blue-600"
            />
            <MetricCard
              title="7-Day Forecast"
              value={`${forecastData.predicted_score_7d.toFixed(1)}%`}
              icon={TrendingUp}
              color={forecastData.will_degrade ? 'bg-red-50' : 'bg-emerald-50'}
              iconColor={forecastData.will_degrade ? 'text-red-500' : 'text-emerald-600'}
              trend={forecastData.predicted_change > 0 ? 'up' : forecastData.predicted_change < 0 ? 'down' : undefined}
              trendValue={`${forecastData.predicted_change > 0 ? '+' : ''}${forecastData.predicted_change.toFixed(1)}%`}
            />
            <MetricCard
              title="Trend Direction"
              value={forecastData.trend.charAt(0).toUpperCase() + forecastData.trend.slice(1)}
              icon={forecastData.trend === 'improving' ? ArrowUpRight : forecastData.trend === 'degrading' ? ArrowDownRight : Activity}
              color={forecastData.trend === 'improving' ? 'bg-emerald-50' : forecastData.trend === 'degrading' ? 'bg-red-50' : 'bg-slate-50'}
              iconColor={forecastData.trend === 'improving' ? 'text-emerald-600' : forecastData.trend === 'degrading' ? 'text-red-500' : 'text-slate-500'}
            />
            <MetricCard
              title="Degradation Risk"
              value={forecastData.degradation_risk.charAt(0).toUpperCase() + forecastData.degradation_risk.slice(1)}
              icon={AlertTriangle}
              color={
                forecastData.degradation_risk === 'critical' ? 'bg-red-50' :
                forecastData.degradation_risk === 'high' ? 'bg-orange-50' :
                forecastData.degradation_risk === 'medium' ? 'bg-amber-50' : 'bg-emerald-50'
              }
              iconColor={
                forecastData.degradation_risk === 'critical' ? 'text-red-600' :
                forecastData.degradation_risk === 'high' ? 'text-orange-500' :
                forecastData.degradation_risk === 'medium' ? 'text-amber-500' : 'text-emerald-600'
              }
            />
          </div>

          {/* Trend Analysis Chart */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5 text-slate-500" />
                  <div>
                    <CardTitle className="text-base">Trend Analysis</CardTitle>
                    <CardDescription>Historical quality scores with forecast projection for {selectedTableName}</CardDescription>
                  </div>
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-500">
                  <span className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-sm bg-blue-500" />
                    Historical
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-sm bg-emerald-500" />
                    Exp. Smoothing
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-sm bg-violet-400" />
                    Linear Trend
                  </span>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <ForecastChart data={forecastData} />
            </CardContent>
          </Card>

          {/* Method Badge */}
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Calendar className="h-3 w-3" />
            <span>Method: <Badge variant="outline" className="text-[10px] px-1.5 py-0">{forecastData.method === 'quality_checks' ? 'Quality Check History' : 'Profile Estimation'}</Badge></span>
          </div>
        </>
      )}

      {/* No data yet */}
      {!forecastData && !loading && !error && tables.length === 0 && (
        <Card>
          <CardContent className="p-8 text-center">
            <TrendingUp className="h-12 w-12 mx-auto mb-3 text-slate-300" />
            <p className="text-sm text-slate-500">No tables found. Ingest data first to see forecasts.</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function MetricCard({
  title, value, icon: Icon, color, iconColor, trend, trendValue
}: {
  title: string
  value: string
  icon: React.ElementType
  color: string
  iconColor: string
  trend?: 'up' | 'down'
  trendValue?: string
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-xs text-slate-500">{title}</p>
            <p className="text-xl font-bold text-slate-900">{value}</p>
            {trendValue && (
              <p className={`text-xs flex items-center gap-1 ${trend === 'up' ? 'text-emerald-600' : trend === 'down' ? 'text-red-500' : 'text-slate-400'}`}>
                {trend === 'up' ? <ArrowUpRight className="h-3 w-3" /> : trend === 'down' ? <ArrowDownRight className="h-3 w-3" /> : null}
                {trendValue}
              </p>
            )}
          </div>
          <div className={`rounded-lg p-2 ${color}`}>
            <Icon className={`h-4 w-4 ${iconColor}`} />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function ForecastChart({ data }: { data: ForecastData }) {
  const [hoveredPoint, setHoveredPoint] = useState<{ x: number; y: number; label: string; value: string } | null>(null)

  const historical = data.historical || []
  const esForecast = data.forecasts?.exponential_smoothing || []
  const ltForecast = data.forecasts?.linear_trend || []

  if (historical.length === 0 && esForecast.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        <div className="text-center">
          <BarChart3 className="h-10 w-10 mx-auto mb-2 opacity-30" />
          <p className="text-sm">No data available for chart</p>
        </div>
      </div>
    )
  }

  // Combine all dates for the x-axis
  const allDates: string[] = [
    ...historical.map(h => h.date),
    ...esForecast.map(f => f.date),
  ]
  const uniqueDates = [...new Set(allDates)]

  // Compute y range
  const allScores = [
    ...historical.map(h => h.score),
    ...esForecast.map(f => f.predicted_score),
    ...ltForecast.map(f => f.predicted_score),
  ].filter(s => s != null && !isNaN(s))
  const yMin = Math.floor(Math.min(...allScores) / 5) * 5 - 5
  const yMax = Math.ceil(Math.max(...allScores) / 5) * 5 + 5
  const yRange = yMax - yMin || 10

  // SVG layout
  const W = 800, H = 280
  const padL = 52, padR = 20, padT = 16, padB = 36
  const chartW = W - padL - padR
  const chartH = H - padT - padB

  const toX = (i: number) => padL + (i / Math.max(uniqueDates.length - 1, 1)) * chartW
  const toY = (v: number) => padT + chartH - ((v - yMin) / yRange) * chartH

  // Find the boundary between historical and forecast
  const histEndIdx = historical.length - 1
  const forecastStartIdx = historical.length > 0 ? historical.length : 0

  // Build SVG path for a series
  const buildPath = (points: { date: string; value: number }[]) => {
    return points.map((p, i) => {
      const idx = uniqueDates.indexOf(p.date)
      if (idx < 0) return ''
      return `${i === 0 ? 'M' : 'L'}${toX(idx).toFixed(1)},${toY(p.value).toFixed(1)}`
    }).join(' ')
  }

  const histPoints = historical.map(h => ({ date: h.date, value: h.score }))
  const esPoints = esForecast.map(f => ({ date: f.date, value: f.predicted_score }))
  const ltPoints = ltForecast.map(f => ({ date: f.date, value: f.predicted_score }))

  // Connect historical last point to forecast first point
  const connectorEs = historical.length > 0 && esForecast.length > 0
    ? `M${toX(histEndIdx).toFixed(1)},${toY(historical[historical.length - 1].score).toFixed(1)}L${toX(uniqueDates.indexOf(esForecast[0].date)).toFixed(1)},${toY(esForecast[0].predicted_score).toFixed(1)}`
    : ''
  const connectorLt = historical.length > 0 && ltForecast.length > 0
    ? `M${toX(histEndIdx).toFixed(1)},${toY(historical[historical.length - 1].score).toFixed(1)}L${toX(uniqueDates.indexOf(ltForecast[0].date)).toFixed(1)},${toY(ltForecast[0].predicted_score).toFixed(1)}`
    : ''

  const gridLines = 5

  return (
    <div className="w-full relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" preserveAspectRatio="xMidYMid meet">
        {/* Grid lines and Y-axis labels */}
        {Array.from({ length: gridLines + 1 }, (_, i) => {
          const val = yMin + (yRange / gridLines) * i
          const y = toY(val)
          return (
            <g key={`grid-${i}`}>
              <line x1={padL} y1={y} x2={W - padR} y2={y} stroke="#e2e8f0" strokeWidth="1" strokeDasharray="4,3" />
              <text x={padL - 8} y={y} textAnchor="end" dominantBaseline="middle" fill="#94a3b8" fontSize="10">
                {Math.round(val)}
              </text>
            </g>
          )
        })}

        {/* X-axis baseline */}
        <line x1={padL} y1={padT + chartH} x2={W - padR} y2={padT + chartH} stroke="#cbd5e1" strokeWidth="1" />

        {/* Forecast zone background */}
        {forecastStartIdx < uniqueDates.length && (
          <rect
            x={toX(forecastStartIdx)} y={padT}
            width={toX(uniqueDates.length - 1) - toX(forecastStartIdx)}
            height={chartH}
            fill="#f0fdf4" opacity="0.6"
          />
        )}

        {/* Historical area fill */}
        {histPoints.length >= 2 && (
          <path
            d={`${buildPath(histPoints)} L${toX(histEndIdx).toFixed(1)},${(padT + chartH).toFixed(1)} L${toX(0).toFixed(1)},${(padT + chartH).toFixed(1)} Z`}
            fill="rgba(59,130,246,0.08)"
          />
        )}

        {/* Historical line */}
        {histPoints.length >= 2 && (
          <path d={buildPath(histPoints)} fill="none" stroke="#3b82f6" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        )}

        {/* Connector to ES forecast */}
        {connectorEs && <path d={connectorEs} fill="none" stroke="#10b981" strokeWidth="1.5" strokeDasharray="6,3" />}

        {/* ES Forecast line */}
        {esPoints.length >= 2 && (
          <path d={buildPath(esPoints)} fill="none" stroke="#10b981" strokeWidth="2" strokeDasharray="6,3" strokeLinecap="round" strokeLinejoin="round" />
        )}

        {/* Connector to LT forecast */}
        {connectorLt && <path d={connectorLt} fill="none" stroke="#8b5cf6" strokeWidth="1.5" strokeDasharray="4,4" />}

        {/* LT Forecast line */}
        {ltPoints.length >= 2 && (
          <path d={buildPath(ltPoints)} fill="none" stroke="#8b5cf6" strokeWidth="2" strokeDasharray="4,4" strokeLinecap="round" strokeLinejoin="round" />
        )}

        {/* Historical data points */}
        {histPoints.map((p, i) => {
          const idx = uniqueDates.indexOf(p.date)
          return (
            <circle
              key={`h-${i}`}
              cx={toX(idx)} cy={toY(p.value)} r="4"
              fill="white" stroke="#3b82f6" strokeWidth="2"
              className="cursor-pointer"
              onMouseEnter={(e) => setHoveredPoint({ x: toX(idx), y: toY(p.value), label: p.date, value: `Score: ${p.value.toFixed(1)}%` })}
              onMouseLeave={() => setHoveredPoint(null)}
            />
          )
        })}

        {/* ES forecast data points */}
        {esPoints.map((p, i) => {
          const idx = uniqueDates.indexOf(p.date)
          return (
            <circle
              key={`es-${i}`}
              cx={toX(idx)} cy={toY(p.value)} r="3.5"
              fill="white" stroke="#10b981" strokeWidth="2"
              className="cursor-pointer"
              onMouseEnter={(e) => setHoveredPoint({ x: toX(idx), y: toY(p.value), label: p.date, value: `Forecast: ${p.value.toFixed(1)}%` })}
              onMouseLeave={() => setHoveredPoint(null)}
            />
          )
        })}

        {/* LT forecast data points */}
        {ltPoints.map((p, i) => {
          const idx = uniqueDates.indexOf(p.date)
          return (
            <circle
              key={`lt-${i}`}
              cx={toX(idx)} cy={toY(p.value)} r="3"
              fill="white" stroke="#8b5cf6" strokeWidth="1.5"
              className="cursor-pointer"
              onMouseEnter={(e) => setHoveredPoint({ x: toX(idx), y: toY(p.value), label: p.date, value: `Linear: ${p.value.toFixed(1)}%` })}
              onMouseLeave={() => setHoveredPoint(null)}
            />
          )
        })}

        {/* X-axis labels */}
        {uniqueDates.map((date, i) => {
          // Show every Nth label to avoid overlap
          const step = Math.max(1, Math.floor(uniqueDates.length / 10))
          if (i % step !== 0 && i !== uniqueDates.length - 1) return null
          return (
            <text key={`x-${i}`} x={toX(i)} y={padT + chartH + 20} textAnchor="middle" fontSize="9" fill="#94a3b8">
              {date.slice(5)}
            </text>
          )
        })}

        {/* Forecast zone label */}
        {forecastStartIdx < uniqueDates.length && (
          <text
            x={(toX(forecastStartIdx) + toX(uniqueDates.length - 1)) / 2}
            y={padT + 12}
            textAnchor="middle"
            fontSize="9"
            fill="#10b981"
            fontWeight="500"
          >
            Forecast
          </text>
        )}

        {/* Hover tooltip */}
        {hoveredPoint && (
          <g>
            <rect
              x={hoveredPoint.x - 55} y={hoveredPoint.y - 38}
              width={110} height={32}
              fill="white" stroke="#e2e8f0" strokeWidth="1"
              rx="6" ry="6"
            />
            <text x={hoveredPoint.x} y={hoveredPoint.y - 22} textAnchor="middle" fontSize="9" fontWeight="600" fill="#334155">
              {hoveredPoint.label.slice(5)}
            </text>
            <text x={hoveredPoint.x} y={hoveredPoint.y - 11} textAnchor="middle" fontSize="8" fill="#64748b">
              {hoveredPoint.value}
            </text>
          </g>
        )}
      </svg>
    </div>
  )
}