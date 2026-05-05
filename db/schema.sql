-- DataGuard Database Schema
-- Converted from Prisma to raw SQL per project conventions

-- ============================================
-- CORE ENTITIES
-- ============================================

CREATE TABLE IF NOT EXISTS Service (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  platform TEXT NOT NULL DEFAULT '',
  connection TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'active',
  createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
  updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_service_type ON Service(type);
CREATE INDEX IF NOT EXISTS idx_service_status ON Service(status);

CREATE TABLE IF NOT EXISTS Table_entity (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  fullyQualifiedName TEXT NOT NULL DEFAULT '',
  serviceId TEXT NOT NULL REFERENCES Service(id),
  columns TEXT NOT NULL DEFAULT '[]',
  columnCount INTEGER NOT NULL DEFAULT 0,
  rowCount INTEGER NOT NULL DEFAULT 0,
  qualityScore REAL NOT NULL DEFAULT 0,
  freshnessStatus TEXT NOT NULL DEFAULT 'fresh',
  schemaHash TEXT NOT NULL DEFAULT '',
  tags TEXT NOT NULL DEFAULT '[]',
  owners TEXT NOT NULL DEFAULT '[]',
  description TEXT NOT NULL DEFAULT '',
  lastProfiledAt DATETIME,
  createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
  updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_table_serviceId ON Table_entity(serviceId);
CREATE INDEX IF NOT EXISTS idx_table_freshness ON Table_entity(freshnessStatus);

CREATE TABLE IF NOT EXISTS Dataset (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  serviceId TEXT REFERENCES Service(id),
  tableName TEXT NOT NULL DEFAULT '',
  filePath TEXT NOT NULL DEFAULT '',
  format TEXT NOT NULL DEFAULT 'csv',
  rowCount INTEGER NOT NULL DEFAULT 0,
  columnCount INTEGER NOT NULL DEFAULT 0,
  qualityScore REAL NOT NULL DEFAULT 0,
  metadata TEXT NOT NULL DEFAULT '{}',
  createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
  updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_dataset_serviceId ON Dataset(serviceId);
CREATE INDEX IF NOT EXISTS idx_dataset_format ON Dataset(format);

-- ============================================
-- QUALITY RULES
-- ============================================

CREATE TABLE IF NOT EXISTS QualityRule (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  ruleType TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'built-in',
  severity TEXT NOT NULL DEFAULT 'warning',
  checkType TEXT NOT NULL,
  checkConfig TEXT NOT NULL DEFAULT '{}',
  generatedCode TEXT,
  naturalLanguage TEXT,
  codeLanguage TEXT NOT NULL DEFAULT 'python',
  datasetId TEXT REFERENCES Dataset(id),
  tableName TEXT NOT NULL DEFAULT '',
  columnName TEXT NOT NULL DEFAULT '',
  isActive INTEGER NOT NULL DEFAULT 1,
  lastTriggered DATETIME,
  lastResult TEXT,
  runCount INTEGER NOT NULL DEFAULT 0,
  failCount INTEGER NOT NULL DEFAULT 0,
  createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
  updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_rule_type ON QualityRule(ruleType);
CREATE INDEX IF NOT EXISTS idx_rule_category ON QualityRule(category);
CREATE INDEX IF NOT EXISTS idx_rule_table ON QualityRule(tableName);

-- ============================================
-- CHECK RESULTS
-- ============================================

CREATE TABLE IF NOT EXISTS QualityCheck (
  id TEXT PRIMARY KEY,
  ruleId TEXT NOT NULL REFERENCES QualityRule(id),
  datasetId TEXT REFERENCES Dataset(id),
  tableName TEXT NOT NULL DEFAULT '',
  columnName TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL,
  passed INTEGER NOT NULL DEFAULT 0,
  message TEXT NOT NULL DEFAULT '',
  totalRows INTEGER NOT NULL DEFAULT 0,
  passedRows INTEGER NOT NULL DEFAULT 0,
  failedRows INTEGER NOT NULL DEFAULT 0,
  passRate REAL NOT NULL DEFAULT 0,
  metricValue REAL NOT NULL DEFAULT 0,
  thresholdValue REAL NOT NULL DEFAULT 0,
  failedSamples TEXT NOT NULL DEFAULT '[]',
  executionTimeMs INTEGER NOT NULL DEFAULT 0,
  executedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_check_ruleId ON QualityCheck(ruleId);
CREATE INDEX IF NOT EXISTS idx_check_status ON QualityCheck(status);

-- ============================================
-- DQ TESTS (Legacy)
-- ============================================

CREATE TABLE IF NOT EXISTS DQTest (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT NOT NULL DEFAULT 'custom',
  status TEXT NOT NULL DEFAULT 'pending',
  tableId TEXT NOT NULL REFERENCES Table_entity(id),
  columnName TEXT NOT NULL DEFAULT '',
  config TEXT NOT NULL DEFAULT '{}',
  severity TEXT NOT NULL DEFAULT 'warning',
  createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
  updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_dqtest_tableId ON DQTest(tableId);

CREATE TABLE IF NOT EXISTS DQTestResult (
  id TEXT PRIMARY KEY,
  testId TEXT NOT NULL REFERENCES DQTest(id),
  status TEXT NOT NULL,
  score REAL NOT NULL DEFAULT 0,
  message TEXT NOT NULL DEFAULT '',
  metrics TEXT NOT NULL DEFAULT '{}',
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_dqresult_testId ON DQTestResult(testId);

-- ============================================
-- PROFILING
-- ============================================

CREATE TABLE IF NOT EXISTS TableProfile (
  id TEXT PRIMARY KEY,
  tableId TEXT NOT NULL REFERENCES Table_entity(id),
  profileData TEXT NOT NULL DEFAULT '{}',
  rowCount INTEGER NOT NULL DEFAULT 0,
  columnCount INTEGER NOT NULL DEFAULT 0,
  duration INTEGER NOT NULL DEFAULT 0,
  createdAt DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_profile_tableId ON TableProfile(tableId);

-- ============================================
-- LINEAGE
-- ============================================

CREATE TABLE IF NOT EXISTS DataLineage (
  id TEXT PRIMARY KEY,
  sourceTableId TEXT NOT NULL REFERENCES Table_entity(id),
  targetTableId TEXT NOT NULL REFERENCES Table_entity(id),
  transformation TEXT NOT NULL DEFAULT '',
  columnLineage TEXT NOT NULL DEFAULT '[]',
  createdAt DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_lineage_source ON DataLineage(sourceTableId);
CREATE INDEX IF NOT EXISTS idx_lineage_target ON DataLineage(targetTableId);

-- ============================================
-- ALERTS
-- ============================================

CREATE TABLE IF NOT EXISTS Alert (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  alertType TEXT NOT NULL,
  severity TEXT NOT NULL DEFAULT 'warning',
  status TEXT NOT NULL DEFAULT 'open',
  sourceType TEXT NOT NULL DEFAULT '',
  sourceId TEXT NOT NULL DEFAULT '',
  sourceName TEXT NOT NULL DEFAULT '',
  metricValue TEXT NOT NULL DEFAULT '',
  suggestion TEXT NOT NULL DEFAULT '',
  createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
  updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_alert_type ON Alert(alertType);
CREATE INDEX IF NOT EXISTS idx_alert_status ON Alert(status);

-- ============================================
-- GOVERNANCE
-- ============================================

CREATE TABLE IF NOT EXISTS Tag (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'default',
  description TEXT NOT NULL DEFAULT '',
  color TEXT NOT NULL DEFAULT '#6366f1',
  createdAt DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_tag_category ON Tag(category);

CREATE TABLE IF NOT EXISTS GlossaryTerm (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  definition TEXT NOT NULL DEFAULT '',
  category TEXT NOT NULL DEFAULT 'general',
  status TEXT NOT NULL DEFAULT 'draft',
  relatedTerms TEXT NOT NULL DEFAULT '[]',
  createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
  updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_glossary_status ON GlossaryTerm(status);

CREATE TABLE IF NOT EXISTS Team (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  members TEXT NOT NULL DEFAULT '[]',
  createdAt DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- ACTIVITY LOG
-- ============================================

CREATE TABLE IF NOT EXISTS Activity (
  id TEXT PRIMARY KEY,
  action TEXT NOT NULL,
  entityType TEXT NOT NULL,
  entityId TEXT NOT NULL DEFAULT '',
  entityName TEXT NOT NULL DEFAULT '',
  description TEXT NOT NULL DEFAULT '',
  userId TEXT NOT NULL DEFAULT 'system',
  metadata TEXT NOT NULL DEFAULT '{}',
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_activity_entity ON Activity(entityType, entityId);

-- ============================================
-- QUALITY REPORTS (LLM-generated)
-- ============================================

CREATE TABLE IF NOT EXISTS QualityReport (
  id TEXT PRIMARY KEY,
  tableName TEXT NOT NULL,
  datasetId TEXT DEFAULT '',
  overallScore REAL NOT NULL DEFAULT 0,
  totalChecks INTEGER NOT NULL DEFAULT 0,
  passedChecks INTEGER NOT NULL DEFAULT 0,
  failedChecks INTEGER NOT NULL DEFAULT 0,
  summary TEXT NOT NULL DEFAULT '',
  diagnosis TEXT NOT NULL DEFAULT '',
  actionPlan TEXT NOT NULL DEFAULT '',
  fixCode TEXT NOT NULL DEFAULT '',
  fixLanguage TEXT NOT NULL DEFAULT 'python',
  checkResults TEXT NOT NULL DEFAULT '[]',
  createdAt DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_report_table ON QualityReport(tableName);
