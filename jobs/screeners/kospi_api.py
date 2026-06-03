import os
import re
from datetime import date, timedelta
from typing import Dict, List
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd
import requests

from .common import (
    MarketConfig,
    add_technical_features,
    build_market_regime,
    build_candidates,
    latest_feature_row,
    score_universe,
    start_date,
)


OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]
SELECTED_COLUMNS = ["ticker", "security_name", "close", "adv"]
NAVER_COLUMNS = ["ticker", "security_name", "close", "volume", "value"]
EXCLUDE_NAME_KEYWORDS = [
    "ETF", "ETN",
    "KODEX", "TIGER", "ACE", "KBSTAR", "SOL", "HANARO", "KOSEF",
    "ARIRANG", "TIMEFOLIO", "PLUS", "RISE", "WON",
]

CFG = MarketConfig(
    market="KOSPI_API",
    lookback_days=420,
    universe_size=200,
    min_price=1_000.0,
    min_adv20=5_000_000_000.0,
    min_final_score=70.0,
    min_rs_rank=70.0,
    min_close_to_52w_high_ratio=0.80,
    entry_volume_multiplier=1.4,
    pullback_volume_multiplier=1.0,
    fixed_stop_pct=0.10,
    max_risk_to_stop=0.10,
    max_atr_pct=0.10,
    max_close_to_ma50_ratio=1.35,
    max_entry_extension_pct=0.05,
    stop_atr_multiple=2.0,
    structure_stop_atr_buffer=0.5,
    trailing_atr_multiple=2.5,
    min_market_regime_score=55.0,
    benchmark_tickers=["069500", "102110"],
)


def krx_date(value: str) -> str:
    return value.replace("-", "")


def resolve_latest_trading_date(end_date: str) -> str:
    return end_date


def is_excluded_name(name: str) -> bool:
    normalized = name.lower()
    return any(keyword.lower() in normalized for keyword in EXCLUDE_NAME_KEYWORDS)


def market_ohlcv_value(row: pd.Series, english_name: str, fallback_position: int) -> float:
    if english_name in row:
        return pd.to_numeric(row[english_name], errors="coerce")
    if len(row) > fallback_position:
        return pd.to_numeric(row.iloc[fallback_position], errors="coerce")
    return float("nan")


def fetch_naver_current_value() -> pd.DataFrame:
    rows = []
    seen = set()
    headers = {"User-Agent": "Mozilla/5.0"}
    link_pattern = re.compile(r'/item/main\.naver\?code=(\d{6})"[^>]*>([^<]+)</a>')
    number_pattern = re.compile(r'<td class="number">([^<]*)</td>')

    for page in range(1, 45):
        params = [
            ("sosok", "0"),
            ("page", str(page)),
            ("fieldIds", "quant"),
            ("fieldIds", "amount"),
        ]
        url = f"https://finance.naver.com/sise/sise_market_sum.naver?{urlencode(params)}"
        try:
            with urlopen(Request(url, headers=headers), timeout=30) as response:
                html = response.read().decode("euc-kr", errors="ignore")
        except Exception as exc:
            print(f"[WARN] failed to fetch Naver KOSPI page {page}: {exc}")
            continue

        matches = list(link_pattern.finditer(html))
        if not matches:
            break

        for index, match in enumerate(matches):
            ticker, name = match.group(1), match.group(2).strip()
            if ticker in seen or is_excluded_name(name):
                continue
            next_start = matches[index + 1].start() if index + 1 < len(matches) else len(html)
            row_html = html[match.end():next_start]
            numbers = [to_float_text(value) for value in number_pattern.findall(row_html)]
            if len(numbers) < 4:
                continue

            close = numbers[0]
            volume = numbers[2]
            trading_value_million = numbers[3]
            trading_value = trading_value_million * 1_000_000
            if pd.isna(close) or pd.isna(trading_value) or close < CFG.min_price:
                continue

            seen.add(ticker)
            rows.append({
                "ticker": ticker,
                "security_name": name,
                "close": float(close),
                "volume": float(volume) if not pd.isna(volume) else None,
                "value": float(trading_value),
            })

    if not rows:
        return pd.DataFrame(columns=NAVER_COLUMNS)
    return pd.DataFrame(rows, columns=NAVER_COLUMNS)


def to_float_text(value: str) -> float:
    text = re.sub(r"[^0-9.\-]", "", value)
    return float(text) if text else float("nan")


class KisClient:
    def __init__(self) -> None:
        self.base_url = (os.environ.get("KIS_BASE_URL") or "https://openapi.koreainvestment.com:9443").rstrip("/")
        self.app_key = os.environ["KIS_APP_KEY"]
        self.app_secret = os.environ["KIS_APP_SECRET"]
        self.access_token = os.environ.get("KIS_ACCESS_TOKEN") or self.fetch_access_token()

    def fetch_access_token(self) -> str:
        response = requests.post(
            f"{self.base_url}/oauth2/tokenP",
            json={
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
            },
            headers={"content-type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def headers(self, tr_id: str) -> Dict[str, str]:
        return {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P",
        }

    def volume_rank(self) -> pd.DataFrame:
        response = requests.get(
            f"{self.base_url}/uapi/domestic-stock/v1/quotations/volume-rank",
            headers=self.headers("FHPST01710000"),
            params={
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_COND_SCR_DIV_CODE": "20171",
                "FID_INPUT_ISCD": "0000",
                "FID_DIV_CLS_CODE": "1",
                "FID_BLNG_CLS_CODE": "3",
                "FID_TRGT_CLS_CODE": "111111111",
                "FID_TRGT_EXLS_CLS_CODE": "0000000000",
                "FID_INPUT_PRICE_1": "",
                "FID_INPUT_PRICE_2": "",
                "FID_VOL_CNT": "",
                "FID_INPUT_DATE_1": "",
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("rt_cd") not in (None, "0"):
            print(f"[WARN] KIS volume-rank failed: {payload.get('msg1') or payload}")
            return pd.DataFrame(columns=SELECTED_COLUMNS)

        rows = []
        for row in payload.get("output") or []:
            ticker = row.get("mksc_shrn_iscd") or row.get("stck_shrn_iscd")
            name = row.get("hts_kor_isnm") or row.get("stck_kor_isnm") or ticker
            if not ticker or is_excluded_name(name):
                continue
            close = parse_number(row.get("stck_prpr"))
            trading_value = parse_number(row.get("acml_tr_pbmn"))
            if pd.isna(trading_value):
                trading_value = parse_number(row.get("avrg_vol") or row.get("vol_tnrt"))
            if pd.isna(trading_value) or pd.isna(close) or close < CFG.min_price:
                continue
            rows.append({"ticker": ticker, "security_name": name, "close": float(close), "adv": float(trading_value)})

        if not rows:
            return pd.DataFrame(columns=SELECTED_COLUMNS)
        return pd.DataFrame(rows, columns=SELECTED_COLUMNS).sort_values("adv", ascending=False).reset_index(drop=True)

    def daily_chart(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        start_dt = date.fromisoformat(start)
        end_dt = date.fromisoformat(end)
        frames = []

        chunk_start = start_dt
        while chunk_start <= end_dt:
            chunk_end = min(chunk_start + timedelta(days=89), end_dt)
            frames.append(self._daily_chart_chunk(ticker, chunk_start.isoformat(), chunk_end.isoformat()))
            chunk_start = chunk_end + timedelta(days=1)

        frames = [frame for frame in frames if not frame.empty]
        if not frames:
            return pd.DataFrame(columns=OHLCV_COLUMNS + ["value"])

        combined = pd.concat(frames).sort_index()
        combined = combined[~combined.index.duplicated(keep="last")]
        return combined[OHLCV_COLUMNS + ["value"]]

    def _daily_chart_chunk(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        response = requests.get(
            f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
            headers=self.headers("FHKST03010100"),
            params={
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": ticker,
                "FID_INPUT_DATE_1": start.replace("-", ""),
                "FID_INPUT_DATE_2": end.replace("-", ""),
                "FID_PERIOD_DIV_CODE": "D",
                "FID_ORG_ADJ_PRC": "0",
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("output2") or []
        if not rows:
            return pd.DataFrame(columns=OHLCV_COLUMNS + ["value"])

        df = pd.DataFrame(rows)
        normalized = pd.DataFrame({
            "open": to_number(df["stck_oprc"]).to_numpy(),
            "high": to_number(df["stck_hgpr"]).to_numpy(),
            "low": to_number(df["stck_lwpr"]).to_numpy(),
            "close": to_number(df["stck_clpr"]).to_numpy(),
            "volume": to_number(df["acml_vol"]).to_numpy(),
            "value": to_number(df["acml_tr_pbmn"] if "acml_tr_pbmn" in df else [None] * len(df)).to_numpy(),
        }, index=pd.to_datetime(df["stck_bsop_date"]).dt.date)
        normalized["value"] = normalized["value"].fillna(normalized["close"] * normalized["volume"])
        return normalized.sort_index()[OHLCV_COLUMNS + ["value"]].dropna(subset=OHLCV_COLUMNS)


def to_number(values) -> pd.Series:
    if values is None:
        return pd.Series(dtype="float64")
    return pd.to_numeric(pd.Series(values).astype(str).str.replace(",", "", regex=False), errors="coerce")


def parse_number(value) -> float:
    if value is None:
        return float("nan")
    text = str(value).replace(",", "").strip()
    if not text:
        return float("nan")
    return pd.to_numeric(text, errors="coerce")


def fetch_top_by_current_value(client: KisClient) -> pd.DataFrame:
    selected = client.volume_rank()
    if not selected.empty:
        print(f"[INFO] KIS volume-rank returned {len(selected)} rows")
    if len(selected) >= CFG.universe_size:
        return selected.head(CFG.universe_size).reset_index(drop=True)

    print("[WARN] KIS volume-rank returns at most about 30 rows; supplementing with Naver Finance fallback.")
    naver = fetch_naver_current_value()
    if naver.empty:
        return selected[SELECTED_COLUMNS].reset_index(drop=True)

    supplement = naver.rename(columns={"value": "adv"})[SELECTED_COLUMNS]
    combined = pd.concat([selected[SELECTED_COLUMNS], supplement], ignore_index=True)
    combined = combined.drop_duplicates(subset=["ticker"], keep="first")
    return combined.sort_values("adv", ascending=False).head(CFG.universe_size).reset_index(drop=True)


def download_ohlcv(tickers: List[str], start: str, end: str, client: KisClient) -> Dict[str, pd.DataFrame]:
    result: Dict[str, pd.DataFrame] = {}
    for ticker in sorted(set(tickers)):
        try:
            df = client.daily_chart(ticker, start, end)
        except Exception as exc:
            print(f"[WARN] failed to download {ticker} from KIS: {exc}")
            continue
        if len(df) > 0:
            result[ticker] = df
    return result


def retain_downloaded_universe(ohlcv: Dict[str, pd.DataFrame], universe: pd.DataFrame) -> pd.DataFrame:
    selected = universe[universe["ticker"].isin(ohlcv.keys())].copy()
    if selected.empty:
        print("[WARN] No KOSPI_API symbols were downloaded from KIS daily chart data.")
        return pd.DataFrame(columns=SELECTED_COLUMNS)
    return selected[SELECTED_COLUMNS].reset_index(drop=True)


def run(end_date: str) -> dict:
    client = KisClient()
    effective_end_date = resolve_latest_trading_date(end_date)
    selected = fetch_top_by_current_value(client)
    tickers = selected["ticker"].tolist()
    names = selected.set_index("ticker")["security_name"].to_dict()
    all_tickers = sorted(set(tickers + CFG.benchmark_tickers))

    ohlcv = download_ohlcv(all_tickers, start_date(effective_end_date, CFG.lookback_days), effective_end_date, client)
    selected = retain_downloaded_universe(ohlcv, selected)
    tickers = selected["ticker"].tolist()
    names = selected.set_index("ticker")["security_name"].to_dict()
    print(f"[INFO] KOSPI_API downloaded={len(ohlcv)} selected={len(selected)}")

    if CFG.benchmark_tickers[0] not in ohlcv or CFG.benchmark_tickers[1] not in ohlcv:
        print("[WARN] KOSPI_API benchmark ETF data is missing from KIS.")
        return {
            "market": CFG.market,
            "run_date": effective_end_date,
            "selected": selected,
            "scored": pd.DataFrame(),
            "candidates": pd.DataFrame(),
            "market_bullish": False,
            "market_regime_score": 0.0,
            "market_exposure": 0.0,
        }

    primary = add_technical_features(ohlcv[CFG.benchmark_tickers[0]])
    secondary = add_technical_features(ohlcv[CFG.benchmark_tickers[1]])

    rows = []
    skipped_short_history = 0
    skipped_liquidity = 0
    for ticker in tickers:
        if ticker not in ohlcv:
            continue
        df = add_technical_features(ohlcv[ticker])
        if len(df) < 260:
            skipped_short_history += 1
            continue
        last = df.iloc[-1]
        if last["close"] < CFG.min_price or last["adv20"] < CFG.min_adv20:
            skipped_liquidity += 1
            continue
        row = latest_feature_row(ticker, names.get(ticker, ""), df, primary, secondary, CFG)
        if row:
            rows.append(row)

    print(
        "[INFO] KOSPI_API scoring "
        f"rows={len(rows)} skipped_short_history={skipped_short_history} skipped_liquidity={skipped_liquidity}"
    )

    scored = score_universe(pd.DataFrame(rows)) if rows else pd.DataFrame()
    market_regime = build_market_regime(primary, secondary, scored)
    candidates = build_candidates(scored, CFG, market_regime) if not scored.empty else pd.DataFrame()
    return {
        "market": CFG.market,
        "run_date": effective_end_date,
        "selected": selected,
        "scored": scored,
        "candidates": candidates,
        "market_bullish": market_regime["market_bullish"],
        "market_regime_score": market_regime["score"],
        "market_exposure": market_regime["exposure"],
    }
