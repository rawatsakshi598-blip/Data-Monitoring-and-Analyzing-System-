import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = 'http://localhost:3001'

export async function POST(request: NextRequest) {
  try {
    // Read the full request body as ArrayBuffer and forward to Python backend
    const contentType = request.headers.get('content-type') || ''
    const bodyBuffer = await request.arrayBuffer()

    const headers: Record<string, string> = {}
    if (contentType) headers['content-type'] = contentType
    const contentLength = request.headers.get('content-length')
    if (contentLength) headers['content-length'] = contentLength

    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 30000) // 30s for large files

    const res = await fetch(`${BACKEND_URL}/api/ingest`, {
      method: 'POST',
      headers,
      body: bodyBuffer,
      signal: controller.signal,
    })
    clearTimeout(timeout)

    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (error) {
    console.error('[ingest proxy] Error:', error)
    return NextResponse.json(
      { success: false, error: 'Backend unavailable — please ensure the Python backend is running on port 3001 (cd mini-services/backend && venv/bin/python3 -m uvicorn index:app --port 3001)' },
      { status: 502 }
    )
  }
}

export async function GET() {
  return NextResponse.json({
    message: 'Ingest API — proxies to Python FastAPI backend',
    backend: `${BACKEND_URL}/api/ingest`,
  })
}
