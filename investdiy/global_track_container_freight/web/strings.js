/* Global Container Freight Tracker: Chinese / English dictionary.
   Lane names come from latest.csv (name / name_en); index values are in points in both languages.
   The disclaimer is not here: the shared /static/site.js adds it to the footer. */
i18n.add({
  zh: {
    'page.title': '全球集装箱运价数据跟踪',

    // section navigation
    'nav.label': '页面目录',
    'nav.comp': '综合指数', 'nav.lanes': 'CCFI 分航线', 'nav.scfis': 'SCFIS', 'nav.about': '关于本页',

    // header
    'k.scfi': 'SCFI 综合指数', 'k.ccfi': 'CCFI 综合指数', 'k.scfisEu': 'SCFIS 欧洲航线', 'k.scfisUs': 'SCFIS 美西航线',
    'k.sub': '{d} · 较上期 {c}',
    'k.subNone': '{d}',
    'take.now': '截至 {d}，SCFI 报 {scfi} 点，较上期 {c1}；CCFI 报 {ccfi} 点，较上期 {c2}。',
    'take.scfis': '{d} 发布的 SCFIS 欧洲航线报 {eu} 点（{c3}），美西航线报 {us} 点（{c4}）。',
    'take.cover': '自 {since} 起每周采集官方页面；此前的数据来自网页存档快照，只覆盖部分周次（CCFI 综合指数共 {n} 期），图中以圆点标出。',
    'loadError': '数据加载失败，请先运行 {cmd} 生成 data/out/。',
    'pts': '{v} 点',

    // charts
    'comp.h2': '综合指数：SCFI 与 CCFI',
    'comp.note': 'SCFI 只反映上海港出口的即期运价，对市场变化更敏感；CCFI 覆盖中国 10 个主要港口并包含长约运价，走势更平滑。两者基期不同，点数不可直接比较，只看方向与幅度。相隔超过 17 天的两期之间不连线。',
    'lanes.h2': 'CCFI 分航线',
    'lanes.note': '点击下方按钮或表格行选择航线（最多 8 条）。各航线基期均为 1998 年 1 月 1 日 = 1000 点，可直接比较相对涨跌。',
    'lanes.pick': '选择航线',
    'scfis.h2': 'SCFIS 结算运价指数',
    'scfis.note': '上海港出口集装箱即期成交运价，每周一发布，反映上一周已离港船舶的实际结算价格；欧洲航线是上期所集运指数（欧线）期货的结算标的。基期 2020 年 6 月 1 日 = 1000 点。',
    'lg.scfi': 'SCFI 综合', 'lg.ccfi': 'CCFI 综合', 'lg.eu': '欧洲航线', 'lg.us': '美西航线',
    'tip.archive': '（存档）',

    // table
    't.lane': '航线', 't.date': '日期', 't.value': '最新（点）', 't.1w': '较上期', 't.4w': '近 4 周', 't.52w': '近 52 周', 't.n': '期数',
    't.none': '—',

    // download links
    'file.history': '全部数据', 'file.latest': '最新值',

    // about
    'a.h2': '关于本页',
    'a.what': '<b>概述</b>：跟踪上海航运交易所发布的三个集装箱运价指数。<b>CCFI</b>（中国出口集装箱运价指数）反映中国 10 个主要港口出口至 12 条航线的即期与长约运价，基期 1998 年 1 月 1 日 = 1000 点；<b>SCFI</b>（上海出口集装箱运价指数）反映上海港出口的即期运价，基期 2009 年 10 月 16 日 = 1000 点，二者每周五发布。<b>SCFIS</b>（上海出口集装箱结算运价指数）反映即期成交运价，每周一发布，含欧洲与美西航线。',
    'a.src': '<b>数据来源</b>：<a href="https://www.sse.net.cn/index/singleIndex?indexType=ccfi" target="_blank" rel="noopener">上海航运交易所</a>的公开指数页面，每次更新读取最近两期的 CCFI（综合及 12 条航线）与 SCFI 综合指数，以及 <a href="https://www.sse.net.cn/index/scfisTrace" target="_blank" rel="noopener">SCFIS 最近四期</a>。更早的数据来自 <a href="https://web.archive.org/" target="_blank" rel="noopener">Internet Archive</a> 保存的同一批页面快照，用同一解析程序读取。',
    'a.history': '<b>历史数据</b>：上海航运交易所的单期历史查询与多期查询需要付费账号，公开页面只显示最近几期，因此历史随每周更新逐步积累。网页存档自 2016 年起约有数十个快照，每个快照含两期（SCFIS 一至四期），只能提供零散的历史参照；存档与官方页面同一期的数值不一致时以官方页面为准。',
    'a.calc': '<b>计算</b>：涨跌幅相对同一序列约 1、4、52 周前的一期计算（允许相差 3 天，以适应节假日提前或推迟发布）；找不到相应的一期时留空。',
    'a.limits': '<b>局限</b>：SCFI 分航线运价（美元 / 箱）在公开页面上不显示，本页未收录。春节等假期期间可能停发一期。存档快照的时间不均匀，2020 年等年份几乎没有数据，不能据此判断这些年份的高点和低点。官方页面改版可能导致解析失败，届时数据会停止更新。',
  },
  en: {
    'page.title': 'Global Container Freight Tracker',

    'nav.label': 'Page sections',
    'nav.comp': 'Composite', 'nav.lanes': 'CCFI lanes', 'nav.scfis': 'SCFIS', 'nav.about': 'About',

    'k.scfi': 'SCFI composite', 'k.ccfi': 'CCFI composite', 'k.scfisEu': 'SCFIS Europe', 'k.scfisUs': 'SCFIS US West Coast',
    'k.sub': '{d} · {c} w/w',
    'k.subNone': '{d}',
    'take.now': 'As of {d}, the SCFI stands at {scfi}, {c1} on the previous period, and the CCFI at {ccfi}, {c2}.',
    'take.scfis': 'The SCFIS published on {d} is {eu} for Europe ({c3}) and {us} for the US West Coast ({c4}).',
    'take.cover': 'Official pages have been collected weekly since {since}. Earlier data comes from web archive snapshots and covers only some weeks ({n} periods of the CCFI composite); those points are shown as dots.',
    'loadError': 'Failed to load data. Run {cmd} first to generate data/out/.',
    'pts': '{v}',

    'comp.h2': 'Composite indices: SCFI and CCFI',
    'comp.note': 'The SCFI covers spot rates out of Shanghai only and reacts faster; the CCFI covers 10 major Chinese ports and includes contract rates, so it moves more smoothly. Their bases differ, so compare direction and size of moves, not levels. Periods more than 17 days apart are not joined by a line.',
    'lanes.h2': 'CCFI by trade lane',
    'lanes.note': 'Pick lanes with the buttons below or by clicking table rows (up to 8). Every lane is based at 1000 on 1 January 1998, so relative moves are comparable.',
    'lanes.pick': 'Pick lanes',
    'scfis.h2': 'SCFIS settlement index',
    'scfis.note': 'Spot rates actually settled for containers shipped from Shanghai, published on Mondays for vessels that departed the previous week. The Europe lane is the settlement basis of the Shanghai International Energy Exchange container freight (Europe) futures. Base: 1 June 2020 = 1000.',
    'lg.scfi': 'SCFI composite', 'lg.ccfi': 'CCFI composite', 'lg.eu': 'Europe', 'lg.us': 'US West Coast',
    'tip.archive': ' (archive)',

    't.lane': 'Lane', 't.date': 'Date', 't.value': 'Latest (points)', 't.1w': 'W/w', 't.4w': '4 weeks', 't.52w': '52 weeks', 't.n': 'Periods',
    't.none': '—',

    'file.history': 'all data', 'file.latest': 'latest values',

    'a.h2': 'About this page',
    'a.what': '<b>Overview</b>: this page tracks three container freight indices published by the Shanghai Shipping Exchange (SSE). The <b>CCFI</b> (China Containerized Freight Index) covers spot and contract rates from 10 major Chinese ports on 12 trade lanes, based at 1000 on 1 January 1998. The <b>SCFI</b> (Shanghai Containerized Freight Index) covers spot rates out of Shanghai, based at 1000 on 16 October 2009. Both are published on Fridays. The <b>SCFIS</b> (settlement index) tracks settled spot rates for Europe and the US West Coast and is published on Mondays.',
    'a.src': '<b>Data sources</b>: the public index pages of the <a href="https://www.sse.net.cn/index/singleIndex?indexType=ccfi" target="_blank" rel="noopener">Shanghai Shipping Exchange</a>. Each update reads the last two periods of the CCFI (composite and 12 lanes) and the SCFI composite, and the <a href="https://www.sse.net.cn/index/scfisTrace" target="_blank" rel="noopener">last four periods of the SCFIS</a>. Earlier data comes from snapshots of the same pages kept by the <a href="https://web.archive.org/" target="_blank" rel="noopener">Internet Archive</a>, read by the same parser.',
    'a.history': '<b>History</b>: the SSE\'s historical and multi-period queries require a paid account and its public pages show only the latest periods, so history builds up with each weekly update. The web archive holds a few dozen snapshots per page since 2016, each with two periods (one to four for the SCFIS), which give only scattered historical reference points. Where an archived value differs from the official page for the same period, the official value is kept.',
    'a.calc': '<b>Calculation</b>: changes are measured against the period of the same series about 1, 4 and 52 weeks earlier (within 3 days, since holidays move publication dates); when there is no such period the change is left blank.',
    'a.limits': '<b>Limitations</b>: SCFI lane rates (USD per box) are not shown on the public pages and are not included. A period may be skipped around holidays such as the Spring Festival. Archive snapshots are unevenly spread and some years (such as 2020) have almost none, so highs and lows in those years cannot be read from this page. A redesign of the official pages may break parsing, in which case the data stops updating.',
  },
});
