import sqlite3, json, uuid, random
from datetime import datetime, timezone, timedelta

conn = sqlite3.connect("db/custom.db")
cur = conn.cursor()
cur.execute('SELECT id, name, rowCount FROM "Table" LIMIT 1')
table = cur.fetchone()
table_id, table_name, row_count = table[0], table[1], table[2]
now = datetime.now(timezone.utc).isoformat()

# Create Dataset
dataset_id = uuid.uuid4().hex
cur.execute(
    "INSERT INTO Dataset (id,name,description,type,status,rowCount,columnCount,qualityScore,lastChecked,createdAt,updatedAt) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
    (
        dataset_id,
        table_name,
        "Customer data",
        "sqlite",
        "active",
        row_count,
        6,
        78.5,
        now,
        now,
        now,
    ),
)

# Create 8 QualityRules
rules = [
    (
        "Completeness - Email Not Null",
        "completeness",
        "completeness",
        '{"column":"email","threshold":0.95}',
        "critical",
    ),
    (
        "Uniqueness - Customer ID",
        "uniqueness",
        "uniqueness",
        '{"column":"customer_id","threshold":1.0}',
        "critical",
    ),
    (
        "Validity - Age Range",
        "validity",
        "validity",
        '{"column":"age","min":0,"max":120}',
        "warning",
    ),
    (
        "Completeness - Name",
        "completeness",
        "completeness",
        '{"column":"name","threshold":0.99}',
        "warning",
    ),
    (
        "Validity - Email Format",
        "validity",
        "validity",
        '{"column":"email","pattern":"email"}',
        "critical",
    ),
    (
        "Freshness - Signup Date",
        "freshness",
        "timeliness",
        '{"column":"signup_date","maxAgeHours":8760}',
        "warning",
    ),
    ("Volume - Minimum Rows", "volume", "completeness", '{"minRows":100}', "critical"),
    (
        "Uniqueness - Email",
        "uniqueness",
        "uniqueness",
        '{"column":"email","threshold":0.99}',
        "critical",
    ),
]
rule_ids = []
for name, rtype, dim, config, sev in rules:
    rid = uuid.uuid4().hex
    rule_ids.append(rid)
    cur.execute(
        "INSERT INTO QualityRule (id,name,type,dimension,config,severity,datasetId,enabled,schedule,createdAt,updatedAt) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (rid, name, rtype, dim, config, sev, dataset_id, 1, "manual", now, now),
    )

# Create 24 QualityCheck results (3 runs × 8 rules)
outcomes = [
    [
        (0, "failed", 72.3, 71),
        (1, "passed", 100.0, 0),
        (2, "warning", 88.5, 12),
        (3, "passed", 99.2, 12),
        (4, "failed", 65.2, 125),
        (5, "passed", 94.1, 0),
        (6, "passed", 100.0, 0),
        (7, "warning", 91.8, 123),
    ],
    [
        (0, "failed", 73.1, 68),
        (1, "passed", 100.0, 0),
        (2, "warning", 89.2, 10),
        (3, "passed", 99.5, 8),
        (4, "failed", 66.8, 118),
        (5, "passed", 95.3, 0),
        (6, "passed", 100.0, 0),
        (7, "warning", 92.4, 114),
    ],
    [
        (0, "failed", 70.8, 78),
        (1, "passed", 100.0, 0),
        (2, "failed", 79.1, 24),
        (3, "passed", 98.7, 19),
        (4, "failed", 62.5, 141),
        (5, "warning", 90.2, 0),
        (6, "passed", 100.0, 0),
        (7, "warning", 89.6, 156),
    ],
]
random.seed(42)
for run_idx, run_outcomes in enumerate(outcomes):
    run_time = (
        datetime.now(timezone.utc) - timedelta(hours=(run_idx + 1) * 6)
    ).isoformat()
    for r_idx, status, score, failed in run_outcomes:
        cid = uuid.uuid4().hex
        cur.execute(
            "INSERT INTO QualityCheck (id,ruleId,datasetId,status,score,recordsChecked,recordsFailed,duration,failures,createdAt) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                cid,
                rule_ids[r_idx],
                dataset_id,
                status,
                score,
                row_count,
                failed,
                random.randint(45, 380),
                "[]",
                run_time,
            ),
        )

conn.commit()
conn.close()
print("Seeded successfully!")
