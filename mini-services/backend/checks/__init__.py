from checks.base_check import BaseCheck
from checks.completeness_check import CompletenessCheck
from checks.uniqueness_check import UniquenessCheck
from checks.validity_check import ValidityCheck
from checks.freshness_check import FreshnessCheck
from checks.schema_check import SchemaCheck
from checks.volume_check import VolumeCheck
from checks.anomaly_check import AnomalyCheck

REGISTRY: dict[str, type[BaseCheck]] = {
    "completeness": CompletenessCheck,
    "uniqueness": UniquenessCheck,
    "validity": ValidityCheck,
    "freshness": FreshnessCheck,
    "schema": SchemaCheck,
    "volume": VolumeCheck,
    "anomaly": AnomalyCheck,
}

_ALIASES: dict[str, str] = {
    "missing": "completeness",
    "not_null": "completeness",
    "duplicate": "uniqueness",
    "unique": "uniqueness",
    "valid_values": "validity",
    "regex": "validity",
    "range": "validity",
    "timeliness": "freshness",
    "schema_change": "schema",
    "row_count": "volume",
    "outlier": "anomaly",
    "drift": "anomaly",
    "zscore": "anomaly",
}


def get_check(check_type: str) -> type[BaseCheck]:
    canonical = _ALIASES.get(check_type, check_type)
    cls = REGISTRY.get(canonical)
    if cls is None:
        raise ValueError(f"Unknown check type: {check_type}")
    return cls


def list_checks() -> list[dict]:
    return [
        {"type": k, "name": v.__name__, "description": v.__doc__ or ""}
        for k, v in REGISTRY.items()
    ]
