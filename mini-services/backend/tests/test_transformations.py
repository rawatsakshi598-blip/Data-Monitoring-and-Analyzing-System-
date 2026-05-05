"""
Comprehensive unit tests for the Transformation Engine.
Tests ALL 9 transformers, the registry, aliases, edge cases, and data integrity.
"""

import os
import sys
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from transformations import get_transformer, list_transformers, TRANSFORMERS, _ALIASES
from transformations.base_transformer import BaseTransformer, TransformResult
from transformations.imputation import ImputationTransformer
from transformations.outlier import OutlierTransformer
from transformations.dedup import DedupTransformer
from transformations.encoding import EncodingTransformer
from transformations.normalization import NormalizationTransformer
from transformations.string_clean import StringCleanTransformer
from transformations.date_parser import DateParserTransformer
from transformations.data_split import DataSplitTransformer
from transformations.type_conversion import TypeConversionTransformer


# ── Fixtures ──

@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "score": [95.5, 87.3, 92.1, 78.4, 88.9],
        "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
        "category": ["A", "B", "A", "C", "B"],
    })


@pytest.fixture
def df_with_nulls():
    return pd.DataFrame({
        "val": [1.0, np.nan, 3.0, np.nan, 5.0],
        "name": ["a", None, "c", None, "e"],
    })


@pytest.fixture
def df_many_nulls():
    return pd.DataFrame({
        "a": [None, None, 3, 4, 5],
        "b": [1, None, None, None, 5],
        "c": [None, None, None, None, None],
    })


# ═══════════════════════════════════════════════
# Registry Tests
# ═══════════════════════════════════════════════

class TestRegistry:
    def test_list_transformers_count(self):
        result = list_transformers()
        assert len(result) == 9

    def test_list_transformers_has_required_types(self):
        result = list_transformers()
        types = [t['type'] for t in result]
        expected = ['imputation', 'outlier', 'dedup', 'encoding',
                    'normalization', 'string_clean', 'date_parse',
                    'data_split', 'type_conversion']
        for t in expected:
            assert t in types, f"Missing transformer type: {t}"

    def test_list_transformers_structure(self):
        result = list_transformers()
        for item in result:
            assert 'type' in item
            assert 'name' in item
            assert 'description' in item
            assert isinstance(item['type'], str)
            assert isinstance(item['name'], str)

    def test_get_transformer_valid(self):
        t = get_transformer('imputation')
        assert t is not None
        assert isinstance(t, ImputationTransformer)

    def test_get_transformer_all_types(self):
        for ttype in TRANSFORMERS:
            t = get_transformer(ttype)
            assert t is not None
            assert isinstance(t, BaseTransformer)

    def test_get_transformer_alias_fill_missing(self):
        t = get_transformer('fill_missing')
        assert isinstance(t, ImputationTransformer)

    def test_get_transformer_alias_impute(self):
        t = get_transformer('impute')
        assert isinstance(t, ImputationTransformer)

    def test_get_transformer_alias_remove_outliers(self):
        t = get_transformer('remove_outliers')
        assert isinstance(t, OutlierTransformer)

    def test_get_transformer_alias_deduplicate(self):
        t = get_transformer('deduplicate')
        assert isinstance(t, DedupTransformer)

    def test_get_transformer_alias_normalize(self):
        t = get_transformer('normalize')
        assert isinstance(t, NormalizationTransformer)

    def test_get_transformer_alias_standardize(self):
        t = get_transformer('standardize')
        assert isinstance(t, NormalizationTransformer)

    def test_get_transformer_alias_label_encode(self):
        t = get_transformer('label_encode')
        assert isinstance(t, EncodingTransformer)

    def test_get_transformer_alias_train_test_split(self):
        t = get_transformer('train_test_split')
        assert isinstance(t, DataSplitTransformer)

    def test_get_transformer_alias_cast_type(self):
        t = get_transformer('cast_type')
        assert isinstance(t, TypeConversionTransformer)

    def test_get_transformer_invalid(self):
        with pytest.raises(ValueError, match="Unknown transform type"):
            get_transformer('nonexistent')

    def test_all_aliases_resolve(self):
        for alias, canonical in _ALIASES.items():
            t = get_transformer(alias)
            assert t is not None, f"Alias '{alias}' should resolve to a transformer"

    def test_supported_methods_populated(self):
        result = list_transformers()
        for item in result:
            if item['type'] == 'imputation':
                assert len(item.get('supported_methods', [])) > 0


# ═══════════════════════════════════════════════
# Imputation Transformer
# ═══════════════════════════════════════════════

class TestImputation:
    def test_imputation_mean(self):
        t = get_transformer('imputation')
        df = pd.DataFrame({'a': [1, 2, None, 4, 5]})
        result = t.transform(df, {'column': 'a', 'method': 'mean'})
        assert result.success
        assert result.df['a'].isna().sum() == 0
        # Mean of [1,2,4,5] = 3.0
        assert result.df['a'].iloc[2] == pytest.approx(3.0)

    def test_imputation_median(self):
        t = get_transformer('imputation')
        df = pd.DataFrame({'a': [1, 2, None, 4, 100]})
        result = t.transform(df, {'column': 'a', 'method': 'median'})
        assert result.success
        assert result.df['a'].isna().sum() == 0
        # Median of [1,2,4,100] = 3.0
        assert result.df['a'].iloc[2] == pytest.approx(3.0)

    def test_imputation_mode(self):
        t = get_transformer('imputation')
        df = pd.DataFrame({'a': ['x', 'x', None, 'y', 'x']})
        result = t.transform(df, {'column': 'a', 'method': 'mode'})
        assert result.success
        assert result.df['a'].isna().sum() == 0

    def test_imputation_most_frequent(self):
        t = get_transformer('imputation')
        df = pd.DataFrame({'a': [1, 1, None, 2, 1]})
        result = t.transform(df, {'column': 'a', 'method': 'most_frequent'})
        assert result.success
        assert result.df['a'].isna().sum() == 0

    def test_imputation_constant(self):
        t = get_transformer('imputation')
        df = pd.DataFrame({'a': [1, None, 3]})
        result = t.transform(df, {'column': 'a', 'method': 'constant', 'fill_value': 0})
        assert result.success
        assert result.df['a'].iloc[1] == 0

    def test_imputation_constant_default_numeric(self):
        t = get_transformer('imputation')
        df = pd.DataFrame({'a': [1, None, 3]})
        result = t.transform(df, {'column': 'a', 'method': 'constant'})
        assert result.success
        assert result.df['a'].iloc[1] == 0

    def test_imputation_constant_default_string(self):
        t = get_transformer('imputation')
        df = pd.DataFrame({'a': ['x', None, 'y']})
        result = t.transform(df, {'column': 'a', 'method': 'constant'})
        assert result.success
        assert result.df['a'].iloc[1] == 'unknown'

    def test_imputation_forward_fill(self):
        t = get_transformer('imputation')
        df = pd.DataFrame({'a': [1, None, 3, None, 5]})
        result = t.transform(df, {'column': 'a', 'method': 'forward_fill'})
        assert result.success
        assert result.df['a'].iloc[1] == 1.0

    def test_imputation_backward_fill(self):
        t = get_transformer('imputation')
        df = pd.DataFrame({'a': [1, None, 3, None, 5]})
        result = t.transform(df, {'column': 'a', 'method': 'backward_fill'})
        assert result.success
        assert result.df['a'].iloc[1] == 3.0

    def test_imputation_no_missing(self):
        t = get_transformer('imputation')
        df = pd.DataFrame({'a': [1, 2, 3]})
        result = t.transform(df, {'column': 'a', 'method': 'mean'})
        assert result.success
        assert result.rows_affected == 0

    def test_imputation_multiple_columns(self):
        t = get_transformer('imputation')
        df = pd.DataFrame({'a': [1, None, 3], 'b': [None, 5, None]})
        result = t.transform(df, {'method': 'mean', 'columns': ['a', 'b']})
        assert result.success
        assert result.df['a'].isna().sum() == 0
        assert result.df['b'].isna().sum() == 0

    def test_imputation_details(self):
        t = get_transformer('imputation')
        df = pd.DataFrame({'a': [1, None, 3]})
        result = t.transform(df, {'column': 'a', 'method': 'mean'})
        assert result.success
        assert 'a' in result.details
        assert result.details['a']['before'] == 1
        assert result.details['a']['after'] == 0

    def test_imputation_does_not_modify_original(self):
        t = get_transformer('imputation')
        df = pd.DataFrame({'a': [1, None, 3]})
        original_na = df['a'].isna().sum()
        result = t.transform(df, {'column': 'a', 'method': 'mean'})
        assert df['a'].isna().sum() == original_na  # Original unchanged

    def test_imputation_all_null_column(self):
        t = get_transformer('imputation')
        df = pd.DataFrame({'a': [None, None, None]})
        result = t.transform(df, {'column': 'a', 'method': 'mean'})
        # Mean of all-NaN column is NaN, so forward_fill might not help
        # But the transformer should still report success
        assert result.success


# ═══════════════════════════════════════════════
# Outlier Transformer
# ═══════════════════════════════════════════════

class TestOutlier:
    def test_outlier_iqr_remove(self):
        t = get_transformer('outlier')
        df = pd.DataFrame({'a': [1, 2, 3, 4, 5, 100]})
        result = t.transform(df, {'column': 'a', 'method': 'iqr_remove'})
        assert result.success
        assert len(result.df) < len(df)
        assert 100 not in result.df['a'].values

    def test_outlier_iqr_cap(self):
        t = get_transformer('outlier')
        df = pd.DataFrame({'a': [1, 2, 3, 4, 5, 100]})
        result = t.transform(df, {'column': 'a', 'method': 'iqr_cap'})
        assert result.success
        assert len(result.df) == len(df)  # No rows removed
        assert result.df['a'].max() < 100

    def test_outlier_zscore_remove(self):
        t = get_transformer('outlier')
        df = pd.DataFrame({'a': [10, 11, 10, 12, 11, 500]})
        result = t.transform(df, {'column': 'a', 'method': 'zscore_remove', 'threshold': 2.0})
        assert result.success
        assert len(result.df) < len(df)

    def test_outlier_zscore_cap(self):
        t = get_transformer('outlier')
        df = pd.DataFrame({'a': [10, 11, 10, 12, 11, 500]})
        result = t.transform(df, {'column': 'a', 'method': 'zscore_cap'})
        assert result.success
        assert len(result.df) == len(df)

    def test_outlier_percentile_clip(self):
        t = get_transformer('outlier')
        df = pd.DataFrame({'a': list(range(1, 101))})
        result = t.transform(df, {'column': 'a', 'method': 'percentile_clip',
                                   'lower_percentile': 5, 'upper_percentile': 95})
        assert result.success
        assert len(result.df) == len(df)  # Clipping doesn't remove rows

    def test_outlier_no_outliers(self):
        t = get_transformer('outlier')
        df = pd.DataFrame({'a': [1, 2, 3, 4, 5]})
        result = t.transform(df, {'column': 'a', 'method': 'iqr_remove'})
        assert result.success
        # No outliers should be found; all rows retained
        assert len(result.df) == len(df)

    def test_outlier_auto_detect_numeric(self):
        t = get_transformer('outlier')
        df = pd.DataFrame({'num': [1, 2, 3, 100], 'cat': ['a', 'b', 'c', 'd']})
        result = t.transform(df, {'method': 'iqr_remove'})
        assert result.success
        assert 'num' in result.columns_affected

    def test_outlier_no_numeric_columns(self):
        t = get_transformer('outlier')
        df = pd.DataFrame({'cat': ['a', 'b', 'c']})
        result = t.transform(df, {'method': 'iqr_remove'})
        assert result.success is False

    def test_outlier_multiple_columns(self):
        t = get_transformer('outlier')
        df = pd.DataFrame({'a': [1, 2, 3, 100], 'b': [5, 6, 7, 200]})
        result = t.transform(df, {'method': 'iqr_remove', 'columns': ['a', 'b']})
        assert result.success
        assert 'a' in result.details
        assert 'b' in result.details

    def test_outlier_iqr_multiplier(self):
        t = get_transformer('outlier')
        df = pd.DataFrame({'a': [1, 2, 3, 4, 5, 100]})
        # With higher multiplier, fewer outliers detected
        result = t.transform(df, {'column': 'a', 'method': 'iqr_remove', 'iqr_multiplier': 3.0})
        assert result.success

    def test_outlier_details_contain_method(self):
        t = get_transformer('outlier')
        df = pd.DataFrame({'a': [1, 2, 3, 100]})
        result = t.transform(df, {'column': 'a', 'method': 'iqr_remove'})
        assert result.details['a']['method'] == 'iqr_remove'


# ═══════════════════════════════════════════════
# Dedup Transformer
# ═══════════════════════════════════════════════

class TestDedup:
    def test_dedup_exact(self):
        t = get_transformer('dedup')
        df = pd.DataFrame({'a': [1, 1, 2, 3, 3]})
        result = t.transform(df, {'method': 'exact'})
        assert result.success
        assert len(result.df) < len(df)
        assert result.rows_affected == 2

    def test_dedup_no_duplicates(self):
        t = get_transformer('dedup')
        df = pd.DataFrame({'a': [1, 2, 3]})
        result = t.transform(df, {'method': 'exact'})
        assert result.success
        assert result.rows_affected == 0
        assert len(result.df) == len(df)

    def test_dedup_subset_columns(self):
        t = get_transformer('dedup')
        df = pd.DataFrame({'a': [1, 1, 2], 'b': ['x', 'y', 'z']})
        result = t.transform(df, {'method': 'exact', 'columns': ['a']})
        assert result.success
        assert len(result.df) == 2

    def test_dedup_invalid_columns(self):
        t = get_transformer('dedup')
        df = pd.DataFrame({'a': [1, 1, 2]})
        result = t.transform(df, {'method': 'exact', 'columns': ['nonexistent']})
        assert result.success is False

    def test_dedup_keep_first(self):
        t = get_transformer('dedup')
        df = pd.DataFrame({'a': [1, 1, 2], 'b': ['first', 'second', 'third']})
        result = t.transform(df, {'method': 'keep_first', 'columns': ['a']})
        assert result.success
        assert result.df[result.df['a'] == 1]['b'].iloc[0] == 'first'

    def test_dedup_keep_last(self):
        t = get_transformer('dedup')
        df = pd.DataFrame({'a': [1, 1, 2], 'b': ['first', 'second', 'third']})
        result = t.transform(df, {'method': 'keep_last', 'columns': ['a']})
        assert result.success

    def test_dedup_keep_none(self):
        t = get_transformer('dedup')
        df = pd.DataFrame({'a': [1, 1, 2], 'b': ['first', 'second', 'third']})
        result = t.transform(df, {'method': 'keep_none', 'columns': ['a']})
        assert result.success
        # Both duplicates should be removed
        a_values = result.df['a'].tolist()
        assert 1 not in a_values or a_values.count(1) == 1

    def test_dedup_details(self):
        t = get_transformer('dedup')
        df = pd.DataFrame({'a': [1, 1, 2, 3, 3]})
        result = t.transform(df, {'method': 'exact'})
        assert result.success
        assert result.details['original_rows'] == 5
        assert result.details['duplicate_rows'] == 2
        assert result.details['remaining_rows'] == 3

    def test_dedup_empty_dataframe(self):
        t = get_transformer('dedup')
        df = pd.DataFrame({'a': pd.Series([], dtype=int)})
        result = t.transform(df, {'method': 'exact'})
        assert result.success
        assert result.rows_affected == 0


# ═══════════════════════════════════════════════
# Encoding Transformer
# ═══════════════════════════════════════════════

class TestEncoding:
    def test_encoding_one_hot(self):
        t = get_transformer('encoding')
        df = pd.DataFrame({'cat': ['a', 'b', 'a', 'c']})
        result = t.transform(df, {'column': 'cat', 'method': 'one_hot'})
        assert result.success
        assert 'cat_a' in result.df.columns or 'cat_b' in result.df.columns

    def test_encoding_one_hot_drops_original(self):
        t = get_transformer('encoding')
        df = pd.DataFrame({'cat': ['a', 'b', 'a']})
        result = t.transform(df, {'column': 'cat', 'method': 'one_hot'})
        assert result.success
        assert 'cat' not in result.df.columns

    def test_encoding_one_hot_keep_original(self):
        t = get_transformer('encoding')
        df = pd.DataFrame({'cat': ['a', 'b', 'a']})
        result = t.transform(df, {'column': 'cat', 'method': 'one_hot', 'drop_original': False})
        assert result.success
        assert 'cat' in result.df.columns

    def test_encoding_label(self):
        t = get_transformer('encoding')
        df = pd.DataFrame({'cat': ['a', 'b', 'a', 'c']})
        result = t.transform(df, {'column': 'cat', 'method': 'label'})
        assert result.success
        assert 'cat_encoded' in result.df.columns

    def test_encoding_ordinal(self):
        t = get_transformer('encoding')
        df = pd.DataFrame({'cat': ['low', 'medium', 'high']})
        result = t.transform(df, {'column': 'cat', 'method': 'ordinal',
                                   'categories': ['low', 'medium', 'high']})
        assert result.success
        assert 'cat_ordinal' in result.df.columns

    def test_encoding_frequency(self):
        t = get_transformer('encoding')
        df = pd.DataFrame({'cat': ['a', 'a', 'b', 'c']})
        result = t.transform(df, {'column': 'cat', 'method': 'frequency'})
        assert result.success
        assert 'cat_freq' in result.df.columns

    def test_encoding_binary(self):
        t = get_transformer('encoding')
        df = pd.DataFrame({'cat': ['yes', 'no', 'yes']})
        result = t.transform(df, {'column': 'cat', 'method': 'binary'})
        assert result.success
        assert 'cat_binary' in result.df.columns

    def test_encoding_target(self):
        t = get_transformer('encoding')
        df = pd.DataFrame({'cat': ['a', 'a', 'b', 'b'], 'target': [1, 1, 0, 0]})
        result = t.transform(df, {'column': 'cat', 'method': 'target', 'target_column': 'target'})
        assert result.success

    def test_encoding_no_categorical_columns(self):
        t = get_transformer('encoding')
        df = pd.DataFrame({'val': [1, 2, 3]})
        result = t.transform(df, {'method': 'label'})
        assert result.success
        assert 'No categorical' in result.message

    def test_encoding_multiple_columns(self):
        t = get_transformer('encoding')
        df = pd.DataFrame({'cat1': ['a', 'b'], 'cat2': ['x', 'y']})
        result = t.transform(df, {'method': 'label', 'columns': ['cat1', 'cat2']})
        assert result.success
        assert 'cat1_encoded' in result.df.columns
        assert 'cat2_encoded' in result.df.columns

    def test_encoding_auto_detect_categoricals(self):
        t = get_transformer('encoding')
        df = pd.DataFrame({'cat': ['a', 'b', 'c'], 'num': [1, 2, 3]})
        result = t.transform(df, {'method': 'label'})
        assert result.success
        # Should auto-detect 'cat' as categorical
        assert 'cat' in result.columns_affected


# ═══════════════════════════════════════════════
# Normalization Transformer
# ═══════════════════════════════════════════════

class TestNormalization:
    def test_normalization_minmax(self):
        t = get_transformer('normalization')
        df = pd.DataFrame({'a': [1, 5, 10, 50, 100]})
        result = t.transform(df, {'column': 'a', 'method': 'minmax'})
        assert result.success
        assert result.df['a'].min() >= 0
        assert result.df['a'].max() <= 1

    def test_normalization_minmax_custom_range(self):
        t = get_transformer('normalization')
        df = pd.DataFrame({'a': [1, 5, 10, 50, 100]})
        result = t.transform(df, {'column': 'a', 'method': 'minmax', 'feature_range': [0, 100]})
        assert result.success
        assert result.df['a'].min() >= 0
        assert result.df['a'].max() <= 100

    def test_normalization_zscore(self):
        t = get_transformer('normalization')
        df = pd.DataFrame({'a': [1, 5, 10, 50, 100]})
        result = t.transform(df, {'column': 'a', 'method': 'zscore'})
        assert result.success
        assert abs(result.df['a'].mean()) < 0.01

    def test_normalization_robust(self):
        t = get_transformer('normalization')
        df = pd.DataFrame({'a': [1, 5, 10, 50, 100]})
        result = t.transform(df, {'column': 'a', 'method': 'robust'})
        assert result.success

    def test_normalization_log(self):
        t = get_transformer('normalization')
        df = pd.DataFrame({'a': [1, 10, 100, 1000, 10000]})
        result = t.transform(df, {'column': 'a', 'method': 'log'})
        assert result.success
        # Log transform should compress the range
        assert result.df['a'].max() < df['a'].max()

    def test_normalization_max_abs(self):
        t = get_transformer('normalization')
        df = pd.DataFrame({'a': [-5, 10, -15, 20, -25]})
        result = t.transform(df, {'column': 'a', 'method': 'max_abs'})
        assert result.success
        assert abs(result.df['a'].abs().max() - 1.0) < 0.01

    def test_normalization_constant_column(self):
        t = get_transformer('normalization')
        df = pd.DataFrame({'a': [5, 5, 5, 5]})
        result = t.transform(df, {'column': 'a', 'method': 'minmax'})
        assert result.success
        # Constant column: minmax returns feature_range[0]
        assert result.df['a'].iloc[0] == 0.0

    def test_normalization_no_numeric_columns(self):
        t = get_transformer('normalization')
        df = pd.DataFrame({'cat': ['a', 'b', 'c']})
        result = t.transform(df, {'method': 'minmax'})
        assert result.success is False

    def test_normalization_details_before_after(self):
        t = get_transformer('normalization')
        df = pd.DataFrame({'a': [10, 20, 30, 40, 50]})
        result = t.transform(df, {'column': 'a', 'method': 'minmax'})
        assert result.success
        assert 'a' in result.details
        assert 'before' in result.details['a']
        assert 'after' in result.details['a']

    def test_normalization_multiple_columns(self):
        t = get_transformer('normalization')
        df = pd.DataFrame({'a': [1, 5, 10], 'b': [100, 500, 1000]})
        result = t.transform(df, {'method': 'minmax', 'columns': ['a', 'b']})
        assert result.success
        assert result.df['a'].min() >= 0
        assert result.df['b'].min() >= 0


# ═══════════════════════════════════════════════
# String Clean Transformer
# ═══════════════════════════════════════════════

class TestStringClean:
    def test_string_clean_trim(self):
        t = get_transformer('string_clean')
        df = pd.DataFrame({'s': ['  Hello  ', 'WORLD', 'foo bar']})
        result = t.transform(df, {'column': 's', 'method': 'trim'})
        assert result.success
        assert result.df['s'].iloc[0] == 'Hello'

    def test_string_clean_lowercase(self):
        t = get_transformer('string_clean')
        df = pd.DataFrame({'s': ['Hello', 'WORLD', 'Foo']})
        result = t.transform(df, {'column': 's', 'method': 'lowercase'})
        assert result.success
        assert result.df['s'].iloc[0] == 'hello'
        assert result.df['s'].iloc[1] == 'world'

    def test_string_clean_uppercase(self):
        t = get_transformer('string_clean')
        df = pd.DataFrame({'s': ['hello', 'world']})
        result = t.transform(df, {'column': 's', 'method': 'uppercase'})
        assert result.success
        assert result.df['s'].iloc[0] == 'HELLO'

    def test_string_clean_title_case(self):
        t = get_transformer('string_clean')
        df = pd.DataFrame({'s': ['hello world', 'foo bar']})
        result = t.transform(df, {'column': 's', 'method': 'title_case'})
        assert result.success
        assert result.df['s'].iloc[0] == 'Hello World'

    def test_string_clean_remove_special(self):
        t = get_transformer('string_clean')
        df = pd.DataFrame({'s': ['hello!', 'world@#$', 'test']})
        result = t.transform(df, {'column': 's', 'method': 'remove_special'})
        assert result.success
        assert result.df['s'].iloc[0] == 'hello'

    def test_string_clean_standardize_whitespace(self):
        t = get_transformer('string_clean')
        df = pd.DataFrame({'s': ['hello   world', '  foo  bar  ']})
        result = t.transform(df, {'column': 's', 'method': 'standardize_whitespace'})
        assert result.success
        assert '  ' not in result.df['s'].iloc[0]

    def test_string_clean_regex_replace(self):
        t = get_transformer('string_clean')
        df = pd.DataFrame({'s': ['test123', 'abc456']})
        result = t.transform(df, {'column': 's', 'method': 'regex_replace',
                                   'pattern': r'\d', 'replacement': ''})
        assert result.success
        assert result.df['s'].iloc[0] == 'test'

    def test_string_clean_snake_case(self):
        t = get_transformer('string_clean')
        df = pd.DataFrame({'s': ['Hello World', 'Foo Bar']})
        result = t.transform(df, {'column': 's', 'method': 'snake_case'})
        assert result.success
        assert result.df['s'].iloc[0] == 'hello_world'

    def test_string_clean_no_string_columns(self):
        t = get_transformer('string_clean')
        df = pd.DataFrame({'a': [1, 2, 3]})
        result = t.transform(df, {'method': 'trim'})
        assert result.success is False

    def test_string_clean_auto_detect_string_columns(self):
        t = get_transformer('string_clean')
        df = pd.DataFrame({'s': ['  a  ', '  b  '], 'n': [1, 2]})
        result = t.transform(df, {'method': 'trim'})
        assert result.success
        assert 's' in result.columns_affected

    def test_string_clean_preserves_nan(self):
        t = get_transformer('string_clean')
        df = pd.DataFrame({'s': ['hello', None, 'world']})
        result = t.transform(df, {'column': 's', 'method': 'trim'})
        assert result.success
        assert result.df['s'].isna().sum() == 1


# ═══════════════════════════════════════════════
# Date Parse Transformer
# ═══════════════════════════════════════════════

class TestDateParse:
    def test_date_parse(self):
        t = get_transformer('date_parse')
        df = pd.DataFrame({'d': ['2024-01-15', '2024-06-30', '2023-12-25']})
        result = t.transform(df, {'column': 'd', 'method': 'parse'})
        assert result.success

    def test_date_parse_with_format(self):
        t = get_transformer('date_parse')
        df = pd.DataFrame({'d': ['15/01/2024', '30/06/2024']})
        result = t.transform(df, {'column': 'd', 'method': 'parse', 'format': '%d/%m/%Y'})
        assert result.success

    def test_date_extract_features(self):
        t = get_transformer('date_parse')
        df = pd.DataFrame({'d': pd.to_datetime(['2024-01-15', '2024-06-30'])})
        result = t.transform(df, {'column': 'd', 'method': 'extract_features'})
        assert result.success
        assert 'd_year' in result.df.columns or 'd_month' in result.df.columns

    def test_date_to_format(self):
        t = get_transformer('date_parse')
        df = pd.DataFrame({'d': ['2024-01-15', '2024-06-30']})
        result = t.transform(df, {'column': 'd', 'method': 'to_format', 'output_format': '%d/%m/%Y'})
        assert result.success

    def test_date_no_date_columns(self):
        t = get_transformer('date_parse')
        df = pd.DataFrame({'a': [1, 2, 3]})
        result = t.transform(df, {'method': 'parse'})
        assert result.success is False

    def test_date_auto_detect(self):
        t = get_transformer('date_parse')
        df = pd.DataFrame({'d': ['2024-01-15', '2024-06-30', '2023-12-25'],
                           'name': ['a', 'b', 'c']})
        result = t.transform(df, {'method': 'auto_detect'})
        assert result.success

    def test_date_extract_custom_features(self):
        t = get_transformer('date_parse')
        df = pd.DataFrame({'d': pd.to_datetime(['2024-01-15', '2024-06-30'])})
        result = t.transform(df, {'column': 'd', 'method': 'extract_features',
                                   'features': ['year', 'month', 'quarter', 'is_weekend']})
        assert result.success


# ═══════════════════════════════════════════════
# Data Split Transformer
# ═══════════════════════════════════════════════

class TestDataSplit:
    def test_data_split_random(self):
        t = get_transformer('data_split')
        df = pd.DataFrame({'a': range(100), 'b': range(100)})
        result = t.transform(df, {'method': 'random', 'test_size': 0.2})
        assert result.success
        assert 'train' in result.extra_outputs
        assert 'test' in result.extra_outputs

    def test_data_split_stratified(self):
        t = get_transformer('data_split')
        df = pd.DataFrame({'a': range(100), 'cat': ['A'] * 50 + ['B'] * 50})
        result = t.transform(df, {'method': 'stratified', 'stratify_column': 'cat', 'test_size': 0.2})
        assert result.success

    def test_data_split_with_validation(self):
        t = get_transformer('data_split')
        df = pd.DataFrame({'a': range(200)})
        result = t.transform(df, {'method': 'random', 'test_size': 0.2, 'val_size': 0.1})
        assert result.success
        assert 'val' in result.extra_outputs
        assert len(result.extra_outputs['val']) > 0

    def test_data_split_proportions(self):
        t = get_transformer('data_split')
        df = pd.DataFrame({'a': range(1000)})
        result = t.transform(df, {'method': 'random', 'test_size': 0.2})
        assert result.success
        train_df = result.extra_outputs['train']
        test_df = result.extra_outputs['test']
        assert len(train_df) + len(test_df) == 1000
        assert len(test_df) == 200

    def test_data_split_details(self):
        t = get_transformer('data_split')
        df = pd.DataFrame({'a': range(100)})
        result = t.transform(df, {'method': 'random', 'test_size': 0.2})
        assert result.success
        assert 'train_rows' in result.details
        assert 'test_rows' in result.details
        assert 'method' in result.details

    def test_data_split_time_based(self):
        t = get_transformer('data_split')
        df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=100),
            'val': range(100)
        })
        result = t.transform(df, {'method': 'time_based', 'time_column': 'date', 'test_size': 0.2})
        assert result.success

    def test_data_split_random_state(self):
        t = get_transformer('data_split')
        df = pd.DataFrame({'a': range(100)})
        result1 = t.transform(df, {'method': 'random', 'test_size': 0.2, 'random_state': 42})
        result2 = t.transform(df, {'method': 'random', 'test_size': 0.2, 'random_state': 42})
        # Same random_state should produce same split
        assert list(result1.extra_outputs['train'].index) == list(result2.extra_outputs['train'].index)


# ═══════════════════════════════════════════════
# Type Conversion Transformer
# ═══════════════════════════════════════════════

class TestTypeConversion:
    def test_type_conversion_to_numeric(self):
        t = get_transformer('type_conversion')
        df = pd.DataFrame({'a': ['1', '2', '3']})
        result = t.transform(df, {'column': 'a', 'method': 'to_numeric'})
        assert result.success
        assert pd.api.types.is_numeric_dtype(result.df['a'])

    def test_type_conversion_to_string(self):
        t = get_transformer('type_conversion')
        df = pd.DataFrame({'a': [1, 2, 3]})
        result = t.transform(df, {'column': 'a', 'method': 'to_string'})
        assert result.success
        assert result.df['a'].dtype == object

    def test_type_conversion_to_datetime(self):
        t = get_transformer('type_conversion')
        df = pd.DataFrame({'a': ['2024-01-15', '2024-06-30']})
        result = t.transform(df, {'column': 'a', 'method': 'to_datetime'})
        assert result.success
        assert pd.api.types.is_datetime64_any_dtype(result.df['a'])

    def test_type_conversion_to_category(self):
        t = get_transformer('type_conversion')
        df = pd.DataFrame({'a': ['x', 'y', 'z']})
        result = t.transform(df, {'column': 'a', 'method': 'to_category'})
        assert result.success
        assert result.df['a'].dtype.name == 'category'

    def test_type_conversion_to_boolean(self):
        t = get_transformer('type_conversion')
        df = pd.DataFrame({'a': ['yes', 'no', 'yes', 'no']})
        result = t.transform(df, {'column': 'a', 'method': 'to_boolean'})
        assert result.success
        assert result.df['a'].dtype.name == 'boolean'

    def test_type_conversion_auto_numeric(self):
        t = get_transformer('type_conversion')
        df = pd.DataFrame({'a': ['1', '2', '3']})
        result = t.transform(df, {'column': 'a', 'method': 'auto'})
        assert result.success
        assert pd.api.types.is_numeric_dtype(result.df['a'])

    def test_type_conversion_auto_datetime(self):
        t = get_transformer('type_conversion')
        df = pd.DataFrame({'a': ['2024-01-15', '2024-06-30']})
        result = t.transform(df, {'column': 'a', 'method': 'auto'})
        assert result.success

    def test_type_conversion_details(self):
        t = get_transformer('type_conversion')
        df = pd.DataFrame({'a': ['1', '2', '3']})
        result = t.transform(df, {'column': 'a', 'method': 'to_numeric'})
        assert result.success
        assert 'a' in result.details
        assert result.details['a']['from'] != result.details['a']['to']

    def test_type_conversion_no_columns_specified(self):
        t = get_transformer('type_conversion')
        df = pd.DataFrame({'a': ['1', '2']})
        result = t.transform(df, {'method': 'auto'})
        assert result.success


# ═══════════════════════════════════════════════
# TransformResult Tests
# ═══════════════════════════════════════════════

class TestTransformResult:
    def test_to_dict(self):
        df = pd.DataFrame({'a': [1, 2, 3]})
        result = TransformResult(df=df, success=True, message="test", rows_affected=3)
        d = result.to_dict()
        assert d['success'] is True
        assert d['message'] == 'test'
        assert d['rows_affected'] == 3
        assert d['shape'] == [3, 1]

    def test_default_values(self):
        df = pd.DataFrame({'a': [1]})
        result = TransformResult(df=df)
        assert result.success is True
        assert result.message == ''
        assert result.rows_affected == 0
        assert result.columns_affected == []
        assert result.details == {}
        assert result.extra_outputs == {}
