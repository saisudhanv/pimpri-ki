from datetime import datetime

from pydantic import BaseModel, Field


class ComparisonRow(BaseModel):
    target_time: datetime
    decision_cutoff: datetime
    forecast_publish_time: datetime | None = None
    forecast_mw: float | None = None
    actual_mw: float | None = None
    error_mw: float | None = None
    selected: bool = False


class AccuracyResponse(BaseModel):
    valid_sample_count: int
    missing_actual_count: int
    missing_forecast_count: int
    zero_actual_count: int
    mae_mw: float | None = None
    rmse_mw: float | None = None
    bias_mw: float | None = None
    mape_percent: float | None = None
    wape_percent: float | None = None
    evaluation_start: datetime | None = None
    evaluation_end: datetime | None = None


class ResidualDemandRequest(BaseModel):
    demand_mw: float = Field(ge=0)
    forecast_mw: float | None = Field(default=None, ge=0)


class ResidualDemandResponse(BaseModel):
    demand_mw: float
    forecast_wind_mw: float
    residual_demand_mw: float
    hypothetical: bool = True
