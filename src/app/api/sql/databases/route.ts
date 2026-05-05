import { NextResponse } from 'next/server'

const BACKEND = 'http://localhost:3001/api'

export async function GET() {
  try {
    const res = await fetch(`${BACKEND}/sql/databases`)
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ error: 'Backend unavailable — please ensure the Python backend is running on port 3001' }, { status: 502 })
  }
}
