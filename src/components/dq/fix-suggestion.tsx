'use client'

import { useState } from 'react'
import { Wrench, Loader2, AlertCircle, CheckCircle2, Copy } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'

interface Fix {
  fix_code: string
  explanation: string
  generationMethod?: string
}

interface Props {
  ruleName: string
  checkResult: { status: string; score: number; message: string }
}

export default function FixSuggestion({ ruleName, checkResult }: Props) {
  const [fix, setFix] = useState<Fix | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function generateFix() {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/ai/generate-fix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ruleName, checkResult }),
      })
      if (!res.ok) throw new Error('Failed to generate fix')
      const data = await res.json()
      setFix(data.fix || data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fix generation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Wrench className="h-4 w-4" />
          AI Fix Suggestion — {ruleName}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-2 text-sm">
          <Badge variant={checkResult.status === 'failed' ? 'destructive' : 'outline'}>{checkResult.status}</Badge>
          <span className="text-slate-500">Score: {checkResult.score}%</span>
        </div>
        <p className="text-sm text-slate-600">{checkResult.message}</p>

        <Button onClick={generateFix} disabled={loading} size="sm">
          {loading ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Generating fix...</> : <><Wrench className="h-4 w-4 mr-2" />Suggest Fix</>}
        </Button>

        {error && <div className="flex items-center gap-2 text-red-600 text-sm"><AlertCircle className="h-4 w-4" />{error}</div>}

        {fix && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              <Badge variant="outline">{fix.generationMethod || 'generated'}</Badge>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-slate-700 mb-1">Explanation</h4>
              <p className="text-sm text-slate-600">{fix.explanation}</p>
            </div>
            {fix.fix_code && (
              <div>
                <div className="flex items-center justify-between mb-1">
                  <h4 className="text-sm font-semibold text-slate-700">Fix Code</h4>
                  <Button variant="ghost" size="sm" onClick={() => { navigator.clipboard.writeText(fix.fix_code); toast.success('Copied!') }}>
                    <Copy className="h-3 w-3 mr-1" />Copy
                  </Button>
                </div>
                <pre className="bg-slate-900 text-slate-100 rounded-lg p-3 text-xs font-mono overflow-x-auto">{fix.fix_code}</pre>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
