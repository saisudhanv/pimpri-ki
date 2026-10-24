# Five-minute demonstration

1. Introduce the day-ahead problem: wind uncertainty affects the residual demand view, but this tool does not claim to calculate a utility's actual purchase.
2. Show the KPI strip and the forecast-versus-actual trace for the January 2026 decision window.
3. Change the cutoff and explain that the selected publication changes only when it was available by that cutoff.
4. Open the vintage explorer: the 10:30 publication for the 12:00 interval is visible in the fixture history but cannot be selected at the 10:00 cutoff. The 08:30 publication (850 MW) is selected; actual is 880 MW.
5. Enter hypothetical demand and explain residual demand as `max(0, demand - selected wind)`.

## Technical-lead walkthrough

`backend/app/selection.py` is a dedicated, independently testable cutoff algorithm. `metrics.py` handles missing values, zero actuals, and non-finite inputs. `data.py` is the Elexon integration boundary and demo fixture loader. FastAPI exposes consistent JSON and CORS is restricted by `FRONTEND_ORIGINS`. The frontend calls the backend only, displays source status, and labels synthetic data.

The current trade-off is a small JSON fixture so the application is deterministic and runnable without external access. A production ingestion job should persist append-only FUELHH/WINDFOR records, validate source responses, record refresh status, and mount durable storage.
