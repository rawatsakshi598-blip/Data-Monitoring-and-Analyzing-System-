"""
Transformation Engine — Data preprocessing operations.
Handles imputation, outlier removal, encoding, normalization, dedup,
string cleaning, date parsing, data splitting, and type conversion.
Each transformer is a pure function: df_in + config → df_out + metadata.
"""

from transformations.imputation import ImputationTransformer
from transformations.outlier import OutlierTransformer
from transformations.dedup import DedupTransformer
from transformations.encoding import EncodingTransformer
from transformations.normalization import NormalizationTransformer
from transformations.string_clean import StringCleanTransformer
from transformations.date_parser import DateParserTransformer
from transformations.data_split import DataSplitTransformer
from transformations.type_conversion import TypeConversionTransformer

# ── Registry ──

TRANSFORMERS = {
    "imputation": ImputationTransformer,
    "outlier": OutlierTransformer,
    "dedup": DedupTransformer,
    "encoding": EncodingTransformer,
    "normalization": NormalizationTransformer,
    "string_clean": StringCleanTransformer,
    "date_parse": DateParserTransformer,
    "data_split": DataSplitTransformer,
    "type_conversion": TypeConversionTransformer,
}

_ALIASES = {
    "fill_missing": "imputation",
    "impute": "imputation",
    "remove_outliers": "outlier",
    "cap_outliers": "outlier",
    "winsorize": "outlier",
    "remove_duplicates": "dedup",
    "deduplicate": "dedup",
    "one_hot": "encoding",
    "label_encode": "encoding",
    "ordinal_encode": "encoding",
    "target_encode": "encoding",
    "scale": "normalization",
    "standardize": "normalization",
    "minmax": "normalization",
    "normalize": "normalization",
    "zscore": "normalization",
    "clean_string": "string_clean",
    "trim": "string_clean",
    "strip": "string_clean",
    "parse_date": "date_parse",
    "extract_date": "date_parse",
    "split_data": "data_split",
    "train_test_split": "data_split",
    "convert_type": "type_conversion",
    "cast_type": "type_conversion",
}


def get_transformer(transform_type: str):
    canonical = _ALIASES.get(transform_type, transform_type)
    cls = TRANSFORMERS.get(canonical)
    if cls is None:
        raise ValueError(f"Unknown transform type: {transform_type}")
    return cls()


def list_transformers() -> list[dict]:
    return [
        {
            "type": k,
            "name": v.__name__,
            "description": v.__doc__ or "",
            "supported_methods": v.supported_methods if hasattr(v, 'supported_methods') else [],
        }
        for k, v in TRANSFORMERS.items()
    ]
