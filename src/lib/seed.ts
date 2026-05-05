/**
 * Database seeder — uses better-sqlite3 (not Prisma)
 * Run with: bunx tsx src/lib/seed.ts
 *
 * Note: The Python backend (port 3001) handles its own DB init/seed
 * via init_db(). This script is for standalone Node.js seeding if needed.
 */
import { db } from './db'
import { v4 as uuidv4 } from 'uuid'

function seed() {
  // Check if already seeded
  const count = (db.prepare('SELECT COUNT(*) as cnt FROM Service').get() as any).cnt
  if (count > 0) {
    console.log('Database already seeded, skipping.')
    return
  }

  const insertService = db.prepare(`
    INSERT INTO Service (id, name, type, description, platform, connection, status)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `)

  const services = [
    { name: 'analytics-warehouse', type: 'database', description: 'Central analytics data warehouse built on Snowflake', platform: 'snowflake', connection: JSON.stringify({ account: 'corp', warehouse: 'ANALYTICS_WH' }) },
    { name: 'postgres-production', type: 'database', description: 'Primary PostgreSQL database for customer and order data', platform: 'postgresql', connection: JSON.stringify({ host: 'db-master.internal', database: 'production' }) },
    { name: 'kafka-events', type: 'messaging', description: 'Apache Kafka cluster for real-time event streaming', platform: 'kafka', connection: JSON.stringify({ brokers: ['kafka-broker1:9092'] }) },
    { name: 's3-data-lake', type: 'storage', description: 'AWS S3 data lake for raw and processed data', platform: 's3', connection: JSON.stringify({ bucket: 'company-data-lake' }) },
    { name: 'airflow-orchestrator', type: 'pipeline', description: 'Apache Airflow for DAG scheduling', platform: 'airflow', connection: JSON.stringify({ url: 'http://airflow.internal:8080' }) },
    { name: 'metabase-dashboard', type: 'dashboard', description: 'Metabase for BI dashboards', platform: 'metabase', connection: JSON.stringify({ url: 'http://metabase.internal:3000' }) },
    { name: 'bigquery-ml-training', type: 'mlModel', description: 'BigQuery datasets for ML training', platform: 'bigquery', connection: JSON.stringify({ project: 'ml-platform' }) },
  ]

  const serviceIds: Record<string, string> = {}
  for (const s of services) {
    const id = uuidv4()
    insertService.run(id, s.name, s.type, s.description, s.platform, s.connection, 'active')
    serviceIds[s.name] = id
  }

  // Tags
  const insertTag = db.prepare(`INSERT INTO Tag (id, name, category, description, color) VALUES (?, ?, ?, ?, ?)`)
  const tags = [
    { name: 'PII', category: 'Classification', description: 'Personally Identifiable Information', color: '#ef4444' },
    { name: 'Sensitive', category: 'Classification', description: 'Data requiring special handling', color: '#f97316' },
    { name: 'Financial', category: 'Domain', description: 'Financial records', color: '#8b5cf6' },
    { name: 'Gold', category: 'Tier', description: 'Critical business table', color: '#f59e0b' },
    { name: 'Silver', category: 'Tier', description: 'Important business table', color: '#94a3b8' },
    { name: 'Bronze', category: 'Tier', description: 'Raw data', color: '#d97706' },
  ]
  for (const t of tags) {
    insertTag.run(uuidv4(), t.name, t.category, t.description, t.color)
  }

  // Glossary Terms
  const insertGlossary = db.prepare(`INSERT INTO GlossaryTerm (id, name, definition, category, status) VALUES (?, ?, ?, ?, ?)`)
  const terms = [
    { name: 'Customer', definition: 'An individual or organization that purchases products or services', category: 'Business Entity' },
    { name: 'Transaction', definition: 'A record of a commercial exchange', category: 'Business Entity' },
    { name: 'Monthly Active Users', definition: 'Count of unique users in the last 30 days', category: 'Metric' },
  ]
  for (const t of terms) {
    insertGlossary.run(uuidv4(), t.name, t.definition, t.category, 'approved')
  }

  // Teams
  const insertTeam = db.prepare(`INSERT INTO Team (id, name, description, members) VALUES (?, ?, ?, ?)`)
  const teams = [
    { name: 'data-engineering', description: 'Manages data pipelines and ETL', members: JSON.stringify(['alice', 'bob']) },
    { name: 'analytics', description: 'Business intelligence and reporting', members: JSON.stringify(['eve', 'frank']) },
    { name: 'data-science', description: 'ML models and experiments', members: JSON.stringify(['henry', 'iris']) },
  ]
  for (const t of teams) {
    insertTeam.run(uuidv4(), t.name, t.description, t.members)
  }

  console.log('Seed data created successfully')
  console.log(`  Services: ${services.length}`)
  console.log(`  Tags: ${tags.length}`)
  console.log(`  Glossary Terms: ${terms.length}`)
  console.log(`  Teams: ${teams.length}`)
}

seed()
