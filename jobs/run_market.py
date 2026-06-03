import argparse
import json
import math
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import requests

from screeners import kosdaq, kospi_api, nasdaq


RUNNERS = {
    "NASDAQ": nasdaq.run,
    "KOSDAQ": kosdaq.run,
    "KOSPI_API": kospi_api.run,
}

CANDIDATE_ONLY_FIELDS = [
    "market_regime_score",
    "market_exposure",
    "entry_pivot",
    "entry_extension_pct",
    "breakout_entry",
    "pullback_entry",
    "entry_setup",
    "stop_basis",
]


def records(df: pd.DataFrame) -> list:
    if df.empty:
        return []
    clean = df.replace([np.inf, -np.inf], np.nan).where(pd.notnull(df), None)
    return [sanitize_record(row) for row in clean.to_dict(orient="records")]


def sanitize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def sanitize_record(row: Dict[str, Any]) -> Dict[str, Any]:
    return {key: sanitize_value(value) for key, value in row.items()}


def write_local_payload(payload: Dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{payload['market'].lower()}_{payload['run_date']}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def supabase_headers() -> Dict[str, str]:
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def insert_supabase(table: str, body: Any) -> requests.Response:
    url = f"{os.environ['SUPABASE_URL'].rstrip('/')}/rest/v1/{table}"
    response = requests.post(url, headers=supabase_headers(), json=body, timeout=60)
    if not response.ok:
        print(f"[ERROR] Supabase insert failed: table={table} status={response.status_code}")
        print(response.text[:2000])
        response.raise_for_status()
    return response


def upload_to_supabase(payload: Dict[str, Any]) -> None:
    run_body = {
        "market": payload["market"],
        "run_date": payload["run_date"],
        "status": "completed",
        "market_bullish": payload["market_bullish"],
        "market_regime_score": payload.get("market_regime_score"),
        "market_exposure": payload.get("market_exposure"),
        "selected_count": len(payload["selected"]),
        "scored_count": len(payload["scored"]),
        "candidate_count": len(payload["candidates"]),
        "started_at": payload["started_at"],
        "finished_at": payload["finished_at"],
    }
    run = insert_supabase("screening_runs", run_body).json()[0]
    run_id = run["id"]

    result_rows = []
    candidates_by_ticker = {row["ticker"]: row for row in payload["candidates"]}
    for row in payload["scored"]:
        row = dict(row)
        candidate = candidates_by_ticker.get(row["ticker"])
        row["run_id"] = run_id
        row["market"] = payload["market"]
        row["run_date"] = payload["run_date"]
        row["is_candidate"] = candidate is not None
        row["entry_trigger"] = bool(candidate.get("entry_trigger")) if candidate else False
        row["stop_price"] = candidate.get("stop_price") if candidate else None
        row["risk_to_stop"] = candidate.get("risk_to_stop") if candidate else None
        for field in CANDIDATE_ONLY_FIELDS:
            row[field] = candidate.get(field) if candidate else None
        result_rows.append(sanitize_record(row))

    if result_rows:
        for index in range(0, len(result_rows), 250):
            insert_supabase("screening_results", result_rows[index:index + 250])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", choices=sorted(RUNNERS), required=True)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--output-dir", default="data")
    args = parser.parse_args()

    started_at = datetime.now(timezone.utc).isoformat()
    result = RUNNERS[args.market](args.date)
    finished_at = datetime.now(timezone.utc).isoformat()

    payload = {
        "market": result["market"],
        "run_date": result["run_date"],
        "market_bullish": result["market_bullish"],
        "market_regime_score": result.get("market_regime_score"),
        "market_exposure": result.get("market_exposure"),
        "selected": records(result["selected"]),
        "scored": records(result["scored"]),
        "candidates": records(result["candidates"]),
        "started_at": started_at,
        "finished_at": finished_at,
    }

    path = write_local_payload(payload, Path(args.output_dir))
    print(f"[INFO] local payload saved: {path}")

    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        upload_to_supabase(payload)
        print("[INFO] uploaded to Supabase")
    else:
        print("[INFO] Supabase env vars are missing; skipped upload")


if __name__ == "__main__":
    main()
