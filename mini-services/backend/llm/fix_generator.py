"""
Fix Generator - LLM-powered fix suggestions
Falls back to template when no LLM available
"""

import json
import os
from llm.client import call_llm, extract_json
from llm.prompts import FIX_SYSTEM, FIX_USER


def _template_fix(rule_name: str, check_result: dict) -> dict:
    status = check_result.get("status", "failed")
    score = check_result.get("score", 0)
    message = check_result.get("message", "")
    
    if "null" in message.lower() or "missing" in message.lower() or "completeness" in rule_name.lower():
        fix_code = (
            "# Fix null/missing values\n"
            "import pandas as pd\n"
            "# df['column'] = df['column'].fillna(df['column'].median())  # numeric\n"
            "# df['column'] = df['column'].fillna('unknown')  # string\n"
            "# df = df.dropna(subset=['column'])  # drop rows\n"
        )
        explanation = "Fill null values with appropriate defaults or drop rows with missing data."
    elif "unique" in message.lower() or "duplicate" in message.lower():
        fix_code = (
            "# Fix duplicate values\n"
            "import pandas as pd\n"
            "# df = df.drop_duplicates(subset=['column'])\n"
            "# df['column'] = df.groupby('column').cumcount().astype(str) + '_' + df['column']\n"
        )
        explanation = "Remove duplicates or make values unique by appending a counter."
    elif "format" in message.lower() or "email" in message.lower() or "valid" in message.lower():
        fix_code = (
            "# Fix format/validation issues\n"
            "import pandas as pd\n"
            "import re\n"
            "# valid = df['column'].str.match(r'^pattern$')\n"
            "# invalid = df[~valid]\n"
            "# df.loc[~valid, 'column'] = df.loc[~valid, 'column'].apply(fix_function)\n"
        )
        explanation = "Identify invalid format values and correct them or flag for review."
    else:
        fix_code = (
            "# General fix\n"
            "import pandas as pd\n"
            "# Investigate failed records\n"
            "# failed = df[df['column'].apply(check_function) == False]\n"
            "# Apply corrections based on root cause\n"
        )
        explanation = f"Investigate the {score}% score issue and apply targeted corrections."

    return {
        "fix_code": fix_code,
        "explanation": explanation,
        "generationMethod": "template",
    }


def generate(rule_name: str, check_result: dict) -> dict:
    api_key = os.environ.get("LLM_API_KEY", "")
    
    if api_key:
        user_prompt = FIX_USER.format(
            rule_name=rule_name,
            check_result=json.dumps(check_result),
        )
        response = call_llm(FIX_SYSTEM, user_prompt, temperature=0.3)
        if response:
            data = extract_json(response)
            if data and data.get("fix_code"):
                data["generationMethod"] = "llm"
                return data
    
    return _template_fix(rule_name, check_result)


class FixGenerator:
    def generate(self, rule_name: str, check_result: dict) -> dict:
        return generate(rule_name, check_result)
