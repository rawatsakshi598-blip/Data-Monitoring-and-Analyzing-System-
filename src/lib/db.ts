import Database from 'better-sqlite3'
import path from 'path'
import fs from 'fs'

const dbDir = path.join(process.cwd(), 'db')
if (!fs.existsSync(dbDir)) fs.mkdirSync(dbDir, { recursive: true })

const db = new Database(path.join(dbDir, 'custom.db'))
db.pragma('journal_mode = WAL')
db.pragma('foreign_keys = ON')

const schemaPath = path.join(dbDir, 'schema.sql')
if (fs.existsSync(schemaPath)) {
  db.exec(fs.readFileSync(schemaPath, 'utf-8'))
}

export { db }
