import re
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Guaranteed SPY mega-caps & HWH core watchlist (always included in US scan)
US_CORE_GUARANTEED = [
    ("UNH", "유나이티드헬스"),
    ("LLY", "일라이 릴리"),
    ("WMT", "월마트"),
    ("COST", "코스트코"),
    ("KO", "코카콜라"),
    ("PEP", "펩시코"),
    ("PG", "프록터앤갬블"),
    ("PM", "필립모리스"),
    ("JNJ", "존슨앤존슨"),
    ("ABBV", "애브비"),
    ("XOM", "엑슨모빌"),
    ("CVX", "셰브론"),
    ("LMT", "록히드마틴"),
    ("RTX", "RTX"),
    ("AAPL", "애플"),
    ("MSFT", "마이크로소프트"),
    ("NVDA", "엔비디아"),
    ("GOOGL", "알파벳 Class A"),
    ("AMZN", "아마존닷컴"),
    ("META", "메타 플랫폼스"),
    ("TSLA", "테슬라"),
    ("AVGO", "브로드컴"),
    ("AMD", "AMD"),
    ("PLTR", "팔란티어"),
    ("INTC", "인텔"),
    ("SBUX", "스타벅스"),
    ("NKE", "나이키"),
    ("BABA", "알리바바 ADR"),
    ("COIN", "코인베이스"),
    ("IREN", "아이렌"),
    ("WULF", "테라울프"),
    ("RKLB", "로켓랩"),
    ("ASTS", "AST 스페이스모바일"),
    ("SMR", "뉴스케일파워"),
]

KR_EXCLUDE_PATTERN = re.compile(
    r"(우$|우B$|우C$|스팩|SPAC|ETF|ETN|리츠|인버스|레버리지|TIGER|KODEX|KBSTAR|RISE|ACE|SOL|HANARO|ARIRANG|PLUS|TIMEFOLIO|맥쿼리인프라)"
)


def fetch_kr_universe(kospi_n: int = 120, kosdaq_n: int = 80) -> list[dict]:
    """Fetch top market-cap KOSPI & KOSDAQ common stocks via Naver Mobile JSON API."""
    results = []
    seen = set()

    for market, target_n in [("KOSPI", kospi_n), ("KOSDAQ", kosdaq_n)]:
        collected = 0
        page = 1
        while collected < target_n and page <= 8:
            url = f"https://m.stock.naver.com/api/stocks/marketValue/{market}?page={page}&pageSize=50"
            r = requests.get(url, headers=HEADERS, timeout=12)
            r.raise_for_status()
            stocks = r.json().get("stocks", [])
            if not stocks:
                break
            for s in stocks:
                code = str(s.get("itemCode", "")).strip()
                name = str(s.get("stockName", "")).strip()
                if not code or len(code) != 6 or not code.isdigit():
                    continue
                if code in seen or KR_EXCLUDE_PATTERN.search(name):
                    continue
                seen.add(code)
                results.append(
                    {
                        "symbol": code,
                        "name": name,
                        "market": "KR",
                        "exchange": market,
                        "market_cap_str": str(s.get("marketValue", "")),
                    }
                )
                collected += 1
                if collected >= target_n:
                    break
            page += 1
    return results


def _normalize_yf_symbol(sym: str) -> str:
    # Naver uses "BRK B", Yahoo Finance uses "BRK-B"
    sym = sym.strip().upper().replace(" ", "-").replace(".", "-")
    return sym


def fetch_us_universe(nasdaq_n: int = 100, nyse_n: int = 120) -> list[dict]:
    """Fetch top market-cap NASDAQ & NYSE (SPY mega-caps) + HWH core watchlist."""
    results = []
    seen = set()

    for exch, target_n in [("NASDAQ", nasdaq_n), ("NYSE", nyse_n)]:
        collected = 0
        page = 1
        while collected < target_n and page <= 6:
            url = f"https://api.stock.naver.com/stock/exchange/{exch}/marketValue?page={page}&pageSize=50"
            r = requests.get(url, headers=HEADERS, timeout=12)
            r.raise_for_status()
            stocks = r.json().get("stocks", [])
            if not stocks:
                break
            for s in stocks:
                raw_sym = str(s.get("symbolCode", "")).strip()
                name_kr = str(s.get("stockName", "")).strip()
                name_en = str(s.get("stockNameEng", "")).strip()
                if not raw_sym:
                    continue
                yf_sym = _normalize_yf_symbol(raw_sym)
                # Skip dual-class duplicate GOOG if GOOGL already present
                if yf_sym == "GOOG" and "GOOGL" in seen:
                    continue
                if yf_sym in seen:
                    continue
                seen.add(yf_sym)
                results.append(
                    {
                        "symbol": yf_sym,
                        "name": name_kr or name_en or yf_sym,
                        "name_en": name_en,
                        "market": "US",
                        "exchange": exch,
                        "market_cap_str": str(s.get("marketValue", "")),
                    }
                )
                collected += 1
                if collected >= target_n:
                    break
            page += 1

    # Guarantee SPY mega-caps & HWH core watchlist are included
    for sym, kr_name in US_CORE_GUARANTEED:
        if sym not in seen:
            seen.add(sym)
            results.append(
                {
                    "symbol": sym,
                    "name": kr_name,
                    "name_en": sym,
                    "market": "US",
                    "exchange": "CORE",
                    "market_cap_str": "",
                }
            )

    return results


if __name__ == "__main__":
    kr = fetch_kr_universe()
    us = fetch_us_universe()
    print(f"KR: {len(kr)} stocks | US: {len(us)} stocks")
    for check in ["UNH", "LLY", "WMT", "COST", "KO", "NVDA", "PLTR"]:
        found = [x for x in us if x["symbol"] == check]
        print(f"  Check {check}: {found[0]['name'] if found else 'MISSING'}")
