import { NextRequest, NextResponse } from 'next/server'

const BACKEND = 'http://localhost:3001/api'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
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

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const path = request.nextUrl.pathname.replace(/^\/api/, '')
  const url = `${BACKEND}${path}`
  try {
    const res = await fetch(url, { method: 'DELETE' })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 502 })
  }
}
