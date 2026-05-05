import { NextRequest, NextResponse } from 'next/server'

const BACKEND = 'http://localhost:3001/api'

export async function POST(request: NextRequest) {
  const path = request.nextUrl.pathname.replace(/^\/api/, '')
  const url = `${BACKEND}${path}`
  try {
    const body = await request.json()
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 502 })
  }
}
