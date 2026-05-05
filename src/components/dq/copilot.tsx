'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import {
  MessageSquare, Send, Bot, User, Loader2, Sparkles, Trash2,
  Copy, Check, Code, Table2, Lightbulb, AlertTriangle,
  CheckCircle2, XCircle, Zap, Download, Eye,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

// ── Types ──
interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  type?: 'text' | 'code' | 'suggestion'
  actions?: FixAction[]
}

interface FixAction {
  id: string
  type: string        // imputation | outlier | encoding | dedup
  priority: string    // high | medium | low
  title: string
  description: string
  action: string      // transform type to send
  config: Record<string, any>
  status: 'pending' | 'applying' | 'applied' | 'failed'
  result?: { success: boolean; message: string; rows_affected: number; newTableName?: string }
}

interface TableInfo {
  id: string
  name: string
}

const SUGGESTIONS = [
  { label: 'Clean missing values', prompt: 'How should I handle missing values in my dataset?' },
  { label: 'Outlier detection', prompt: 'What methods can I use to detect outliers?' },
  { label: 'Feature engineering', prompt: 'Suggest feature engineering steps for my dataset.' },
  { label: 'Data quality issues', prompt: 'What data quality issues should I look for?' },
]

const STORAGE_KEY = 'dataguard-copilot-state'

function saveState(state: { messages: ChatMessage[]; tableContext: string }) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {}
}

function loadState(): { messages: ChatMessage[]; tableContext: string } | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch {}
  return null
}

// ── Code Block ──
function CodeBlock({ code, language }: { code: string; language: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <div className="relative rounded-lg bg-slate-900 p-3 my-2">
      {language && (
        <Badge variant="secondary" className="absolute top-2 right-12 text-[10px] bg-slate-700 text-slate-300">
          {language}
        </Badge>
      )}
      <button
        onClick={() => { navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
        className="absolute top-2 right-2 p-1 rounded hover:bg-slate-700 transition"
      >
        {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5 text-slate-400" />}
      </button>
      <pre className="text-sm text-slate-200 font-mono overflow-x-auto whitespace-pre-wrap">{code}</pre>
    </div>
  )
}

// ── Message Content ──
function MessageContent({ content }: { content: string }) {
  const parts = content.split(/(```[\s\S]*?```)/g)
  return (
    <div className="space-y-2">
      {parts.map((part, i) => {
        if (part.startsWith('```') && part.endsWith('```')) {
          const lines = part.slice(3, -3).split('\n')
          const lang = lines[0].trim()
          const code = lines.slice(lang ? 1 : 0).join('\n')
          return <CodeBlock key={i} code={code} language={lang} />
        }
        return (
          <div key={i} className="whitespace-pre-wrap text-sm leading-relaxed">
            {part.split(/(\*\*.*?\*\*)/g).map((segment, j) => {
              if (segment.startsWith('**') && segment.endsWith('**')) {
                return <strong key={j} className="font-semibold">{segment.slice(2, -2)}</strong>
              }
              return <span key={j}>{segment}</span>
            })}
          </div>
        )
      })}
    </div>
  )
}

// ── Fix Action Card ──
function FixActionCard({
  action,
  tableId,
  onStatusChange,
}: {
  action: FixAction
  tableId: string
  onStatusChange: (id: string, status: FixAction['status'], result?: FixAction['result']) => void
}) {
  const handleApply = async () => {
    onStatusChange(action.id, 'applying')
    try {
      const res = await fetch('/api/transforms/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tableId,
          transformType: action.action,
          config: action.config,
          saveCopy: true,
        }),
      })
      const data = await res.json()
      if (data.success) {
        onStatusChange(action.id, 'applied', {
          success: true,
          message: data.message,
          rows_affected: data.rows_affected ?? 0,
          newTableName: data.newTableName,
        })
        if (data.saveCopyError) {
          toast.warning(`${action.title}: Transform succeeded but fixed copy creation failed: ${data.saveCopyError}`)
        } else if (data.newTableName) {
          toast.success(`${action.title}: ${data.rows_affected ?? 0} rows affected — Saved as ${data.newTableName}`)
        } else {
          toast.success(`${action.title}: ${data.rows_affected ?? 0} rows affected`)
        }
      } else {
        onStatusChange(action.id, 'failed', {
          success: false,
          message: data.error || data.message || 'Transform failed',
          rows_affected: 0,
        })
        toast.error(`${action.title} failed: ${data.error || data.message}`)
      }
    } catch (err: any) {
      onStatusChange(action.id, 'failed', {
        success: false,
        message: err?.message || 'Network error',
        rows_affected: 0,
      })
      toast.error(`${action.title} failed: ${err?.message || 'Network error'}`)
    }
  }

  const priorityConfig: Record<string, { className: string; icon: React.ReactNode }> = {
    high: { className: 'bg-red-50 text-red-700 border-red-200', icon: <AlertTriangle className="h-3 w-3" /> },
    medium: { className: 'bg-amber-50 text-amber-700 border-amber-200', icon: <Zap className="h-3 w-3" /> },
    low: { className: 'bg-blue-50 text-blue-700 border-blue-200', icon: <Lightbulb className="h-3 w-3" /> },
  }
  const pc = priorityConfig[action.priority] || priorityConfig.medium

  const statusConfig: Record<string, { className: string; icon: React.ReactNode; label: string }> = {
    pending: { className: 'bg-slate-50 text-slate-600 border-slate-200', icon: <Sparkles className="h-3 w-3" />, label: 'Apply' },
    applying: { className: 'bg-blue-50 text-blue-600 border-blue-200', icon: <Loader2 className="h-3 w-3 animate-spin" />, label: 'Applying...' },
    applied: { className: 'bg-emerald-50 text-emerald-600 border-emerald-200', icon: <CheckCircle2 className="h-3 w-3" />, label: 'Applied' },
    failed: { className: 'bg-red-50 text-red-600 border-red-200', icon: <XCircle className="h-3 w-3" />, label: 'Failed' },
  }
  const sc = statusConfig[action.status] || statusConfig.pending

  return (
    <div className="rounded-lg border bg-white p-3 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className={cn('gap-1 text-[10px]', pc.className)}>
              {pc.icon}
              {action.priority}
            </Badge>
            <span className="text-sm font-medium text-slate-900">{action.title}</span>
          </div>
          <p className="text-xs text-slate-500 leading-relaxed">{action.description}</p>
        </div>
        {action.status === 'pending' && (
          <Button size="sm" className="gap-1.5 text-xs h-7 shrink-0" onClick={handleApply}>
            <Sparkles className="h-3 w-3" />
            Apply
          </Button>
        )}
        {action.status === 'applying' && (
          <Badge variant="outline" className={cn('gap-1 text-[11px]', sc.className)}>
            <Loader2 className="h-3 w-3 animate-spin" />
            {sc.label}
          </Badge>
        )}
        {action.status === 'applied' && (
          <Badge variant="outline" className={cn('gap-1 text-[11px]', sc.className)}>
            <CheckCircle2 className="h-3 w-3" />
            Applied
          </Badge>
        )}
        {action.status === 'failed' && (
          <Badge variant="outline" className={cn('gap-1 text-[11px]', sc.className)}>
            <XCircle className="h-3 w-3" />
            Failed
          </Badge>
        )}
      </div>
      {action.result && action.status === 'applied' && (
        <div className="text-[11px] text-emerald-600 flex items-center gap-1">
          <CheckCircle2 className="h-3 w-3" />
          {action.result.rows_affected} rows affected
          {action.result.newTableName && (
            <span className="text-emerald-700 font-medium"> | Saved as: {action.result.newTableName}</span>
          )}
        </div>
      )}
      {action.result && action.status === 'failed' && (
        <div className="text-[11px] text-red-600 flex items-center gap-1">
          <XCircle className="h-3 w-3" />
          {action.result.message}
        </div>
      )}
    </div>
  )
}

// ── Main Component ──
export default function Copilot() {
  const saved = loadState()
  const [messages, setMessages] = useState<ChatMessage[]>(saved?.messages?.length ? saved.messages : [])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [tableContext, setTableContext] = useState<string>(saved?.tableContext || '')
  const [tables, setTables] = useState<TableInfo[]>([])
  const [analyzing, setAnalyzing] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Find the UUID for a given table name
  const getTableId = useCallback((name: string): string => {
    const found = tables.find(t => t.name === name)
    return found?.id || name
  }, [tables])

  // Fetch available tables
  useEffect(() => {
    const fetchTables = async () => {
      try {
        const res = await fetch('/api/tables')
        if (res.ok) {
          const data = await res.json()
          if (Array.isArray(data)) {
            setTables(data.map((t: any) => ({ id: t.id, name: t.name || t.tableName || '' })).filter((t: TableInfo) => t.name.length > 0))
          }
        }
      } catch {}
    }
    fetchTables()
  }, [])

  // Persist chat state
  useEffect(() => {
    saveState({ messages, tableContext })
  }, [messages, tableContext])

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [])

  useEffect(() => { scrollToBottom() }, [messages, scrollToBottom])

  // ── Auto-Analyze ──
  const handleAutoAnalyze = async () => {
    if (!tableContext) {
      toast.error('Please select a table first')
      return
    }
    setAnalyzing(true)

    // Add user message
    const userMsg: ChatMessage = {
      id: `m${Date.now()}`,
      role: 'user',
      content: `Auto-analyze ${tableContext}`,
      timestamp: new Date().toISOString(),
    }
    setMessages(prev => [...prev, userMsg])

    try {
      const tableId = getTableId(tableContext)
      const res = await fetch(`/api/copilot/suggestions/${encodeURIComponent(tableId)}`)
      if (!res.ok) throw new Error('Failed to analyze')
      const data = await res.json()

      const suggestions: any[] = data.suggestions || []
      const infoSuggestion = suggestions.find((s: any) => s.type === 'info')

      if (infoSuggestion || suggestions.length === 0) {
        // No issues found
        const aiMsg: ChatMessage = {
          id: `m${Date.now() + 1}`,
          role: 'assistant',
          content: `Your **${tableContext}** data looks clean! No major issues detected. Run an ML readiness check for deeper analysis.`,
          timestamp: new Date().toISOString(),
          type: 'suggestion',
        }
        setMessages(prev => [...prev, aiMsg])
      } else {
        // Create fix actions from suggestions
        const actions: FixAction[] = suggestions
          .filter((s: any) => s.type !== 'info')
          .map((s: any, idx: number) => ({
            id: `fix-${Date.now()}-${idx}`,
            type: s.type,
            priority: s.priority || 'medium',
            title: s.title,
            description: s.description,
            action: s.action || s.type,
            config: s.config || {},
            status: 'pending' as const,
          }))

        const highCount = actions.filter(a => a.priority === 'high').length
        const mediumCount = actions.filter(a => a.priority === 'medium').length

        const aiMsg: ChatMessage = {
          id: `m${Date.now() + 1}`,
          role: 'assistant',
          content: `Analysis complete for **${tableContext}**:\n\nFound **${actions.length} issues** (${highCount} high, ${mediumCount} medium). Click Apply on each fix, or use Auto-Fix to apply all at once.`,
          timestamp: new Date().toISOString(),
          type: 'suggestion',
          actions,
        }
        setMessages(prev => [...prev, aiMsg])
      }
    } catch (err: any) {
      const aiMsg: ChatMessage = {
        id: `m${Date.now() + 1}`,
        role: 'assistant',
        content: `Failed to analyze **${tableContext}**: ${err?.message || 'Unknown error'}. Make sure the Python backend is running on port 3001.`,
        timestamp: new Date().toISOString(),
      }
      setMessages(prev => [...prev, aiMsg])
    } finally {
      setAnalyzing(false)
    }
  }

  // ── Auto-Fix All ──
  const handleAutoFixAll = () => {
    // Collect all pending actions across all messages
    const pendingActions: { msgId: string; action: FixAction }[] = []
    for (const msg of messages) {
      if (!msg.actions) continue
      for (const action of msg.actions) {
        if (action.status === 'pending') {
          pendingActions.push({ msgId: msg.id, action })
        }
      }
    }

    if (pendingActions.length === 0) return

    // Mark all as applying
    for (const { msgId, action } of pendingActions) {
      setMessages(prev => prev.map(m =>
        m.id === msgId
          ? { ...m, actions: m.actions?.map(a => a.id === action.id ? { ...a, status: 'applying' as const } : a) }
          : m
      ))
    }

    const applyAll = async () => {
      const tableId = getTableId(tableContext)

      // Use batch endpoint to apply all transforms in one call — creates ONE _fixed file
      const transforms = pendingActions.map(({ action }) => ({
        transformType: action.action,
        config: action.config,
      }))

      try {
        const res = await fetch('/api/transforms/execute-batch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tableId,
            transforms,
            saveCopy: true,
          }),
        })
        const data = await res.json()

        if (data.success) {
          // Map step results back to each action
          const stepResults = data.step_results || []
          for (let i = 0; i < pendingActions.length; i++) {
            const { msgId, action } = pendingActions[i]
            const step = stepResults[i]
            const stepSuccess = step?.success ?? true
            const stepRows = step?.rows_affected ?? 0
            const stepMsg = step?.message || ''

            setMessages(prev => prev.map(m =>
              m.id === msgId
                ? {
                    ...m,
                    actions: m.actions?.map(a => a.id === action.id ? {
                      ...a,
                      status: stepSuccess ? 'applied' as const : 'failed' as const,
                      result: {
                        success: stepSuccess,
                        message: stepMsg,
                        rows_affected: stepRows,
                        newTableName: i === pendingActions.length - 1 ? data.newTableName : undefined,
                      },
                    } : a),
                  }
                : m
            ))

            if (stepSuccess) {
              toast.success(`${action.title}: ${stepRows} rows affected`)
            } else {
              toast.error(`${action.title} failed: ${stepMsg}`)
            }
          }

          // Final toast with the single fixed file name
          if (data.saveCopyError) {
            toast.warning(`Transforms applied but fixed copy failed: ${data.saveCopyError}`)
          } else if (data.newTableName) {
            toast.success(`All fixes applied! Saved as ${data.newTableName} (1 file with ${pendingActions.length} fixes)`)
          } else {
            toast.success('All fixes applied!')
          }
        } else {
          // Batch failed entirely
          for (const { msgId, action } of pendingActions) {
            setMessages(prev => prev.map(m =>
              m.id === msgId
                ? {
                    ...m,
                    actions: m.actions?.map(a => a.id === action.id ? {
                      ...a,
                      status: 'failed' as const,
                      result: { success: false, message: data.error || 'Batch transform failed', rows_affected: 0 },
                    } : a),
                  }
                : m
            ))
          }
          toast.error(`Auto-Fix failed: ${data.error || 'Unknown error'}`)
        }
      } catch (err: any) {
        // Network error
        for (const { msgId, action } of pendingActions) {
          setMessages(prev => prev.map(m =>
            m.id === msgId
              ? {
                  ...m,
                  actions: m.actions?.map(a => a.id === action.id ? {
                    ...a,
                    status: 'failed' as const,
                    result: { success: false, message: 'Network error', rows_affected: 0 },
                  } : a),
                }
              : m
          ))
        }
        toast.error(`Auto-Fix failed: ${err?.message || 'Network error'}`)
      }
    }
    applyAll()
  }

  // ── Update fix action status ──
  const handleActionStatusChange = (actionId: string, status: FixAction['status'], result?: FixAction['result']) => {
    setMessages(prev => prev.map(msg => {
      if (!msg.actions) return msg
      return {
        ...msg,
        actions: msg.actions.map(a =>
          a.id === actionId ? { ...a, status, result: result || a.result } : a
        ),
      }
    }))
  }

  // ── Chat Send ──
  const handleSend = async (text?: string) => {
    const prompt = text || input.trim()
    if (!prompt) return

    const userMsg: ChatMessage = {
      id: `m${Date.now()}`,
      role: 'user',
      content: prompt,
      timestamp: new Date().toISOString(),
    }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch('/api/copilot/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: prompt, tableId: tableContext ? getTableId(tableContext) : undefined }),
      })
      if (res.ok) {
        const data = await res.json()
        const aiMsg: ChatMessage = {
          id: `m${Date.now() + 1}`,
          role: 'assistant',
          content: data.content || data.message || data.response || 'I processed your request.',
          timestamp: new Date().toISOString(),
          type: 'text',
        }
        setMessages(prev => [...prev, aiMsg])
      } else {
        throw new Error('Failed')
      }
    } catch (err: any) {
      let errorMsg = 'Sorry, I\'m unable to connect to the AI backend. '
      if (err instanceof TypeError && err.message.includes('fetch')) {
        errorMsg += 'The backend server is not responding. Please start the Python backend on port 3001.'
      } else {
        errorMsg += `Error: ${err?.message || 'Unknown error'}`
      }
      const aiMsg: ChatMessage = {
        id: `m${Date.now() + 1}`,
        role: 'assistant',
        content: errorMsg,
        timestamp: new Date().toISOString(),
        type: 'text',
      }
      setMessages(prev => [...prev, aiMsg])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleClear = () => {
    setMessages([])
    localStorage.removeItem(STORAGE_KEY)
    toast.success('Chat cleared')
  }

  // Count pending fixes across all messages
  const pendingFixCount = messages.reduce((acc, msg) =>
    acc + (msg.actions?.filter(a => a.status === 'pending').length || 0), 0)

  return (
    <div className="space-y-4 h-[calc(100vh-10rem)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">AI Data Copilot</h2>
          <p className="text-sm text-slate-500 mt-1">Your AI assistant for data preparation and quality</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={tableContext || "__none__"} onValueChange={(v) => setTableContext(v === "__none__" ? "" : v)}>
            <SelectTrigger className="w-52">
              <Table2 className="h-4 w-4 mr-2 text-slate-400" />
              <SelectValue placeholder="Select table..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__none__">No table selected</SelectItem>
              {tables.map((t) => <SelectItem key={t.id} value={t.name}>{t.name}</SelectItem>)}
            </SelectContent>
          </Select>
          <Button
            variant="default"
            size="sm"
            className="gap-2"
            onClick={handleAutoAnalyze}
            disabled={analyzing || !tableContext}
          >
            {analyzing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
            {analyzing ? 'Analyzing...' : 'Auto-Analyze'}
          </Button>
          {pendingFixCount > 0 && (
            <Button variant="outline" size="sm" className="gap-2" onClick={handleAutoFixAll}>
              <Zap className="h-3.5 w-3.5" />
              Auto-Fix All ({pendingFixCount})
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={handleClear} className="gap-2">
            <Trash2 className="h-3.5 w-3.5" /> Clear
          </Button>
        </div>
      </div>

      {/* Chat Area */}
      <Card className="flex-1 flex flex-col min-h-0">
        <ScrollArea className="flex-1 p-4" ref={scrollRef}>
          <div className="space-y-4 max-w-3xl mx-auto">
            {messages.length === 0 && (
              <div className="text-center py-12">
                <Bot className="h-12 w-12 text-slate-300 mx-auto mb-4" />
                <h3 className="font-semibold text-slate-700 mb-1">Data Preparation Copilot</h3>
                <p className="text-sm text-slate-400 mb-4">Select a table and click Auto-Analyze, or ask a question below.</p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {SUGGESTIONS.map((s, i) => (
                    <Button
                      key={i}
                      variant="outline"
                      size="sm"
                      className="gap-1.5 text-xs h-8"
                      onClick={() => handleSend(s.prompt)}
                      disabled={loading}
                    >
                      <Lightbulb className="h-3 w-3" />
                      {s.label}
                    </Button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <div key={msg.id} className={cn('flex gap-3', msg.role === 'user' ? 'justify-end' : 'justify-start')}>
                {msg.role === 'assistant' && (
                  <Avatar className="h-8 w-8 shrink-0">
                    <AvatarFallback className="bg-emerald-100 text-emerald-600">
                      <Bot className="h-4 w-4" />
                    </AvatarFallback>
                  </Avatar>
                )}
                <div className={cn(
                  'rounded-xl px-4 py-3 max-w-[85%]',
                  msg.role === 'user'
                    ? 'bg-slate-900 text-white'
                    : 'bg-white border border-slate-200 shadow-sm'
                )}>
                  <MessageContent content={msg.content} />

                  {/* Fix Action Cards */}
                  {msg.actions && msg.actions.length > 0 && (
                    <div className="mt-3 space-y-2">
                      <p className="text-xs font-medium text-slate-500 mb-1">Suggested Fixes:</p>
                      {msg.actions.map((action) => (
                        <FixActionCard
                          key={action.id}
                          action={action}
                          tableId={tableContext ? getTableId(tableContext) : ''}
                          onStatusChange={handleActionStatusChange}
                        />
                      ))}
                    </div>
                  )}

                  <p className={cn(
                    'text-[10px] mt-2',
                    msg.role === 'user' ? 'text-slate-400' : 'text-slate-300'
                  )}>
                    {new Date(msg.timestamp).toLocaleTimeString()}
                  </p>
                </div>
                {msg.role === 'user' && (
                  <Avatar className="h-8 w-8 shrink-0">
                    <AvatarFallback className="bg-slate-100 text-slate-600">
                      <User className="h-4 w-4" />
                    </AvatarFallback>
                  </Avatar>
                )}
              </div>
            ))}

            {(loading || analyzing) && (
              <div className="flex gap-3">
                <Avatar className="h-8 w-8 shrink-0">
                  <AvatarFallback className="bg-emerald-100 text-emerald-600">
                    <Bot className="h-4 w-4" />
                  </AvatarFallback>
                </Avatar>
                <div className="rounded-xl bg-white border border-slate-200 shadow-sm px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin text-emerald-500" />
                    <span className="text-sm text-slate-500">{analyzing ? 'Analyzing data...' : 'Thinking...'}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        <Separator />

        {/* Input */}
        <div className="p-4">
          <div className="flex gap-2 max-w-3xl mx-auto">
            <div className="flex-1 relative">
              <input
                type="text"
                placeholder={tableContext ? `Ask about ${tableContext}...` : "Select a table and click Auto-Analyze..."}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                className="w-full rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                disabled={loading}
              />
            </div>
            <Button onClick={() => handleSend()} disabled={loading || !input.trim()} className="gap-2">
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}
