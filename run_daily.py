import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path

import pandas as pd

from universe import fetch_kr_universe, fetch_us_universe
from data_fetcher import fetch_market_thermometer, fetch_universe_data
from hwh_scorer import add_indicators, score_stock
from hwh_chart_drawer import draw_hwh_chart
from dashboard_builder import build_dashboard_html

OUT_DIR = Path(__file__).resolve().parent / "output"


def _build_thermometer(benchmarks: dict) -> tuple[list[dict], float | None]:
    specs = [
        ("KOSPI", "KOSPI", lambda v: f"{v:,.1f}"),
        ("KOSDAQ", "KOSDAQ", lambda v: f"{v:,.1f}"),
        ("US100", "US100 (NQ)", lambda v: f"{v:,.1f}"),
        ("SP500", "S&P 500", lambda v: f"{v:,.1f}"),
        ("SOXX", "반도체 SOXX", lambda v: f"${v:,.2f}"),
        ("BTC", "비트코인", lambda v: f"${v:,.0f}"),
        ("USDKRW", "원/달러", lambda v: f"{v:,.1f}원"),
    ]
    cards = []
    for key, label, fmt in specs:
        df = benchmarks.get(key)
        if df is None or len(df) < 20:
            continue
        df = add_indicators(df)
        last, prev = df.iloc[-1], df.iloc[-2]
        c = float(last["close"])
        chg = (c / float(prev["close"]) - 1) * 100
        rsi = round(float(last["rsi14"]), 1) if pd.notna(last["rsi14"]) else 50.0
        sma120 = last["sma120"]
        sma500 = last["sma500"]
        if pd.notna(sma500) and c < sma500:
            ma_status = "500일선 하회"
        elif pd.notna(sma120) and c < sma120:
            ma_status = "120일선 하회"
        else:
            ma_status = "120일선 상회"
        cards.append(
            {
                "key": key,
                "label": label,
                "price_str": fmt(c),
                "chg_pct": round(chg, 2),
                "rsi": rsi,
                "ma_status": ma_status,
            }
        )

    fx_ratio = None
    if "USDKRW" in benchmarks and "DXY" in benchmarks:
        fx = float(benchmarks["USDKRW"].iloc[-1]["close"])
        dxy = float(benchmarks["DXY"].iloc[-1]["close"])
        if dxy > 0:
            fx_ratio = round(fx / dxy, 2)
    return cards, fx_ratio


def run(
    market: str = "all",
    top_charts: int = 5,
    no_cache: bool = False,
    upload_drive: bool = False,
    out_html: str | None = None,
    standalone_web: bool = False,
):
    today_str = dt.date.today().strftime("%Y-%m-%d")
    run_dir = OUT_DIR / today_str
    charts_dir = run_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/5] Fetching cross-asset thermometer...", flush=True)
    benchmarks = fetch_market_thermometer(use_cache=not no_cache)
    thermometer, fx_ratio = _build_thermometer(benchmarks)

    kr_scored, us_scored = [], []
    kr_data, us_data = {}, {}

    if market in ("all", "kr"):
        print(f"[2/5] Scanning KR universe (KOSPI 120 + KOSDAQ 80)...", flush=True)
        kr_uni = fetch_kr_universe(120, 80)
        kr_data = fetch_universe_data(kr_uni, "KR", use_cache=not no_cache)
        for meta in kr_uni:
            df = kr_data.get(meta["symbol"])
            bench = benchmarks.get("KOSPI" if meta["exchange"] == "KOSPI" else "KOSDAQ")
            res = score_stock(meta, df, bench)
            if res is not None:
                kr_scored.append(res)
        kr_scored.sort(key=lambda x: x["total_score"], reverse=True)
        print(f"      KR fetched={len(kr_data)}, qualified(non-overheated)={len(kr_scored)}", flush=True)

    if market in ("all", "us"):
        print(f"[3/5] Scanning US universe (NASDAQ 100 + NYSE 120 + SPY/HWH Core)...", flush=True)
        us_uni = fetch_us_universe(100, 120)
        us_data = fetch_universe_data(us_uni, "US", use_cache=not no_cache)
        for meta in us_uni:
            df = us_data.get(meta["symbol"])
            bench = benchmarks.get("NDX" if meta["exchange"] == "NASDAQ" else "SP500")
            res = score_stock(meta, df, bench)
            if res is not None:
                us_scored.append(res)
        us_scored.sort(key=lambda x: x["total_score"], reverse=True)
        print(f"      US fetched={len(us_data)}, qualified(non-overheated)={len(us_scored)}", flush=True)

    top_items = kr_scored[:25] + us_scored[:25]
    top_items.sort(key=lambda x: x["total_score"], reverse=True)

    print(f"[4/5] Rendering HWH auto-trendline charts (KR Top {top_charts} + US Top {top_charts})...", flush=True)
    charts_b64 = {}
    for subset, dmap in [(kr_scored[:top_charts], kr_data), (us_scored[:top_charts], us_data)]:
        for rank, item in enumerate(subset, 1):
            sym = item["symbol"]
            key = f"{item['market']}:{sym}"
            png_path = charts_dir / f"{item['market']}_{rank:02d}_{sym}.png"
            charts_b64[key] = draw_hwh_chart(item, dmap[sym], out_path=png_path)
            print(f"      Charted {key} ({item['name']}) -> {item['total_score']}점 [{item['setup_type']}]", flush=True)

    payload = {
        "scan_date": today_str,
        "fx_ratio": fx_ratio,
        "thermometer": thermometer,
        "stats": {
            "kr_scanned": len(kr_data),
            "us_scanned": len(us_data),
        },
        "items": top_items,
        "charts": charts_b64,
    }

    (run_dir / "screener_results.json").write_text(
        json.dumps({k: v for k, v in payload.items() if k != "charts"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    html = build_dashboard_html(payload, standalone_web=standalone_web)
    local_html = Path(out_html) if out_html else (run_dir / f"hwh_daily_screener_{today_str}.html")
    local_html.parent.mkdir(parents=True, exist_ok=True)
    local_html.write_text(html, encoding="utf-8")
    print(f"[5/5] Dashboard built: {local_html} ({local_html.stat().st_size // 1024} KB)", flush=True)

    print("\n================ KR TOP 10 ================")
    for i, x in enumerate(kr_scored[:10], 1):
        print(f"  {i:2d}. {x['name']:12s} ({x['symbol']}) | {x['total_score']:5.1f}점 | {x['setup_type']:12s} | RSI {x['rsi14']:4.1f} | R:R 1:{x['rr_ratio']:.1f} | {x['close']:,.0f}원 ({x['chg_pct']:+.2f}%)")

    print("\n================ US TOP 10 ================")
    for i, x in enumerate(us_scored[:10], 1):
        print(f"  {i:2d}. {x['name']:16s} ({x['symbol']:5s}) | {x['total_score']:5.1f}점 | {x['setup_type']:12s} | RSI {x['rsi14']:4.1f} | R:R 1:{x['rr_ratio']:.1f} | ${x['close']:,.2f} ({x['chg_pct']:+.2f}%)")

    if upload_drive:
        res = subprocess.run(["gdrive", "mutate", "upload", str(local_html), "--json"], capture_output=True, text=True)
        print("\nDrive upload:", res.stdout.strip() or res.stderr.strip())

    return local_html, payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HWH Daily KR/US Stock Screener")
    parser.add_argument("--market", choices=["all", "kr", "us"], default="all")
    parser.add_argument("--top", type=int, default=5, help="Number of top charts per market")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--upload-drive", action="store_true")
    parser.add_argument("--out-html", type=str, default=None, help="Custom HTML output path (e.g. docs/index.html)")
    parser.add_argument("--standalone-web", action="store_true", help="Use public Tailwind CDN + dark theme for GitHub Pages")
    args = parser.parse_args()
    run(
        market=args.market,
        top_charts=args.top,
        no_cache=args.no_cache,
        upload_drive=args.upload_drive,
        out_html=args.out_html,
        standalone_web=args.standalone_web,
    )
