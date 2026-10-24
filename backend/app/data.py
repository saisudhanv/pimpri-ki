import json
from pathlib import Path

import httpx
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FIXTURE = DATA_DIR / "demo.json"
ELEXON_BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets"


def _parse_records(records: list[dict], forecast: bool) -> pd.DataFrame:
    rows = []
    for record in records:
        target = record.get("startTime")
        value = record.get("generation")
        if target is None or value is None:
            continue
        row = {"target_time": target, "forecast_mw" if forecast else "actual_mw": value}
        if forecast:
            row["publish_time"] = record.get("publishTime")
        rows.append(row)
    return pd.DataFrame(rows)


def load_demo() -> tuple[pd.DataFrame, pd.DataFrame]:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return _parse_records(payload["forecasts"], True), _parse_records(payload["actuals"], False)


def fetch_dataset(dataset: str, start: str, end: str) -> list[dict]:
    params = {"from": start, "to": end}
    with httpx.Client(timeout=30) as client:
        response = client.get(f"{ELEXON_BASE_URL}/{dataset}/stream", params=params)
        response.raise_for_status()
        payload = response.json()
    if isinstance(payload, dict):
        return payload.get("data", payload.get("records", []))
    return payload
