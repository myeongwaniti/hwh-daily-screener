import ast
import concurrent.futures
import datetime as dt
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

CACHE_ROOT = Path(__file__).resolve().parent / "cache"


def _make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=0.6, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    return s


SESSION = _make_session()


def fetch_kr_daily(code: str, start_date: str = "20240101") -> pd.DataFrame | None:
    url = (
        f"https://fchart.stock.naver.com/siseJson.naver"
        f"?symbol={code}&requestType=1&startTime={start_date}&endTime=20991231&timeframe=day"
    )
    try:
        r = SESSION.get(url, timeout=12)
        if r.status_code != 200:
            return None
        rows = []
        for line in r.text.splitlines():
            line = line.strip().rstrip(",")
            if line.startswith('["20'):
                rows.append(ast.literal_eval(line))
        if len(rows) < 130:
            return None
        df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume", "foreign_rate"])
        df["date"] = pd.to_datetime(df["date"])
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df[(df["low"] > 0) & (df["close"] > 0) & (df["volume"] > 0)].dropna(subset=["close"]).reset_index(drop=True)
        return df if len(df) >= 130 else None
    except Exception:
        return None


def fetch_yf_daily(symbol: str, range_: str = "3y") -> pd.DataFrame | None:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={range_}&interval=1d"
    try:
        r = SESSION.get(url, timeout=12)
        if r.status_code != 200:
            return None
        res = r.json().get("chart", {}).get("result")
        if not res:
            return None
        data = res[0]
        ts = data.get("timestamp")
        if not ts:
            return None
        q = data["indicators"]["quote"][0]
        tz_name = data.get("meta", {}).get("exchangeTimezoneName", "America/New_York")
        dates = pd.to_datetime(ts, unit="s", utc=True).tz_convert(tz_name).tz_localize(None).normalize()
        df = pd.DataFrame(
            {
                "date": dates,
                "open": q.get("open"),
                "high": q.get("high"),
                "low": q.get("low"),
                "close": q.get("close"),
                "volume": q.get("volume"),
            }
        )
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = (
            df.dropna(subset=["open", "high", "low", "close"])
            .drop_duplicates(subset=["date"], keep="last")
            .reset_index(drop=True)
        )
        df = df[df["low"] > 0].reset_index(drop=True)
        return df if len(df) >= 130 else None
    except Exception:
        return None


def fetch_market_thermometer(use_cache: bool = True) -> dict:
    """Fetch cross-asset benchmarks for RS calculation & top dashboard banner."""
    today_dir = CACHE_ROOT / dt.date.today().strftime("%Y-%m-%d")
    today_dir.mkdir(parents=True, exist_ok=True)
    cache_file = today_dir / "benchmarks.pkl"
    if use_cache and cache_file.exists():
        with open(cache_file, "rb") as f:
            return pickle.load(f)

    benchmarks = {}
    kr_idx = [("KOSPI", "KOSPI"), ("KOSDAQ", "KOSDAQ")]
    for key, sym in kr_idx:
        df = fetch_kr_daily(sym, start_date="20240101")
        if df is not None:
            benchmarks[key] = df

    yf_syms = [
        ("US100", "NQ=F"),
        ("NDX", "^NDX"),
        ("SP500", "^GSPC"),
        ("SOXX", "SOXX"),
        ("BTC", "BTC-USD"),
        ("DXY", "DX-Y.NYB"),
        ("USDKRW", "KRW=X"),
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as ex:
        futs = {ex.submit(fetch_yf_daily, sym, "3y"): key for key, sym in yf_syms}
        for fut in concurrent.futures.as_completed(futs):
            key = futs[fut]
            df = fut.result()
            if df is not None:
                benchmarks[key] = df

    with open(cache_file, "wb") as f:
        pickle.dump(benchmarks, f)
    return benchmarks


def fetch_universe_data(universe: list[dict], market: str, use_cache: bool = True, max_workers: int = 12) -> dict[str, pd.DataFrame]:
    """Fetch daily OHLCV for all symbols in universe with daily local cache."""
    today_dir = CACHE_ROOT / dt.date.today().strftime("%Y-%m-%d")
    today_dir.mkdir(parents=True, exist_ok=True)
    cache_file = today_dir / f"{market.lower()}_ohlcv.pkl"

    if use_cache and cache_file.exists():
        with open(cache_file, "rb") as f:
            return pickle.load(f)

    data_map = {}
    fn = fetch_kr_daily if market == "KR" else fetch_yf_daily

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(fn, item["symbol"]): item["symbol"] for item in universe}
        for fut in concurrent.futures.as_completed(futs):
            sym = futs[fut]
            df = fut.result()
            if df is not None:
                data_map[sym] = df

    with open(cache_file, "wb") as f:
        pickle.dump(data_map, f)
    return data_map
