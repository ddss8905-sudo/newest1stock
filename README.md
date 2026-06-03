# Stock Screener App

NASDAQ and KOSDAQ trend-following screener dashboard for Vercel.

## Architecture
- GitHub Actions runs the Python screeners.
- Supabase stores screening runs and results.
- Vercel hosts the Next.js dashboard.

## Execution
- NASDAQ and KOSDAQ run on demand from the dashboard.
- GitHub Actions workflows keep `workflow_dispatch` enabled and do not run on a daily schedule.

## Setup
1. Create a Supabase project.
2. Run `db/setup_supabase.sql` in the Supabase SQL editor for a fresh database.
   - If you prefer separate files, run `db/schema.sql` first, then any files in `db/migrations`.
3. Add these secrets to GitHub Actions:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
4. Add the same values to Vercel environment variables.
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `GITHUB_ACTIONS_TOKEN`
   - `GITHUB_REPOSITORY` (defaults to `ddss8905-sudo/stocke`)
   - `GITHUB_DISPATCH_BRANCH` (defaults to `main`)
   - `KIS_APP_KEY`
   - `KIS_APP_SECRET`
   - `KIS_BASE_URL` (defaults to Korea Investment production OpenAPI)
5. Install web dependencies and run locally:

```powershell
npm install
npm run dev
```

6. Test the Python jobs locally:

```powershell
cd jobs
py -m pip install -r requirements.txt
py run_market.py --market KOSDAQ
py run_market.py --market NASDAQ
```

If Supabase environment variables are not set, the Python job writes a local JSON payload under `jobs/data`.
If Vercel environment variables are not set, the web app displays sample rows.

## On-demand screening
The dashboard includes a `Run now` button. It calls `/api/run-screener`, which triggers the matching GitHub Actions workflow through `workflow_dispatch`.

Create a GitHub fine-grained token with access to this repository and Actions workflow permission, then add it to Vercel as:

```text
GITHUB_ACTIONS_TOKEN=...
```

The button starts the workflow. Results appear after the workflow finishes and uploads new rows to Supabase.

## KOSPI API market
`KOSPI_API` uses Korea Investment OpenAPI credentials from GitHub Actions secrets:

```text
KIS_APP_KEY
KIS_APP_SECRET
KIS_BASE_URL
```

Before using `KOSPI_API`, run `db/migrations/001_add_kospi_api_market.sql` in Supabase SQL Editor so the existing market check constraints accept the new market value.

## Risk and regime filters
The shared screener logic applies to `NASDAQ`, `KOSDAQ`, and `KOSPI_API`.

- Market regime is scored from the primary benchmark, secondary benchmark, and universe breadth. New candidates require a minimum regime score.
- Candidate risk uses a structure/ATR stop instead of only a fixed percent stop.
- Entry triggers are split into breakout and pullback setups.
- Overextended names are filtered by ATR percent, distance from the 50-day moving average, and pivot extension.

Run `db/migrations/002_add_risk_regime_entry_columns.sql` in Supabase SQL Editor before uploading new runs that include these fields.

## Exit tracking model
Exit rules need position state, not just a daily screener row. A position tracker should store the entry price, initial stop, highest high since entry, current trailing stop, and latest action. Each daily run can then update that state with fresh OHLCV data.

The shared Python module includes `evaluate_position_exit`, which returns `hold`, `trim_or_watch`, or `hard_exit` based on the initial stop, 2R trailing stop, 50-day moving average break, and market regime weakness. The next practical step is adding a `positions` table and a small job that calls this function for held tickers after the screener finishes.
