import json
import os
from pathlib import Path

import pandas as pd
import requests

from data_fetcher import fetch_market_thermometer
from hwh_scorer import add_indicators


def _analyze_index(name: str, df: pd.DataFrame, is_btc: bool = False) -> dict:
    df = add_indicators(df)
    last, prev = df.iloc[-1], df.iloc[-2]
    c = float(last["close"])
    chg = (c / float(prev["close"]) - 1) * 100
    rsi = float(last["rsi14"]) if pd.notna(last["rsi14"]) else 50.0
    smas = {p: (float(last[f"sma{p}"]) if pd.notna(last[f"sma{p}"]) else None) for p in [20, 60, 120, 200, 300, 400, 500]}

    sma20, sma60, sma120, sma200, sma400, sma500 = (
        smas[20], smas[60], smas[120], smas[200], smas[400], smas[500]
    )

    season_ma = sma400 if is_btc else sma500
    season_label = "400일선(시즌선)" if is_btc else "500일선(장기이평)"

    if sma120 and c > sma120 and sma20 and c > sma20:
        status = "1단계(상승 가속 · 정배열)"
    elif sma120 and c > sma120:
        status = "2단계(생명선 120일선 위 기간조정)"
    elif season_ma and c > season_ma:
        status = "3단계(120일선 이탈 · 장기이평 방어 테스트)"
    else:
        status = f"4단계({season_label} 하회 · 하락 추세 / 바닥 탐색)"

    # Nearest support & resistance from SMAs
    sups = sorted([v for v in smas.values() if v is not None and v <= c * 1.005], reverse=True)
    ress = sorted([v for v in smas.values() if v is not None and v >= c * 1.015])

    return {
        "name": name,
        "date": last["date"].strftime("%Y-%m-%d"),
        "close": c,
        "chg_pct": round(chg, 2),
        "rsi": round(rsi, 1),
        "status": status,
        "smas": smas,
        "near_sup": sups[0] if sups else c * 0.95,
        "near_res": ress[0] if ress else c * 1.05,
        "sma120": sma120,
        "season_ma": season_ma,
        "season_label": season_label,
    }


def _rule_based_review(stats: dict, fx_ratio: float | None) -> str:
    nq = stats.get("US100")
    kp = stats.get("KOSPI")
    kd = stats.get("KOSDAQ")
    sx = stats.get("SOXX")
    btc = stats.get("BTC")
    fx = stats.get("USDKRW")

    lines = ["📝 <b>[현우현 관점] 오늘의 나스닥 · 코스피 데일리 리뷰</b>\n"]

    if nq:
        lines.append(
            f"🇺🇸 <b>나스닥 선물 (US100): {nq['close']:,.1f} ({nq['chg_pct']:+.2f}%)</b> | RSI {nq['rsi']}\n"
            f"• 추세 위치: {nq['status']}\n"
            f"• 핵심 분기: 하단 지지 <b>{nq['near_sup']:,.0f}</b> 방어 여부가 관건. "
            f"반등 시 <b>{nq['near_res']:,.0f}</b> 돌파·지지 컨펌 나오기 전까지는 데드캣바운스 경계(추격 매수 금지)."
        )
        if sx:
            lines.append(f"• 반도체 선행(SOXX): <b>${sx['close']:,.2f} ({sx['chg_pct']:+.2f}%)</b> · RSI {sx['rsi']} ({sx['status']})")
        lines.append("")

    if kp:
        lines.append(
            f"🇰🇷 <b>코스피 (KOSPI): {kp['close']:,.1f} ({kp['chg_pct']:+.2f}%)</b> | RSI {kp['rsi']}\n"
            f"• 추세 위치: {kp['status']}\n"
            f"• 핵심 분기: 지지 <b>{kp['near_sup']:,.1f}</b> / 상단 저항 <b>{kp['near_res']:,.1f}</b>. "
            f"지수 흔들릴 땐 120·500일선 돌파 컨펌 나온 상대강도(RS) 우수 개별주만 선별 대응."
        )
        if kd:
            lines.append(f"• 코스닥 (KOSDAQ): <b>{kd['close']:,.1f} ({kd['chg_pct']:+.2f}%)</b> · RSI {kd['rsi']}")
        lines.append("")

    if fx and fx_ratio:
        if fx_ratio <= 13.0:
            fx_msg = "원화 강세 구간(12.7 마지노선 근접) → 원화 채굴해 달러·미장/418660 분할 매집 유리"
        elif fx_ratio >= 14.4:
            fx_msg = "고환율 구간(14.4~15.0 경계) → 달러 추격 매수 금지, 미장 익절 후 국장 애국베팅 유리"
        else:
            fx_msg = "중립 구간 → 비율×DXY 양축 보며 분할 환전 대응"
        lines.append(
            f"💱 <b>환율 · 비트코인 크로스체크</b>\n"
            f"• 원/달러: <b>{fx['close']:,.1f}원 ({fx['chg_pct']:+.2f}%)</b> | 순수 원화체력(÷DXY): <b>{fx_ratio:.2f}</b>\n"
            f"  → {fx_msg}"
        )
    if btc:
        lines.append(f"• 비트코인: <b>${btc['close']:,.0f} ({btc['chg_pct']:+.2f}%)</b> · RSI {btc['rsi']} ({btc['status']})")

    lines.append("\n💡 <i>\"포모 매수와 패닉 셀링만 피하고, 지지 이탈 시 짧게 자르고 저항에서 분할 익절합시다.\"</i>")
    return "\n".join(lines)


def _gemini_review(stats: dict, fx_ratio: float | None, api_key: str) -> str | None:
    prompt = f"""당신은 네이버 블로거 현우현(hwh_gusdn524)입니다. 아래 오늘의 실시간 시장 데이터를 바탕으로, 현우현 특유의 담백하고 직설적인 트레이더 톤으로 텔레그램용 [오늘의 나스닥·코스피 데일리 리뷰]를 작성하세요.
규칙:
- HTML 태그(<b>, <i>)만 사용해 깔끔하게 작성 (마크다운 ** 금지), 900자 이내.
- 120일선(생명선), 500일선(장기이평, 비트코인은 400일선), RSI(14), 순수 원화체력(USD/KRW÷DXY), 양방향 시나리오(돌파 컨펌 vs 이탈 시 하방 지지), FOMO·패닉셀 경계를 반드시 포함.

실시간 데이터:
{json.dumps({'stats': stats, 'fx_ratio': fx_ratio}, ensure_ascii=False)}
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    try:
        r = requests.post(
            url,
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=25,
        )
        if r.status_code == 200:
            cands = r.json().get("candidates", [])
            if cands:
                return cands[0]["content"]["parts"][0]["text"].strip()
    except Exception:
        pass
    return None


def generate_market_review(benchmarks: dict | None = None) -> str:
    if benchmarks is None:
        benchmarks = fetch_market_thermometer(use_cache=True)

    stats = {}
    for key in ["US100", "SP500", "SOXX", "KOSPI", "KOSDAQ", "BTC", "USDKRW"]:
        if key in benchmarks and len(benchmarks[key]) >= 20:
            stats[key] = _analyze_index(key, benchmarks[key], is_btc=(key == "BTC"))

    fx_ratio = None
    if "USDKRW" in benchmarks and "DXY" in benchmarks:
        fx = float(benchmarks["USDKRW"].iloc[-1]["close"])
        dxy = float(benchmarks["DXY"].iloc[-1]["close"])
        if dxy > 0:
            fx_ratio = round(fx / dxy, 2)

    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if gemini_key:
        ai_text = _gemini_review(stats, fx_ratio, gemini_key)
        if ai_text:
            return ai_text

    return _rule_based_review(stats, fx_ratio)


if __name__ == "__main__":
    print(generate_market_review())
