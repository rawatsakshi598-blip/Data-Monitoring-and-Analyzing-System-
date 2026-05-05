#!/usr/bin/env python3
"""
Patch script for index.py — Adds _resolve_table_id_async() and updates 5 endpoints.
Run:  cd mini-services/backend && python3 patch_index.py
"""

import os, sys, shutil

filepath = sys.argv[1] if len(sys.argv) > 1 else "index.py"

if not os.path.exists(filepath):
    print(f"ERROR: File not found: {filepath}")
    print(f"Usage: python3 {sys.argv[0]} [path/to/index.py]")
    sys.exit(1)

# Backup
backup = filepath + ".bak"
if not os.path.exists(backup):
    shutil.copy2(filepath, backup)
    print(f"Backup saved to: {backup}")

with open(filepath, "r") as f:
    content = f.read()

applied = 0
skipped = 0
failed = 0


# ───────────────────────────────────────────────
# PATCH 1: Add _resolve_table_id_async function
# ───────────────────────────────────────────────
RESOLVE_FUNC = '''

async def _resolve_table_id_async(table_id_or_name: str) -> str:
    """Resolve a table name to its UUID. If already a UUID, return as-is."""
    try:
        async with get_db() as db:
            row = await query_one(db, 'SELECT id FROM "Table" WHERE id=?', (table_id_or_name,))
            if row:
                return row['id']
            row = await query_one(db, 'SELECT id FROM "Table" WHERE name=?', (table_id_or_name,))
            if row:
                return row['id']
    except Exception:
        pass
    return table_id_or_name


'''

if "_resolve_table_id_async" not in content:
    marker = '@app.post("/api/transforms/execute")'
    if marker in content:
        content = content.replace(marker, RESOLVE_FUNC + marker, 1)
        applied += 1
        print("PATCH 1 OK: Added _resolve_table_id_async function")
    else:
        failed += 1
        print("PATCH 1 FAIL: Could not find marker for _resolve_table_id_async")
else:
    skipped += 1
    print("PATCH 1 SKIP: _resolve_table_id_async already exists")


# ───────────────────────────────────────────────
# PATCH 2: execute_transform — resolve table name
# ───────────────────────────────────────────────
old2 = '        body = await request.json()\n        table_id = body.get("tableId")\n        transform_type = body.get("transformType")\n        config = body.get("config", {})\n        if not table_id or not transform_type:\n            return JSONResponse(status_code=400, content={"error": "tableId and transformType required"})\n\n        from transformations import get_transformer\n        from transformations.history import TransformHistory\n\n        df = load_dataframe(table_id)\n        if df is None:\n            return JSONResponse(status_code=404, content={"error": "No data found for table"})'

new2 = '        body = await request.json()\n        table_id_raw = body.get("tableId")\n        transform_type = body.get("transformType")\n        config = body.get("config", {})\n        if not table_id_raw or not transform_type:\n            return JSONResponse(status_code=400, content={"error": "tableId and transformType required"})\n\n        # Resolve table name -> UUID so load_dataframe finds the CSV\n        table_id = await _resolve_table_id_async(table_id_raw)\n\n        from transformations import get_transformer\n        from transformations.history import TransformHistory\n\n        df = load_dataframe(table_id)\n        if df is None:\n            return JSONResponse(status_code=404, content={"error": f"No data file found for table (resolved ID: {table_id}). Try re-ingesting the data."})'

if old2 in content:
    idx = content.find('@app.post("/api/transforms/execute")')
    if idx >= 0:
        patch_idx = content.find(old2, idx)
        if patch_idx >= 0:
            content = content[:patch_idx] + new2 + content[patch_idx + len(old2):]
            applied += 1
            print("PATCH 2 OK: execute_transform now resolves table names")
        else:
            failed += 1
            print("PATCH 2 FAIL: Could not find exact block in execute_transform")
    else:
        failed += 1
        print("PATCH 2 FAIL: Could not find execute_transform endpoint")
else:
    skipped += 1
    print("PATCH 2 SKIP: Already applied or block not found")


# ───────────────────────────────────────────────
# PATCH 3: score_ml_readiness — resolve table name
# ───────────────────────────────────────────────
old3 = '        body = await request.json()\n        table_id = body.get("tableId")\n        target_column = body.get("targetColumn", "")\n        if not table_id:\n            return JSONResponse(status_code=400, content={"error": "tableId required"})\n\n        df = load_dataframe(table_id)\n        if df is None:\n            return JSONResponse(status_code=404, content={"error": "No data found for table"})'

new3 = '        body = await request.json()\n        table_id_raw = body.get("tableId")\n        target_column = body.get("targetColumn", "")\n        if not table_id_raw:\n            return JSONResponse(status_code=400, content={"error": "tableId required"})\n\n        # Resolve table name -> UUID so load_dataframe finds the CSV\n        table_id = await _resolve_table_id_async(table_id_raw)\n\n        df = load_dataframe(table_id)\n        if df is None:\n            return JSONResponse(status_code=404, content={"error": f"No data file found for table (resolved ID: {table_id}). Try re-ingesting the data."})'

if '@app.post("/api/ml-readiness")' in content:
    idx = content.find('@app.post("/api/ml-readiness")')
    section = content[idx:idx+800]
    if old3 in section:
        content = content[:idx] + content[idx:].replace(old3, new3, 1)
        applied += 1
        print("PATCH 3 OK: score_ml_readiness now resolves table names")
    else:
        skipped += 1
        print("PATCH 3 SKIP: Already applied or block not found in ml-readiness")
else:
    failed += 1
    print("PATCH 3 FAIL: Could not find ml-readiness endpoint")


# ───────────────────────────────────────────────
# PATCH 4: copilot_suggestions — resolve table name
# ───────────────────────────────────────────────
old4 = '        df = load_dataframe(tableId)\n        async with get_db() as db:\n            tbl = await query_one(db, \'SELECT * FROM "Table" WHERE id=?\', (tableId,))'

new4 = '        # Resolve table name -> UUID\n        resolved_id = await _resolve_table_id_async(tableId)\n        df = load_dataframe(resolved_id)\n        async with get_db() as db:\n            tbl = await query_one(db, \'SELECT * FROM "Table" WHERE id=?\', (resolved_id,))'

if old4 in content and "resolved_id = await _resolve_table_id_async" not in content:
    content = content.replace(old4, new4, 1)
    applied += 1
    print("PATCH 4 OK: copilot_suggestions now resolves table names")
elif "resolved_id = await _resolve_table_id_async" in content:
    skipped += 1
    print("PATCH 4 SKIP: Already applied")
else:
    failed += 1
    print("PATCH 4 FAIL: Exact block not found in copilot_suggestions")


# ───────────────────────────────────────────────
# PATCH 5: profile_table POST — resolve table name
# ───────────────────────────────────────────────
old5 = '        body = await request.json()\n        table_id = body.get("tableId")\n        if not table_id:\n            return JSONResponse(status_code=400, content={"error": "tableId required"})\n        df = load_dataframe(table_id)\n        if df is None:\n            return JSONResponse(status_code=404, content={"error": "No data file found for table"})'

new5 = '        body = await request.json()\n        table_id_raw = body.get("tableId")\n        if not table_id_raw:\n            return JSONResponse(status_code=400, content={"error": "tableId required"})\n        # Resolve table name -> UUID so load_dataframe finds the CSV\n        table_id = await _resolve_table_id_async(table_id_raw)\n        df = load_dataframe(table_id)\n        if df is None:\n            return JSONResponse(status_code=404, content={"error": "No data file found for table"})'

if '@app.post("/api/profile")' in content:
    idx = content.find('@app.post("/api/profile")')
    section = content[idx:idx+600]
    if old5 in section:
        content = content[:idx] + content[idx:].replace(old5, new5, 1)
        applied += 1
        print("PATCH 5 OK: profile_table POST now resolves table names")
    else:
        skipped += 1
        print("PATCH 5 SKIP: Already applied or block not found in profile")
else:
    failed += 1
    print("PATCH 5 FAIL: Could not find profile endpoint")


# ───────────────────────────────────────────────
# PATCH 6: generate_auto_eda — resolve table name
# ───────────────────────────────────────────────
old6 = '        body = await request.json()\n        table_id = body.get("tableId")\n        if not table_id:\n            return JSONResponse(status_code=400, content={"error": "tableId required"})\n\n        df = load_dataframe(table_id)\n        if df is None:\n            return JSONResponse(status_code=404, content={"error": "No data found for table"})\n\n        async with get_db() as db:\n            tbl = await query_one(db, \'SELECT name FROM "Table" WHERE id=?\', (table_id,))\n            table_name = tbl[\'name\'] if tbl else table_id'

new6 = '        body = await request.json()\n        table_id_raw = body.get("tableId")\n        if not table_id_raw:\n            return JSONResponse(status_code=400, content={"error": "tableId required"})\n\n        # Resolve table name -> UUID so load_dataframe finds the CSV\n        table_id = await _resolve_table_id_async(table_id_raw)\n\n        df = load_dataframe(table_id)\n        if df is None:\n            return JSONResponse(status_code=404, content={"error": "No data found for table"})\n\n        async with get_db() as db:\n            tbl = await query_one(db, \'SELECT name FROM "Table" WHERE id=?\', (table_id,))\n            table_name = tbl[\'name\'] if tbl else table_id'

if '@app.post("/api/auto-eda")' in content:
    idx = content.find('@app.post("/api/auto-eda")')
    section = content[idx:idx+800]
    if old6 in section:
        content = content[:idx] + content[idx:].replace(old6, new6, 1)
        applied += 1
        print("PATCH 6 OK: generate_auto_eda now resolves table names")
    else:
        skipped += 1
        print("PATCH 6 SKIP: Already applied or block not found in auto-eda")
else:
    failed += 1
    print("PATCH 6 FAIL: Could not find auto-eda endpoint")


# ───────────────────────────────────────────────
# Write the patched file
# ───────────────────────────────────────────────
with open(filepath, "w") as f:
    f.write(content)

print()
print("=" * 50)
print(f"APPLIED: {applied}  |  SKIPPED: {skipped}  |  FAILED: {failed}")
print("=" * 50)
if failed > 0:
    print()
    print("Some patches failed. You can manually add this line after reading table_id:")
    print('    table_id = await _resolve_table_id_async(table_id_raw)')
    print(f"Restore backup: cp {backup} {filepath}")
