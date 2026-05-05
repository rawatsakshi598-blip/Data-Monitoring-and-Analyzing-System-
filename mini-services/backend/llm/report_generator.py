"""
Report Generator - LLM-powered quality report from check results
Falls back to template when no LLM available
"""

import json
import re
from llm.client import call_llm, extract_json
from llm.prompts import REPORT_SYSTEM, REPORT_USER


def _template_fallback(table_name, checks):
    passed = sum(1 for c in checks if c.get("status") == "passed")
    failed = len(checks) - passed
    total = len(checks)
    avg_score = round(sum(c.get("score", 100) for c in checks) / max(total, 1), 1)

    failures = [c for c in checks if c.get("status") == "failed"]
    failure_details = []
    for f in failures:
        msg = f.get("message", "")
        if not msg:
            msg = f"score={f.get('score', 0)}, records_failed={f.get('recordsFailed', 0)}"
        failure_details.append(f"- {msg}")

    if not failures:
        diagnosis = "All quality checks passed. Data meets defined quality thresholds."
        action_plan = "1. Continue monitoring.\n2. Schedule next quality check cycle."
        fix_code = ""
    else:
        diagnosis = f"{failed} of {total} checks failed:\n" + "\n".join(failure_details)
        action_plan = (
            "1. Review each failed check above.\n"
            "2. Investigate root cause (ETL bug, schema change, data source issue).\n"
            "3. Apply targeted fixes to affected columns.\n"
            "4. Re-run quality checks to verify fixes."
        )
        fix_code = ""

    return {
        "summary": f"Table '{table_name}': {passed}/{total} checks passed, average score {avg_score}%.",
        "diagnosis": diagnosis,
        "action_plan": action_plan,
        "fix_code": fix_code,
        "table_name": table_name,
        "passed": passed,
        "failed": failed,
        "total": total,
        "average_score": avg_score,
        "generationMethod": "template",
    }


def generate(dataset, checks):
    table_name = dataset.get("name", "unknown") if isinstance(dataset, dict) else "unknown"
    passed = sum(1 for c in checks if c.get("status") == "passed")
    failed = len(checks) - passed
    total = len(checks)
    avg_score = round(sum(c.get("score", 100) for c in checks) / max(total, 1), 1)

    results_summary = json.dumps([
        {
            "status": c.get("status"),
            "score": c.get("score"),
            "message": (c.get("message", "")[:100] if c.get("message") else ""),
        }
        for c in checks[:20]
    ])

    user_prompt = REPORT_USER.format(
        table_name=table_name,
        check_results=results_summary,
        passed=passed,
        failed=failed,
        total=total,
    )

    # Force JSON output from LLM
    user_prompt += (
        "\n\nIMPORTANT: Respond ONLY with valid JSON using these exact keys: "
        '{"summary": "string", "diagnosis": "string", "action_plan": "string", '
        '"fix_code": "string or empty", "average_score": number}'
    )

    response = call_llm(REPORT_SYSTEM, user_prompt, temperature=0.3)

    if response:
        report = extract_json(response)
        if report and isinstance(report, dict):
            if not report.get("summary"):
                report["summary"] = f"Table '{table_name}': {passed}/{total} checks passed."
            report["generationMethod"] = "llm"
            report["table_name"] = table_name
            report["passed"] = passed
            report["failed"] = failed
            report["total"] = total
            report["average_score"] = report.get("average_score", avg_score)
            return report

        # LLM responded but not valid JSON — use raw text as report
        text = response.strip()
        # Remove markdown wrappers if present
        if text.startswith("```"):
            text = re.sub(r'^```\w*\n?', '', text)
            text = re.sub(r'\n?```$', '', text)
            text = text.strip()

        summary = text[:400]
        diagnosis = text
        action_plan = ""
        fix_code = ""

        # Try to extract sections from prose
        diag_m = re.search(
            r'(?:diagnosis|analysis|findings|issues? found)[:\s]*\n?(.*?)'
            r'(?=(?:action[_ ]?plan|recommendation|fix|suggestion|next[_ ]?step|$))',
            text, re.IGNORECASE | re.DOTALL
        )
        if diag_m:
            diagnosis = diag_m.group(1).strip()
            summary = diagnosis[:400]

        action_m = re.search(
            r'(?:action[_ ]?plan|recommendations?|next[_ ]?steps?|suggested[_ ]?actions?)[:\s]*\n?(.*?)'
            r'(?=(?:fix[_ ]?code|```|$))',
            text, re.IGNORECASE | re.DOTALL
        )
        if action_m:
            action_plan = action_m.group(1).strip()

        code_m = re.search(r'```(?:python)?\s*(.*?)```', text, re.DOTALL)
        if code_m:
            fix_code = code_m.group(1).strip()

        return {
            "summary": summary,
            "diagnosis": diagnosis,
            "action_plan": action_plan,
            "fix_code": fix_code,
            "table_name": table_name,
            "passed": passed,
            "failed": failed,
            "total": total,
            "average_score": avg_score,
            "generationMethod": "llm",
        }

    return _template_fallback(table_name, checks)


class ReportGenerator:
    def generate(self, dataset, checks):
        return generate(dataset, checks)
