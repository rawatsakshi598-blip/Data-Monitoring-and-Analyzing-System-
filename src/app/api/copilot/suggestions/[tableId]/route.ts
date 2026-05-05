import { NextRequest, NextResponse } from 'next/server'

const BACKEND = 'http://localhost:3001/api'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ tableId: string }> }
) {
  const { tableId } = await params
  try {
    const res = await fetch(`${BACKEND}/copilot/suggestions/${tableId}`)
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 502 })
  }
}
