'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { TrendingUp, BarChart3, Calendar, ArrowUpRight, ArrowDownRight, Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { toast } from 'sonner'

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

interface ForecastItem {
  metric: string
  current: number
  forecast: number
  trend: 'up' | 'down'
  horizon: string
}

// No mock data — all data comes from the Python backend

export default function ForecastingView() {
  const [forecasts, setForecasts] = useState<ForecastItem[]>([])
  const [forecastError, setForecastError] = useState<string | null>(null)
  const [selectedTable, setSelectedTable] = useState('')
  const [tables, setTables] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)

  const fetchTables = useCallback(async () => {
    try {
      const res = await fetch('/api/tables')
      if (res.ok) {
        const data = await res.json()
        const tableList = Array.isArray(data) ? data.map((t: { name?: string; tableName?: string }) => t.name || t.tableName || '').filter(Boolean) : []
        setTables(tableList)
        if (tableList.length > 0) setSelectedTable(tableList[0])
      } else {
        setTables([])
        setForecastError('Failed to load tables from backend')
      }
    } catch {
      setTables([])
      setForecastError('Backend unavailable — please ensure the Python backend is running on port 3001')
    } finally {
      setInitialLoading(false)
    }
  }, [])

  useEffect(() => { fetchTables() }, [fetchTables])

  const fetchForecast = useCallback(async () => {
    if (!selectedTable) return
    setLoading(true)
    try {
      const res = await fetch(`/api/forecast/${encodeURIComponent(selectedTable)}`)
      if (res.ok) {
        const data = await res.json()
        const items: ForecastItem[] = Array.isArray(data) ? data : data?.forecasts || data?.results || []
        setForecasts(items)
        setForecastError(items.length === 0 ? 'No forecast data available for this table. Run quality checks first to generate historical data.' : null)
        if (items.length > 0) toast.success('Forecast loaded')
      } else {
        setForecasts([])
        setForecastError('Failed to load forecast from backend')
      }
    } catch {
      setForecasts([])
      setForecastError('Backend unavailable — please ensure the Python backend is running on port 3001')
    } finally {
      setLoading(false)
    }
  }, [selectedTable])

  useEffect(() => {
    if (selectedTable) fetchForecast()
  }, [selectedTable, fetchForecast])

  if (initialLoading) {
    return (
      <div className="space-y-6 p-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="h-8 w-64 bg-slate-200 rounded animate-pulse" />
            <div className="h-4 w-96 bg-slate-100 rounded animate-pulse mt-2" />
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-36 bg-slate-100 rounded-xl animate-pulse" />
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
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold">Quality Forecasting</h1>
          <p className="text-sm text-muted-foreground">
            Predict future data quality scores and identify potential issues before they occur
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={selectedTable} onValueChange={setSelectedTable}>
            <SelectTrigger className="w-48"><SelectValue placeholder="Select table" /></SelectTrigger>
            <SelectContent>
              {tables.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
            </SelectContent>
          </Select>
          <Button onClick={fetchForecast} disabled={loading} className="gap-2">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <TrendingUp className="h-4 w-4" />}
            Refresh
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center h-48 gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
          <p className="text-sm text-slate-500">Loading forecast data...</p>
        </div>
      ) : forecastError ? (
        <Card className="border-amber-200 bg-amber-50/50">
          <CardContent className="p-6 text-center">
            <TrendingUp className="h-10 w-10 text-amber-400 mx-auto mb-3" />
            <p className="text-sm text-amber-700 font-medium">{forecastError}</p>
          </CardContent>
        </Card>
      ) : forecasts.length === 0 ? (
        <Card>
          <CardContent className="p-6 text-center">
            <TrendingUp className="h-10 w-10 text-slate-300 mx-auto mb-3" />
            <p className="text-sm text-slate-500">No forecast data yet. Select a table and click Refresh to load forecasts.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {forecasts.map((f) => (
            <motion.div key={f.metric} variants={fadeInUp}>
              <Card className="shadow-sm">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      {f.metric}
                    </CardTitle>
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Calendar className="h-3 w-3" />
                      {f.horizon}
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex items-end justify-between">
                    <div>
                      <p className="text-2xl font-bold">{f.current}%</p>
                      <p className="text-xs text-muted-foreground">Current</p>
                    </div>
                    <div className="text-right">
                      <div className={`flex items-center gap-1 text-sm font-semibold ${f.trend === 'up' ? 'text-emerald-600' : 'text-red-600'}`}>
                        {f.trend === 'up' ? (
                          <ArrowUpRight className="h-4 w-4" />
                        ) : (
                          <ArrowDownRight className="h-4 w-4" />
                        )}
                        {f.forecast}%
                      </div>
                      <p className="text-xs text-muted-foreground">Forecast</p>
                    </div>
                  </div>
                  <div className="mt-3 h-1.5 rounded-full bg-slate-100">
                    <div
                      className={`h-1.5 rounded-full ${f.trend === 'up' ? 'bg-emerald-500' : 'bg-red-400'}`}
                      style={{ width: `${f.forecast}%` }}
                    />
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}

      <motion.div variants={fadeInUp}>
        <Card className="shadow-sm">
          <CardHeader>
            <div className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-muted-foreground" />
              <div>
                <CardTitle className="text-base">Trend Analysis</CardTitle>
                <CardDescription>Historical quality scores with forecast projection</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-center h-64 text-muted-foreground">
              <div className="text-center">
                <TrendingUp className="h-12 w-12 mx-auto mb-3 opacity-30" />
                <p className="text-sm">Forecasting chart will be displayed here</p>
                <p className="text-xs mt-1">Connect to a data source to see trend projections</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  )
}
