import json


def build_dashboard_html(payload: dict, standalone_web: bool = False) -> str:
    """Build a Monochrome Atelier editorial-style interactive HTML dashboard."""
    data_json = json.dumps(payload, ensure_ascii=False)
    tw_cdn = (
        "https://cdn.tailwindcss.com"
        if standalone_web
        else "https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>HWH ATELIER — 현우현 일일 종가 스크리너</title>
  <script src="{tw_cdn}"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Noto+Sans+KR:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <style>
    :root {{
      --black: #000000;
      --ink-900: #141414;
      --ink-600: #615f5f;
      --ink-500: #7d7d7d;
      --line-200: #e3e1e1;
      --mist-100: #e9e9eb;
      --white: #ffffff;
      --green-600: #00a65a;
      --red-600: #c1121f;
    }}
    * {{
      border-radius: 0 !important;
      box-sizing: border-box;
    }}
    body {{
      background-color: var(--white);
      color: var(--ink-900);
      font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
      font-size: 14px;
      line-height: 1.5;
      margin: 0;
      padding: 0;
    }}
    .font-serif-display {{
      font-family: 'Instrument Serif', Georgia, serif;
      letter-spacing: -0.02em;
    }}
    .caps-label {{
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--ink-500);
      font-weight: 500;
    }}
    .hairline-b {{ border-bottom: 1px solid var(--line-200); }}
    .hairline-t {{ border-top: 1px solid var(--line-200); }}
    .hairline-r {{ border-right: 1px solid var(--line-200); }}
    .hairline-all {{ border: 1px solid var(--line-200); }}
    .btn-black {{
      background: var(--black);
      color: var(--white);
      border: 1px solid var(--black);
      transition: background 0.2s ease, color 0.2s ease;
    }}
    .btn-black:hover {{
      background: #2b2b2b;
    }}
    .btn-outline {{
      background: var(--white);
      color: var(--ink-900);
      border: 1px solid var(--ink-900);
      transition: background 0.2s ease, color 0.2s ease;
    }}
    .btn-outline:hover {{
      background: var(--mist-100);
    }}
    .chip-btn {{
      background: var(--white);
      color: var(--ink-600);
      border: 1px solid var(--line-200);
      transition: all 0.2s ease;
    }}
    .chip-btn:hover {{
      border-color: var(--ink-900);
      color: var(--ink-900);
    }}
    .chip-btn.active {{
      background: var(--black);
      color: var(--white);
      border-color: var(--black);
    }}
    .row-item {{
      transition: background 0.2s ease;
      border-bottom: 1px solid var(--line-200);
    }}
    .row-item:hover {{
      background: #f7f7f8;
    }}
    .row-item.active {{
      background: var(--mist-100);
      border-left: 3px solid var(--black);
    }}
    .score-bar {{
      transition: width 0.4s ease;
    }}
    ::-webkit-scrollbar {{ width: 5px; height: 5px; }}
    ::-webkit-scrollbar-thumb {{ background: var(--line-200); }}
  </style>
</head>
<body class="antialiased">
  <div class="max-w-[1380px] mx-auto px-5 sm:px-8 pb-14">

    <!-- Top Atelier Navigation Bar -->
    <header class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 py-5 border-b border-[#141414]">
      <div class="flex items-center gap-6">
        <span class="text-xs font-bold tracking-[0.2em] uppercase text-black">HWH ATELIER</span>
        <nav class="hidden md:flex items-center gap-5 text-[11px] tracking-[0.12em] uppercase text-[#615f5f]">
          <a href="#thermometer-sec" class="hover:text-black transition">MACRO</a>
          <a href="#screener-sec" class="hover:text-black transition">SCREENER</a>
          <a href="#gallery-sec" id="navGalleryLink" class="hover:text-black transition">GALLERY</a>
        </nav>
      </div>
      <div class="flex flex-wrap items-center gap-2.5">
        <span id="scanDateBadge" class="text-xs font-mono text-[#615f5f] mr-1"></span>
        <button id="copyCmdBtn" class="btn-outline px-3.5 py-2 text-xs font-medium tracking-wider uppercase cursor-pointer">
          <span id="copyCmdText">COPY RUN CMD</span>
        </button>
        <button id="galleryToggleBtn" class="btn-black px-4 py-2 text-xs font-medium tracking-wider uppercase cursor-pointer">
          CHART GALLERY
        </button>
      </div>
    </header>

    <!-- 00 / Cross-Asset Thermometer Strip -->
    <section id="thermometer-sec" class="py-6 hairline-b">
      <div class="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-2 mb-4">
        <div class="flex items-baseline gap-3">
          <span class="caps-label">00 · CROSS-ASSET THERMOMETER</span>
          <span class="text-xs text-[#615f5f]">현우현 선행지표 실시간 체크</span>
        </div>
        <span id="fxRatioNote" class="text-xs font-medium text-[#141414]"></span>
      </div>
      <div id="thermometerGrid" class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 border-t border-l border-[#e3e1e1]"></div>
    </section>

    <!-- 01 / Filter & Controls Bar -->
    <section id="screener-sec" class="py-5 hairline-b space-y-4">
      <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
        <!-- Market Tabs -->
        <div class="flex flex-wrap items-center gap-2">
          <button data-market="ALL" class="market-tab chip-btn px-4 py-2 text-xs font-semibold tracking-wide cursor-pointer">전체 TOP</button>
          <button data-market="KR" class="market-tab chip-btn px-4 py-2 text-xs font-semibold tracking-wide cursor-pointer">국내주식 (KR)</button>
          <button data-market="US" class="market-tab chip-btn px-4 py-2 text-xs font-semibold tracking-wide cursor-pointer">미국주식 (SPY/NDX)</button>
        </div>

        <!-- Underline Search & Sort -->
        <div class="flex flex-wrap items-center gap-5">
          <div class="flex items-center border-b border-[#141414] pb-1 w-56">
            <input id="searchInput" type="text" placeholder="종목명 · 티커 검색" class="w-full text-sm bg-transparent text-[#141414] placeholder:text-[#7d7d7d] focus:outline-none" />
            <span class="text-xs text-[#615f5f]">→</span>
          </div>
          <select id="sortSelect" class="border-b border-[#141414] pb-1 text-sm bg-transparent text-[#141414] focus:outline-none cursor-pointer pr-2">
            <option value="total_score">정렬: 현우현 총점순</option>
            <option value="rr_ratio">정렬: 손익비(R:R)순</option>
            <option value="rsi_asc">정렬: RSI 낮은순</option>
            <option value="rs_5d">정렬: 상대강도(RS)순</option>
          </select>
        </div>
      </div>

      <!-- Setup Filter Chips -->
      <div class="flex flex-wrap items-center gap-2 pt-1">
        <span class="caps-label mr-2">SETUP FILTER</span>
        <button data-setup="ALL" class="setup-chip chip-btn px-3 py-1.5 text-xs font-medium cursor-pointer">전체</button>
        <button data-setup="턴어라운드 5~6단계" class="setup-chip chip-btn px-3 py-1.5 text-xs font-medium cursor-pointer">턴어라운드 5~6단계</button>
        <button data-setup="장기이평 공포매집" class="setup-chip chip-btn px-3 py-1.5 text-xs font-medium cursor-pointer">장기이평(400~500) 매집</button>
        <button data-setup="강세 기간조정" class="setup-chip chip-btn px-3 py-1.5 text-xs font-medium cursor-pointer">강세 기간조정</button>
        <button data-setup="DIV" class="setup-chip chip-btn px-3 py-1.5 text-xs font-medium cursor-pointer">상승 다이버전스</button>
        <button data-setup="CHART_ONLY" class="setup-chip chip-btn px-3 py-1.5 text-xs font-medium cursor-pointer">빗각 작도 완료만</button>
      </div>
    </section>

    <!-- 02 / Editorial Split-Pane Workspace -->
    <main class="grid grid-cols-1 lg:grid-cols-12 border-b border-[#e3e1e1]">
      <!-- Left Column: Ranked Candidates (5 cols) -->
      <div class="lg:col-span-5 lg:border-r border-[#e3e1e1] py-6 lg:pr-6">
        <div class="flex items-baseline justify-between pb-3 mb-1 border-b border-[#141414]">
          <div>
            <span class="caps-label">01 · CANDIDATES</span>
            <h2 class="font-serif-display text-3xl text-black mt-0.5">Ranked Stocks <span class="text-base font-sans font-normal text-[#615f5f]">(<span id="countReadout">0</span>)</span></h2>
          </div>
          <span class="text-xs text-[#7d7d7d]">보유자 영역 자동 제외</span>
        </div>
        <div id="stockList" class="max-h-[820px] overflow-y-auto"></div>
      </div>

      <!-- Right Column: Master Analysis & Auto-Trendline Chart (7 cols) -->
      <div id="detailPanel" class="lg:col-span-7 py-6 lg:pl-8 space-y-6">
        <div class="py-20 text-center text-sm text-[#7d7d7d]">좌측 리스트에서 종목을 선택하세요.</div>
      </div>
    </main>

    <!-- 03 / Top-10 Chart Gallery -->
    <section id="gallery-sec" class="hidden py-8 space-y-5 hairline-b">
      <div class="flex items-end justify-between pb-3 border-b border-[#141414]">
        <div>
          <span class="caps-label">02 · CHART ARCHIVE</span>
          <h2 class="font-serif-display text-3xl text-black mt-0.5">Auto-Trendline Gallery <span class="text-sm font-sans font-normal text-[#615f5f]">(KR Top 5 · US Top 5)</span></h2>
        </div>
        <button id="closeGalleryBtn" class="btn-outline px-3 py-1.5 text-xs uppercase tracking-wider cursor-pointer">CLOSE</button>
      </div>
      <div id="galleryGrid" class="grid grid-cols-1 md:grid-cols-2 gap-6"></div>
    </section>

    <!-- Minimal Footer -->
    <footer class="pt-5 flex flex-col sm:flex-row justify-between gap-2 text-xs text-[#7d7d7d]">
      <span>※ 본 대시보드는 현우현(hwh_gusdn524) 방법론 정량 필터링 결과이며 매매 리딩이 아닙니다. 최종 진입은 일봉 종가 마감과 본인 리스크 기준에 따르세요.</span>
      <span id="metaStats" class="font-mono text-[#615f5f]"></span>
    </footer>
  </div>

  <!-- Lightbox Modal (Only overlay uses shadow per Monochrome Atelier spec) -->
  <div id="lightbox" class="fixed inset-0 z-50 hidden items-center justify-center bg-black/85 p-4 cursor-zoom-out">
    <img id="lightboxImg" src="" alt="확대 차트" class="max-w-full max-h-[94vh] shadow-2xl border border-[#e3e1e1]" />
  </div>

  <script>
    const PAYLOAD = {data_json};

    let state = {{
      market: "ALL",
      setup: "ALL",
      search: "",
      sort: "total_score",
      selectedKey: null,
    }};

    function fmtPrice(val, market) {{
      if (val == null || isNaN(val)) return "-";
      return market === "KR"
        ? Math.round(val).toLocaleString("ko-KR") + "원"
        : "$" + Number(val).toLocaleString("en-US", {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
    }}

    function renderThermometer() {{
      document.getElementById("scanDateBadge").textContent = "DATE · " + PAYLOAD.scan_date;
      document.getElementById("metaStats").textContent =
        `SCANNED KR ${{PAYLOAD.stats.kr_scanned}} · US ${{PAYLOAD.stats.us_scanned}} · CHARTS ${{Object.keys(PAYLOAD.charts).length}}`;

      if (PAYLOAD.fx_ratio) {{
        const r = PAYLOAD.fx_ratio;
        const msg = r <= 13.0
          ? `순수 원화체력 (USD/KRW÷DXY): ${{r.toFixed(2)}} — 원화 강세(12.7 근접 · 달러/미장 유리)`
          : r >= 14.4
          ? `순수 원화체력 (USD/KRW÷DXY): ${{r.toFixed(2)}} — 고환율(14.4~15.0 · 국장 유리)`
          : `순수 원화체력 (USD/KRW÷DXY): ${{r.toFixed(2)}} — 중립 구간`;
        document.getElementById("fxRatioNote").textContent = msg;
      }}

      const grid = document.getElementById("thermometerGrid");
      grid.innerHTML = PAYLOAD.thermometer.map(t => {{
        const up = t.chg_pct >= 0;
        const chgClr = up ? "text-[#00a65a]" : "text-[#c1121f]";
        return `
          <div class="p-3.5 border-r border-b border-[#e3e1e1] bg-white flex flex-col justify-between gap-1.5">
            <div class="flex items-center justify-between">
              <span class="caps-label">${{t.label}}</span>
              <span class="text-xs font-mono text-[#615f5f]">RSI ${{t.rsi}}</span>
            </div>
            <div class="font-serif-display text-2xl text-black leading-tight tabular-nums">${{t.price_str}}</div>
            <div class="flex items-center justify-between text-xs">
              <span class="font-mono font-semibold ${{chgClr}}">${{up ? "+" : ""}}${{t.chg_pct.toFixed(2)}}%</span>
              <span class="text-[#7d7d7d]">${{t.ma_status}}</span>
            </div>
          </div>`;
      }}).join("");
    }}

    function getFilteredItems() {{
      let items = [...PAYLOAD.items];
      if (state.market !== "ALL") items = items.filter(x => x.market === state.market);
      if (state.setup === "DIV") items = items.filter(x => x.has_div);
      else if (state.setup === "CHART_ONLY") items = items.filter(x => Boolean(PAYLOAD.charts[x.market + ":" + x.symbol]));
      else if (state.setup !== "ALL") items = items.filter(x => x.setup_type === state.setup);

      if (state.search.trim()) {{
        const q = state.search.trim().toLowerCase();
        items = items.filter(x => x.name.toLowerCase().includes(q) || x.symbol.toLowerCase().includes(q));
      }}

      items.sort((a, b) => {{
        if (state.sort === "rr_ratio") return b.rr_ratio - a.rr_ratio;
        if (state.sort === "rsi_asc") return a.rsi14 - b.rsi14;
        if (state.sort === "rs_5d") return b.rs_5d - a.rs_5d;
        return b.total_score - a.total_score;
      }});
      return items;
    }}

    function renderList() {{
      const items = getFilteredItems();
      document.getElementById("countReadout").textContent = items.length;
      const list = document.getElementById("stockList");

      if (!items.length) {{
        list.innerHTML = `<div class="py-14 text-center text-sm text-[#7d7d7d]">조건에 맞는 종목이 없습니다.</div>`;
        return;
      }}

      if (!state.selectedKey || !items.some(x => (x.market + ":" + x.symbol) === state.selectedKey)) {{
        state.selectedKey = items[0].market + ":" + items[0].symbol;
      }}

      list.innerHTML = items.map((x, idx) => {{
        const key = x.market + ":" + x.symbol;
        const active = key === state.selectedKey;
        const hasChart = Boolean(PAYLOAD.charts[key]);
        const up = x.chg_pct >= 0;
        const scoreHigh = x.total_score >= 88;
        return `
          <div data-key="${{key}}" class="stock-row row-item px-3.5 py-3.5 cursor-pointer flex items-center justify-between gap-3 ${{active ? 'active' : ''}}">
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <span class="text-xs font-mono text-[#7d7d7d] w-6">${{String(idx + 1).padStart(2, '0')}}</span>
                <span class="text-xs font-mono px-1.5 py-0.5 border border-[#e3e1e1] text-[#615f5f]">${{x.market}}</span>
                <span class="font-semibold text-[15px] text-[#141414] truncate">${{x.name}}</span>
                <span class="text-xs font-mono text-[#7d7d7d]">${{x.symbol}}</span>
                ${{hasChart ? '<span class="text-[11px] px-1.5 py-0.5 bg-black text-white font-medium">작도</span>' : ''}}
              </div>
              <div class="flex flex-wrap items-center gap-2.5 mt-1.5 pl-8 text-xs text-[#615f5f]">
                <span>${{x.setup_type}}</span>
                <span>·</span>
                <span class="font-mono">RSI ${{x.rsi14}}</span>
                <span>·</span>
                <span class="font-mono">R:R 1:${{x.rr_ratio}}</span>
                ${{x.has_div ? '<span class="text-[#00a65a] font-semibold">· 상승다이버</span>' : ''}}
              </div>
            </div>
            <div class="text-right shrink-0">
              <div class="font-serif-display text-2xl leading-none ${{scoreHigh ? 'text-[#00a65a]' : 'text-black'}}">${{x.total_score}}<span class="text-xs font-sans text-[#7d7d7d] ml-0.5">점</span></div>
              <div class="text-xs font-mono mt-1.5 tabular-nums text-[#141414]">
                ${{fmtPrice(x.close, x.market)}}
                <span class="ml-1 ${{up ? 'text-[#00a65a]' : 'text-[#c1121f]'}}">${{up ? '+' : ''}}${{x.chg_pct}}%</span>
              </div>
            </div>
          </div>`;
      }}).join("");

      list.querySelectorAll(".stock-row").forEach(el => {{
        el.addEventListener("click", () => {{
          state.selectedKey = el.dataset.key;
          renderList();
          renderDetail();
        }});
      }});

      renderDetail();
    }}

    function renderDetail() {{
      const panel = document.getElementById("detailPanel");
      const item = PAYLOAD.items.find(x => (x.market + ":" + x.symbol) === state.selectedKey);
      if (!item) return;

      const key = item.market + ":" + item.symbol;
      const chartB64 = PAYLOAD.charts[key];
      const tPct = ((item.target1 / item.close - 1) * 100).toFixed(1);
      const sPct = ((item.stop_loss / item.close - 1) * 100).toFixed(1);
      const up = item.chg_pct >= 0;

      const bars = [
        {{ label: "이평·턴어라운드", val: item.score_ma, max: 35 }},
        {{ label: "RSI·상승다이버", val: item.score_rsi, max: 25 }},
        {{ label: "지지·빗각 중첩", val: item.score_sr, max: 20 }},
        {{ label: "거래량·상대강도", val: item.score_vr, max: 20 }},
      ];

      panel.innerHTML = `
        <!-- Editorial Header -->
        <div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 pb-4 border-b border-[#141414]">
          <div>
            <span class="caps-label">${{item.exchange}} · ${{item.date}}</span>
            <h2 class="text-2xl sm:text-3xl font-bold text-black mt-1">
              ${{item.name}} <span class="font-serif-display font-normal text-2xl text-[#615f5f] ml-1">${{item.symbol}}</span>
            </h2>
            <p class="text-sm text-[#615f5f] mt-1">${{item.stage}}</p>
          </div>
          <div class="flex items-end gap-5">
            <div class="text-right">
              <div class="caps-label">CLOSE</div>
              <div class="text-xl font-bold font-mono text-black tabular-nums">${{fmtPrice(item.close, item.market)}}</div>
              <div class="text-xs font-mono ${{up ? 'text-[#00a65a]' : 'text-[#c1121f]'}}">
                ${{up ? '+' : ''}}${{item.chg_pct}}% · RS(5d) ${{item.rs_5d >= 0 ? '+' : ''}}${{item.rs_5d}}%
              </div>
            </div>
            <div class="pl-5 border-l border-[#e3e1e1] text-right">
              <div class="caps-label">SCORE</div>
              <div class="font-serif-display text-4xl leading-none text-[#00a65a]">${{Math.round(item.total_score)}}</div>
            </div>
          </div>
        </div>

        <!-- 4-Column Hairline Actionable Price Grid -->
        <div class="grid grid-cols-2 sm:grid-cols-4 border-t border-l border-[#e3e1e1]">
          <div class="p-3.5 border-r border-b border-[#e3e1e1]">
            <div class="caps-label">BUY ZONE (매수 타점)</div>
            <div class="text-sm font-bold font-mono text-[#00a65a] mt-1.5 leading-snug">
              ${{fmtPrice(item.buy_lo, item.market)}}<br/>~ ${{fmtPrice(item.buy_hi, item.market)}}
            </div>
          </div>
          <div class="p-3.5 border-r border-b border-[#e3e1e1]">
            <div class="caps-label">TARGET 1 (1차 저항)</div>
            <div class="text-base font-bold font-mono text-[#141414] mt-1.5">${{fmtPrice(item.target1, item.market)}}</div>
            <div class="text-xs font-mono text-[#615f5f] mt-0.5">+${{tPct}}%</div>
          </div>
          <div class="p-3.5 border-r border-b border-[#e3e1e1]">
            <div class="caps-label">STOP LOSS (종가 손절)</div>
            <div class="text-base font-bold font-mono text-[#c1121f] mt-1.5">${{fmtPrice(item.stop_loss, item.market)}}</div>
            <div class="text-xs font-mono text-[#615f5f] mt-0.5">${{sPct}}%</div>
          </div>
          <div class="p-3.5 border-r border-b border-[#e3e1e1]">
            <div class="caps-label">RISK : REWARD</div>
            <div class="font-serif-display text-3xl text-black mt-1 leading-none">1 : ${{item.rr_ratio}}</div>
            <div class="text-xs font-mono text-[#615f5f] mt-1">RSI ${{item.rsi14}} · 20이격 ${{item.disp20 >= 0 ? '+' : ''}}${{item.disp20}}%</div>
          </div>
        </div>

        <!-- 4-Axis Score Bars -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 py-1">
          ${{bars.map(b => `
            <div class="space-y-1.5">
              <div class="flex justify-between text-xs">
                <span class="text-[#615f5f]">${{b.label}}</span>
                <span class="font-mono font-semibold text-black">${{b.val}}/${{b.max}}</span>
              </div>
              <div class="h-1.5 bg-[#e9e9eb] overflow-hidden">
                <div class="score-bar h-full bg-black" style="width: ${{(b.val / b.max * 100).toFixed(0)}}%"></div>
              </div>
            </div>`).join("")}}
        </div>

        <!-- Tags & Diagnosis -->
        <div class="p-4 bg-[#f8f8f9] border border-[#e3e1e1] space-y-2.5">
          <div class="flex flex-wrap gap-1.5">
            ${{item.tags.map(t => `<span class="text-xs px-2.5 py-0.5 bg-white border border-[#e3e1e1] text-[#141414]">${{t}}</span>`).join("")}}
          </div>
          <p class="text-sm text-[#141414] leading-relaxed">
            <span class="font-bold text-black mr-1.5">[현우현 관점 진단]</span>${{item.comment}}
          </p>
        </div>

        <!-- Automated HWH Trendline Chart -->
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <span class="caps-label">AUTO-TRENDLINE CHART (7 SMA · 빗각 · S/R · RSI)</span>
            ${{chartB64 ? '<span class="text-xs text-[#615f5f]">클릭 시 확대</span>' : ''}}
          </div>
          ${{chartB64
            ? `<img src="data:image/png;base64,${{chartB64}}" alt="${{item.name}} 작도 차트" class="zoomable-chart w-full border border-[#e3e1e1] cursor-zoom-in hover:opacity-95 transition" />`
            : `<div class="p-10 border border-dashed border-[#e3e1e1] text-center text-sm text-[#7d7d7d] space-y-1">
                 <div>상위 Top 5(KR/US 각 5종목)에 자동 빗각 작도 차트가 생성되었습니다.</div>
                 <div>정밀 작도가 필요하면 채팅창에 <strong class="text-black">"${{item.name}} 현우현 스타일로 작도해줘"</strong>라고 입력해 주세요.</div>
               </div>`
          }}
        </div>
      `;

      const img = panel.querySelector(".zoomable-chart");
      if (img) img.addEventListener("click", () => openLightbox(img.src));
    }}

    function renderGallery() {{
      const grid = document.getElementById("galleryGrid");
      const chartItems = PAYLOAD.items.filter(x => Boolean(PAYLOAD.charts[x.market + ":" + x.symbol]));
      grid.innerHTML = chartItems.map(x => {{
        const key = x.market + ":" + x.symbol;
        return `
          <div class="border border-[#e3e1e1] p-4 space-y-3 bg-white">
            <div class="flex items-baseline justify-between border-b border-[#e3e1e1] pb-2">
              <div class="font-bold text-base text-black">${{x.name}} <span class="text-xs font-mono text-[#7d7d7d] ml-1">${{x.symbol}}</span></div>
              <span class="text-xs font-mono font-semibold text-[#00a65a]">${{x.total_score}}점 · R:R 1:${{x.rr_ratio}}</span>
            </div>
            <img src="data:image/png;base64,${{PAYLOAD.charts[key]}}" class="gallery-img w-full border border-[#e3e1e1] cursor-zoom-in" />
          </div>`;
      }}).join("");

      grid.querySelectorAll(".gallery-img").forEach(im => {{
        im.addEventListener("click", () => openLightbox(im.src));
      }});
    }}

    function openLightbox(src) {{
      const lb = document.getElementById("lightbox");
      document.getElementById("lightboxImg").src = src;
      lb.classList.remove("hidden");
      lb.classList.add("flex");
    }}

    document.getElementById("lightbox").addEventListener("click", () => {{
      const lb = document.getElementById("lightbox");
      lb.classList.add("hidden");
      lb.classList.remove("flex");
    }});

    function syncControlStyles() {{
      document.querySelectorAll(".market-tab").forEach(btn => {{
        btn.classList.toggle("active", btn.dataset.market === state.market);
      }});
      document.querySelectorAll(".setup-chip").forEach(btn => {{
        btn.classList.toggle("active", btn.dataset.setup === state.setup);
      }});
    }}

    document.querySelectorAll(".market-tab").forEach(btn => {{
      btn.addEventListener("click", () => {{ state.market = btn.dataset.market; syncControlStyles(); renderList(); }});
    }});
    document.querySelectorAll(".setup-chip").forEach(btn => {{
      btn.addEventListener("click", () => {{ state.setup = btn.dataset.setup; syncControlStyles(); renderList(); }});
    }});
    document.getElementById("searchInput").addEventListener("input", e => {{ state.search = e.target.value; renderList(); }});
    document.getElementById("sortSelect").addEventListener("change", e => {{ state.sort = e.target.value; renderList(); }});

    function toggleGallery() {{
      const sec = document.getElementById("gallery-sec");
      sec.classList.toggle("hidden");
      if (!sec.classList.contains("hidden")) sec.scrollIntoView({{ behavior: "smooth" }});
    }}
    document.getElementById("galleryToggleBtn").addEventListener("click", toggleGallery);
    document.getElementById("navGalleryLink").addEventListener("click", e => {{ e.preventDefault(); toggleGallery(); }});
    document.getElementById("closeGalleryBtn").addEventListener("click", () => {{
      document.getElementById("gallery-sec").classList.add("hidden");
    }});

    document.getElementById("copyCmdBtn").addEventListener("click", () => {{
      navigator.clipboard?.writeText("오늘 국장/미장 현우현 스크리너 돌려줘");
      const txt = document.getElementById("copyCmdText");
      txt.textContent = "COPIED!";
      setTimeout(() => txt.textContent = "COPY RUN CMD", 2000);
    }});

    renderThermometer();
    syncControlStyles();
    renderList();
    renderGallery();
  </script>
</body>
</html>
"""
