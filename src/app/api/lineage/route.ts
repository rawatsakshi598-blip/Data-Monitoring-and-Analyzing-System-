import { NextRequest, NextResponse } from 'next/server'

const BACKEND = 'http://localhost:3001/api'

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const qs = searchParams.toString()
  const path = request.nextUrl.pathname.replace(/^\/api/, '')
  const url = `${BACKEND}${path}${qs ? '?' + qs : ''}`
  try {
    const res = await fetch(url)
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 502 })
  }
}
