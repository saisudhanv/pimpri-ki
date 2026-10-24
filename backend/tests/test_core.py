import pandas as pd

from app.metrics import calculate_metrics
from app.selection import select_forecast_vintages


def test_latest_eligible_forecast_and_cutoff():
    forecasts = pd.DataFrame([
        {"target_time": "2026-01-01T12:00:00Z", "publish_time": "2026-01-01T08:00:00Z", "forecast_mw": 10},
        {"target_time": "2026-01-01T12:00:00Z", "publish_time": "2026-01-01T11:00:00Z", "forecast_mw": 20},
    ])
    actuals = pd.DataFrame([{"target_time": "2026-01-01T12:00:00Z", "actual_mw": 12}])
    result = select_forecast_vintages(forecasts, actuals, pd.Timestamp("2026-01-01T10:00:00Z"))
    assert result.iloc[0]["forecast_mw"] == 10
    assert result.iloc[0]["forecast_publish_time"].hour == 8


def test_metrics_and_zero_actual_mape_exclusion():
    frame = pd.DataFrame({"target_time": ["2026-01-01T00:00:00Z"] * 3, "forecast_mw": [10, 0, None], "actual_mw": [8, 0, 4]})
    result = calculate_metrics(frame)
    assert result["valid_sample_count"] == 2
    assert result["zero_actual_count"] == 1
    assert result["mae_mw"] == 1
    assert result["mape_percent"] == 25


def test_missing_eligible_forecast_is_not_zero():
    forecasts = pd.DataFrame(columns=["target_time", "publish_time", "forecast_mw"])
    actuals = pd.DataFrame([{"target_time": "2026-01-01T12:00:00Z", "actual_mw": 4}])
    result = select_forecast_vintages(forecasts, actuals, pd.Timestamp("2026-01-01T10:00:00Z"))
    assert pd.isna(result.iloc[0]["forecast_mw"])
