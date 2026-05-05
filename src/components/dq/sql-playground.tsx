'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Code, Play, Clock, Database, ChevronRight, ChevronDown,
  RefreshCw, AlertCircle, Search, X, Table2, Loader2,
  Sparkles, Send, Wand2, Eye,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

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

interface DatabaseInfo {
  name: string
  fileName: string
  sizeBytes: number
  sizeMB: number
  tableCount: number
  tables: string[]
}

interface ColumnInfo {
  cid: number
  name: string
  type: string
  notnull: boolean
  defaultValue: string | null
  primaryKey: boolean
}

interface TableInfo {
  name: string
  columns: ColumnInfo[]
  columnCount: number
  rowCount: number
}

interface QueryResult {
  success: boolean
  columns: string[]
  rows: Record<string, unknown>[]
  rowCount: number
  truncated: boolean
  database: string
  executionTimeMs: number
  error?: string
}

export default function SQLPlaygroundView() {
  // Database & schema state
  const [databases, setDatabases] = useState<DatabaseInfo[]>([])
  const [selectedDb, setSelectedDb] = useState<string>('')
  const [tables, setTables] = useState<TableInfo[]>([])
  const [loadingDb, setLoadingDb] = useState(false)
  const [loadingTables, setLoadingTables] = useState(false)
  const [expandedTable, setExpandedTable] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)

  // Query state
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<QueryResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [executing, setExecuting] = useState(false)

  // History
  const [queryHistory, setQueryHistory] = useState<string[]>([])
  const [showHistory, setShowHistory] = useState(false)

  // AI NL->SQL state
  const [nlQuestion, setNlQuestion] = useState('')
  const [aiGenerating, setAiGenerating] = useState(false)
  const [aiExplanation, setAiExplanation] = useState<string | null>(null)
  const [aiMethod, setAiMethod] = useState<string>('')

  // Search within tables
  const [tableSearch, setTableSearch] = useState('')

  // Table data preview state
  const [previewTable, setPreviewTable] = useState<string | null>(null)
  const [previewColumns, setPreviewColumns] = useState<string[]>([])
  const [previewRows, setPreviewRows] = useState<Record<string, unknown>[]>([])
  const [previewTotalRows, setPreviewTotalRows] = useState(0)
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [showPreviewPanel, setShowPreviewPanel] = useState(false)

  // Load databases on mount
  useEffect(() => {
    loadDatabases()
  }, [])

  const loadDatabases = async () => {
    setLoadingDb(true)
    try {
      const res = await fetch('/api/sql/databases')
      const data = await res.json()
      if (data.databases) {
        setDatabases(data.databases)
        if (data.databases.length > 0 && !selectedDb) {
          const defaultDb = data.databases.find((d: DatabaseInfo) => d.name === 'delhi_accidents')?.name || data.databases.find((d: DatabaseInfo) => d.name === 'cities')?.name || data.databases[0].name
          setSelectedDb(defaultDb)
        }
      }
    } catch (err) {
      console.error('Failed to load databases:', err)
    } finally {
      setLoadingDb(false)
    }
  }

  // Load tables when database changes
  useEffect(() => {
    if (selectedDb) {
      loadTables(selectedDb)
    }
  }, [selectedDb])

  const loadTables = async (db: string) => {
    setLoadingTables(true)
    setTables([])
    try {
      const res = await fetch(`/api/sql/tables?database=${encodeURIComponent(db)}`)
      const data = await res.json()
      if (data.tables) {
        setTables(data.tables)
      }
    } catch (err) {
      console.error('Failed to load tables:', err)
    } finally {
      setLoadingTables(false)
    }
  }

  const handleExecute = useCallback(async () => {
    if (!query.trim()) return
    setExecuting(true)
    setResults(null)
    setError(null)

    try {
      const res = await fetch('/api/sql/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query.trim(), database: selectedDb }),
      })
      const data = await res.json()

      if (data.error) {
        setError(data.error)
      } else {
        setResults(data)
      }

      // Add to history (dedup, keep last 20)
      setQueryHistory(prev => {
        const updated = [query.trim(), ...prev.filter(q => q !== query.trim())]
        return updated.slice(0, 20)
      })
    } catch (err) {
      setError('Failed to connect to backend. Is the server running?')
    } finally {
      setExecuting(false)
    }
  }, [query, selectedDb])

  // Keyboard shortcut: Ctrl+Enter to execute
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault()
        handleExecute()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [handleExecute])

  const insertTableName = (tableName: string) => {
    setQuery(prev => {
      const prefix = prev.trim() ? prev + ' ' : ''
      return prefix + tableName
    })
  }

  const insertSelectAll = (tableName: string) => {
    setQuery(`SELECT * FROM ${tableName} LIMIT 100;`)
  }

  const handleAiQuery = useCallback(async () => {
    if (!nlQuestion.trim() || !selectedDb) return
    setAiGenerating(true)
    setAiExplanation(null)
    setAiMethod('')

    try {
      const res = await fetch('/api/sql/ai-query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: nlQuestion.trim(), database: selectedDb }),
      })
      const data = await res.json()

      if (data.error) {
        setError(data.error)
      } else if (data.sql) {
        setQuery(data.sql)
        if (data.explanation) {
          setAiExplanation(data.explanation)
        }
        setAiMethod(data.generationMethod || 'unknown')
      }
    } catch (err) {
      setError('Failed to connect to backend for AI query generation.')
    } finally {
      setAiGenerating(false)
    }
  }, [nlQuestion, selectedDb])

  const loadTablePreview = useCallback(async (tableName: string) => {
    if (!selectedDb) return
    setLoadingPreview(true)
    setPreviewTable(tableName)
    setShowPreviewPanel(true)
    try {
      const res = await fetch(`/api/sql/table-preview?database=${encodeURIComponent(selectedDb)}&table=${encodeURIComponent(tableName)}&limit=50`)
      const data = await res.json()
      if (data.error) {
        setError(data.error)
      } else {
        setPreviewColumns(data.resultColumns || [])
        setPreviewRows(data.rows || [])
        setPreviewTotalRows(data.totalRows || 0)
      }
    } catch (err) {
      setError('Failed to load table preview.')
    } finally {
      setLoadingPreview(false)
    }
  }, [selectedDb])

  const filteredTables = tables.filter(t =>
    t.name.toLowerCase().includes(tableSearch.toLowerCase())
  )

  // Sample queries per database
  const sampleQueries: Record<string, { label: string; sql: string }[]> = {
    cities: [
      { label: 'Find Delhi cities', sql: "SELECT * FROM cities WHERE name LIKE '%Delhi%';" },
      { label: 'Top 10 by population', sql: 'SELECT name, state, population FROM cities ORDER BY population DESC LIMIT 10;' },
      { label: 'Cities by state', sql: 'SELECT state, COUNT(*) as city_count, SUM(population) as total_pop FROM cities GROUP BY state ORDER BY total_pop DESC;' },
      { label: 'High literacy cities', sql: "SELECT name, state, literacy_rate FROM cities WHERE literacy_rate > 90 AND country = 'India' ORDER BY literacy_rate DESC LIMIT 20;" },
      { label: 'Mega city stats', sql: "SELECT c.name, c.population, c.avg_temp_celsius, e.gdp_billion_usd, e.main_industry FROM cities c JOIN city_economy e ON c.id = e.city_id WHERE c.city_type = 'Mega';" },
      { label: 'Capital cities', sql: 'SELECT name, country, population, is_capital FROM cities WHERE is_capital = 1 ORDER BY population DESC;' },
    ],
    sales: [
      { label: 'Delhi orders', sql: "SELECT * FROM orders WHERE city = 'Delhi' LIMIT 50;" },
      { label: 'Revenue by city', sql: 'SELECT city, COUNT(*) as order_count, ROUND(SUM(total_amount),2) as revenue FROM orders GROUP BY city ORDER BY revenue DESC LIMIT 15;' },
      { label: 'Top products', sql: 'SELECT p.name, p.category, SUM(o.quantity) as total_sold, ROUND(SUM(o.total_amount),2) as revenue FROM orders o JOIN products p ON o.product_id = p.id GROUP BY p.id ORDER BY revenue DESC LIMIT 10;' },
      { label: 'Monthly trend', sql: "SELECT substr(order_date,1,7) as month, COUNT(*) as orders, ROUND(SUM(total_amount),2) as revenue FROM orders WHERE status = 'Delivered' GROUP BY month ORDER BY month;" },
      { label: 'Payment methods', sql: 'SELECT payment_method, COUNT(*) as count, ROUND(AVG(total_amount),2) as avg_order FROM orders GROUP BY payment_method ORDER BY count DESC;' },
    ],
    hr: [
      { label: 'Delhi employees', sql: "SELECT emp_id, name, department, designation, salary FROM employees WHERE city = 'Delhi';" },
      { label: 'Dept headcount', sql: 'SELECT department, COUNT(*) as count, ROUND(AVG(salary),0) as avg_salary FROM employees WHERE status = "Active" GROUP BY department ORDER BY count DESC;' },
      { label: 'Top earners', sql: 'SELECT name, department, designation, salary FROM employees WHERE status = "Active" ORDER BY salary DESC LIMIT 20;' },
      { label: 'Attendance today', sql: "SELECT e.name, e.department, a.status, a.hours_worked FROM attendance a JOIN employees e ON a.emp_id = e.emp_id WHERE a.date = '2024-12-27' ORDER BY a.status;" },
      { label: 'Gender distribution', sql: 'SELECT department, gender, COUNT(*) as count FROM employees WHERE status = "Active" GROUP BY department, gender ORDER BY department;' },
    ],
    delhi_accidents: [
      { label: 'All Delhi accidents', sql: "SELECT S_No, Month, Crash_Date, Location, Killed, Injured, Vehicle_1, Crash_Type FROM delhi_accidents WHERE State = 'Delhi' ORDER BY Crash_Date;" },
      { label: 'Accidents by state', sql: 'SELECT State, COUNT(*) as accident_count, SUM(Killed) as total_killed, SUM(Injured) as total_injured FROM delhi_accidents WHERE State IS NOT NULL GROUP BY State ORDER BY accident_count DESC LIMIT 15;' },
      { label: 'Crash type analysis', sql: 'SELECT Crash_Type, COUNT(*) as count, SUM(Killed) as killed, SUM(Injured) as injured FROM delhi_accidents GROUP BY Crash_Type ORDER BY count DESC;' },
      { label: 'Vehicle involvement', sql: 'SELECT Vehicle_1, COUNT(*) as accident_count, SUM(Killed) as killed FROM delhi_accidents GROUP BY Vehicle_1 ORDER BY accident_count DESC LIMIT 10;' },
      { label: 'Monthly trend', sql: 'SELECT Month, COUNT(*) as accident_count, SUM(Killed) as killed, SUM(Injured) as injured FROM delhi_accidents GROUP BY Month ORDER BY accident_count DESC;' },
      { label: 'Deadliest crashes', sql: 'SELECT Crash_Date, Location, State, Killed, Injured, Vehicle_1, Crash_Type FROM delhi_accidents WHERE Killed >= 5 ORDER BY Killed DESC;' },
    ],
    uploaded_data: [
      { label: 'Show all tables', sql: "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;" },
    ],
    custom: [
      { label: 'All services', sql: 'SELECT name, platform, status, owner FROM Service ORDER BY name;' },
      { label: 'Tables by quality', sql: 'SELECT name, rowCount, qualityScore, freshnessStatus FROM "Table" ORDER BY qualityScore ASC;' },
      { label: 'Active alerts', sql: "SELECT title, severity, alertType, source, status FROM Alert WHERE status = 'active';" },
      { label: 'Quality rules', sql: 'SELECT name, type, dimension, severity, enabled FROM QualityRule;' },
    ],
  }

  const currentSamples = sampleQueries[selectedDb] || sampleQueries.custom || []

  const formatCellValue = (value: unknown): string => {
    if (value === null || value === undefined) return 'NULL'
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  return (
    <motion.div
      className="flex h-[calc(100vh-4rem)] overflow-hidden"
      variants={staggerContainer}
      initial="hidden"
      animate="visible"
    >
      {/* Left Sidebar: Schema Browser */}
      <motion.div
        variants={fadeInUp}
        className={`border-r bg-slate-50/50 flex flex-col transition-all duration-200 ${sidebarOpen ? 'w-72' : 'w-10'}`}
      >
        <div className="flex items-center justify-between p-3 border-b">
          {sidebarOpen && (
            <span className="text-sm font-semibold text-slate-700 flex items-center gap-1.5">
              <Table2 className="h-4 w-4" />
              Schema Browser
            </span>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            {sidebarOpen ? <X className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
          </Button>
        </div>

        {sidebarOpen && (
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {/* DB selector */}
            <div className="px-1 pb-2">
              <label className="text-xs text-muted-foreground mb-1 block">Database</label>
              <Select value={selectedDb} onValueChange={setSelectedDb}>
                <SelectTrigger className="h-8 text-xs">
                  <Database className="h-3 w-3 mr-1.5 text-indigo-500" />
                  <SelectValue placeholder="Select database" />
                </SelectTrigger>
                <SelectContent>
                  {databases.map(db => (
                    <SelectItem key={db.name} value={db.name}>
                      <span className="flex items-center gap-2">
                        {db.name}
                        <span className="text-[10px] text-muted-foreground">({db.tableCount} tables, {db.sizeMB}MB)</span>
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Table search */}
            <div className="px-1 pb-2 relative">
              <Search className="h-3 w-3 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                value={tableSearch}
                onChange={e => setTableSearch(e.target.value)}
                placeholder="Search tables..."
                className="w-full h-7 pl-7 pr-2 rounded-md border bg-white text-xs focus:outline-none focus:ring-1 focus:ring-indigo-400"
              />
            </div>

            {/* Tables list */}
            {loadingTables ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : (
              filteredTables.map(table => (
                <div key={table.name} className="rounded-md border bg-white mb-1">
                  <button
                    className="w-full flex items-center justify-between px-2.5 py-1.5 text-left hover:bg-slate-50 transition text-xs"
                    onClick={() => setExpandedTable(expandedTable === table.name ? null : table.name)}
                  >
                    <span className="flex items-center gap-1.5 min-w-0">
                      <Table2 className="h-3 w-3 text-indigo-400 shrink-0" />
                      <span className="truncate font-medium">{table.name}</span>
                    </span>
                    <span className="flex items-center gap-1.5 shrink-0">
                      <Badge variant="secondary" className="text-[10px] px-1 py-0 h-4">
                        {table.rowCount.toLocaleString()}
                      </Badge>
                      {expandedTable === table.name ? (
                        <ChevronDown className="h-3 w-3 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="h-3 w-3 text-muted-foreground" />
                      )}
                    </span>
                  </button>

                  {expandedTable === table.name && (
                    <div className="border-t px-2.5 py-2 space-y-1.5">
                      {/* Column list */}
                      {table.columns.map(col => (
                        <div key={col.name} className="flex items-center gap-1.5 text-[11px]">
                          {col.primaryKey ? (
                            <Badge className="text-[9px] px-1 py-0 h-3.5 bg-amber-100 text-amber-700 border-amber-200">PK</Badge>
                          ) : col.notnull ? (
                            <Badge variant="outline" className="text-[9px] px-1 py-0 h-3.5">NN</Badge>
                          ) : (
                            <span className="w-4" />
                          )}
                          <span className="font-mono text-slate-700">{col.name}</span>
                          <span className="text-muted-foreground ml-auto">{col.type || 'ANY'}</span>
                        </div>
                      ))}

                      {/* Quick actions */}
                      <div className="flex gap-1.5 pt-1">
                        <Button
                          variant="default"
                          size="sm"
                          className="h-6 text-[10px] px-2 bg-indigo-600 hover:bg-indigo-700"
                          onClick={() => loadTablePreview(table.name)}
                          disabled={loadingPreview}
                        >
                          <Eye className="h-2.5 w-2.5 mr-0.5" />
                          Preview Data
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-6 text-[10px] px-2"
                          onClick={() => insertSelectAll(table.name)}
                        >
                          SELECT *
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-6 text-[10px] px-2"
                          onClick={() => insertTableName(table.name)}
                        >
                          Insert name
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </motion.div>

      {/* Table Data Preview Panel */}
      {showPreviewPanel && previewTable && (
        <div className="border-r bg-white flex flex-col w-96 shrink-0">
          <div className="flex items-center justify-between p-3 border-b bg-indigo-50/50">
            <span className="text-sm font-semibold text-slate-700 flex items-center gap-1.5">
              <Eye className="h-4 w-4 text-indigo-600" />
              Preview: {previewTable}
            </span>
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="text-[10px]">
                {previewTotalRows.toLocaleString()} total rows
              </Badge>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => { setShowPreviewPanel(false); setPreviewTable(null) }}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          <div className="flex-1 overflow-auto">
            {loadingPreview ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin text-indigo-500" />
              </div>
            ) : previewRows.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow className="bg-slate-50 hover:bg-slate-50 sticky top-0">
                    <TableHead className="w-8 text-center text-[10px]">#</TableHead>
                    {previewColumns.map(col => (
                      <TableHead key={col} className="font-mono text-[10px] whitespace-nowrap min-w-[80px]">
                        {col}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {previewRows.map((row, i) => (
                    <TableRow key={i} className={i % 2 === 0 ? '' : 'bg-slate-50/50'}>
                      <TableCell className="text-center text-[10px] text-muted-foreground font-mono">
                        {i + 1}
                      </TableCell>
                      {previewColumns.map(col => {
                        const val = row[col]
                        const isNull = val === null || val === undefined
                        return (
                          <TableCell key={col} className={`font-mono text-[10px] max-w-[120px] truncate ${isNull ? 'text-red-400 italic' : ''}`}>
                            {isNull ? 'NULL' : formatCellValue(val)}
                          </TableCell>
                        )
                      })}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="py-12 text-center text-xs text-slate-400">
                No data in this table
              </div>
            )}
          </div>

          <div className="border-t p-2 bg-slate-50/50">
            <Button
              variant="outline"
              size="sm"
              className="w-full h-7 text-xs gap-1"
              onClick={() => {
                insertSelectAll(previewTable)
                setShowPreviewPanel(false)
              }}
            >
              <Play className="h-3 w-3" />
              Run SELECT * FROM {previewTable}
            </Button>
          </div>
        </div>
      )}

      {/* Main Content */}
      <motion.div variants={fadeInUp} className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 pt-4 pb-2 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">SQL Playground</h1>
            <p className="text-sm text-muted-foreground">
              Write and execute SQL queries across multiple databases
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="gap-1">
              <Database className="h-3 w-3" />
              {selectedDb || 'No DB selected'}
            </Badge>
            {results && (
              <Badge variant="outline" className="gap-1">
                <Clock className="h-3 w-3" />
                {results.executionTimeMs}ms
              </Badge>
            )}
          </div>
        </div>

        {/* Sample queries */}
        <div className="px-6 pb-2 flex items-center gap-2 flex-wrap">
          <span className="text-xs text-muted-foreground">Quick queries:</span>
          {currentSamples.map((sq) => (
            <button
              key={sq.label}
              onClick={() => setQuery(sq.sql)}
              className="text-xs px-2.5 py-1 rounded-md bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 text-slate-600 transition border border-transparent hover:border-indigo-200"
            >
              {sq.label}
            </button>
          ))}
        </div>

        {/* AI Natural Language -> SQL */}
        <div className="px-6 pb-3">
          <div className="flex items-center gap-2 mb-1.5">
            <Sparkles className="h-4 w-4 text-violet-500" />
            <span className="text-sm font-medium text-slate-700">Ask in Natural Language</span>
            {aiMethod && (
              <Badge
                variant={aiMethod === 'llm' ? 'default' : 'secondary'}
                className={`text-[10px] ${aiMethod === 'llm' ? 'bg-violet-100 text-violet-700 border-violet-200' : 'bg-slate-100 text-slate-500'}`}
              >
                {aiMethod === 'llm' ? 'AI Generated' : 'Keyword Match'}
              </Badge>
            )}
          </div>
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Wand2 className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-violet-400" />
              <input
                type="text"
                value={nlQuestion}
                onChange={(e) => setNlQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleAiQuery()
                  }
                }}
                placeholder="e.g. Show me all cities with population over 1 million..."
                className="w-full h-10 pl-9 pr-3 rounded-lg border border-violet-200 bg-violet-50/50 text-sm focus:outline-none focus:ring-2 focus:ring-violet-300 focus:border-violet-300 placeholder:text-violet-300"
                disabled={aiGenerating}
              />
            </div>
            <Button
              className="gap-1.5 bg-violet-600 hover:bg-violet-700 h-10"
              onClick={handleAiQuery}
              disabled={aiGenerating || !nlQuestion.trim() || !selectedDb}
            >
              {aiGenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              {aiGenerating ? 'Generating...' : 'Generate SQL'}
            </Button>
          </div>
          {aiExplanation && (
            <div className="mt-1.5 px-3 py-2 rounded-md bg-violet-50 border border-violet-100 flex items-start gap-2">
              <Sparkles className="h-3.5 w-3.5 text-violet-500 shrink-0 mt-0.5" />
              <p className="text-xs text-violet-700">{aiExplanation}</p>
            </div>
          )}
        </div>

        {/* Query Editor */}
        <div className="px-6 pb-3">
          <div className="relative">
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full h-36 rounded-lg border bg-slate-950 text-white placeholder-white/30 font-mono text-sm p-4 pr-24 focus:outline-none focus:ring-2 focus:ring-white/30 resize-y caret-white"
              spellCheck={false}
              placeholder={`SELECT * FROM delhi_accidents WHERE State = 'Delhi' LIMIT 100;\n\n-- Ctrl+Enter to execute`}
              style={{ textShadow: '0 0 8px rgba(255,255,255,0.25)' }}
            />
            <div className="absolute top-3 right-3 flex flex-col gap-1.5">
              <Button size="sm" className="gap-1.5 bg-emerald-600 hover:bg-emerald-700" onClick={handleExecute} disabled={executing || !query.trim()}>
                {executing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                {executing ? 'Running...' : 'Execute'}
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="gap-1 text-xs"
                onClick={() => setShowHistory(!showHistory)}
              >
                History
              </Button>
            </div>
          </div>

          {/* History dropdown */}
          {showHistory && queryHistory.length > 0 && (
            <div className="mt-1 border rounded-md bg-white shadow-lg max-h-48 overflow-y-auto">
              {queryHistory.map((q, i) => (
                <button
                  key={i}
                  onClick={() => { setQuery(q); setShowHistory(false) }}
                  className="w-full text-left px-3 py-2 text-xs font-mono hover:bg-slate-50 border-b last:border-0 truncate"
                >
                  {q}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Error display */}
        {error && (
          <div className="mx-6 mb-3 p-3 rounded-lg bg-red-50 border border-red-200 flex items-start gap-2">
            <AlertCircle className="h-4 w-4 text-red-500 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-800">Query Error</p>
              <p className="text-xs text-red-600 mt-0.5">{error}</p>
            </div>
            <Button variant="ghost" size="icon" className="h-6 w-6 ml-auto shrink-0" onClick={() => setError(null)}>
              <X className="h-3 w-3" />
            </Button>
          </div>
        )}

        {/* Results */}
        <div className="flex-1 overflow-auto px-6 pb-6">
          {results && results.success ? (
            <Card className="shadow-sm">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ChevronRight className="h-4 w-4 text-emerald-500" />
                    <CardTitle className="text-base">Results</CardTitle>
                    <Badge variant="secondary">{results.rowCount.toLocaleString()} rows</Badge>
                    {results.truncated && (
                      <Badge variant="outline" className="text-amber-600 border-amber-300">
                        Truncated at 1000
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">
                      {results.database}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs gap-1"
                      onClick={loadDatabases}
                    >
                      <RefreshCw className="h-3 w-3" />
                      Refresh
                    </Button>
                  </div>
                </div>
                <CardDescription>
                  Query executed in {results.executionTimeMs}ms on <b>{results.database}</b> database
                </CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-slate-50">
                        <TableHead className="w-10 text-center">#</TableHead>
                        {results.columns.map((col) => (
                          <TableHead key={col} className="font-mono text-xs whitespace-nowrap">
                            {col}
                          </TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {results.rows.map((row, i) => (
                        <TableRow key={i} className={i % 2 === 0 ? '' : 'bg-slate-50/50'}>
                          <TableCell className="text-center text-xs text-muted-foreground font-mono">
                            {i + 1}
                          </TableCell>
                          {results.columns.map((col) => {
                            const val = row[col]
                            const display = formatCellValue(val)
                            const isNull = val === null || val === undefined
                            return (
                              <TableCell key={col} className={`font-mono text-xs max-w-xs truncate ${isNull ? 'text-red-400 italic' : ''}`}>
                                {isNull ? 'NULL' : display}
                              </TableCell>
                            )
                          })}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          ) : !error && !executing ? (
            <div className="flex flex-col items-center justify-center h-64 text-center">
              <Database className="h-12 w-12 text-slate-300 mb-3" />
              <p className="text-muted-foreground text-sm">
                Select a database, write a query, and hit Execute
              </p>
              <p className="text-muted-foreground text-xs mt-1">
                Try: <code className="bg-slate-100 px-1.5 py-0.5 rounded text-emerald-600">SELECT * FROM delhi_accidents WHERE State = &apos;Delhi&apos;</code>
              </p>
            </div>
          ) : executing ? (
            <div className="flex flex-col items-center justify-center h-64">
              <Loader2 className="h-8 w-8 animate-spin text-emerald-500 mb-3" />
              <p className="text-muted-foreground text-sm">Executing query...</p>
            </div>
          ) : null}
        </div>
      </motion.div>
    </motion.div>
  )
}