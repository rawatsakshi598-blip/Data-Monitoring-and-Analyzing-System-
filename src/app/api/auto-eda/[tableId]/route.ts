import { NextRequest, NextResponse } from 'next/server'

const BACKEND = 'http://localhost:3001/api'

export async function GET(request: NextRequest, { params }: { params: Promise<{ tableId: string }> }) {
  const { tableId } = await params
  const url = `${BACKEND}/auto-eda/${encodeURIComponent(tableId)}`
  try {
    const res = await fetch(url)
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 502 })
  }
}
