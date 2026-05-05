"""
Quality Trend Forecasting — Predict quality score degradation.
Uses simple time-series methods (moving average, exponential smoothing).
"""

import pandas as pd
import numpy as np
from typing import Optional


class QualityForecastEngine:
    """Forecast quality scores and detect degradation trends."""

    def forecast(self, historical_scores: list[dict], periods: int = 7) -> dict:
        """
        Forecast quality scores based on historical data.
        historical_scores: [{"date": "2024-01-01", "score": 95.2}, ...]
        """
        if len(historical_scores) < 3:
            return {
                "success": False,
                "error": "Need at least 3 data points for forecasting",
                "minimum_required": 3,
            }

        df = pd.DataFrame(historical_scores)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')

        scores = df['score'].values

        # Simple Moving Average
        sma_forecast = self._sma_forecast(scores, periods)

        # Exponential Smoothing
        es_forecast = self._exp_smoothing(scores, periods, alpha=0.3)

        # Linear Trend
        linear_forecast = self._linear_trend(df, periods)

        # Detect trend direction
        trend = self._detect_trend(scores)

        # Generate dates for forecast
        last_date = df['date'].iloc[-1]
        forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=periods, freq='D')

        result = {
            "success": True,
            "trend": trend,
            "current_score": float(scores[-1]),
            "predicted_score_7d": round(float(es_forecast[-1]), 1),
            "predicted_change": round(float(es_forecast[-1] - scores[-1]), 1),
            "will_degrade": es_forecast[-1] < scores[-1],
            "degradation_risk": self._assess_risk(scores, es_forecast),
            "forecasts": {
                "exponential_smoothing": [
                    {"date": d.strftime('%Y-%m-%d'), "predicted_score": round(float(s), 1)}
                    for d, s in zip(forecast_dates, es_forecast)
                ],
                "linear_trend": [
                    {"date": d.strftime('%Y-%m-%d'), "predicted_score": round(float(s), 1)}
                    for d, s in zip(forecast_dates, linear_forecast)
                ] if linear_forecast is not None else [],
            },
            "method": "exponential_smoothing",
        }

        return result

    def _sma_forecast(self, scores, periods):
        window = min(7, len(scores))
        avg = np.mean(scores[-window:])
        return [avg] * periods

    def _exp_smoothing(self, scores, periods, alpha=0.3):
        smoothed = [scores[0]]
        for s in scores[1:]:
            smoothed.append(alpha * s + (1 - alpha) * smoothed[-1])
        # Project forward
        last_smoothed = smoothed[-1]
        # Add slight trend
        trend = (smoothed[-1] - smoothed[max(0, len(smoothed) - 3)]) / min(3, len(smoothed))
        forecast = []
        for i in range(periods):
            forecast.append(last_smoothed + trend * (i + 1))
        return forecast

    def _linear_trend(self, df, periods):
        try:
            scores = df['score'].values
            x = np.arange(len(scores))
            coeffs = np.polyfit(x, scores, 1)
            future_x = np.arange(len(scores), len(scores) + periods)
            return np.polyval(coeffs, future_x)
        except Exception:
            return None

    def _detect_trend(self, scores):
        if len(scores) < 3:
            return "stable"
        recent = scores[-3:]
        if all(recent[i] > recent[i+1] for i in range(len(recent)-1)):
            return "degrading"
        if all(recent[i] < recent[i+1] for i in range(len(recent)-1)):
            return "improving"
        # Use linear regression slope
        x = np.arange(len(scores))
        slope = np.polyfit(x, scores, 1)[0]
        if slope < -0.5:
            return "degrading"
        elif slope > 0.5:
            return "improving"
        return "stable"

    def _assess_risk(self, scores, forecast):
        current = scores[-1]
        predicted = forecast[-1]
        drop = current - predicted
        if drop > 10:
            return "critical"
        elif drop > 5:
            return "high"
        elif drop > 2:
            return "medium"
        return "low"


quality_forecast = QualityForecastEngine()
