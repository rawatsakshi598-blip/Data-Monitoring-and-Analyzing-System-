'use client'

import { useState } from 'react'
import { FileText, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

interface Report {
  summary: string
  diagnosis: string
  action_plan: string
  fix_code: string
  generationMethod?: string
  passed?: number
  failed?: number
  total?: number
  average_score?: number
}

interface Props {
  datasetId: string
  datasetName?: string
}

export default function QualityReport({ datasetId, datasetName }: Props) {
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function generateReport() {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/ai/generate-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ datasetId }),
      })
      if (!res.ok) throw new Error('Failed to generate report')
      const data = await res.json()
      setReport(data.report || data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Report generation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <FileText className="h-4 w-4" />
          AI Quality Report — {datasetName || datasetId.slice(0, 8)}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Button onClick={generateReport} disabled={loading || !datasetId}>
          {loading ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Generating...</> : <><FileText className="h-4 w-4 mr-2" />Generate Report</>}
        </Button>

        {error && <div className="flex items-center gap-2 text-red-600 text-sm"><AlertCircle className="h-4 w-4" />{error}</div>}

        {report && (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              <Badge variant="outline">{report.generationMethod || 'generated'}</Badge>
              {report.average_score != null && <Badge variant="secondary">Score: {report.average_score}%</Badge>}
              {report.passed != null && <Badge variant="secondary">{report.passed}/{report.total} passed</Badge>}
            </div>

            <div>
              <h4 className="text-sm font-semibold text-slate-700 mb-1">Summary</h4>
              <p className="text-sm text-slate-600">{report.summary}</p>
            </div>

            <div>
              <h4 className="text-sm font-semibold text-slate-700 mb-1">Diagnosis</h4>
              <p className="text-sm text-slate-600 whitespace-pre-line">{report.diagnosis}</p>
            </div>

            <div>
              <h4 className="text-sm font-semibold text-slate-700 mb-1">Action Plan</h4>
              <p className="text-sm text-slate-600 whitespace-pre-line">{report.action_plan}</p>
            </div>

            {report.fix_code && (
              <div>
                <h4 className="text-sm font-semibold text-slate-700 mb-1">Suggested Fix</h4>
                <pre className="bg-slate-900 text-slate-100 rounded-lg p-3 text-xs font-mono overflow-x-auto">{report.fix_code}</pre>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
