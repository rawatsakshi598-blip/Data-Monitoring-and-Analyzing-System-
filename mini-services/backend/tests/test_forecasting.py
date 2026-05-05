"""
Comprehensive unit tests for the Quality Forecasting Engine.
Tests forecasting, trend detection, risk assessment, and edge cases.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from forecasting.engine import quality_forecast, QualityForecastEngine


# ── Fixtures ──

@pytest.fixture
def improving_scores():
    return [{'date': f'2024-01-{i:02d}', 'score': 80 + i} for i in range(1, 10)]


@pytest.fixture
def degrading_scores():
    return [{'date': f'2024-01-{i:02d}', 'score': 95 - i * 2} for i in range(1, 10)]


@pytest.fixture
def stable_scores():
    # Scores oscillate around 90 with very small fluctuations (slope ~0)
    return [{'date': f'2024-01-{i:02d}', 'score': 90.0 + 0.01 * (i % 2)} for i in range(1, 30)]


@pytest.fixture
def minimal_scores():
    return [{'date': f'2024-01-{i:02d}', 'score': 95.0 - i * 0.5} for i in range(1, 15)]


# ═══════════════════════════════════════════════
# Basic Forecasting
# ═══════════════════════════════════════════════

class TestBasicForecast:
    def test_forecast_basic(self, minimal_scores):
        result = quality_forecast.forecast(minimal_scores)
        assert result['success']
        assert 'trend' in result
        assert 'forecasts' in result

    def test_forecast_has_current_score(self, minimal_scores):
        result = quality_forecast.forecast(minimal_scores)
        assert 'current_score' in result
        assert result['current_score'] == minimal_scores[-1]['score']

    def test_forecast_has_predicted_score(self, minimal_scores):
        result = quality_forecast.forecast(minimal_scores)
        assert 'predicted_score_7d' in result

    def test_forecast_has_predicted_change(self, minimal_scores):
        result = quality_forecast.forecast(minimal_scores)
        assert 'predicted_change' in result

    def test_forecast_has_degradation_risk(self, minimal_scores):
        result = quality_forecast.forecast(minimal_scores)
        assert 'degradation_risk' in result

    def test_forecast_has_will_degrade(self, minimal_scores):
        result = quality_forecast.forecast(minimal_scores)
        assert 'will_degrade' in result
        # may be numpy bool_, use == comparison
        assert result['will_degrade'] in [True, False]

    def test_forecast_has_method(self, minimal_scores):
        result = quality_forecast.forecast(minimal_scores)
        assert 'method' in result
        assert result['method'] == 'exponential_smoothing'


# ═══════════════════════════════════════════════
# Forecast Methods
# ═══════════════════════════════════════════════

class TestForecastMethods:
    def test_exponential_smoothing_forecast(self, minimal_scores):
        result = quality_forecast.forecast(minimal_scores)
        assert 'exponential_smoothing' in result['forecasts']
        es = result['forecasts']['exponential_smoothing']
        assert len(es) == 7  # Default periods
        for entry in es:
            assert 'date' in entry
            assert 'predicted_score' in entry

    def test_linear_trend_forecast(self, minimal_scores):
        result = quality_forecast.forecast(minimal_scores)
        assert 'linear_trend' in result['forecasts']
        lt = result['forecasts']['linear_trend']
        if lt:  # May be empty if regression fails
            for entry in lt:
                assert 'date' in entry
                assert 'predicted_score' in entry

    def test_custom_periods(self):
        scores = [{'date': f'2024-01-{i:02d}', 'score': 90.0} for i in range(1, 10)]
        result = quality_forecast.forecast(scores, periods=14)
        assert len(result['forecasts']['exponential_smoothing']) == 14


# ═══════════════════════════════════════════════
# Trend Detection
# ═══════════════════════════════════════════════

class TestTrendDetection:
    def test_improving_trend(self, improving_scores):
        result = quality_forecast.forecast(improving_scores)
        assert result['trend'] == 'improving'

    def test_degrading_trend(self, degrading_scores):
        result = quality_forecast.forecast(degrading_scores)
        assert result['trend'] == 'degrading'

    def test_stable_trend(self, stable_scores):
        result = quality_forecast.forecast(stable_scores)
        assert result['trend'] == 'stable'

    def test_trend_is_string(self, minimal_scores):
        result = quality_forecast.forecast(minimal_scores)
        assert isinstance(result['trend'], str)
        assert result['trend'] in ['improving', 'degrading', 'stable']


# ═══════════════════════════════════════════════
# Risk Assessment
# ═══════════════════════════════════════════════

class TestRiskAssessment:
    def test_risk_levels(self, minimal_scores):
        result = quality_forecast.forecast(minimal_scores)
        assert result['degradation_risk'] in ['critical', 'high', 'medium', 'low']

    def test_improving_low_risk(self, improving_scores):
        result = quality_forecast.forecast(improving_scores)
        assert result['degradation_risk'] == 'low'

    def test_degrading_higher_risk(self, degrading_scores):
        result = quality_forecast.forecast(degrading_scores)
        assert result['degradation_risk'] in ['critical', 'high', 'medium']

    def test_will_degrade_flag(self, degrading_scores):
        result = quality_forecast.forecast(degrading_scores)
        assert result['will_degrade'] == True

    def test_improving_no_degrade(self, improving_scores):
        result = quality_forecast.forecast(improving_scores)
        assert result['will_degrade'] == False


# ═══════════════════════════════════════════════
# Edge Cases
# ═══════════════════════════════════════════════

class TestEdgeCases:
    def test_forecast_insufficient_data(self):
        scores = [{'date': '2024-01-01', 'score': 95.0}]
        result = quality_forecast.forecast(scores)
        assert not result['success']

    def test_forecast_exactly_three_points(self):
        scores = [
            {'date': '2024-01-01', 'score': 90.0},
            {'date': '2024-01-02', 'score': 91.0},
            {'date': '2024-01-03', 'score': 92.0},
        ]
        result = quality_forecast.forecast(scores)
        assert result['success']

    def test_forecast_two_points(self):
        scores = [
            {'date': '2024-01-01', 'score': 90.0},
            {'date': '2024-01-02', 'score': 91.0},
        ]
        result = quality_forecast.forecast(scores)
        assert not result['success']

    def test_forecast_empty_list(self):
        result = quality_forecast.forecast([])
        assert not result['success']

    def test_forecast_minimum_required_in_error(self):
        scores = [{'date': '2024-01-01', 'score': 95.0}]
        result = quality_forecast.forecast(scores)
        assert 'minimum_required' in result
        assert result['minimum_required'] == 3

    def test_forecast_constant_scores(self):
        scores = [{'date': f'2024-01-{i:02d}', 'score': 95.0} for i in range(1, 10)]
        result = quality_forecast.forecast(scores)
        assert result['success']
        assert result['trend'] == 'stable'


# ═══════════════════════════════════════════════
# Engine Instance
# ═══════════════════════════════════════════════

class TestEngineInstance:
    def test_engine_instance(self):
        assert isinstance(quality_forecast, QualityForecastEngine)

    def test_direct_engine_usage(self):
        engine = QualityForecastEngine()
        scores = [{'date': f'2024-01-{i:02d}', 'score': 90 + i} for i in range(1, 10)]
        result = engine.forecast(scores)
        assert result['success']
