import { NextRequest, NextResponse } from 'next/server'

const BACKEND = 'http://localhost:3001/api'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string; tableName: string }> }
) {
  const { id, tableName } = await params
  const { searchParams } = new URL(request.url)
  const limit = searchParams.get('limit') || '100'
  const url = `${BACKEND}/connectors/${id}/tables/${encodeURIComponent(tableName)}?limit=${limit}`
  try {
    const res = await fetch(url)
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 502 })
  }
}