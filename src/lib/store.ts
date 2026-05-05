import { create } from 'zustand'

export type ViewType =
  | 'overview'
  | 'services'
  | 'tables'
  | 'ingest'
  | 'quality'
  | 'checks'
  | 'lineage'
  | 'governance'
  | 'activity'
  | 'alerts'
  | 'settings'
  | 'pipeline'
  | 'auto-eda'
  | 'auto-fix'
  | 'ml-readiness'
  | 'connectors'
  | 'scheduler'
  | 'copilot'
  | 'statistical'
  | 'contracts'
  | 'forecasting'
  | 'sql-playground'
  | 'fixed-datasets'

interface AppState {
  currentView: ViewType
  sidebarOpen: boolean
  setCurrentView: (view: ViewType) => void
  setSidebarOpen: (open: boolean) => void
}

export const useAppStore = create<AppState>((set) => ({
  currentView: 'overview',
  sidebarOpen: true,
  setCurrentView: (view) => set({ currentView: view }),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}))

// ── Shared Types ──

export interface Dataset {
  id: string
  name: string
  description: string | null
  type: string
  connectionInfo: string | null
  status: string
  rowCount: number
  columnCount: number
  qualityScore: number | null
  lastChecked: string | null
  createdAt: string
  updatedAt: string
}

export interface QualityRule {
  id: string
  name: string
  description: string | null
  type: string
  dimension: string
  severity: string
  config: string
  enabled: boolean
  schedule: string | null
  lastTriggered: string | null
  datasetId: string | null
  createdAt: string
  updatedAt: string
}

export interface QualityCheck {
  id: string
  ruleId: string
  datasetId: string
  status: string
  score: number | null
  recordsChecked: number
  recordsFailed: number
  duration: number
  failures: string
  createdAt: string
  ruleName?: string
  datasetName?: string
}

export interface Alert {
  id: string
  title: string
  message: string
  severity: string
  alertType: string
  source: string | null
  channel: string
  status: string
  assignedTo: string | null
  createdAt: string
  resolvedAt: string | null
}

export interface ComplianceReport {
  id: string
  datasetId: string
  framework: string
  status: string
  findings: string
  score: number
  createdAt: string
}
