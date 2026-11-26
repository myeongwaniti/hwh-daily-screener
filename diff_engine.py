import json
from pathlib import Path
import pandas as pd
import numpy as np

from hwh_scorer import add_indicators


def _find_prev_snapshot(out_dir: Path, today_str: str) -> dict | None:
    candidates = sorted(
        [p for p in out_dir.iterdir() if p.is_dir() and p.name < today_str and (p / "screener_results.json").exists()],
        key=lambda p: p.name,
        reverse=True,
    )
    if candidates:
        try:
            return json.loads((candidates[0] / "screener_results.json").read_text(encoding="utf-8"))
        except Exception:
            pass
    hist = out_dir.parent / "history" / "prev_snapshot.json"
    if hist.exists():
        try:
            data = json.loads(hist.read_text(encoding="utf-8"))
            if data.get("scan_date", "") < today_str:
                return data
        except Exception:
            pass
    return None


def compute_daily_diff(out_dir: Path, today_str: str, kr_scored: list[dict], us_scored: list[dict]) -> dict:
    prev = _find_prev_snapshot(out_dir, today_str)
    prev_date = prev.get("scan_date") if prev else None
    prev_items = prev.get("items", []) if prev else []

    prev_kr = [x for x in prev_items if x.get("market") == "KR"]
    prev_us = [x for x in prev_items if x.get("market") == "US"]
    prev_kr.sort(key=lambda x: x.get("total_score", 0), reverse=True)
    prev_us.sort(key=lambda x: x.get("total_score", 0), reverse=True)

    today_kr_map = {x["symbol"]: (idx + 1, x) for idx, x in enumerate(kr_scored)}
    today_us_map = {x["symbol"]: (idx + 1, x) for idx, x in enumerate(us_scored)}
    prev_kr_top10 = {x["symbol"] for x in prev_kr[:10]}
    prev_us_top10 = {x["symbol"] for x in prev_us[:10]}

    new_top10 = []
    for mkt, scored, p_top10 in [("KR", kr_scored, prev_kr_top10), ("US", us_scored, prev_us_top10)]:
        for rank, x in enumerate(scored[:10], 1):
            if prev and x["symbol"] not in p_top10:
                new_top10.append({
                    "key": f"{mkt}:{x['symbol']}",
                    "market": mkt,
                    "symbol": x["symbol"],
                    "name": x["name"],
                    "rank": rank,
                    "score": x["total_score"],
                    "chg_pct": x["chg_pct"],
                    "setup": x["setup_type"],
                })

    missed_surged = []
    dropped_warning = []
    for mkt, prev_list, t_map in [("KR", prev_kr[:15], today_kr_map), ("US", prev_us[:15], today_us_map)]:
        for p_rank, px in enumerate(prev_list, 1):
            sym = px["symbol"]
            t_entry = t_map.get(sym)
            if t_entry is None:
                # Dropped completely (either overheated RSI/surge or disqualified)
                missed_surged.append({
                    "key": f"{mkt}:{sym}",
                    "market": mkt,
                    "symbol": sym,
                    "name": px["name"],
                    "prev_rank": p_rank,
                    "prev_score": px["total_score"],
                    "reason": "과열/조건 이탈 (스크리너 제외)",
                })
            else:
                t_rank, tx = t_entry
                if tx["chg_pct"] >= 4.0 or (p_rank <= 10 and t_rank > 12 and tx["chg_pct"] >= 2.5):
                    missed_surged.append({
                        "key": f"{mkt}:{sym}",
                        "market": mkt,
                        "symbol": sym,
                        "name": tx["name"],
                        "prev_rank": p_rank,
                        "curr_rank": t_rank,
                        "chg_pct": tx["chg_pct"],
                        "reason": f"급등 {tx['chg_pct']:+.2f}% (타점 이격)",
                    })
                elif p_rank <= 10 and (t_rank > 10 or (tx["total_score"] - px["total_score"] <= -4.0)):
                    dropped_warning.append({
                        "key": f"{mkt}:{sym}",
                        "market": mkt,
                        "symbol": sym,
                        "name": tx["name"],
                        "prev_rank": p_rank,
                        "curr_rank": t_rank,
                        "score_diff": round(tx["total_score"] - px["total_score"], 1),
                        "chg_pct": tx["chg_pct"],
                        "reason": f"순위 {p_rank}→{t_rank}위 ({tx['total_score'] - px['total_score']:+.1f}점)",
                    })

    near_miss = []
    for mkt, scored in [("KR", kr_scored), ("US", us_scored)]:
        cutoff = scored[9]["total_score"] if len(scored) >= 10 else 0
        for rank, x in enumerate(scored[10:15], 11):
            if x["rr_ratio"] >= 1.5 or (cutoff - x["total_score"]) <= 3.0:
                near_miss.append({
                    "key": f"{mkt}:{x['symbol']}",
                    "market": mkt,
                    "symbol": x["symbol"],
                    "name": x["name"],
                    "rank": rank,
                    "score": x["total_score"],
                    "rr_ratio": x["rr_ratio"],
                    "chg_pct": x["chg_pct"],
                })

    return {
        "prev_date": prev_date,
        "new_top10": new_top10[:8],
        "missed_surged": missed_surged[:8],
        "dropped_warning": dropped_warning[:8],
        "near_miss": near_miss[:8],
    }


def build_series_payload(df: pd.DataFrame, max_bars: int = 260) -> list[dict]:
    df = add_indicators(df.copy()).dropna(subset=["close"]).reset_index(drop=True)
    sub = df.tail(max_bars).reset_index(drop=True)
    rows = []
    for _, r in sub.iterrows():
        item = {
            "time": r["date"].strftime("%Y-%m-%d"),
            "open": round(float(r["open"]), 2),
            "high": round(float(r["high"]), 2),
            "low": round(float(r["low"]), 2),
            "close": round(float(r["close"]), 2),
            "volume": int(r["volume"]) if pd.notna(r["volume"]) else 0,
        }
        for p in [20, 60, 120, 200, 300, 400, 500]:
            v = r.get(f"sma{p}")
            if pd.notna(v):
                item[f"sma{p}"] = round(float(v), 2)
        if pd.notna(r.get("rsi14")):
            item["rsi14"] = round(float(r["rsi14"]), 1)
        rows.append(item)
    return rows


def project_trendlines(df: pd.DataFrame, trendlines: list[dict], max_bars: int = 260) -> list[dict]:
    df = df.dropna(subset=["close"]).reset_index(drop=True)
    sub = df.tail(max_bars).reset_index(drop=True)
    if len(sub) < 10:
        return []
    dates = sub["date"].dt.strftime("%Y-%m-%d").tolist()
    last_date = sub["date"].iloc[-1]
    future_dates = [(last_date + pd.offsets.BDay(i)).strftime("%Y-%m-%d") for i in range(1, 16)]
    all_dates = dates + future_dates

    # Map dates on full df so anchor points before 260 bars still project accurately
    full_dates = df["date"]
    out = []
    for tl in trendlines:
        i1 = int((full_dates - pd.Timestamp(tl["p1_date"])).abs().idxmin())
        i2 = int((full_dates - pd.Timestamp(tl["p2_date"])).abs().idxmin())
        if i2 <= i1:
            continue
        slope = (tl["p2_price"] - tl["p1_price"]) / (i2 - i1)
        offset = len(df) - len(sub)
        pts = []
        start_sub_idx = max(0, i1 - offset)
        for j in range(start_sub_idx, len(all_dates)):
            full_idx = offset + j
            val = tl["p1_price"] + slope * (full_idx - i1)
            if val > 0:
                pts.append({"time": all_dates[j], "value": round(float(val), 2)})
        today_val = tl["p1_price"] + slope * ((len(df) - 1) - i1)
        out.append({
            "label": tl["label"],
            "color": tl.get("color", "#003566"),
            "style": tl.get("style", "solid"),
            "today_val": round(float(today_val), 2),
            "points": pts,
        })
    return out


def evaluate_watched_markups(markups: dict, dmaps: dict) -> list[dict]:
    results = []
    for key, cfg in markups.items():
        df = dmaps.get(key)
        if df is None or len(df) < 50:
            continue
        df = add_indicators(df.copy()).dropna(subset=["close"]).reset_index(drop=True)
        last, prev = df.iloc[-1], df.iloc[-2]
        c = float(last["close"])
        chg = round((c / float(prev["close"]) - 1) * 100, 2)
        rsi = round(float(last["rsi14"]), 1) if pd.notna(last["rsi14"]) else 50.0
        lv = cfg["levels"]

        proj_tls = project_trendlines(df, cfg.get("trendlines", []))
        tl_breakout = any(c > tl["today_val"] for tl in proj_tls[-1:]) if proj_tls else False

        if c <= lv["stop"]:
            status = "손절선 이탈 경고"
            tone = "danger"
        elif lv["planb_low"] <= c <= lv["planb_high"]:
            status = "Plan B 2차 매집 구간"
            tone = "warn"
        elif lv["buy1_low"] <= c <= lv["buy1_high"]:
            status = "1차 매집존 진입"
            tone = "buy"
        elif c >= lv["target2"]:
            status = "2차 목표가 도달"
            tone = "target"
        elif c >= lv["target1"]:
            status = "1차 목표가 도달"
            tone = "target"
        elif tl_breakout:
            status = "단기 하락빗각 돌파"
            tone = "breakout"
        else:
            dist_buy1 = round((c / lv["buy1_high"] - 1) * 100, 1)
            status = f"매집존 대기 (상단 대비 {dist_buy1:+.1f}%)"
            tone = "neutral"

        results.append({
            "key": key,
            "symbol": cfg["symbol"],
            "market": cfg["market"],
            "name": cfg["name"],
            "ccy": cfg["ccy"],
            "date": last["date"].strftime("%Y-%m-%d"),
            "close": round(c, 2),
            "chg_pct": chg,
            "rsi14": rsi,
            "status": status,
            "tone": tone,
            "levels": lv,
            "trendlines": proj_tls,
            "report": cfg["report"],
        })
    return results
