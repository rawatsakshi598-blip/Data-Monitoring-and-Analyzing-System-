import { NextRequest, NextResponse } from 'next/server'

const BACKEND = 'http://localhost:3001/api'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ tableId: string }> }
) {
  try {
    const { tableId } = await params
    const { searchParams } = new URL(request.url)
    const qs = searchParams.toString()
    const url = `${BACKEND}/table-data/${tableId}${qs ? '?' + qs : ''}`

    console.log(`[table-data proxy] Fetching: ${url}`)

    const res = await fetch(url, { signal: AbortSignal.timeout(15000) })

    if (!res.ok) {
      const text = await res.text()
      console.log(`[table-data proxy] Backend returned ${res.status}: ${text.substring(0, 200)}`)
      try {
        const data = JSON.parse(text)
        return NextResponse.json(data, { status: res.status })
      } catch {
        return NextResponse.json({ error: text || `Backend error ${res.status}` }, { status: res.status })
      }
    }

    const data = await res.json()
    console.log(`[table-data proxy] Success: ${data.rows?.length ?? 0} rows`)
    return NextResponse.json(data, { status: res.status })
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err)
    console.error(`[table-data proxy] Error: ${message}`)
    return NextResponse.json(
      { error: `Proxy error: ${message}` },
      { status: 502 }
    )
  }
}
