import { NextResponse } from 'next/server'

export async function GET() {
  try {
    const res = await fetch('http://localhost:3001/api/')
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 502 })
  }
}
