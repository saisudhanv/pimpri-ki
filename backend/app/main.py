import os
from datetime import date, time

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .data import load_demo
from .metrics import calculate_metrics
from .models import AccuracyResponse, ResidualDemandRequest, ResidualDemandResponse
from .selection import select_forecast_vintages

app = FastAPI(title="Wind Procurement Intelligence", version="1.0.0")
origins = [
    item.strip().rstrip("/")
    for item in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,https://pimpri-ki-g6v8.vercel.app",
    ).split(",")
    if item.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://pimpri-ki-[a-z0-9-]+\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _dataset(cutoff: str = "10:00", start_date: date | None = None, end_date: date | None = None) -> pd.DataFrame:
    forecasts, actuals = load_demo()
    try:
        cutoff_time = time.fromisoformat(cutoff)
    except ValueError as error:
        raise ValueError("cutoff must be a valid 24-hour time, for example 10:00") from error
    # Demo data uses UTC timestamps; the configured cutoff is Europe/London.
    decision = pd.Timestamp("2026-01-01", tz="Europe/London").replace(hour=cutoff_time.hour, minute=cutoff_time.minute)
    result = select_forecast_vintages(forecasts, actuals, decision.tz_convert("UTC"))
    if start_date and end_date:
        if end_date < start_date:
            raise ValueError("end_date must not be before start_date")
        target = pd.to_datetime(result["target_time"], utc=True)
        result = result[(target.dt.date >= start_date) & (target.dt.date <= end_date)]
    return result


def _records(frame: pd.DataFrame) -> list[dict]:
    return frame.where(pd.notna(frame), None).to_dict(orient="records")


@app.get("/health")
def health():
    return {"status": "ok", "service": "wind-procurement-intelligence"}


@app.get("/api/comparison")
def comparison(
    cutoff: str = Query("10:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$"),
    start_date: date | None = None,
    end_date: date | None = None,
):
    try:
        rows = _dataset(cutoff, start_date, end_date)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"mode": "demo", "rows": _records(rows)}


@app.get("/api/accuracy", response_model=AccuracyResponse)
def accuracy(
    cutoff: str = Query("10:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$"),
    start_date: date | None = None,
    end_date: date | None = None,
):
    try:
        return calculate_metrics(_dataset(cutoff, start_date, end_date))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/api/forecasts")
def forecasts(cutoff: str = Query("10:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")):
    return {"mode": "demo", "rows": _records(_dataset(cutoff)[["target_time", "forecast_publish_time", "forecast_mw", "decision_cutoff"]])}


@app.get("/api/actuals")
def actuals():
    _, actual = load_demo()
    return {"mode": "demo", "rows": _records(actual)}


@app.get("/api/forecast-vintages")
def vintages(target_time: str | None = None):
    forecasts, _ = load_demo()
    if target_time:
        try:
            target = pd.Timestamp(target_time)
        except (TypeError, ValueError) as error:
            raise HTTPException(status_code=422, detail="target_time must be a valid ISO-8601 timestamp") from error
        if target.tzinfo is None:
            target = target.tz_localize("UTC")
        else:
            target = target.tz_convert("UTC")
        forecasts["target_time"] = pd.to_datetime(forecasts["target_time"], utc=True)
        forecasts = forecasts[forecasts["target_time"] == target]
    return {"mode": "demo", "rows": _records(forecasts)}


@app.get("/api/overview")
def overview(cutoff: str = Query("10:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")):
    rows = _dataset(cutoff)
    metrics = calculate_metrics(rows)
    return {"mode": "demo", "status": "fixture-ready", "decision_period": "1-31 January 2026", "cutoff": cutoff, "metrics": metrics, "row_count": len(rows)}


@app.get("/api/data-quality")
def data_quality():
    forecasts, actuals = load_demo()
    return {"mode": "demo", "retrieval_status": "fixture-ready", "actual_record_count": len(actuals), "forecast_record_count": len(forecasts), "unique_target_intervals": int(forecasts["target_time"].nunique()), "missing_actual_values": int(actuals["actual_mw"].isna().sum()), "duplicate_forecast_records": int(forecasts.duplicated(["target_time", "publish_time"]).sum()), "last_successful_refresh": None, "note": "Synthetic fixture data; not official Elexon observations."}


@app.post("/api/refresh")
def refresh():
    """Expose the controlled refresh boundary without pretending demo data was retrieved."""
    return {"status": "not-run", "mode": "demo", "message": "Refresh is disabled for the synthetic fixture. Configure an ingestion job before enabling Elexon backfill."}


@app.post("/api/residual-demand", response_model=ResidualDemandResponse)
def residual_demand(request: ResidualDemandRequest):
    wind = request.forecast_mw if request.forecast_mw is not None else float(_dataset().iloc[0]["forecast_mw"])
    return ResidualDemandResponse(demand_mw=request.demand_mw, forecast_wind_mw=wind, residual_demand_mw=max(0.0, request.demand_mw - wind))
