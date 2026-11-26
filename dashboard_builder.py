import json


def build_dashboard_html(payload: dict, standalone_web: bool = False) -> str:
    """Build an emoji-free Monochrome Atelier interactive dashboard with TradingView Lightweight Charts + Side-by-Side Report."""
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
  <title>HWH RESEARCH TERMINAL — 현우현 종가 스크리너 &amp; 관제</title>
  <script src="{tw_cdn}"></script>
  <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Noto+Sans+KR:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <style>
    :root {{
      --black: #000000;
      --ink-900: #141414;
      --ink-600: #595757;
      --ink-500: #7d7d7d;
      --line-200: #e3e1e1;
      --mist-100: #f5f5f5;
      --white: #ffffff;
      --up: #007f4e;
      --down: #c1121f;
      --navy: #003566;
    }}
    * {{
      border-radius: 0 !important;
      box-sizing: border-box;
    }}
    body {{
      background-color: var(--white);
      color: var(--ink-900);
      font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
      font-size: 13px;
      line-height: 1.5;
      margin: 0;
      padding: 0;
    }}
    .font-serif-display {{
      font-family: 'Instrument Serif', Georgia, serif;
      letter-spacing: -0.02em;
    }}
    .caps-label {{
      font-size: 10.5px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--ink-500);
      font-weight: 600;
    }}
    .num {{ font-variant-numeric: tabular-nums; }}
    .hairline-b {{ border-bottom: 1px solid var(--line-200); }}
    .hairline-t {{ border-top: 1px solid var(--line-200); }}
    .hairline-r {{ border-right: 1px solid var(--line-200); }}
    .hairline-l {{ border-left: 1px solid var(--line-200); }}
    .hairline-all {{ border: 1px solid var(--line-200); }}
    .pill-btn {{
      border: 1px solid var(--line-200);
      background: var(--white);
      color: var(--ink-600);
      padding: 4px 10px;
      font-size: 11.5px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.12s ease;
    }}
    .pill-btn:hover {{
      border-color: var(--ink-900);
      color: var(--ink-900);
    }}
    .pill-btn.active {{
      background: var(--ink-900);
      border-color: var(--ink-900);
      color: var(--white);
    }}
    .stock-tab {{
      border: 1px solid var(--line-200);
      background: var(--white);
      padding: 6px 11px;
      cursor: pointer;
      text-align: left;
      transition: all 0.12s ease;
    }}
    .stock-tab:hover {{ border-color: var(--ink-900); }}
    .stock-tab.active {{
      background: var(--ink-900);
      color: var(--white);
      border-color: var(--ink-900);
    }}
    .stock-tab.active .muted-sub {{ color: #bdbdbd; }}
    .report-scroll {{
      max-height: 620px;
      overflow-y: auto;
    }}
    .tbl-row {{ cursor: pointer; transition: background 0.1s ease; }}
    .tbl-row:hover {{ background: var(--mist-100); }}
    .tbl-row.selected {{ background: #efefef; }}
  </style>
</head>
<body>
  <!-- TOP HEADER -->
  <header class="hairline-b sticky top-0 z-30 bg-white">
    <div class="max-w-[1440px] mx-auto px-5 py-3 flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-baseline gap-4">
        <span class="font-serif-display text-2xl font-normal tracking-tight text-black">HWH Terminal</span>
        <span class="caps-label">현우현 일일 종가 스크리너 &amp; 지속 관제</span>
      </div>
      <div class="flex flex-wrap items-center gap-5 text-xs">
        <div><span class="caps-label mr-1.5">기준일</span><span id="scan-date" class="font-semibold num"></span></div>
        <div><span class="caps-label mr-1.5">스캔</span><span id="scan-counts" class="font-semibold num"></span></div>
        <div><span class="caps-label mr-1.5">원화체력 (USDKRW/DXY)</span><span id="fx-ratio" class="font-semibold num"></span></div>
      </div>
    </div>
  </header>

  <main class="max-w-[1440px] mx-auto px-5 py-5 space-y-6">
    <!-- 1. CROSS-ASSET THERMOMETER -->
    <section class="hairline-all bg-white">
      <div class="px-4 py-2 hairline-b flex items-center justify-between bg-[#fafafa]">
        <span class="caps-label">글로벌 시장 온도계 (Cross-Asset Thermometer)</span>
        <span class="text-[11px] text-[#7d7d7d]">120일선(생명선) · 500일선(장기추세) 기준</span>
      </div>
      <div id="thermometer-grid" class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 divide-x divide-y lg:divide-y-0 divide-[#e3e1e1]"></div>
    </section>

    <!-- 2. DAILY DIFF BRIEFING (YESTERDAY VS TODAY) -->
    <section class="hairline-all bg-white">
      <div class="px-4 py-2.5 hairline-b flex flex-wrap items-center justify-between gap-2 bg-[#fafafa]">
        <div class="flex items-center gap-3">
          <span class="caps-label">일일 변화 브리핑 (어제 vs 오늘)</span>
          <span id="diff-dates" class="text-xs font-medium text-[#595757] num"></span>
        </div>
        <span class="text-[11px] text-[#7d7d7d]">종목 클릭 시 하단 인터랙티브 차트 및 보고서로 즉시 이동</span>
      </div>
      <div id="diff-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 divide-y lg:divide-y-0 lg:divide-x divide-[#e3e1e1]"></div>
    </section>

    <!-- 3. INTERACTIVE CHART + SIDE-BY-SIDE STOCK REPORT -->
    <section id="workspace-section" class="hairline-all bg-white">
      <!-- Stock Selector Bar -->
      <div class="p-3 hairline-b bg-[#fafafa] space-y-2.5">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span class="caps-label">지속 관제 작도 종목 (트레이딩뷰 인터랙티브 차트 + 정밀 보고서)</span>
          <div class="flex items-center gap-1.5">
            <button class="pill-btn active" data-mkt-filter="ALL" onclick="setMarketFilter('ALL')">전체</button>
            <button class="pill-btn" data-mkt-filter="KR" onclick="setMarketFilter('KR')">국장 KR</button>
            <button class="pill-btn" data-mkt-filter="US" onclick="setMarketFilter('US')">미장 US</button>
          </div>
        </div>
        <div id="watched-tabs" class="flex flex-wrap gap-1.5"></div>
      </div>

      <!-- Split View: Left Chart (62%) + Right Report (38%) -->
      <div class="grid grid-cols-1 lg:grid-cols-12">
        <!-- LEFT: TradingView Lightweight Charts -->
        <div class="lg:col-span-8 lg:hairline-r flex flex-col">
          <!-- Chart Toolbar & Crosshair Readout -->
          <div class="px-4 py-3 hairline-b flex flex-wrap items-center justify-between gap-3">
            <div>
              <div class="flex items-baseline gap-2.5">
                <h2 id="chart-title" class="text-lg font-bold tracking-tight m-0"></h2>
                <span id="chart-price" class="text-base font-bold num"></span>
                <span id="chart-chg" class="text-xs font-semibold num"></span>
              </div>
              <div id="crosshair-readout" class="text-[11px] text-[#595757] num mt-0.5">
                차트를 드래그해 과거~현재 앞뒤 이동, 휠로 확대/축소, 마우스를 올려 OHLC·이평선 수치를 확인하세요.
              </div>
            </div>
            <div class="flex flex-wrap items-center gap-1.5">
              <button id="btn-toggle-ma" class="pill-btn active" onclick="toggleLayer('ma')">이평선(7)</button>
              <button id="btn-toggle-tl" class="pill-btn active" onclick="toggleLayer('tl')">하락빗각</button>
              <button id="btn-toggle-lv" class="pill-btn active" onclick="toggleLayer('lv')">매집·손절선</button>
              <span class="text-[#e3e1e1] mx-1">|</span>
              <button class="pill-btn" onclick="setRangeBars(65)">3M</button>
              <button class="pill-btn" onclick="setRangeBars(130)">6M</button>
              <button class="pill-btn active" onclick="setRangeBars(260)">1Y</button>
            </div>
          </div>

          <!-- MA Legend Strip -->
          <div class="px-4 py-1.5 hairline-b bg-[#fcfcfc] flex flex-wrap items-center gap-3 text-[11px] num">
            <span class="font-medium text-[#7d7d7d]">SMA:</span>
            <span style="color:#e63946">20일</span>
            <span style="color:#1d4ed8">60일</span>
            <span style="color:#00a65a; font-weight:700">120일(생명선)</span>
            <span style="color:#f57c00; font-weight:700">200일</span>
            <span style="color:#8b2fc9">300일</span>
            <span style="color:#c59b08; font-weight:700">400일</span>
            <span style="color:#111111; font-weight:700">500일(장기)</span>
            <span class="text-[#d4d4d4]">|</span>
            <span style="color:#003566; font-weight:700">하락빗각</span>
            <span style="color:#007f4e; font-weight:700">매집존</span>
            <span style="color:#c1121f; font-weight:700">손절선</span>
          </div>

          <!-- Main Candle Chart + RSI Subchart -->
          <div class="relative w-full bg-white">
            <div id="tv-main-chart" class="w-full" style="height: 430px;"></div>
            <div class="px-4 py-1 hairline-t hairline-b bg-[#fafafa] flex items-center justify-between text-[11px]">
              <span class="caps-label">RSI (14) 모멘텀</span>
              <span id="rsi-live-badge" class="font-semibold num text-[#4b0082]"></span>
            </div>
            <div id="tv-rsi-chart" class="w-full" style="height: 135px;"></div>
          </div>
        </div>

        <!-- RIGHT: Stock Research Report -->
        <div class="lg:col-span-4 flex flex-col bg-white">
          <div class="px-4 py-3 hairline-b bg-[#fafafa] flex items-center justify-between">
            <span class="caps-label">종목 정밀 보고서 (HWH Memo)</span>
            <span id="report-status-badge" class="text-[11px] font-semibold px-2 py-0.5 border border-[#141414]"></span>
          </div>
          <div id="report-body" class="p-4 space-y-4 report-scroll"></div>
        </div>
      </div>
    </section>

    <!-- 4. KR & US SCREENER TABLES -->
    <section class="grid grid-cols-1 xl:grid-cols-2 gap-5">
      <div class="hairline-all bg-white">
        <div class="px-4 py-2.5 hairline-b bg-[#fafafa] flex items-center justify-between">
          <span class="caps-label">KR 스크리너 TOP 15 (코스피 120 + 코스닥 80)</span>
          <span class="text-[11px] text-[#7d7d7d]">행 클릭 시 차트·보고서 전환</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse text-xs">
            <thead>
              <tr class="hairline-b text-[10.5px] text-[#7d7d7d] uppercase bg-[#fcfcfc]">
                <th class="py-2 px-3">#</th>
                <th class="py-2 px-2">종목</th>
                <th class="py-2 px-2 text-right">점수</th>
                <th class="py-2 px-2">셋업</th>
                <th class="py-2 px-2 text-right">현재가</th>
                <th class="py-2 px-2 text-right">등락</th>
                <th class="py-2 px-2 text-right">RSI</th>
                <th class="py-2 px-3 text-right">R:R</th>
              </tr>
            </thead>
            <tbody id="kr-table-body" class="divide-y divide-[#e3e1e1]"></tbody>
          </table>
        </div>
      </div>

      <div class="hairline-all bg-white">
        <div class="px-4 py-2.5 hairline-b bg-[#fafafa] flex items-center justify-between">
          <span class="caps-label">US 스크리너 TOP 15 (NASDAQ 100 + NYSE 120)</span>
          <span class="text-[11px] text-[#7d7d7d]">행 클릭 시 차트·보고서 전환</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse text-xs">
            <thead>
              <tr class="hairline-b text-[10.5px] text-[#7d7d7d] uppercase bg-[#fcfcfc]">
                <th class="py-2 px-3">#</th>
                <th class="py-2 px-2">종목</th>
                <th class="py-2 px-2 text-right">점수</th>
                <th class="py-2 px-2">셋업</th>
                <th class="py-2 px-2 text-right">현재가</th>
                <th class="py-2 px-2 text-right">등락</th>
                <th class="py-2 px-2 text-right">RSI</th>
                <th class="py-2 px-3 text-right">R:R</th>
              </tr>
            </thead>
            <tbody id="us-table-body" class="divide-y divide-[#e3e1e1]"></tbody>
          </table>
        </div>
      </div>
    </section>
  </main>

  <script>
    const PAYLOAD = {data_json};
    let currentKey = null;
    let marketFilter = 'ALL';
    let layers = {{ ma: true, tl: true, lv: true }};
    let mainChart = null, rsiChart = null;
    let candleSeries = null;
    let maSeriesMap = {{}};
    let tlSeriesList = [];
    let priceLinesList = [];
    let rsiSeries = null;

    const itemByKey = {{}};
    (PAYLOAD.items || []).forEach(it => {{ itemByKey[it.market + ':' + it.symbol] = it; }});
    const watchedByKey = {{}};
    (PAYLOAD.watched || []).forEach(w => {{ watchedByKey[w.key] = w; }});

    function fmtPrice(v, mkt) {{
      if (v === null || v === undefined || isNaN(v)) return '-';
      return mkt === 'KR' ? Math.round(v).toLocaleString('ko-KR') + '원' : '$' + Number(v).toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
    }}

    function chgClass(pct) {{
      if (pct > 0) return 'text-[#007f4e]';
      if (pct < 0) return 'text-[#c1121f]';
      return 'text-[#595757]';
    }}

    function initHeader() {{
      document.getElementById('scan-date').textContent = PAYLOAD.scan_date || '-';
      const st = PAYLOAD.stats || {{}};
      document.getElementById('scan-counts').textContent = `KR ${{st.kr_scanned || 0}} · US ${{st.us_scanned || 0}}`;
      const fx = PAYLOAD.fx_ratio;
      document.getElementById('fx-ratio').textContent = fx ? `${{fx}} (12.7 이하 강세)` : '-';
    }}

    function renderThermometer() {{
      const el = document.getElementById('thermometer-grid');
      el.innerHTML = (PAYLOAD.thermometer || []).map(c => `
        <div class="p-3 space-y-1">
          <div class="flex items-center justify-between">
            <span class="caps-label">${{c.label}}</span>
            <span class="text-[11px] font-semibold num ${{chgClass(c.chg_pct)}}">${{c.chg_pct > 0 ? '+' : ''}}${{c.chg_pct}}%</span>
          </div>
          <div class="text-sm font-bold num">${{c.price_str}}</div>
          <div class="flex items-center justify-between text-[11px] text-[#595757]">
            <span>${{c.ma_status}}</span>
            <span class="num">RSI ${{c.rsi}}</span>
          </div>
        </div>
      `).join('');
    }}

    function renderDiff() {{
      const d = PAYLOAD.diff || {{}};
      document.getElementById('diff-dates').textContent = d.prev_date ? `${{d.prev_date}} → ${{PAYLOAD.scan_date}}` : '전일 스냅샷 축적 중 (내일부터 자동 비교)';
      const cols = [
        {{ title: '신규 TOP 10 진입', rows: d.new_top10 || [], empty: '신규 진입 종목 없음', fmt: r => `${{r.rank}}위 · ${{r.score}}점 (${{r.chg_pct > 0 ? '+' : ''}}${{r.chg_pct}}%)` }},
        {{ title: '타점 이탈 · 급등 놓침', rows: d.missed_surged || [], empty: '급등 이탈 종목 없음', fmt: r => r.reason }},
        {{ title: '순위 하락 · 이탈 경고', rows: d.dropped_warning || [], empty: '하락 경고 종목 없음', fmt: r => r.reason }},
        {{ title: '아쉬운 문턱 (11~15위)', rows: d.near_miss || [], empty: '해당 대기열 없음', fmt: r => `${{r.rank}}위 · ${{r.score}}점 · R:R 1:${{r.rr_ratio}}` }},
      ];
      document.getElementById('diff-grid').innerHTML = cols.map(c => `
        <div class="p-3.5 space-y-2">
          <div class="caps-label text-[#141414]">${{c.title}}</div>
          ${{c.rows.length ? c.rows.map(r => `
            <div onclick="selectStock('${{r.key}}')" class="flex items-center justify-between py-1 border-b border-[#f0efef] last:border-0 cursor-pointer hover:bg-[#f5f5f5] px-1">
              <div>
                <span class="font-semibold text-xs">${{r.name}}</span>
                <span class="text-[10.5px] text-[#7d7d7d] ml-1">${{r.symbol}}</span>
              </div>
              <span class="text-[11px] text-[#595757] num">${{c.fmt(r)}}</span>
            </div>
          `).join('') : `<div class="text-xs text-[#7d7d7d] py-2">${{c.empty}}</div>`}}
        </div>
      `).join('');
    }}

    function renderWatchedTabs() {{
      const el = document.getElementById('watched-tabs');
      const list = (PAYLOAD.watched || []).filter(w => marketFilter === 'ALL' || w.market === marketFilter);
      el.innerHTML = list.map(w => `
        <button onclick="selectStock('${{w.key}}')" class="stock-tab ${{currentKey === w.key ? 'active' : ''}}">
          <div class="flex items-center gap-2">
            <span class="text-xs font-bold">${{w.name}}</span>
            <span class="text-[10.5px] muted-sub num">${{w.symbol}}</span>
          </div>
          <div class="text-[10.5px] muted-sub num mt-0.5">${{fmtPrice(w.close, w.market)}} (${{w.chg_pct > 0 ? '+' : ''}}${{w.chg_pct}}%) · ${{w.status}}</div>
        </button>
      `).join('');
    }}

    function renderTables() {{
      const items = PAYLOAD.items || [];
      const kr = items.filter(x => x.market === 'KR').slice(0, 15);
      const us = items.filter(x => x.market === 'US').slice(0, 15);
      const fill = (tbodyId, rows) => {{
        document.getElementById(tbodyId).innerHTML = rows.map((x, idx) => {{
          const k = x.market + ':' + x.symbol;
          return `
            <tr onclick="selectStock('${{k}}')" class="tbl-row ${{currentKey === k ? 'selected' : ''}}">
              <td class="py-2 px-3 num text-[#7d7d7d]">${{idx + 1}}</td>
              <td class="py-2 px-2"><span class="font-semibold">${{x.name}}</span> <span class="text-[10.5px] text-[#7d7d7d]">${{x.symbol}}</span></td>
              <td class="py-2 px-2 text-right font-bold num">${{x.total_score.toFixed(1)}}</td>
              <td class="py-2 px-2 text-[11px] text-[#595757]">${{x.setup_type}}</td>
              <td class="py-2 px-2 text-right num font-medium">${{fmtPrice(x.close, x.market)}}</td>
              <td class="py-2 px-2 text-right num font-semibold ${{chgClass(x.chg_pct)}}">${{x.chg_pct > 0 ? '+' : ''}}${{x.chg_pct.toFixed(2)}}%</td>
              <td class="py-2 px-2 text-right num">${{x.rsi14.toFixed(1)}}</td>
              <td class="py-2 px-3 text-right num font-semibold">1:${{x.rr_ratio.toFixed(1)}}</td>
            </tr>
          `;
        }}).join('');
      }};
      fill('kr-table-body', kr);
      fill('us-table-body', us);
    }}

    function initCharts() {{
      const mainEl = document.getElementById('tv-main-chart');
      const rsiEl = document.getElementById('tv-rsi-chart');
      const baseOpts = {{
        layout: {{ background: {{ color: '#ffffff' }}, textColor: '#333333', fontFamily: 'Noto Sans KR, sans-serif', fontSize: 11 }},
        grid: {{ vertLines: {{ color: '#f0f0f0' }}, horzLines: {{ color: '#f0f0f0' }} }},
        crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
        rightPriceScale: {{ borderColor: '#e3e1e1' }},
        timeScale: {{ borderColor: '#e3e1e1', timeVisible: true }},
      }};
      mainChart = LightweightCharts.createChart(mainEl, {{ ...baseOpts, width: mainEl.clientWidth, height: 430 }});
      rsiChart = LightweightCharts.createChart(rsiEl, {{ ...baseOpts, width: rsiEl.clientWidth, height: 135, timeScale: {{ borderColor: '#e3e1e1', visible: true }} }});

      candleSeries = mainChart.addCandlestickSeries({{
        upColor: '#00802b', downColor: '#c1121f', borderUpColor: '#00802b', borderDownColor: '#c1121f',
        wickUpColor: '#00802b', wickDownColor: '#c1121f',
      }});

      const maColors = {{
        sma20: ['#e63946', 1, LightweightCharts.LineStyle.Dashed],
        sma60: ['#1d4ed8', 1, LightweightCharts.LineStyle.Dashed],
        sma120: ['#00a65a', 2, LightweightCharts.LineStyle.Solid],
        sma200: ['#f57c00', 2, LightweightCharts.LineStyle.Solid],
        sma300: ['#8b2fc9', 2, LightweightCharts.LineStyle.Solid],
        sma400: ['#c59b08', 2, LightweightCharts.LineStyle.Solid],
        sma500: ['#111111', 3, LightweightCharts.LineStyle.Solid],
      }};
      Object.entries(maColors).forEach(([k, [color, lineWidth, lineStyle]]) => {{
        maSeriesMap[k] = mainChart.addLineSeries({{ color, lineWidth, lineStyle, priceLineVisible: false, lastValueVisible: false }});
      }});

      rsiSeries = rsiChart.addLineSeries({{ color: '#6a0dad', lineWidth: 2, priceLineVisible: false }});
      rsiSeries.createPriceLine({{ price: 70, color: '#c1121f', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dotted, axisLabelVisible: true }});
      rsiSeries.createPriceLine({{ price: 50, color: '#888888', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: false }});
      rsiSeries.createPriceLine({{ price: 30, color: '#0047ab', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dotted, axisLabelVisible: true }});

      // Sync time scales
      mainChart.timeScale().subscribeVisibleLogicalRangeChange(range => {{
        if (range) rsiChart.timeScale().setVisibleLogicalRange(range);
      }});
      rsiChart.timeScale().subscribeVisibleLogicalRangeChange(range => {{
        if (range) mainChart.timeScale().setVisibleLogicalRange(range);
      }});

      // Crosshair readout
      mainChart.subscribeCrosshairMove(param => {{
        if (!param || !param.time || !currentKey) return;
        const rows = (PAYLOAD.series || {{}})[currentKey] || [];
        const bar = rows.find(r => r.time === param.time);
        if (!bar) return;
        const mkt = currentKey.split(':')[0];
        document.getElementById('crosshair-readout').textContent =
          `${{bar.time}} | O:${{fmtPrice(bar.open, mkt)}} H:${{fmtPrice(bar.high, mkt)}} L:${{fmtPrice(bar.low, mkt)}} C:${{fmtPrice(bar.close, mkt)}} | ` +
          `120일:${{fmtPrice(bar.sma120, mkt)}} 500일:${{fmtPrice(bar.sma500, mkt)}} | RSI:${{bar.rsi14 ?? '-'}}`;
      }});

      window.addEventListener('resize', () => {{
        mainChart.applyOptions({{ width: mainEl.clientWidth }});
        rsiChart.applyOptions({{ width: rsiEl.clientWidth }});
      }});
    }}

    function clearOverlayLines() {{
      tlSeriesList.forEach(s => mainChart.removeSeries(s));
      tlSeriesList = [];
      priceLinesList.forEach(pl => candleSeries.removePriceLine(pl));
      priceLinesList = [];
    }}

    function renderSelectedChart(key) {{
      const rows = (PAYLOAD.series || {{}})[key] || [];
      if (!rows.length) return;
      const mkt = key.split(':')[0];
      const w = watchedByKey[key];
      const it = itemByKey[key];
      const last = rows[rows.length - 1];
      const prev = rows[rows.length - 2] || last;
      const chg = ((last.close / prev.close) - 1) * 100;

      document.getElementById('chart-title').textContent = `${{(w || it || {{}}).name || key}} (${{key.split(':')[1]}})`;
      document.getElementById('chart-price').textContent = fmtPrice(last.close, mkt);
      const chgEl = document.getElementById('chart-chg');
      chgEl.textContent = `${{chg > 0 ? '+' : ''}}${{chg.toFixed(2)}}%`;
      chgEl.className = `text-xs font-semibold num ${{chgClass(chg)}}`;
      document.getElementById('rsi-live-badge').textContent = `현재 RSI(14): ${{last.rsi14 ?? '-'}}`;

      candleSeries.setData(rows.map(r => ({{ time: r.time, open: r.open, high: r.high, low: r.low, close: r.close }})));
      rsiSeries.setData(rows.filter(r => r.rsi14 !== undefined).map(r => ({{ time: r.time, value: r.rsi14 }})));

      Object.entries(maSeriesMap).forEach(([k, s]) => {{
        s.applyOptions({{ visible: layers.ma }});
        s.setData(rows.filter(r => r[k] !== undefined).map(r => ({{ time: r.time, value: r[k] }})));
      }});

      clearOverlayLines();

      if (layers.tl && w && w.trendlines) {{
        w.trendlines.forEach(tl => {{
          const ls = mainChart.addLineSeries({{
            color: tl.color || '#003566',
            lineWidth: 2,
            lineStyle: tl.style === 'dashed' ? LightweightCharts.LineStyle.Dashed : LightweightCharts.LineStyle.Solid,
            priceLineVisible: false,
            lastValueVisible: true,
            title: tl.label,
          }});
          ls.setData(tl.points || []);
          tlSeriesList.push(ls);
        }});
      }}

      if (layers.lv) {{
        const lv = w ? w.levels : (it ? {{
          buy1_low: it.entry_zone ? it.entry_zone[0] : null,
          buy1_high: it.entry_zone ? it.entry_zone[1] : null,
          stop: it.stop_loss,
          target1: it.target_120,
        }} : null);
        if (lv) {{
          const specs = [
            [lv.buy1_high, '#007f4e', LightweightCharts.LineStyle.Dashed, '1차 매집 상단'],
            [lv.buy1_low, '#007f4e', LightweightCharts.LineStyle.Solid, '1차 매집 하단(500일)'],
            [lv.planb_high, '#005f99', LightweightCharts.LineStyle.Dotted, 'Plan B'],
            [lv.stop, '#c1121f', LightweightCharts.LineStyle.Dashed, '종가 손절선'],
            [lv.target1, '#d9480f', LightweightCharts.LineStyle.Solid, '1차 목표'],
            [lv.target2, '#9a3412', LightweightCharts.LineStyle.Dotted, '2차 목표'],
          ];
          specs.forEach(([price, color, lineStyle, title]) => {{
            if (price) {{
              priceLinesList.push(candleSeries.createPriceLine({{ price, color, lineWidth: 1, lineStyle, axisLabelVisible: true, title }}));
            }}
          }});
        }}
      }}

      mainChart.timeScale().fitContent();
    }}

    function renderReport(key) {{
      const mkt = key.split(':')[0];
      const w = watchedByKey[key];
      const it = itemByKey[key];
      const badge = document.getElementById('report-status-badge');
      const body = document.getElementById('report-body');

      if (w) {{
        badge.textContent = w.status;
        const lv = w.levels;
        const rep = w.report;
        const tlHtml = (w.trendlines || []).map(t => `<div class="flex justify-between text-xs py-1 border-b border-[#f0efef]"><span>${{t.label}} (오늘 기준)</span><span class="font-semibold num">${{fmtPrice(t.today_val, mkt)}}</span></div>`).join('');
        body.innerHTML = `
          <div class="p-3 bg-[#fafafa] hairline-all text-xs leading-relaxed">${{rep.summary}}</div>
          <div>
            <div class="caps-label mb-1.5">40:60 분할 매매 전략표</div>
            <table class="w-full text-xs border-collapse hairline-all">
              <tr class="hairline-b"><td class="py-1.5 px-2.5 text-[#595757] bg-[#fafafa]">1차 매집존 [40%]</td><td class="py-1.5 px-2.5 font-bold num text-[#007f4e]">${{fmtPrice(lv.buy1_low, mkt)}} ~ ${{fmtPrice(lv.buy1_high, mkt)}}</td></tr>
              <tr class="hairline-b"><td class="py-1.5 px-2.5 text-[#595757] bg-[#fafafa]">2차 Plan B [60%]</td><td class="py-1.5 px-2.5 font-bold num text-[#005f99]">${{fmtPrice(lv.planb_low, mkt)}} ~ ${{fmtPrice(lv.planb_high, mkt)}}</td></tr>
              <tr class="hairline-b"><td class="py-1.5 px-2.5 text-[#595757] bg-[#fafafa]">종가 기준 손절선</td><td class="py-1.5 px-2.5 font-bold num text-[#c1121f]">${{fmtPrice(lv.stop, mkt)}}</td></tr>
              <tr><td class="py-1.5 px-2.5 text-[#595757] bg-[#fafafa]">1차 / 2차 목표가</td><td class="py-1.5 px-2.5 font-bold num">${{fmtPrice(lv.target1, mkt)}} / ${{fmtPrice(lv.target2, mkt)}}</td></tr>
            </table>
          </div>
          ${{tlHtml ? `<div><div class="caps-label mb-1">투영 하락빗각 레벨</div>${{tlHtml}}</div>` : ''}}
          <div class="space-y-2.5 text-xs">
            <div><div class="caps-label mb-0.5">기술적 진단</div><p class="m-0 text-[#333]">${{rep.technical}}</p></div>
            <div><div class="caps-label mb-0.5">펀더멘털 체크</div><p class="m-0 text-[#333]">${{rep.fundamental}}</p></div>
            <div><div class="caps-label mb-0.5">핵심 리스크</div><p class="m-0 text-[#333]">${{rep.risk}}</p></div>
            <div class="p-2.5 hairline-all bg-[#f9fbfd]"><div class="caps-label text-[#003566] mb-0.5">Plan A (상방 시나리오)</div><p class="m-0 text-[#222]">${{rep.plan_a}}</p></div>
            <div class="p-2.5 hairline-all bg-[#fdf9f9]"><div class="caps-label text-[#c1121f] mb-0.5">Plan B (하방 시나리오)</div><p class="m-0 text-[#222]">${{rep.plan_b}}</p></div>
          </div>
        `;
      }} else if (it) {{
        badge.textContent = `${{it.setup_type}} · ${{it.total_score}}점`;
        body.innerHTML = `
          <div class="p-3 bg-[#fafafa] hairline-all text-xs leading-relaxed">
            스크리너 자동 진단 종목입니다. 현재가 <strong>${{fmtPrice(it.close, mkt)}}</strong> (${{it.chg_pct > 0 ? '+' : ''}}${{it.chg_pct}}%), RSI(14) <strong>${{it.rsi14}}</strong>, 손익비(R:R) <strong>1:${{it.rr_ratio}}</strong>.
          </div>
          <div>
            <div class="caps-label mb-1.5">자동 산출 대응 기준</div>
            <table class="w-full text-xs border-collapse hairline-all">
              <tr class="hairline-b"><td class="py-1.5 px-2.5 text-[#595757] bg-[#fafafa]">매수 관심 구간</td><td class="py-1.5 px-2.5 font-bold num text-[#007f4e]">${{it.entry_zone ? fmtPrice(it.entry_zone[0], mkt) + ' ~ ' + fmtPrice(it.entry_zone[1], mkt) : '-'}}</td></tr>
              <tr class="hairline-b"><td class="py-1.5 px-2.5 text-[#595757] bg-[#fafafa]">종가 기준 손절선</td><td class="py-1.5 px-2.5 font-bold num text-[#c1121f]">${{fmtPrice(it.stop_loss, mkt)}}</td></tr>
              <tr><td class="py-1.5 px-2.5 text-[#595757] bg-[#fafafa]">1차 목표 (120일선 등)</td><td class="py-1.5 px-2.5 font-bold num">${{fmtPrice(it.target_120, mkt)}}</td></tr>
            </table>
          </div>
          <div class="text-xs text-[#595757] leading-relaxed">
            상세 빗각·펀더멘털 정밀 보고서를 추가하려면 채팅창에서 해당 종목의 정밀 작도를 요청하세요.
          </div>
        `;
      }} else {{
        badge.textContent = '데이터 없음';
        body.innerHTML = '<div class="text-xs text-[#7d7d7d]">선택한 종목의 보고서 데이터가 없습니다.</div>';
      }}
    }}

    function selectStock(key) {{
      if (!((PAYLOAD.series || {{}})[key])) return;
      currentKey = key;
      renderWatchedTabs();
      renderTables();
      renderSelectedChart(key);
      renderReport(key);
      document.getElementById('workspace-section').scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
    }}

    function setMarketFilter(mkt) {{
      marketFilter = mkt;
      document.querySelectorAll('[data-mkt-filter]').forEach(b => b.classList.toggle('active', b.dataset.mktFilter === mkt));
      renderWatchedTabs();
    }}

    function toggleLayer(name) {{
      layers[name] = !layers[name];
      document.getElementById('btn-toggle-' + name).classList.toggle('active', layers[name]);
      if (currentKey) renderSelectedChart(currentKey);
    }}

    function setRangeBars(cnt) {{
      const rows = (PAYLOAD.series || {{}})[currentKey] || [];
      if (!rows.length) return;
      const to = rows.length - 1;
      const from = Math.max(0, rows.length - cnt);
      mainChart.timeScale().setVisibleLogicalRange({{ from, to: to + 12 }});
    }}

    // Boot
    initHeader();
    renderThermometer();
    renderDiff();
    initCharts();
    const defaultKey = (PAYLOAD.watched && PAYLOAD.watched[0] && PAYLOAD.watched[0].key) || Object.keys(PAYLOAD.series || {{}})[0];
    if (defaultKey) selectStock(defaultKey);
  </script>
</body>
</html>
"""
