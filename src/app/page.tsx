'use client'

import { useEffect, useState } from 'react'
import {
  LayoutDashboard,
  Database,
  ShieldCheck,
  Bell,
  Settings,
  Loader2,
  Search,
  Upload,
  Workflow,
  BarChart3,
  Wrench,
  Brain,
  Plug,
  CalendarClock,
  MessageSquare,

  TrendingUp,
  Code,
  ListChecks,
  CheckCircle2,
} from 'lucide-react'
import { useAppStore, type ViewType } from '@/lib/store'
import { Sidebar } from '@/components/dq/sidebar'
import { Input } from '@/components/ui/input'
import React, { Suspense } from 'react'

const Overview = React.lazy(() => import('@/components/dq/overview'))
const Services = React.lazy(() => import('@/components/dq/services'))
const Tables = React.lazy(() => import('@/components/dq/tables'))
const Ingest = React.lazy(() => import('@/components/dq/ingest'))
const Quality = React.lazy(() => import('@/components/dq/quality'))
const ActivityView = React.lazy(() => import('@/components/dq/activity'))
const Alerts = React.lazy(() => import('@/components/dq/alerts'))
const SettingsView = React.lazy(() => import('@/components/dq/settings'))
const PipelineBuilder = React.lazy(() => import('@/components/dq/pipeline-builder'))
const AutoEDA = React.lazy(() => import('@/components/dq/auto-eda'))
const AutoFix = React.lazy(() => import('@/components/dq/auto-fix'))
const MLReadiness = React.lazy(() => import('@/components/dq/ml-readiness'))
const Connectors = React.lazy(() => import('@/components/dq/connectors'))
const Scheduler = React.lazy(() => import('@/components/dq/scheduler'))
const Copilot = React.lazy(() => import('@/components/dq/copilot'))
const Forecasting = React.lazy(() => import('@/components/dq/forecasting'))
const SQLPlayground = React.lazy(() => import('@/components/dq/sql-playground'))
const Checks = React.lazy(() => import('@/components/dq/checks'))
const FixedDatasets = React.lazy(() => import('@/components/dq/fixed-datasets'))

const viewConfig: Record<ViewType, { label: string; icon: React.ReactNode }> = {
  overview: { label: 'Overview', icon: <LayoutDashboard className="h-4 w-4" /> },
  services: { label: 'Services', icon: <Database className="h-4 w-4" /> },
  tables: { label: 'Explore Tables', icon: <Database className="h-4 w-4" /> },
  ingest: { label: 'Ingest Data', icon: <Upload className="h-4 w-4" /> },
  quality: { label: 'Data Quality', icon: <ShieldCheck className="h-4 w-4" /> },
  activity: { label: 'Activity Feed', icon: <Settings className="h-4 w-4" /> },
  alerts: { label: 'Alerts', icon: <Bell className="h-4 w-4" /> },
  settings: { label: 'Local Setup', icon: <Wrench className="h-4 w-4" /> },
  checks: { label: 'Quality Checks', icon: <ListChecks className="h-4 w-4" /> },
  pipeline: { label: 'Pipeline Builder', icon: <Workflow className="h-4 w-4" /> },
  'auto-eda': { label: 'Auto-EDA Report', icon: <BarChart3 className="h-4 w-4" /> },
  'ml-readiness': { label: 'ML Readiness', icon: <Brain className="h-4 w-4" /> },
  connectors: { label: 'Data Connectors', icon: <Plug className="h-4 w-4" /> },
  scheduler: { label: 'Job Scheduler', icon: <CalendarClock className="h-4 w-4" /> },
  copilot: { label: 'AI Data Copilot', icon: <MessageSquare className="h-4 w-4" /> },
  forecasting: { label: 'Quality Forecasting', icon: <TrendingUp className="h-4 w-4" /> },
  'sql-playground': { label: 'SQL Playground', icon: <Code className="h-4 w-4" /> },
  'auto-fix': { label: 'Auto-Fix Approval', icon: <Wrench className="h-4 w-4" /> },
  'fixed-datasets': { label: 'Fixed Datasets', icon: <CheckCircle2 className="h-4 w-4" /> },
}

function ViewRenderer({ view }: { view: ViewType }) {
  switch (view) {
    case 'overview':
      return <Overview />
    case 'services':
      return <Services />
    case 'tables':
      return <Tables />
    case 'ingest':
      return <Ingest />
    case 'quality':
      return <Quality />
    case 'checks':
      return <Checks />
    case 'activity':
      return <ActivityView />
    case 'alerts':
      return <Alerts />
    case 'settings':
      return <SettingsView />
    case 'pipeline':
      return <PipelineBuilder />
    case 'auto-eda':
      return <AutoEDA />
    case 'ml-readiness':
      return <MLReadiness />
    case 'connectors':
      return <Connectors />
    case 'scheduler':
      return <Scheduler />
    case 'copilot':
      return <Copilot />
    case 'forecasting':
      return <Forecasting />
    case 'sql-playground':
      return <SQLPlayground />
    case 'auto-fix':
      return <AutoFix />
    case 'fixed-datasets':
      return <FixedDatasets />
    default:
      return <Overview />
  }
}

function LoadingFallback() {
  return (
    <div className="flex h-64 items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
    </div>
  )
}

export default function HomePage() {
  const { currentView } = useAppStore()
  const [alertCount, setAlertCount] = useState(4)
  const [overallScore, setOverallScore] = useState(91.7)
  const [searchQuery, setSearchQuery] = useState('')

  const config = viewConfig[currentView]

  useEffect(() => {
    async function fetchStats() {
      try {
        const res = await fetch('/api/stats')
        if (res.ok) {
          const data = await res.json()
          if (data.totalAlerts != null) setAlertCount(data.totalAlerts)
          if (data.averageQualityScore != null) setOverallScore(data.averageQualityScore)
        }
      } catch {
        // keep defaults
      }
    }
    fetchStats()
  }, [])

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar alertCount={alertCount} overallScore={overallScore} />

      <main className="flex-1 lg:ml-60 flex flex-col overflow-hidden">
        <header className="flex items-center gap-4 border-b bg-white px-6 py-3 shadow-sm lg:px-8">
          <div className="w-12 lg:hidden" />
          <nav className="flex items-center gap-2 text-sm text-slate-500">
            <span className="flex items-center gap-1.5 text-slate-900 font-semibold">
              {config.icon}
              {config.label}
            </span>
          </nav>
          <div className="ml-auto">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input
                placeholder="Search tables, services, glossary..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-64 pl-9 h-9 text-sm"
              />
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto bg-gray-50 p-4 md:p-6 lg:p-8">
          <Suspense fallback={<LoadingFallback />}>
            <ViewRenderer view={currentView} />
          </Suspense>
        </div>
      </main>
    </div>
  )
}
