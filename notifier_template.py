"""Telegram Bot daily alert sender for HWH Daily Screener.

Set these two GitHub Repository Secrets (Settings -> Secrets and variables -> Actions):
  - TELEGRAM_BOT_TOKEN : Bot token from @BotFather
  - TELEGRAM_CHAT_ID   : Your personal chat ID (from @userinfobot or getUpdates)
Optional:
  - DASHBOARD_URL      : Your GitHub Pages URL (e.g. https://myeongwaniti.github.io/hwh-daily-screener/)
"""

import json
import os
import sys
from pathlib import Path
import requests


def send_telegram_summary(results_json_path: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    dashboard_url = os.environ.get(
        "DASHBOARD_URL", "https://myeongwaniti.github.io/hwh-daily-screener/"
    ).strip()

    if not token or not chat_id:
        print("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set; skipping Telegram push.")
        return

    data = json.loads(Path(results_json_path).read_text(encoding="utf-8"))
    items = data.get("items", [])
    kr_top = [x for x in items if x["market"] == "KR"][:5]
    us_top = [x for x in items if x["market"] == "US"][:5]
    fx_ratio = data.get("fx_ratio")

    lines = [f"📊 <b>현우현 일일 종가 스크리너 ({data['scan_date']})</b>"]
    if fx_ratio:
        lines.append(f"💱 순수 원화체력(USD/KRW÷DXY): <b>{fx_ratio:.2f}</b>")
    lines.append("")

    lines.append("🇰🇷 <b>국내주식 Top 5</b>")
    for i, x in enumerate(kr_top, 1):
        lines.append(
            f"{i}. <b>{x['name']}</b> ({x['symbol']}) — <b>{x['total_score']}점</b> | "
            f"{x['setup_type']} | R:R 1:{x['rr_ratio']} | {x['close']:,.0f}원 ({x['chg_pct']:+.1f}%)"
        )

    lines.append("\n🇺🇸 <b>미국주식 Top 5</b>")
    for i, x in enumerate(us_top, 1):
        lines.append(
            f"{i}. <b>{x['name']}</b> ({x['symbol']}) — <b>{x['total_score']}점</b> | "
            f"{x['setup_type']} | R:R 1:{x['rr_ratio']} | ${x['close']:,.2f} ({x['chg_pct']:+.1f}%)"
        )

    lines.append(f"\n🔗 <a href=\"{dashboard_url}\">전체 대시보드 &amp; 자동 빗각 차트 열기</a>")

    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": "\n".join(lines),
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=15,
    )
    print("Telegram message status:", r.status_code)

    # Send Top 2 KR + Top 2 US auto-drawn trendline charts
    charts_dir = Path(results_json_path).parent / "charts"
    top_pngs = sorted(charts_dir.glob("KR_0[12]_*.png")) + sorted(charts_dir.glob("US_0[12]_*.png"))
    for png in top_pngs:
        with open(png, "rb") as f:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data={"chat_id": chat_id, "caption": f"📈 {png.stem} (현우현 자동 빗각 작도)"},
                files={"photo": f},
                timeout=20,
            )
            print(f"Telegram photo {png.name}: {resp.status_code}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        send_telegram_summary(sys.argv[1])
