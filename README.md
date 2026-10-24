# Wind Procurement Intelligence

A FastAPI and React dashboard for reconstructing GB national wind forecasts available at a day-ahead procurement decision cutoff, comparing them with actual generation, and exploring forecast uncertainty.

## Scope and data integrity

The January 2026 prototype treats 1-31 January as **decision dates**, with delivery intervals through 1 February. The default `10:00 Europe/London` cutoff is an illustrative, configurable assumption, not a contractual deadline. All timestamps are normalized to UTC internally and displayed in local time.

Official integration boundaries are Elexon's [FUELHH](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream) actual dataset and [WINDFOR](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream) forecast dataset. The verified BMRS base is `https://data.elexon.co.uk/bmrs/api/v1/datasets`. Dataset requests use `settlementDateFrom` and `settlementDateTo`; FUELHH additionally uses `fuelType=WIND`. Responses observed during the October 2026 audit were either a bare JSON list or an envelope containing `value`/`data`, and the client validates both forms.

### January 2026 integration audit

On 24 October 2026, a live FUELHH request for `settlementDateFrom=2026-01-01&settlementDateTo=2026-02-01&fuelType=WIND` returned 1,536 records, all with `fuelType=WIND`, covering `2026-01-01T00:00:00Z` through `2026-02-01T23:30:00Z`. This is 32 days of 48 half-hourly target intervals.

The same documented date-bound request to WINDFOR returned 74 records covering `2026-10-23` through `2026-10-26`, with a single current publication time, rather than January 2026. The client rejects this response with an explicit coverage error. It does not use those records, fill the gap with zeros, or label the demo fixture as historical Elexon data. Therefore January forecast accuracy cannot be reported from the currently accessible WINDFOR stream until an official historical forecast archive or an approved archived extract is provided.

The retrieval code is in `backend/app/data.py`; `fetch_january_2026()` deliberately fails rather than returning a partially valid actuals/forecast pair.

For each target interval, the selection service filters `publishTime <= cutoff`, then chooses the latest eligible publication. Missing forecasts remain missing. Metrics use only valid matched pairs and define `error = forecast - actual`. MAE, RMSE and bias are MW; MAPE excludes zero actuals; WAPE uses the sum of absolute actuals.

## Local setup

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

In another terminal:

```powershell
cd frontend\vite-pro
npm install
npm run dev
```

Open `http://localhost:5173`; API docs are at `http://localhost:8000/docs`.

## Docker

```powershell
docker compose up --build
```

The dashboard is at `http://localhost:8080` and the API at `http://localhost:8000`. No PostgreSQL or paid service is required. For real historical ingestion, implement a durable mounted data directory and configure the backend URL and CORS before deployment.

## API

`GET /health`, `/api/overview`, `/api/forecasts`, `/api/actuals`, `/api/comparison`, `/api/accuracy`, `/api/forecast-vintages`, and `/api/data-quality` expose the analysis. `POST /api/residual-demand` accepts `{ "demand_mw": 2400, "forecast_mw": 850 }`. The residual result is hypothetical and must not be interpreted as a procurement quantity.

## Testing and deployment

Run backend tests with `pytest backend/tests`. Build the frontend with `npm run build` from `frontend/vite-pro`. Vercel can deploy `frontend/vite-pro` with `VITE_API_URL` set to the deployed FastAPI origin. Deploy FastAPI on a Python-compatible service with `FRONTEND_ORIGINS` configured. Serverless filesystems are not durable: use object storage or a database only when persistent production history is required.

Known limitations include the demo-only default dataset, no credentials or production scheduler, and no demand, price, imports, or contractual-position data. Those inputs are deliberately not invented.

## AI tools disclosure

This first version was implemented with AI assistance in VS Code using Copilot SDK. The assistant generated the initial application structure, selection and metric implementations, UI, tests, Docker files, and documentation; all code remains subject to normal engineering review and real Elexon integration validation.
