'use client'

import { useState } from 'react'
import {
  LayoutDashboard,
  Compass,
  Database,
  Table2,
  ShieldCheck,
  TestTubes,
  ListChecks,
  GitBranch,
  Scale,
  Tag,
  Settings,
  Activity,
  Bell,
  Users,
  ChevronDown,
  ChevronRight,
  Menu,
  Hexagon,
  Upload,
  Workflow,
  BarChart3,
  Wrench,
  Brain,
  FolderCheck,
  Plug,
  CalendarClock,
  MessageSquare,
  FlaskConical,
  FileCheck,
  TrendingUp,
  Code,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAppStore, type ViewType } from '@/lib/store'
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from '@/components/ui/sheet'
import { Progress } from '@/components/ui/progress'

interface SidebarProps {
  alertCount?: number
  overallScore?: number
}

interface NavItem {
  label: string
  view: ViewType
  icon: React.ReactNode
  badge?: number
}

interface NavCategory {
  id: string
  label: string
  icon: React.ReactNode
  items: NavItem[]
}

const categories: NavCategory[] = [
  {
    id: 'explore',
    label: 'Explore',
    icon: <Compass className="h-3.5 w-3.5" />,
    items: [
      { label: 'Services', view: 'services', icon: <Database className="h-4 w-4" /> },
      { label: 'Tables', view: 'tables', icon: <Table2 className="h-4 w-4" /> },
    ],
  },
  {
    id: 'data-quality',
    label: 'Data Quality',
    icon: <ShieldCheck className="h-3.5 w-3.5" />,
    items: [
      { label: 'Quality Tests', view: 'quality', icon: <TestTubes className="h-4 w-4" /> },
      { label: 'Checks', view: 'checks', icon: <ListChecks className="h-4 w-4" /> },
      { label: 'Auto-Fix', view: 'auto-fix', icon: <Wrench className="h-4 w-4" /> },
    ],
  },
  {
    id: 'data-prep',
    label: 'Data Prep',
    icon: <Workflow className="h-3.5 w-3.5" />,
    items: [
      { label: 'Pipeline Builder', view: 'pipeline', icon: <Workflow className="h-4 w-4" /> },
      { label: 'Auto-EDA', view: 'auto-eda', icon: <BarChart3 className="h-4 w-4" /> },
      { label: 'ML Readiness', view: 'ml-readiness', icon: <Brain className="h-4 w-4" /> },
      { label: 'Data Copilot', view: 'copilot', icon: <MessageSquare className="h-4 w-4" /> },
      { label: 'Fixed Datasets', view: 'fixed-datasets', icon: <FolderCheck className="h-4 w-4" /> },
    ],
  },
  {
    id: 'data-sources',
    label: 'Data Sources',
    icon: <Database className="h-3.5 w-3.5" />,
    items: [
      { label: 'Connectors', view: 'connectors', icon: <Plug className="h-4 w-4" /> },
      { label: 'Ingest Data', view: 'ingest', icon: <Upload className="h-4 w-4" /> },
    ],
  },
  {
    id: 'analytics',
    label: 'Analytics',
    icon: <BarChart3 className="h-3.5 w-3.5" />,
    items: [
      { label: 'Statistical Tests', view: 'statistical', icon: <FlaskConical className="h-4 w-4" /> },
      { label: 'Forecasting', view: 'forecasting', icon: <TrendingUp className="h-4 w-4" /> },
      { label: 'SQL Playground', view: 'sql-playground', icon: <Code className="h-4 w-4" /> },
    ],
  },
  {
    id: 'governance',
    label: 'Governance',
    icon: <Scale className="h-3.5 w-3.5" />,
    items: [
      { label: 'Data Contracts', view: 'contracts', icon: <FileCheck className="h-4 w-4" /> },
      { label: 'Tags & Glossary', view: 'governance', icon: <Tag className="h-4 w-4" /> },
      { label: 'Lineage', view: 'lineage', icon: <GitBranch className="h-4 w-4" /> },
    ],
  },
  {
    id: 'operations',
    label: 'Operations',
    icon: <Settings className="h-3.5 w-3.5" />,
    items: [
      { label: 'Scheduler', view: 'scheduler', icon: <CalendarClock className="h-4 w-4" /> },
      { label: 'Activity', view: 'activity', icon: <Activity className="h-4 w-4" /> },
      { label: 'Alerts', view: 'alerts', icon: <Bell className="h-4 w-4" />, badge: 0 },
      { label: 'Settings', view: 'settings', icon: <Users className="h-4 w-4" /> },
    ],
  },
]

function SidebarContent({
  alertCount = 0,
  overallScore = 0,
  onNavigate,
}: SidebarProps & { onNavigate?: () => void }) {
  const { currentView, setCurrentView } = useAppStore()
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})

  const toggleCategory = (id: string) => {
    setCollapsed((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  const handleNav = (view: ViewType) => {
    setCurrentView(view)
    onNavigate?.()
  }

  const isCategoryActive = (cat: NavCategory) =>
    cat.items.some((item) => item.view === currentView)

  const scoreColor =
    overallScore >= 90
      ? 'text-emerald-400'
      : overallScore >= 70
        ? 'text-amber-400'
        : 'text-red-400'

  const scoreBarColor =
    overallScore >= 90
      ? '[&>div]:bg-emerald-400'
      : overallScore >= 70
        ? '[&>div]:bg-amber-400'
        : '[&>div]:bg-red-400'

  return (
    <div className="flex h-full flex-col bg-slate-900 text-slate-200">
      <div className="flex items-center gap-3 px-4 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10">
          <Hexagon className="h-5 w-5 text-emerald-400" />
        </div>
        <div>
          <h1 className="text-base font-bold tracking-tight text-white">DataGuard</h1>
          <p className="text-[10px] text-slate-500">Data Intelligence Platform</p>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-2">
        <button
          onClick={() => handleNav('overview')}
          className={cn(
            'flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm transition',
            currentView === 'overview'
              ? 'bg-slate-800 text-white border-l-2 border-l-emerald-400'
              : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200 border-l-2 border-l-transparent'
          )}
        >
          <LayoutDashboard className="h-4 w-4 shrink-0" />
          <span>Overview</span>
        </button>

        {categories.map((cat) => (
          <div key={cat.id}>
            <div className="mt-4 mb-2 px-4">
              <button
                onClick={() => toggleCategory(cat.id)}
                className="flex w-full items-center gap-2 text-xs font-medium uppercase tracking-wider text-slate-500 hover:text-slate-400 transition"
              >
                <span className="flex items-center gap-2">
                  {cat.icon}
                  {cat.label}
                </span>
                <span className="ml-auto">
                  {collapsed[cat.id] ? (
                    <ChevronRight className="h-3 w-3" />
                  ) : (
                    <ChevronDown className="h-3 w-3" />
                  )}
                </span>
              </button>
            </div>

            {!collapsed[cat.id] && (
              <div className="space-y-0.5">
                {cat.items.map((item) => (
                  <button
                    key={`${cat.id}-${item.label}`}
                    onClick={() => handleNav(item.view)}
                    className={cn(
                      'flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm transition',
                      currentView === item.view
                        ? 'bg-slate-800 text-white border-l-2 border-l-emerald-400'
                        : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200 border-l-2 border-l-transparent'
                    )}
                  >
                    <span className="shrink-0">{item.icon}</span>
                    <span>{item.label}</span>
                    {item.view === 'alerts' && alertCount > 0 && (
                      <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1.5 text-[10px] font-semibold text-white">
                        {alertCount}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </nav>

      <div className="border-t border-slate-800 p-4">
        <div className="rounded-lg bg-slate-800/50 p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400">Overall Health</span>
            <span className={cn('text-sm font-bold', scoreColor)}>
              {(overallScore ?? 0).toFixed(1)}%
            </span>
          </div>
          <Progress value={overallScore} className={cn('h-1.5', scoreBarColor)} />
          <p className="mt-1.5 text-[10px] text-slate-500">
            {overallScore >= 90
              ? 'All systems operational'
              : overallScore >= 70
                ? 'Minor issues detected'
                : 'Requires attention'}
          </p>
        </div>
      </div>
    </div>
  )
}

export function Sidebar({ alertCount, overallScore }: SidebarProps) {
  return (
    <>
      <aside className="hidden lg:flex h-screen w-60 shrink-0 flex-col fixed left-0 top-0 z-30">
        <SidebarContent alertCount={alertCount} overallScore={overallScore} />
      </aside>

      <div className="lg:hidden fixed top-0 left-0 z-40 p-3">
        <MobileSidebar alertCount={alertCount} overallScore={overallScore} />
      </div>
    </>
  )
}

function MobileSidebar({ alertCount, overallScore }: SidebarProps) {
  const [open, setOpen] = useState(false)

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <button className="flex h-9 w-9 items-center justify-center rounded-md bg-slate-900 text-slate-200 shadow-md">
          <Menu className="h-5 w-5" />
        </button>
      </SheetTrigger>
      <SheetContent side="left" className="w-60 p-0 bg-slate-900 text-slate-200 border-r-slate-800">
        <SheetTitle className="sr-only">Navigation</SheetTitle>
        <SidebarContent
          alertCount={alertCount}
          overallScore={overallScore}
          onNavigate={() => setOpen(false)}
        />
      </SheetContent>
    </Sheet>
  )
}
