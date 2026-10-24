import json
import math

from datetime import date
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FIXTURE = DATA_DIR / "demo.json"
ELEXON_BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
REQUIRED_FIELDS = {"dataset", "startTime", "publishTime", "generation"}


class ElexonDataError(RuntimeError):
    """Raised when Elexon returns an unusable or out-of-scope response."""


def _records_from_payload(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = payload.get("value", payload.get("data", payload.get("records")))
    else:
        records = None
    if not isinstance(records, list) or not all(isinstance(record, dict) for record in records):
        raise ElexonDataError("Elexon response did not contain a list of record objects.")
    return records


def _validate_records(records: list[dict], dataset: str) -> list[dict]:
    for index, record in enumerate(records):
        missing = REQUIRED_FIELDS - record.keys()
        if missing:
            raise ElexonDataError(
                f"{dataset} record {index} is missing required fields: {', '.join(sorted(missing))}."
            )
        try:
            value = float(record["generation"])
        except (TypeError, ValueError) as error:
            raise ElexonDataError(f"{dataset} record {index} has a non-numeric generation.") from error
        if not math.isfinite(value):
            raise ElexonDataError(f"{dataset} record {index} has a non-finite generation.")
        for field in ("startTime", "publishTime"):
            if pd.isna(pd.to_datetime(record[field], utc=True, errors="coerce")):
                raise ElexonDataError(f"{dataset} record {index} has an invalid {field}.")
    return records


def _parse_records(records: list[dict], forecast: bool) -> pd.DataFrame:
    rows = []
    for record in records:
        target = record["startTime"]
        value = float(record["generation"])
        row = {"target_time": target, "forecast_mw" if forecast else "actual_mw": value}
        if forecast:
            row["publish_time"] = record["publishTime"]
        rows.append(row)
    return pd.DataFrame(rows)


def load_demo() -> tuple[pd.DataFrame, pd.DataFrame]:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return _parse_records(payload["forecasts"], True), _parse_records(payload["actuals"], False)


def fetch_dataset(
    dataset: str,
    start: str | date,
    end: str | date,
    *,
    require_target_coverage: bool = True,
) -> list[dict]:
    """Fetch and validate an Elexon dataset for settlement-date bounds.

    WINDFOR currently exposes a rolling current forecast; old bounds are
    ignored by the service. Coverage validation prevents that live response
    being mistaken for a historical January forecast.
    """
    if dataset not in {"FUELHH", "WINDFOR"}:
        raise ValueError(f"Unsupported Elexon dataset: {dataset}")
    start_date = pd.Timestamp(start).date()
    end_date = pd.Timestamp(end).date()
    if end_date < start_date:
        raise ValueError("end must not be before start")
    params = {
        "settlementDateFrom": start_date.isoformat(),
        "settlementDateTo": end_date.isoformat(),
    }
    if dataset == "FUELHH":
        params["fuelType"] = "WIND"
    url = f"{ELEXON_BASE_URL}/{dataset}/stream"
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with httpx.Client(timeout=60) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                records = _validate_records(_records_from_payload(response.json()), dataset)
            break
        except (httpx.HTTPError, ValueError, ElexonDataError) as error:
            last_error = error
            if attempt == 2:
                raise ElexonDataError(f"Unable to retrieve {dataset}: {error}") from error
    else:
        raise ElexonDataError(f"Unable to retrieve {dataset}: {last_error}")
    if dataset == "FUELHH":
        records = [record for record in records if record.get("fuelType") == "WIND"]
    if require_target_coverage and records:
        targets = pd.to_datetime([record["startTime"] for record in records], utc=True)
        requested_start = pd.Timestamp(start_date, tz="UTC")
        requested_end = pd.Timestamp(end_date + pd.Timedelta(days=1), tz="UTC")
        if targets.max() < requested_start or targets.min() >= requested_end:
            raise ElexonDataError(
                f"{dataset} response does not cover {start_date} through {end_date}; "
                f"returned {targets.min().date()} through {targets.max().date()}."
            )
    if not records:
        raise ElexonDataError(f"{dataset} returned no records for {start_date} through {end_date}.")
    return records


def fetch_january_2026() -> dict[str, list[dict]]:
    """Fetch January delivery actuals and forecasts without fabricating gaps."""
    result: dict[str, list[dict]] = {}
    result["actuals"] = fetch_dataset("FUELHH", "2026-01-01", "2026-02-01")
    result["forecasts"] = fetch_dataset("WINDFOR", "2026-01-01", "2026-02-01")
    return result
