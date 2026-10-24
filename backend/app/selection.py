import pandas as pd


def select_forecast_vintages(
    forecasts: pd.DataFrame, actuals: pd.DataFrame, decision_cutoff: pd.Timestamp
) -> pd.DataFrame:
    """Select the latest publication available at a cutoff per target interval."""
    cutoff = pd.Timestamp(decision_cutoff)
    if cutoff.tzinfo is None:
        cutoff = cutoff.tz_localize("UTC")
    else:
        cutoff = cutoff.tz_convert("UTC")
    f = forecasts.copy()
    a = actuals.copy()
    for frame, columns in ((f, ["target_time", "publish_time"]), (a, ["target_time"])):
        for column in columns:
            frame[column] = pd.to_datetime(frame[column], utc=True, errors="coerce")
    f = f.dropna(subset=["target_time", "publish_time", "forecast_mw"])
    eligible = f[f["publish_time"] <= cutoff].sort_values("publish_time")
    selected = eligible.drop_duplicates("target_time", keep="last").copy()
    selected = selected.rename(columns={"publish_time": "forecast_publish_time"})
    selected["decision_cutoff"] = cutoff
    a = a.rename(columns={"actual_mw": "actual_mw"})
    result = selected[["target_time", "decision_cutoff", "forecast_publish_time", "forecast_mw"]].merge(
        a[["target_time", "actual_mw"]], on="target_time", how="outer"
    )
    result["error_mw"] = result["forecast_mw"] - result["actual_mw"]
    return result.sort_values("target_time").reset_index(drop=True)
