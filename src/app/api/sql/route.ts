import { NextResponse } from 'next/server'

export async function GET() {
  return NextResponse.json({
    message: 'SQL Playground API',
    endpoints: {
      databases: '/api/sql/databases',
      tables: '/api/sql/tables?database=<name>',
      query: 'POST /api/sql/query { query, database }',
    }
  })
}
