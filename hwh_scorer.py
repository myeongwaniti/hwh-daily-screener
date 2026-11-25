import numpy as np
import pandas as pd


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for p in [20, 60, 120, 200, 300, 400, 500]:
        df[f"sma{p}"] = df["close"].rolling(p).mean()
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    df["rsi14"] = 100 - (100 / (1 + avg_gain / avg_loss.replace(0, np.nan)))
    df["vol20"] = df["volume"].rolling(20).mean()
    return df


def find_pivots(df: pd.DataFrame, window: int = 7) -> tuple[list[int], list[int]]:
    """Return local swing high and swing low indices."""
    highs = df["high"].values
    lows = df["low"].values
    n = len(df)
    ph, pl = [], []
    for i in range(window, n - window):
        if highs[i] == np.max(highs[i - window : i + window + 1]):
            ph.append(i)
        if lows[i] == np.min(lows[i - window : i + window + 1]):
            pl.append(i)
    return ph, pl


def detect_bullish_divergence(df: pd.DataFrame, pl: list[int]) -> tuple[bool, list[int]]:
    """Detect HWH-style bullish RSI divergence in last 75 bars."""
    n = len(df)
    recent_pl = [i for i in pl if i >= n - 80]
    # Also include the actual minimum bar in last 15 bars if it's very recent
    recent_min_i = int(df["low"].iloc[-15:].idxmin())
    if recent_min_i not in recent_pl and (not recent_pl or recent_min_i - recent_pl[-1] >= 4):
        recent_pl.append(recent_min_i)
    recent_pl = sorted(recent_pl)

    if len(recent_pl) < 2:
        return False, []

    # Check pairs of swing lows where later low is lower (or within 1.5%) and RSI is meaningfully higher (+2.0)
    for k in range(len(recent_pl) - 1, 0, -1):
        i2 = recent_pl[k]
        if i2 < n - 25:
            continue
        for j in range(k - 1, -1, -1):
            i1 = recent_pl[j]
            if i2 - i1 < 6 or i2 - i1 > 65:
                continue
            p1, p2 = df.loc[i1, "low"], df.loc[i2, "low"]
            r1, r2 = df.loc[i1, "rsi14"], df.loc[i2, "rsi14"]
            if pd.isna(r1) or pd.isna(r2):
                continue
            if p2 <= p1 * 1.015 and r2 >= r1 + 2.2 and r1 <= 42:
                return True, [i1, i2]
    return False, []


def compute_trendlines(df: pd.DataFrame, ph: list[int], pl: list[int]) -> dict:
    """Compute most relevant descending resistance trendline & ascending support trendline."""
    n = len(df)
    close_now = df.iloc[-1]["close"]

    # 1. Descending trendline from recent major high (within last 160 bars) to a lower high
    desc_tl = None
    recent_ph = [i for i in ph if i >= n - 170]
    if len(recent_ph) >= 2:
        # Anchor at highest high in recent_ph
        p1 = max(recent_ph, key=lambda i: df.loc[i, "high"])
        later_ph = [i for i in recent_ph if i > p1 + 8 and df.loc[i, "high"] < df.loc[p1, "high"]]
        best_tl = None
        for p2 in later_ph:
            y1, y2 = df.loc[p1, "high"], df.loc[p2, "high"]
            slope = (y2 - y1) / (p2 - p1)
            if slope >= 0:
                continue
            y_now = y1 + slope * (n - 1 - p1)
            # Check how clean it is (few closes above it between p1 and p2)
            xs = np.arange(p1 + 1, p2)
            line_vals = y1 + slope * (xs - p1)
            violations = int(np.sum(df.loc[xs, "close"].values > line_vals * 1.02))
            if violations <= 2 and y_now > close_now * 0.72 and y_now < close_now * 1.35:
                best_tl = {"i1": p1, "y1": float(y1), "i2": p2, "y2": float(y2), "slope": float(slope), "y_now": float(y_now)}
        desc_tl = best_tl

    # 2. Ascending support trendline from two rising swing lows in last 240 bars
    asc_tl = None
    recent_pl = [i for i in pl if i >= n - 240]
    if len(recent_pl) >= 2:
        best_asc = None
        for idx_a in range(len(recent_pl) - 1):
            i1 = recent_pl[idx_a]
            for idx_b in range(idx_a + 1, len(recent_pl)):
                i2 = recent_pl[idx_b]
                if i2 - i1 < 15:
                    continue
                y1, y2 = df.loc[i1, "low"], df.loc[i2, "low"]
                if y2 <= y1:
                    continue
                slope = (y2 - y1) / (i2 - i1)
                y_now = y1 + slope * (n - 1 - i1)
                if close_now * 0.80 <= y_now <= close_now * 1.05:
                    xs = np.arange(i1 + 1, n - 1)
                    line_vals = y1 + slope * (xs - i1)
                    violations = int(np.sum(df.loc[xs, "close"].values < line_vals * 0.97))
                    if violations <= 3:
                        best_asc = {"i1": i1, "y1": float(y1), "i2": i2, "y2": float(y2), "slope": float(slope), "y_now": float(y_now)}
        asc_tl = best_asc

    return {"desc": desc_tl, "asc": asc_tl}


def cluster_sr_levels(df: pd.DataFrame, ph: list[int], pl: list[int], tol: float = 0.025) -> tuple[list[float], list[float]]:
    """Cluster historical swing highs/lows into meaningful horizontal support & resistance levels."""
    close_now = df.iloc[-1]["close"]
    pts = [float(df.loc[i, "high"]) for i in ph[-25:]] + [float(df.loc[i, "low"]) for i in pl[-25:]]
    pts.sort()
    clusters = []
    for p in pts:
        if not clusters or abs(p - clusters[-1]["mean"]) / clusters[-1]["mean"] > tol:
            clusters.append({"vals": [p], "mean": p})
        else:
            clusters[-1]["vals"].append(p)
            clusters[-1]["mean"] = float(np.mean(clusters[-1]["vals"]))
    # Prefer levels touched >= 2 times, fallback to all
    strong = [c["mean"] for c in clusters if len(c["vals"]) >= 2]
    all_lvls = [c["mean"] for c in clusters]
    lvls = strong if len(strong) >= 4 else all_lvls
    supports = sorted([v for v in lvls if v <= close_now * 1.015], reverse=True)
    resistances = sorted([v for v in lvls if v >= close_now * 1.035])
    return supports, resistances


def score_stock(meta: dict, df_raw: pd.DataFrame, bench_df: pd.DataFrame | None) -> dict | None:
    """Apply HWH 100-point quantitative scoring framework to a single stock."""
    if df_raw is None or len(df_raw) < 130:
        return None
    df = add_indicators(df_raw)
    last = df.iloc[-1]
    prev = df.iloc[-2]
    close = float(last["close"])
    chg_pct = (close / float(prev["close"]) - 1) * 100

    sma20 = float(last["sma20"]) if pd.notna(last["sma20"]) else np.nan
    sma60 = float(last["sma60"]) if pd.notna(last["sma60"]) else np.nan
    sma120 = float(last["sma120"]) if pd.notna(last["sma120"]) else np.nan
    sma200 = float(last["sma200"]) if pd.notna(last["sma200"]) else np.nan
    sma300 = float(last["sma300"]) if pd.notna(last["sma300"]) else np.nan
    sma400 = float(last["sma400"]) if pd.notna(last["sma400"]) else np.nan
    sma500 = float(last["sma500"]) if pd.notna(last["sma500"]) else np.nan
    rsi = float(last["rsi14"]) if pd.notna(last["rsi14"]) else 50.0

    # Weekly SMA60 / SMA120
    wdf = df.set_index("date").resample("W-FRI").agg({"close": "last"}).dropna()
    wsma60 = float(wdf["close"].rolling(60).mean().iloc[-1]) if len(wdf) >= 60 else np.nan
    wsma120 = float(wdf["close"].rolling(120).mean().iloc[-1]) if len(wdf) >= 120 else np.nan

    # Disparity from 20SMA
    disp20 = (close / sma20 - 1) * 100 if pd.notna(sma20) else 0.0

    # AUTOMATIC DISQUALIFICATION: "보유자 영역" (Overheated / FOMO Chase)
    if rsi >= 70.0 or disp20 >= 15.0:
        return None

    ph, pl = find_pivots(df, window=7)
    has_div, div_pts = detect_bullish_divergence(df, pl)
    tls = compute_trendlines(df, ph, pl)
    supports, resistances = cluster_sr_levels(df, ph, pl)

    tags = []

    # ==========================================================
    # 1. MA & Turnaround Structure (Max 35 pts)
    # ==========================================================
    score_ma = 0.0
    setup_type = "관망/중립"
    stage = "3단계: 상승 되돌림"

    # Check recent 20-bar breakout of 120SMA or 400/500SMA + pullback confirm
    recent20 = df.tail(22)
    broke_120 = (
        pd.notna(sma120)
        and (recent20["close"].iloc[:15] < recent20["sma120"].iloc[:15]).any()
        and close >= sma120 * 0.985
    )
    near_120 = pd.notna(sma120) and abs(close / sma120 - 1) <= 0.045

    long_ma = sma500 if pd.notna(sma500) else (sma400 if pd.notna(sma400) else sma300)
    broke_long = (
        pd.notna(long_ma)
        and (recent20["close"].iloc[:15] < recent20["sma400"].iloc[:15]).any()
        and close >= long_ma * 0.985
    ) if pd.notna(sma400) else False

    near_long_cloud = False
    if pd.notna(sma400) and pd.notna(sma500):
        lo_c, hi_c = min(sma400, sma500), max(sma400, sma500)
        if lo_c * 0.92 <= close <= hi_c * 1.05:
            near_long_cloud = True
    elif pd.notna(long_ma) and long_ma * 0.93 <= close <= long_ma * 1.04:
        near_long_cloud = True

    # MA convergence (period consolidation)
    ma_spread = np.nan
    if pd.notna(sma20) and pd.notna(sma60) and pd.notna(sma120):
        ma_spread = (max(sma20, sma60, sma120) / min(sma20, sma60, sma120) - 1) * 100

    # Score Track A: Turnaround 5~6단계
    if broke_120 and near_120:
        score_ma = 33.0
        setup_type = "턴어라운드 5~6단계"
        stage = "5~6단계: 120일선 돌파·지지 컨펌"
        tags.append("120일선 R→B→S 컨펌")
    elif broke_long and near_long_cloud:
        score_ma = 35.0
        setup_type = "턴어라운드 5~6단계"
        stage = "6단계: 장기이평(400~500) 돌파·안착"
        tags.append("장기이평 턴어라운드")
    elif near_long_cloud:
        score_ma = 31.0
        setup_type = "장기이평 공포매집"
        stage = "3단계 끝단: 400~500일선 구름대 지지"
        tags.append("400~500일선 구름대")
        if pd.notna(wsma120) and abs(close / wsma120 - 1) <= 0.06:
            score_ma = min(35.0, score_ma + 4.0)
            tags.append("주봉 120이평 중첩")
        elif pd.notna(wsma60) and abs(close / wsma60 - 1) <= 0.05:
            score_ma = min(35.0, score_ma + 3.0)
            tags.append("주봉 60이평 중첩")
    elif pd.notna(sma60) and pd.notna(sma120) and close >= sma60 * 0.985 and close <= sma60 * 1.045 and sma60 > sma120:
        score_ma = 28.0
        setup_type = "강세 기간조정"
        stage = "2단계: 60일선 기간조정 눌림"
        tags.append("60일선 눌림 지지")
        if pd.notna(ma_spread) and ma_spread <= 6.5:
            score_ma = 33.0
            tags.append(f"이평 밀집({ma_spread:.1f}%)")
    elif pd.notna(sma20) and pd.notna(sma120) and close >= sma20 * 0.99 and close < sma120 and (recent20["close"].iloc[:10] < recent20["sma20"].iloc[:10]).any():
        score_ma = 25.0
        setup_type = "턴어라운드 5~6단계"
        stage = "5단계 초입: 20일선 돌파·계단식 시동"
        tags.append("20일선 돌파 시동")
    elif pd.notna(sma120) and abs(close / sma120 - 1) <= 0.04 and close >= sma120 * 0.97:
        score_ma = 27.0
        setup_type = "강세 기간조정"
        stage = "2단계: 120일선 생명선 방어"
        tags.append("120일선 생명선 지지")
    elif pd.notna(sma200) and abs(close / sma200 - 1) <= 0.04:
        score_ma = 23.0
        setup_type = "장기이평 공포매집"
        stage = "3단계: 200일선 중간 방어"
        tags.append("200일선 지지권")
    else:
        # Deep below 500SMA or mid-air
        if pd.notna(sma500) and close < sma500 * 0.92:
            score_ma = 14.0
            setup_type = "장기이평 공포매집"
            stage = "4단계: 장기이평 하회(칼스탑 필수)"
            tags.append("500일선 하회 과매도")
        else:
            score_ma = 12.0

    # ==========================================================
    # 2. RSI & Bullish Divergence (Max 25 pts)
    # ==========================================================
    score_rsi = 0.0
    if has_div:
        score_rsi += 16.0
        tags.append("일봉 상승 다이버전스")
    if rsi <= 30:
        score_rsi += 12.0
        tags.append(f"RSI 극과매도({rsi:.1f})")
    elif rsi <= 38:
        score_rsi += 9.0
        tags.append(f"RSI 과매도({rsi:.1f})")
    elif 38 < rsi <= 55:
        score_rsi += 6.0
    elif 55 < rsi < 65:
        score_rsi += 3.0
    score_rsi = min(25.0, score_rsi)

    # ==========================================================
    # 3. Horizontal S/R & Trendline (빗각) Confluence (Max 20 pts)
    # ==========================================================
    score_sr = 0.0
    # Horizontal support proximity
    if supports:
        dist_sup = (close - supports[0]) / close
        if -0.015 <= dist_sup <= 0.045:
            score_sr += 10.0
            tags.append("수평 매물대 지지")
        elif dist_sup <= 0.08:
            score_sr += 5.0

    # Descending trendline breakout or retest
    if tls["desc"]:
        tl_y = tls["desc"]["y_now"]
        if tl_y * 0.985 <= close <= tl_y * 1.08:
            score_sr += 10.0
            tags.append("하락 빗각 돌파/리테스트")
        elif tl_y * 0.94 <= close < tl_y * 0.985:
            score_sr += 5.0
            tags.append("하락 빗각 돌파 직전")

    # Ascending trendline support
    if tls["asc"]:
        asc_y = tls["asc"]["y_now"]
        if asc_y * 0.98 <= close <= asc_y * 1.045:
            score_sr += 10.0
            tags.append("상승 빗각 지지")

    score_sr = min(20.0, score_sr)

    # ==========================================================
    # 4. Volume & Relative Strength vs Benchmark (Max 20 pts)
    # ==========================================================
    score_vr = 0.0
    vol_ratio = float(last["volume"] / last["vol20"]) if pd.notna(last["vol20"]) and last["vol20"] > 0 else 1.0
    if chg_pct > 1.0 and vol_ratio >= 1.35:
        score_vr += 9.0
        tags.append(f"거래량 실린 양봉({vol_ratio:.1f}x)")
    elif chg_pct <= 0.5 and vol_ratio <= 0.85:
        score_vr += 7.0
        tags.append("거래량 감소 눌림")
    else:
        score_vr += 4.0

    rs_5d, rs_20d = 0.0, 0.0
    if bench_df is not None and len(bench_df) >= 25 and len(df) >= 25:
        st_5 = (close / float(df.iloc[-6]["close"]) - 1) * 100
        st_20 = (close / float(df.iloc[-21]["close"]) - 1) * 100
        b_5 = (float(bench_df.iloc[-1]["close"]) / float(bench_df.iloc[-6]["close"]) - 1) * 100
        b_20 = (float(bench_df.iloc[-1]["close"]) / float(bench_df.iloc[-21]["close"]) - 1) * 100
        rs_5d = st_5 - b_5
        rs_20d = st_20 - b_20
        if rs_5d > 3.0 and rs_20d > 3.0:
            score_vr += 11.0
            tags.append(f"지수 대비 강세(RS +{rs_5d:.1f}%)")
        elif rs_5d > 1.0 or rs_20d > 2.0:
            score_vr += 7.0
        elif rs_5d > -2.0:
            score_vr += 3.0
    else:
        score_vr += 5.0

    score_vr = min(20.0, score_vr)

    total_score = round(score_ma + score_rsi + score_sr + score_vr, 1)

    # ==========================================================
    # Actionable Entry / Target / Stop-Loss / R:R Calculation
    # ==========================================================
    # Key support anchor for buy zone & stop
    sup_candidates = [v for v in [supports[0] if supports else np.nan, sma400, sma500, sma120, sma60, sma20] if pd.notna(v) and v <= close * 1.015]
    primary_sup = max(sup_candidates) if sup_candidates else close * 0.94
    buy_lo = round(min(primary_sup * 0.99, close * 0.97), 2)
    buy_hi = round(min(close * 1.005, max(primary_sup * 1.02, close * 0.995)), 2)
    stop_loss = round(buy_lo * 0.955, 2)

    # First meaningful resistance target (at least +7% above close)
    res_candidates = [v for v in (resistances + [sma60, sma120, sma200, sma300]) if pd.notna(v) and v >= close * 1.07]
    target1 = round(min(res_candidates), 2) if res_candidates else round(close * 1.15, 2)

    risk = max(close - stop_loss, close * 0.03)
    reward = max(target1 - close, close * 0.05)
    rr_ratio = round(reward / risk, 2)

    # Bonus/penalty for R:R
    if rr_ratio >= 2.2:
        total_score = min(100.0, round(total_score + 4.0, 1))
        tags.append(f"손익비 우수(1:{rr_ratio:.1f})")
    elif rr_ratio < 1.2:
        total_score = max(0.0, round(total_score - 5.0, 1))

    # HWH 1-line diagnosis
    def _p(v: float) -> str:
        return f"{v:,.0f}원" if meta["market"] == "KR" else f"${v:,.2f}"

    if setup_type == "턴어라운드 5~6단계":
        comment = f"이평 턴어라운드 초입({stage}). {_p(buy_lo)}~{_p(buy_hi)} 지지 컨펌 시 손익비 1:{rr_ratio:.1f} 공략, 종가 {_p(stop_loss)} 이탈 시 칼컷."
    elif setup_type == "장기이평 공포매집":
        comment = f"장기이평(400~500선) 중첩 매집존. 분할 접근 유리하며 {_p(stop_loss)} 종가 이탈 시 비중 축소 대응."
    elif setup_type == "강세 기간조정":
        comment = f"추세 살아있는 기간조정 눌림 구간. {_p(buy_lo)}~{_p(buy_hi)} 지지 방어 시 1차 타겟 {_p(target1)} 도전."
    else:
        comment = f"중립 구간. 무리한 진입보다 {_p(buy_lo)} 지지 확인 또는 상단 저항 돌파 컨펌 대기."

    return {
        "symbol": meta["symbol"],
        "name": meta["name"],
        "market": meta["market"],
        "exchange": meta["exchange"],
        "date": last["date"].strftime("%Y-%m-%d"),
        "close": close,
        "chg_pct": round(chg_pct, 2),
        "total_score": total_score,
        "score_ma": round(score_ma, 1),
        "score_rsi": round(score_rsi, 1),
        "score_sr": round(score_sr, 1),
        "score_vr": round(score_vr, 1),
        "setup_type": setup_type,
        "stage": stage,
        "rsi14": round(rsi, 1),
        "disp20": round(disp20, 1),
        "rs_5d": round(rs_5d, 1),
        "rs_20d": round(rs_20d, 1),
        "has_div": has_div,
        "div_pts": div_pts,
        "buy_lo": buy_lo,
        "buy_hi": buy_hi,
        "target1": target1,
        "stop_loss": stop_loss,
        "rr_ratio": rr_ratio,
        "tags": tags[:5],
        "comment": comment,
        "trendlines": tls,
        "supports": supports[:3],
        "resistances": resistances[:3],
        "smas": {
            p: (round(float(last[f"sma{p}"]), 2) if pd.notna(last[f"sma{p}"]) else None)
            for p in [20, 60, 120, 200, 300, 400, 500]
        },
    }
