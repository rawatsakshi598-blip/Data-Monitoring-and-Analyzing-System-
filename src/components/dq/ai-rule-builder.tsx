'use client'

import { useState } from 'react'
import { Sparkles, Loader2, CheckCircle2, AlertCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface Props {
  datasets: { id: string; name: string }[]
  onRuleCreated?: () => void
}

export default function AIRuleBuilder({ datasets, onRuleCreated }: Props) {
  const [prompt, setPrompt] = useState('')
  const [datasetId, setDatasetId] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState('')

  async function handleGenerate() {
    if (!prompt.trim() || !datasetId) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await fetch('/api/nl-rule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt.trim(), datasetId }),
      })
      if (!res.ok) throw new Error('Failed to generate rule')
      const data = await res.json()
      setResult(data)
      onRuleCreated?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="border-dashed border-2 border-primary/20">
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-amber-500" />
          AI Rule Builder
        </CardTitle>
        <CardDescription>Describe your rule in plain English — AI will generate it.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>Rule Description</Label>
          <Textarea
            placeholder="e.g. email should not be null and must contain @ symbol..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="min-h-[80px]"
          />
        </div>
        <div className="flex items-end gap-3">
          <div className="flex-1 space-y-2">
            <Label>Dataset</Label>
            <Select value={datasetId} onValueChange={setDatasetId}>
              <SelectTrigger><SelectValue placeholder="Select dataset" /></SelectTrigger>
              <SelectContent>
                {datasets.map((ds) => (
                  <SelectItem key={ds.id} value={ds.id}>{ds.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button onClick={handleGenerate} disabled={!prompt.trim() || !datasetId || loading}>
            {loading ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Generating...</> : <><Sparkles className="h-4 w-4 mr-2" />Generate</>}
          </Button>
        </div>
        {error && (
          <div className="flex items-center gap-2 text-red-600 text-sm"><AlertCircle className="h-4 w-4" />{error}</div>
        )}
        {result && (
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 space-y-2">
            <div className="flex items-center gap-2 text-emerald-700"><CheckCircle2 className="h-4 w-4" /><span className="font-semibold text-sm">Rule Generated ({String(result.generationMethod || 'unknown').toUpperCase()})</span></div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm">
              <div><p className="text-xs text-muted-foreground">Name</p><p className="font-medium">{String(result.name || '')}</p></div>
              <div><p className="text-xs text-muted-foreground">Type</p><p className="font-medium capitalize">{String(result.type || '')}</p></div>
              <div><p className="text-xs text-muted-foreground">Dimension</p><p className="font-medium capitalize">{String(result.dimension || '')}</p></div>
              <div><p className="text-xs text-muted-foreground">Severity</p><Badge variant="outline">{String(result.severity || '')}</Badge></div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
