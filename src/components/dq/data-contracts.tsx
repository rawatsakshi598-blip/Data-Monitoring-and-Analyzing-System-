'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  FileCheck, Plus, Trash2, CheckCircle2, XCircle, AlertTriangle,
  Play, Download, Code, Loader2, Shield, FileText,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

// ── Types ──
interface ContractField {
  name: string
  type: string
  required: boolean
  nullable: boolean
  unique: boolean
  description: string
  constraints?: string
}

interface ValidationResult {
  rule: string
  status: 'pass' | 'fail' | 'warning'
  message?: string
}

interface DataContract {
  id: string
  name: string
  version: string
  tableName: string
  description: string
  owner: string
  status: 'active' | 'draft' | 'deprecated'
  yamlSpec: string
  fields: ContractField[]
  validations: ValidationResult[]
  lastValidated: string | null
  createdAt: string
  updatedAt: string
}

// ── Helpers ──
function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { className: string; icon: React.ReactNode }> = {
    active: { className: 'bg-emerald-50 text-emerald-700 border-emerald-200', icon: <CheckCircle2 className="h-3 w-3" /> },
    draft: { className: 'bg-slate-50 text-slate-600 border-slate-200', icon: <FileText className="h-3 w-3" /> },
    deprecated: { className: 'bg-amber-50 text-amber-700 border-amber-200', icon: <AlertTriangle className="h-3 w-3" /> },
  }
  const c = config[status] || config.draft
  return (
    <Badge variant="outline" className={cn('gap-1 text-[11px]', c.className)}>
      {c.icon}
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  )
}

function ValidationIcon({ status }: { status: string }) {
  switch (status) {
    case 'pass': return <CheckCircle2 className="h-4 w-4 text-emerald-500" />
    case 'fail': return <XCircle className="h-4 w-4 text-red-500" />
    case 'warning': return <AlertTriangle className="h-4 w-4 text-amber-500" />
    default: return null
  }
}

function ValidationBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pass: 'bg-emerald-500/15 text-emerald-700 border-emerald-500/30',
    fail: 'bg-red-500/15 text-red-700 border-red-500/30',
    warning: 'bg-amber-500/15 text-amber-700 border-amber-500/30',
  }
  return <Badge variant="outline" className={cn('text-[10px]', colors[status] || '')}>{status}</Badge>
}

// ── Main Component ──
export default function DataContracts() {
  const [contracts, setContracts] = useState<DataContract[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedContract, setSelectedContract] = useState<DataContract | null>(null)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [validating, setValidating] = useState(false)
  const [validationHistory, setValidationHistory] = useState<{ contractId: string; timestamp: string; results: ValidationResult[] }[]>([])

  // Create form
  const [newContract, setNewContract] = useState({ name: '', tableName: '', description: '', owner: '', yamlSpec: '' })

  // Edit YAML
  const [editYaml, setEditYaml] = useState('')
  const [yamlEditing, setYamlEditing] = useState(false)

  const fetchContracts = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/contracts')
      if (res.ok) {
        const data = await res.json()
        setContracts(Array.isArray(data) ? data : data?.contracts || [])
        if (Array.isArray(data) && data.length > 0) setSelectedContract(data[0])
      } else {
        throw new Error('Failed')
      }
    } catch {
      setError('Failed to load data contracts from server')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchContracts() }, [fetchContracts])

  // Sync edit YAML when selected contract changes
  useEffect(() => {
    if (selectedContract) {
      setEditYaml(selectedContract.yamlSpec || generateYamlFromContract(selectedContract))
      setYamlEditing(false)
    }
  }, [selectedContract])

  function generateYamlFromContract(contract: DataContract): string {
    return `# Data Contract: ${contract.name}
apiVersion: v2.1.0
kind: dataContract
id: ${contract.id}
name: ${contract.name}
version: ${contract.version}
owner: ${contract.owner}
status: ${contract.status}

schema:
  type: table
  table: ${contract.tableName}
  fields:${contract.fields.map((f) => `\n    - name: ${f.name}\n      type: ${f.type}\n      required: ${f.required}\n      nullable: ${f.nullable}\n      unique: ${f.unique}${f.constraints ? `\n      constraints: ${f.constraints}` : ''}`).join('')}

quality:
  type: qualityChecks
  checks:${contract.validations.map((v) => `\n    - rule: "${v.rule}"\n      status: ${v.status}`).join('') || '\n    - rule: "No validations defined"'}
`
  }

  const handleCreate = async () => {
    if (!newContract.name.trim()) { toast.error('Contract name is required'); return }
    try {
      const res = await fetch('/api/contracts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newContract),
      })
      if (res.ok) {
        const data = await res.json()
        setContracts((prev) => [data, ...prev])
        setSelectedContract(data)
        toast.success('Contract created')
      } else {
        throw new Error('Failed')
      }
    } catch {
      toast.error('Failed to create contract — backend unavailable. Please ensure the Python backend is running on port 3001.')
    }
    setShowCreateDialog(false)
    setNewContract({ name: '', tableName: '', description: '', owner: '', yamlSpec: '' })
  }

  const handleValidate = async () => {
    if (!selectedContract) return
    setValidating(true)
    try {
      const res = await fetch(`/api/contracts/${selectedContract.id}/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ yamlSpec: editYaml }),
      })
      if (res.ok) {
        const data = await res.json()
        const validations: ValidationResult[] = data.validations || data.results || []
        const updated = { ...selectedContract, validations, lastValidated: new Date().toISOString() }
        setSelectedContract(updated)
        setContracts((prev) => prev.map((c) => c.id === updated.id ? updated : c))
        setValidationHistory((prev) => [{ contractId: selectedContract.id, timestamp: new Date().toISOString(), results: validations }, ...prev])
        toast.success('Contract validated')
      } else {
        throw new Error('Failed')
      }
    } catch {
      toast.error('Failed to validate contract — backend unavailable. Please ensure the Python backend is running on port 3001.')
    } finally {
      setValidating(false)
    }
  }

  const handleDelete = async (contractId: string) => {
    try {
      await fetch(`/api/contracts/${contractId}`, { method: 'DELETE' })
    } catch {
      toast.error('Failed to delete contract from backend')
    }
    setContracts((prev) => prev.filter((c) => c.id !== contractId))
    if (selectedContract?.id === contractId) setSelectedContract(null)
    toast.success('Contract deleted')
  }

  const handleSaveYaml = () => {
    if (!selectedContract) return
    const updated = { ...selectedContract, yamlSpec: editYaml, updatedAt: new Date().toISOString() }
    setSelectedContract(updated)
    setContracts((prev) => prev.map((c) => c.id === updated.id ? updated : c))
    setYamlEditing(false)
    toast.success('YAML spec saved')
  }

  const passCount = selectedContract?.validations.filter((v) => v.status === 'pass').length || 0
  const failCount = selectedContract?.validations.filter((v) => v.status === 'fail').length || 0
  const warnCount = selectedContract?.validations.filter((v) => v.status === 'warning').length || 0

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between"><Skeleton className="h-8 w-48" /><Skeleton className="h-10 w-36" /></div>
        <div className="grid gap-6 lg:grid-cols-5"><Skeleton className="h-96 rounded-xl" /><Skeleton className="h-96 rounded-xl lg:col-span-3" /></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Data Contracts</h2>
          <p className="text-sm text-slate-500 mt-1">Define and validate data schema contracts</p>
        </div>
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <Button className="gap-2" onClick={() => setShowCreateDialog(true)}><Plus className="h-4 w-4" /> New Contract</Button>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Data Contract</DialogTitle>
              <DialogDescription>Define a new schema contract for your data</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label>Contract Name</Label>
                <Input placeholder="e.g., Customer Data Contract" value={newContract.name} onChange={(e) => setNewContract((p) => ({ ...p, name: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>Table Name</Label>
                <Input placeholder="e.g., customers" value={newContract.tableName} onChange={(e) => setNewContract((p) => ({ ...p, tableName: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>Owner</Label>
                <Input placeholder="e.g., Data Engineering" value={newContract.owner} onChange={(e) => setNewContract((p) => ({ ...p, owner: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea placeholder="Contract description..." value={newContract.description} onChange={(e) => setNewContract((p) => ({ ...p, description: e.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>YAML Spec (optional)</Label>
                <Textarea placeholder="Paste your YAML spec here..." value={newContract.yamlSpec} onChange={(e) => setNewContract((p) => ({ ...p, yamlSpec: e.target.value }))} className="min-h-[120px] font-mono text-xs" />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancel</Button>
              <Button onClick={handleCreate} disabled={!newContract.name.trim()}>Create Contract</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {error && (
        <Card className="border-red-200 bg-red-50/50">
          <CardContent className="p-4 flex items-center gap-3">
            <XCircle className="h-5 w-5 text-red-500 shrink-0" />
            <p className="text-sm text-red-700">{error}</p>
            <Button variant="outline" size="sm" onClick={fetchContracts} className="ml-auto">Retry</Button>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-5">
        {/* Contract List */}
        <div className="lg:col-span-2">
          <ScrollArea className="h-[600px]">
            <div className="space-y-2 pr-2">
              {contracts.length === 0 ? (
                <Card>
                  <CardContent className="p-8 text-center">
                    <FileCheck className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                    <p className="text-sm text-slate-400">No contracts yet</p>
                  </CardContent>
                </Card>
              ) : contracts.map((contract) => (
                <Card
                  key={contract.id}
                  className={cn('cursor-pointer transition-all hover:shadow-sm', selectedContract?.id === contract.id ? 'ring-2 ring-emerald-500' : '')}
                  onClick={() => setSelectedContract(contract)}
                >
                  <CardContent className="p-3">
                    <div className="flex items-center justify-between mb-1">
                      <h3 className="text-sm font-semibold text-slate-900 truncate">{contract.name}</h3>
                      <StatusBadge status={contract.status} />
                    </div>
                    <p className="text-xs text-slate-500 mb-1">{contract.tableName} · v{contract.version}</p>
                    <div className="flex items-center gap-2 text-[11px] text-slate-400">
                      <span>{contract.fields.length} fields</span>
                      <span>·</span>
                      <span>{contract.owner}</span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </ScrollArea>
        </div>

        {/* Contract Detail */}
        <div className="lg:col-span-3">
          {selectedContract ? (
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-base flex items-center gap-2">
                        <FileCheck className="h-4 w-4" />
                        {selectedContract.name}
                      </CardTitle>
                      <CardDescription>
                        {selectedContract.tableName} · v{selectedContract.version} · {selectedContract.owner}
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button variant="outline" size="sm" className="gap-1" onClick={handleValidate} disabled={validating}>
                        {validating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                        {validating ? 'Validating...' : 'Validate'}
                      </Button>
                      <Button variant="outline" size="sm" className="gap-1" onClick={() => {
                        const blob = new Blob([editYaml], { type: 'text/yaml' })
                        const url = URL.createObjectURL(blob)
                        const a = document.createElement('a')
                        a.href = url; a.download = `${selectedContract.name}.yaml`; a.click()
                        URL.revokeObjectURL(url)
                      }}>
                        <Download className="h-3.5 w-3.5" /> Export
                      </Button>
                      <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-red-500" onClick={() => handleDelete(selectedContract.id)}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-slate-600 mb-4">{selectedContract.description}</p>

                  {/* Validation Summary */}
                  {selectedContract.validations.length > 0 && (
                    <div className="grid grid-cols-3 gap-3 mb-4">
                      <div className="rounded-lg bg-emerald-50 p-3 text-center">
                        <p className="text-lg font-bold text-emerald-700">{passCount}</p>
                        <p className="text-xs text-emerald-600">Passing</p>
                      </div>
                      <div className="rounded-lg bg-amber-50 p-3 text-center">
                        <p className="text-lg font-bold text-amber-700">{warnCount}</p>
                        <p className="text-xs text-amber-600">Warnings</p>
                      </div>
                      <div className="rounded-lg bg-red-50 p-3 text-center">
                        <p className="text-lg font-bold text-red-700">{failCount}</p>
                        <p className="text-xs text-red-600">Failing</p>
                      </div>
                    </div>
                  )}

                  <Tabs defaultValue="fields">
                    <TabsList>
                      <TabsTrigger value="fields">Schema Fields</TabsTrigger>
                      <TabsTrigger value="validations">Validations</TabsTrigger>
                      <TabsTrigger value="yaml">YAML Spec</TabsTrigger>
                      <TabsTrigger value="history">History</TabsTrigger>
                    </TabsList>

                    <TabsContent value="fields">
                      {selectedContract.fields.length > 0 ? (
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Field</TableHead>
                              <TableHead>Type</TableHead>
                              <TableHead>Required</TableHead>
                              <TableHead>Nullable</TableHead>
                              <TableHead>Unique</TableHead>
                              <TableHead>Constraints</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {selectedContract.fields.map((field) => (
                              <TableRow key={field.name}>
                                <TableCell className="font-medium">{field.name}</TableCell>
                                <TableCell><code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">{field.type}</code></TableCell>
                                <TableCell>{field.required ? <CheckCircle2 className="h-4 w-4 text-emerald-500" /> : <XCircle className="h-4 w-4 text-slate-300" />}</TableCell>
                                <TableCell>{field.nullable ? <CheckCircle2 className="h-4 w-4 text-amber-500" /> : <XCircle className="h-4 w-4 text-slate-300" />}</TableCell>
                                <TableCell>{field.unique ? <CheckCircle2 className="h-4 w-4 text-blue-500" /> : <XCircle className="h-4 w-4 text-slate-300" />}</TableCell>
                                <TableCell><code className="text-xs text-slate-500">{field.constraints || '-'}</code></TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      ) : (
                        <div className="text-center py-8 text-slate-400">
                          <Shield className="h-8 w-8 mx-auto mb-2 opacity-50" />
                          <p className="text-sm">No fields defined. Add fields via YAML spec.</p>
                        </div>
                      )}
                    </TabsContent>

                    <TabsContent value="validations" className="space-y-2">
                      {selectedContract.validations.length > 0 ? selectedContract.validations.map((v, i) => (
                        <div key={i} className={cn(
                          'flex items-center gap-3 rounded-lg border p-3',
                          v.status === 'pass' ? 'border-emerald-200' :
                          v.status === 'fail' ? 'border-red-200' : 'border-amber-200'
                        )}>
                          <ValidationIcon status={v.status} />
                          <span className="text-sm text-slate-700 flex-1">{v.rule}</span>
                          <ValidationBadge status={v.status} />
                          {v.message && <span className="text-xs text-slate-400">{v.message}</span>}
                        </div>
                      )) : (
                        <div className="text-center py-8">
                          <Shield className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                          <p className="text-sm text-slate-400">No validations run yet. Click Validate to check.</p>
                        </div>
                      )}
                    </TabsContent>

                    <TabsContent value="yaml">
                      {yamlEditing ? (
                        <div className="space-y-3">
                          <Textarea
                            value={editYaml}
                            onChange={(e) => setEditYaml(e.target.value)}
                            className="min-h-[300px] font-mono text-xs"
                          />
                          <div className="flex items-center gap-2">
                            <Button size="sm" onClick={handleSaveYaml}>Save</Button>
                            <Button size="sm" variant="outline" onClick={() => { setYamlEditing(false); setEditYaml(selectedContract.yamlSpec || generateYamlFromContract(selectedContract)) }}>Cancel</Button>
                          </div>
                        </div>
                      ) : (
                        <div className="relative">
                          <Button variant="outline" size="sm" className="absolute top-2 right-2 z-10 gap-1" onClick={() => setYamlEditing(true)}>
                            <Code className="h-3.5 w-3.5" /> Edit
                          </Button>
                          <div className="rounded-lg bg-slate-900 p-4 font-mono text-xs text-slate-200 whitespace-pre-wrap overflow-x-auto max-h-[400px] overflow-y-auto">
                            {editYaml}
                          </div>
                        </div>
                      )}
                    </TabsContent>

                    <TabsContent value="history" className="space-y-3">
                      {validationHistory.filter((h) => h.contractId === selectedContract.id).length === 0 ? (
                        <div className="text-center py-8">
                          <FileText className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                          <p className="text-sm text-slate-400">No validation history yet</p>
                        </div>
                      ) : validationHistory.filter((h) => h.contractId === selectedContract.id).map((h, i) => (
                        <Card key={i}>
                          <CardContent className="p-3">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-xs font-medium text-slate-700">{new Date(h.timestamp).toLocaleString()}</span>
                              <div className="flex items-center gap-2">
                                <Badge variant="outline" className="text-[10px] bg-emerald-50 text-emerald-700">
                                  {h.results.filter((r) => r.status === 'pass').length} pass
                                </Badge>
                                <Badge variant="outline" className="text-[10px] bg-red-50 text-red-700">
                                  {h.results.filter((r) => r.status === 'fail').length} fail
                                </Badge>
                              </div>
                            </div>
                            <div className="space-y-1">
                              {h.results.map((r, j) => (
                                <div key={j} className="flex items-center gap-2 text-xs">
                                  <ValidationIcon status={r.status} />
                                  <span className="text-slate-600">{r.rule}</span>
                                </div>
                              ))}
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </TabsContent>
                  </Tabs>

                  {selectedContract.lastValidated && (
                    <p className="text-xs text-slate-400 mt-4">
                      Last validated: {new Date(selectedContract.lastValidated).toLocaleString()}
                    </p>
                  )}
                </CardContent>
              </Card>
            </div>
          ) : (
            <Card>
              <CardContent className="p-12 text-center">
                <FileCheck className="h-12 w-12 text-slate-300 mx-auto mb-4" />
                <h3 className="font-semibold text-slate-700 mb-1">Select a Contract</h3>
                <p className="text-sm text-slate-400">Choose a contract to view schema and validations</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
