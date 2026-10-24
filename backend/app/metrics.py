from typing import Any

import numpy as np
import pandas as pd


def calculate_metrics(frame: pd.DataFrame) -> dict[str, Any]:
    """Calculate accuracy only for finite forecast/actual pairs."""
    forecast = pd.to_numeric(frame.get("forecast_mw"), errors="coerce")
    actual = pd.to_numeric(frame.get("actual_mw"), errors="coerce")
    missing_forecast = int(forecast.isna().sum())
    missing_actual = int(actual.isna().sum())
    valid = forecast.notna() & actual.notna() & np.isfinite(forecast) & np.isfinite(actual)
    f = forecast[valid].to_numpy(dtype=float)
    a = actual[valid].to_numpy(dtype=float)
    errors = f - a
    zero_actual = int(np.count_nonzero(a == 0))
    result: dict[str, Any] = {
        "valid_sample_count": int(len(errors)),
        "missing_actual_count": missing_actual,
        "missing_forecast_count": missing_forecast,
        "zero_actual_count": zero_actual,
        "mae_mw": None,
        "rmse_mw": None,
        "bias_mw": None,
        "mape_percent": None,
        "wape_percent": None,
        "evaluation_start": None,
        "evaluation_end": None,
    }
    if len(errors):
        result.update(
            mae_mw=float(np.mean(np.abs(errors))),
            rmse_mw=float(np.sqrt(np.mean(errors**2))),
            bias_mw=float(np.mean(errors)),
            mape_percent=float(np.mean(np.abs(errors[a != 0] / a[a != 0])) * 100)
            if np.any(a != 0)
            else None,
            wape_percent=float(np.sum(np.abs(errors)) / np.sum(np.abs(a)) * 100)
            if np.sum(np.abs(a)) else None,
        )
    if "target_time" in frame.columns and len(frame):
        times = pd.to_datetime(frame["target_time"], utc=True, errors="coerce").dropna()
        if len(times):
            result["evaluation_start"] = times.min().to_pydatetime()
            result["evaluation_end"] = times.max().to_pydatetime()
    return result
