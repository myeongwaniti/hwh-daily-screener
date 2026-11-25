import base64
import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib import font_manager
import numpy as np
import pandas as pd

from hwh_scorer import add_indicators

FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if Path(FONT_PATH).exists():
    font_manager.fontManager.addfont(FONT_PATH)
    plt.rcParams["font.family"] = "Noto Sans CJK KR"
plt.rcParams["axes.unicode_minus"] = False


def _fmt_price(val: float, market: str) -> str:
    if market == "KR":
        return f"{val:,.0f}"
    return f"${val:,.2f}"


def draw_hwh_chart(item: dict, df_raw: pd.DataFrame, out_path: Path | None = None) -> str:
    """Render HWH-style daily chart with 7 SMAs, 400-500 cloud, auto-trendlines, S/R zones, and RSI(14) divergence.
    Returns base64-encoded PNG string."""
    df = add_indicators(df_raw).reset_index(drop=True)
    total_n = len(df)
    window_bars = min(260, total_n)
    offset = total_n - window_bars
    sub = df.iloc[offset:].reset_index(drop=True)
    n = len(sub)
    right_pad = 24
    last = sub.iloc[-1]
    close_now = float(last["close"])
    market = item["market"]

    fig = plt.figure(figsize=(14.5, 9.2), dpi=145, facecolor="#D8D8D8")
    gs = fig.add_gridspec(3, 1, height_ratios=[6.2, 1.25, 1.55], hspace=0.05)
    ax = fig.add_subplot(gs[0])
    ax_vol = fig.add_subplot(gs[1], sharex=ax)
    ax_rsi = fig.add_subplot(gs[2], sharex=ax)

    BG = "#D8D8D8"
    for a in [ax, ax_vol, ax_rsi]:
        a.set_facecolor(BG)
        a.grid(False)
        for sp in a.spines.values():
            sp.set_color("#666666")

    x_arr = np.arange(n)

    # 1. Shaded Buy Zone / Target Zone / Stop Line
    buy_lo, buy_hi = item["buy_lo"], item["buy_hi"]
    target1, stop_loss = item["target1"], item["stop_loss"]

    ax.axhspan(buy_lo, buy_hi, color="#009E60", alpha=0.18, zorder=1)
    ax.axhspan(target1 * 0.985, target1 * 1.015, color="#D90429", alpha=0.15, zorder=1)
    ax.axhline(target1, color="#C1121F", linewidth=1.4, linestyle="-", zorder=4)
    ax.axhline(buy_lo, color="#007F4E", linewidth=1.3, linestyle="-", zorder=4)
    ax.axhline(stop_loss, color="#780000", linewidth=1.5, linestyle="--", zorder=4)

    # 2. 400~500 SMA Cloud
    valid_cloud = sub["sma400"].notna() & sub["sma500"].notna()
    if valid_cloud.any():
        ax.fill_between(
            x_arr[valid_cloud],
            sub.loc[valid_cloud, "sma400"],
            sub.loc[valid_cloud, "sma500"],
            color="#666666",
            alpha=0.18,
            zorder=2,
        )

    # 3. Candlesticks
    y_span = float(sub["high"].max() - sub["low"].min())
    min_body = max(y_span * 0.002, 1e-6)
    for i, row in sub.iterrows():
        o, h, l, c = row["open"], row["high"], row["low"], row["close"]
        clr = "#00802B" if c >= o else "#CC0000"
        ax.plot([i, i], [l, h], color=clr, linewidth=0.85, zorder=3)
        rect = patches.Rectangle((i - 0.34, min(o, c)), 0.68, max(abs(c - o), min_body), facecolor=clr, edgecolor=clr, linewidth=0.35, zorder=4)
        ax.add_patch(rect)

    # 4. HWH 7 SMAs
    ma_styles = [
        ("sma20", "#E63946", "--", 1.1),
        ("sma60", "#1D4ED8", "--", 1.2),
        ("sma120", "#00C853", "-", 2.0),
        ("sma200", "#FF7F00", "-", 2.0),
        ("sma300", "#8B2FC9", "-", 2.2),
        ("sma400", "#D4A017", "-", 2.3),
        ("sma500", "#111111", "-", 2.9),
    ]
    for col, clr, ls, lw in ma_styles:
        if sub[col].notna().any():
            ax.plot(x_arr, sub[col], color=clr, linestyle=ls, linewidth=lw, zorder=5)

    # 5. Algorithmic Pivot Trendlines (빗각)
    tls = item.get("trendlines", {})
    y_min_plot = min(float(sub["low"].min()), stop_loss) * 0.94
    y_max_plot = max(float(sub["high"].max()), target1) * 1.06

    if tls.get("desc"):
        d_tl = tls["desc"]
        i1 = d_tl["i1"] - offset
        if i1 >= -20:
            x0 = max(0, i1)
            x1 = n - 1 + 14
            y0 = d_tl["y1"] + d_tl["slope"] * (x0 - i1)
            y1 = d_tl["y1"] + d_tl["slope"] * (x1 - i1)
            # Clip endpoint if it plunges below chart floor
            if y1 < y_min_plot:
                x1 = i1 + (y_min_plot - d_tl["y1"]) / d_tl["slope"]
                y1 = y_min_plot
            ax.plot([x0, x1], [y0, y1], color="#003566", linewidth=2.0, linestyle="-", zorder=6)

    if tls.get("asc"):
        a_tl = tls["asc"]
        i1 = a_tl["i1"] - offset
        if i1 >= -20:
            x0 = max(0, i1)
            x1 = n - 1 + 14
            y0 = a_tl["y1"] + a_tl["slope"] * (x0 - i1)
            y1 = a_tl["y1"] + a_tl["slope"] * (x1 - i1)
            if y1 > y_max_plot:
                x1 = i1 + (y_max_plot - a_tl["y1"]) / a_tl["slope"]
                y1 = y_max_plot
            ax.plot([x0, x1], [y0, y1], color="#1B4332", linewidth=1.8, linestyle="-.", zorder=6)

    # 6. Clean Right/Left Level Labels
    t_pct = (target1 / close_now - 1) * 100
    s_pct = (stop_loss / close_now - 1) * 100
    ax.text(
        3, target1 + y_span * 0.012,
        f"1차 저항 타겟: {_fmt_price(target1, market)} ({t_pct:+.1f}%)",
        fontsize=8.3, fontweight="bold", color="#B91C1C", ha="left", va="bottom", parse_math=False,
        bbox=dict(boxstyle="square,pad=0.14", fc="#EBEBEB", ec="none", alpha=0.84), zorder=8
    )
    ax.text(
        3, buy_hi + y_span * 0.010,
        f"매수 타점존: {_fmt_price(buy_lo, market)} ~ {_fmt_price(buy_hi, market)}",
        fontsize=8.3, fontweight="bold", color="#006D44", ha="left", va="bottom", parse_math=False,
        bbox=dict(boxstyle="square,pad=0.14", fc="#E8F5E9", ec="none", alpha=0.86), zorder=8
    )
    ax.text(
        3, stop_loss - y_span * 0.012,
        f"종가 손절선: {_fmt_price(stop_loss, market)} ({s_pct:+.1f}%) | 손익비 1:{item['rr_ratio']:.1f}",
        fontsize=8.2, fontweight="bold", color="#780000", ha="left", va="top", parse_math=False,
        bbox=dict(boxstyle="square,pad=0.14", fc="#FDECEC", ec="none", alpha=0.86), zorder=8
    )

    # Scenario directional arrows in right margin
    ax.annotate(
        "", xy=(n - 1 + 16, target1), xytext=(n - 1 + 2, close_now),
        arrowprops=dict(arrowstyle="->", color="#0096C7", lw=2.2, connectionstyle="arc3,rad=-0.12"), zorder=9
    )
    ax.annotate(
        "", xy=(n - 1 + 14, stop_loss), xytext=(n - 1 + 2, close_now),
        arrowprops=dict(arrowstyle="->", color="#C9184A", lw=1.7, ls=":"), zorder=9
    )

    # Current Price Badge
    ax.axhline(close_now, color="#B00020", linewidth=0.8, linestyle="-.", alpha=0.6, zorder=4)
    ax.text(
        n + right_pad - 1, close_now,
        f" {_fmt_price(close_now, market)} ({item['chg_pct']:+.2f}%) ",
        fontsize=8.3, fontweight="bold", color="white", va="center", ha="right", parse_math=False,
        bbox=dict(boxstyle="square,pad=0.22", fc="#C1121F", ec="#780000"), zorder=10
    )

    # Header Box
    sma_parts = []
    for p in [20, 60, 120, 200, 400, 500]:
        v = item["smas"].get(p)
        if v is not None:
            sma_parts.append(f"{p}({_fmt_price(v, market)})")
    header_txt = (
        f"[{item['exchange']}] {item['name']} ({item['symbol']}) 일봉  |  현우현 점수: {item['total_score']}점 ({item['setup_type']})\n"
        f"기준일 {item['date']}  |  SMA: " + "  ".join(sma_parts)
    )
    ax.text(
        0.008, 0.985, header_txt, transform=ax.transAxes,
        fontsize=8.8, fontweight="bold", color="#111111", va="top", ha="left", parse_math=False,
        bbox=dict(boxstyle="square,pad=0.30", fc="#ECECEC", ec="#777777", alpha=0.94), zorder=10
    )

    ax.set_xlim(-2, n + right_pad)
    ax.set_ylim(y_min_plot, y_max_plot)
    ax.yaxis.tick_right()
    if market == "KR":
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x):,}"))
    else:
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.1f}"))
    ax.tick_params(axis="x", labelbottom=False)
    ax.tick_params(axis="y", labelsize=8.2)

    # 7. Volume Panel
    vol_colors = ["#00802B" if c >= o else "#CC0000" for o, c in zip(sub["open"], sub["close"])]
    ax_vol.bar(x_arr, sub["volume"].fillna(0) / 1000, color=vol_colors, width=0.72, zorder=3)
    ax_vol.text(0.008, 0.88, "거래량 (천주)", transform=ax_vol.transAxes, fontsize=8.0, fontweight="bold", color="#222222", va="top")
    ax_vol.yaxis.tick_right()
    ax_vol.tick_params(axis="x", labelbottom=False)
    ax_vol.tick_params(axis="y", labelsize=7.8)

    # 8. RSI(14) Panel
    ax_rsi.plot(x_arr, sub["rsi14"], color="#6A0DAD", linewidth=1.7, zorder=4)
    ax_rsi.axhline(70, color="#CC0000", linewidth=0.9, zorder=2)
    ax_rsi.axhline(50, color="#222222", linewidth=0.7, linestyle="--", zorder=2)
    ax_rsi.axhline(30, color="#0047AB", linewidth=0.9, zorder=2)
    ax_rsi.fill_between(x_arr, sub["rsi14"], 70, where=(sub["rsi14"] >= 70), color="#FF8C00", alpha=0.35, zorder=3)
    ax_rsi.fill_between(x_arr, sub["rsi14"], 30, where=(sub["rsi14"] <= 30), color="#1E90FF", alpha=0.35, zorder=3)

    # Draw auto-detected bullish divergence line if present
    if item.get("has_div") and len(item.get("div_pts", [])) == 2:
        d1, d2 = item["div_pts"][0] - offset, item["div_pts"][1] - offset
        if 0 <= d1 < n and 0 <= d2 < n:
            r1, r2 = float(sub.loc[d1, "rsi14"]), float(sub.loc[d2, "rsi14"])
            ax_rsi.plot([d1, d2], [r1, r2], color="#00802B", linewidth=2.3, zorder=6)
            ax_rsi.scatter([d1, d2], [r1, r2], color="#00802B", s=28, zorder=7)
            ax_rsi.text((d1 + d2) / 2, max(12, min(r1, r2) - 10), f"상승 다이버 ({r1:.1f}→{r2:.1f})",
                        fontsize=7.9, fontweight="bold", color="#006400", ha="center",
                        bbox=dict(boxstyle="square,pad=0.12", fc="#E8F5E9", ec="none", alpha=0.88), zorder=8)

    ax_rsi.text(0.008, 0.88, f"RSI(14): {item['rsi14']:.1f}  |  RS(5d): {item['rs_5d']:+.1f}%",
                transform=ax_rsi.transAxes, fontsize=8.0, fontweight="bold", color="#4B0082", va="top")
    ax_rsi.set_ylim(10, 90)
    ax_rsi.set_yticks([30, 50, 70])
    ax_rsi.yaxis.tick_right()
    ax_rsi.tick_params(axis="y", labelsize=7.8)

    # Monthly x ticks
    month_starts = sub.groupby(sub["date"].dt.to_period("M")).head(1)
    step = max(1, len(month_starts) // 7)
    ticks = month_starts.iloc[::step]
    ax_rsi.set_xticks(ticks.index.tolist())
    ax_rsi.set_xticklabels([d.strftime("%Y-%m") for d in ticks["date"]], fontsize=8.2)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", facecolor=BG, dpi=145)
    plt.close(fig)
    img_bytes = buf.getvalue()

    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(img_bytes)

    return base64.b64encode(img_bytes).decode("ascii")
