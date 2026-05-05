import { NextRequest, NextResponse } from 'next/server'

const BACKEND = 'http://localhost:3001/api'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const res = await fetch(`${BACKEND}/copilot/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error: any) {
    console.error('[copilot/chat proxy] Error:', error?.message || error)
    return NextResponse.json(
      {
        error: 'Backend unavailable — please ensure the Python backend is running on port 3001',
        hint: 'Run: cd mini-services/backend && python index.py',
      },
      { status: 502 },
    )
  }
}