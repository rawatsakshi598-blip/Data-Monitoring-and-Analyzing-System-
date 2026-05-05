#!/usr/bin/env python3
"""
Patch #2 for index.py - Fixes:
1. copilot_suggestions: include ALL categorical columns, not just first 5
2. copilot_suggestions: send "one_hot" (not "onehot") to match encoder
3. execute_transform: smart _fixed naming (strip existing _fixed suffix)
4. copilot_suggestions: also include ALL outlier columns
"""
import os, sys, shutil, re

filepath = sys.argv[1] if len(sys.argv) > 1 else "index.py"
if not os.path.exists(filepath):
    print(f"ERROR: File not found: {filepath}"); sys.exit(1)

backup = filepath + ".bak2"
if not os.path.exists(backup):
    shutil.copy2(filepath, backup)
    print(f"Backup saved to: {backup}")

with open(filepath, "r") as f:
    content = f.read()

applied = 0; skipped = 0; failed = 0

# PATCH 1: encoding config - ALL columns + correct method name
OLD_ENC = '            cat_cols = df.select_dtypes(include=[\'object\', \'category\', \'string\']).columns.tolist()\n            if cat_cols:\n                suggestions.append({\n                    "type": "encoding", "priority": "medium",\n                    "title": f"Encode {len(cat_cols)} categorical columns",\n                    "description": f"Categorical columns need encoding: {\', \'.join(cat_cols[:5])}",\n                    "action": "encoding", "config": {"columns": cat_cols[:5], "method": "onehot"},\n                })'
NEW_ENC = '            cat_cols = df.select_dtypes(include=[\'object\', \'category\', \'string\']).columns.tolist()\n            if cat_cols:\n                suggestions.append({\n                    "type": "encoding", "priority": "medium",\n                    "title": f"Encode {len(cat_cols)} categorical columns",\n                    "description": f"Categorical columns need encoding: {\', \'.join(cat_cols[:8])}{\'...\' if len(cat_cols) > 8 else \'\' }",\n                    "action": "encoding", "config": {"columns": cat_cols, "method": "one_hot"},\n                })'
if OLD_ENC in content:
    content = content.replace(OLD_ENC, NEW_ENC, 1)
    applied += 1; print("PATCH 1 OK: encoding - ALL columns + method=one_hot")
elif '"columns": cat_cols, "method": "one_hot"' in content:
    skipped += 1; print("PATCH 1 SKIP: Already applied")
else:
    failed += 1; print("PATCH 1 FAIL: encoding block not found")

# PATCH 2: outlier config - ALL columns
OLD_OUT = '            if outlier_cols:\n                suggestions.append({\n                    "type": "outlier", "priority": "medium",\n                    "title": "Handle outliers",\n                    "description": f"Outliers detected in: {\', \'.join(outlier_cols[:5])}",\n                    "action": "outlier", "config": {"columns": outlier_cols[:5], "method": "iqr"},\n                })'
NEW_OUT = '            if outlier_cols:\n                suggestions.append({\n                    "type": "outlier", "priority": "medium",\n                    "title": "Handle outliers",\n                    "description": f"Outliers detected in: {\', \'.join(outlier_cols[:8])}{\'...\' if len(outlier_cols) > 8 else \'\' }",\n                    "action": "outlier", "config": {"columns": outlier_cols, "method": "iqr"},\n                })'
if OLD_OUT in content:
    content = content.replace(OLD_OUT, NEW_OUT, 1)
    applied += 1; print("PATCH 2 OK: outlier - ALL columns")
elif '"columns": outlier_cols, "method": "iqr"' in content:
    skipped += 1; print("PATCH 2 SKIP: Already applied")
else:
    failed += 1; print("PATCH 2 FAIL: outlier block not found")

# PATCH 3: smart _fixed naming
OLD_NAME = '                    base_name = orig.get(\'name\', \'data\')\n                    new_table_name = f"{base_name}_fixed"\n                    version = 1\n                    async with get_db() as db:\n                        while await query_one(db, \'SELECT id FROM "Table" WHERE name=?\', (new_table_name,)):\n                            version += 1\n                            new_table_name = f"{base_name}_fixed_v{version}"'
NEW_NAME = '                    base_name = orig.get(\'name\', \'data\')\n                    # Strip existing _fixed_vN or _fixed suffix to avoid chains\n                    clean_base = re.sub(r\'_fixed(_v\\d+)?$\', \'\', base_name)\n                    new_table_name = f"{clean_base}_fixed"\n                    version = 1\n                    async with get_db() as db:\n                        while await query_one(db, \'SELECT id FROM "Table" WHERE name=?\', (new_table_name,)):\n                            version += 1\n                            new_table_name = f"{clean_base}_fixed_v{version}"'
if OLD_NAME in content:
    content = content.replace(OLD_NAME, NEW_NAME, 1)
    applied += 1; print("PATCH 3 OK: Smart _fixed naming")
elif "clean_base = re.sub" in content:
    skipped += 1; print("PATCH 3 SKIP: Already applied")
else:
    failed += 1; print("PATCH 3 FAIL: naming block not found")

# PATCH 4: add 'import re' if missing
if "import re" not in content:
    if "import uuid" in content:
        content = content.replace("import uuid", "import uuid\nimport re", 1)
        applied += 1; print("PATCH 4 OK: Added 'import re'")
    else:
        failed += 1; print("PATCH 4 FAIL: Could not add 'import re'")
else:
    skipped += 1; print("PATCH 4 SKIP: 'import re' already present")

with open(filepath, "w") as f:
    f.write(content)

print()
print("=" * 55)
print(f"  APPLIED: {applied}  |  SKIPPED: {skipped}  |  FAILED: {failed}")
print("=" * 55)
if failed > 0:
    print(f"  Restore: cp {backup} {filepath}")
