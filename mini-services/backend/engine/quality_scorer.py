from models.check_result import CheckResult

WEIGHTS = {
    "completeness": 20, "uniqueness": 20, "validity": 20,
    "freshness": 15, "volume": 10, "schema": 15,
}


class QualityScorer:
    def calculate_score(self, results: list[CheckResult]) -> float:
        if not results:
            return 100.0
        total_w = 0
        weighted = 0
        for r in results:
            w = WEIGHTS.get(r.metric_value, 10) if hasattr(r, 'metric_value') else 10
            total_w += w
            weighted += w * (r.score / 100)
        if total_w == 0:
            return 100.0
        return round(min(max((weighted / total_w) * 100, 0), 100), 1)

    def calculate_table_score(self, results: list[CheckResult]) -> dict:
        if not results:
            return {"overall_score": 100.0, "total": 0, "passed": 0, "failed": 0}
        p = sum(1 for r in results if r.status == "passed")
        return {
            "overall_score": self.calculate_score(results),
            "total": len(results),
            "passed": p,
            "failed": len(results) - p,
        }


scorer = QualityScorer()
