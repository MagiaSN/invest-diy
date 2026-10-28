/* A-Share National Team ETF Tracker: Chinese / English dictionary.
   Amounts are "亿元 / 亿份" in Chinese and "CNY bn / bn units" in English (converted by kit).
   The disclaimer is not here: the shared /static/site.js adds it to the footer. */
i18n.add({
  zh: {
    'page.title': 'A股国家队宽基ETF数据跟踪',
    'bt.promo': '国家队自己收益如何？跟随国家队交易收益如何？', 'bt.promoLink': '查看跟踪回测 →',

    // section navigation
    'nav.label': '页面目录',
    'nav.cum': '累计净申赎', 'nav.cal': '日历', 'nav.pool': '监控池明细', 'nav.ep': '进出场波段',
    'nav.hold': '官方持仓', 'nav.mon': '月度', 'nav.sm': '单只 ETF', 'nav.ck': '媒体核对', 'nav.about': '关于本页',

    // header
    'k.1d': '最近交易日净申赎',
    'k.5d': '近 5 个交易日',
    'k.20d': '近 20 个交易日',
    'k.20d.sub': '约一个月',
    'k.ytd': '今年以来',
    'k.ytd.sub': '自 1 月 1 日起',
    'k.state': '当前状态',
    'k.floor': '国家队确证减持',
    'k.pool': '监控池 {n} 只合计',
    'k.th': '当日信号阈值 {v}',
    'k.floor.value': '≥ {v}',
    'k.floor.sub': '{y} 年末持有 {base}，至少已减持 {pct}%',
    'link.basis': '查看依据 ↓',
    'take.wave': '截至 {asof}，监控池处于{state}：自 {start} 起出现 {days} 个信号日，累计净申赎 {flow}，同期沪深300 {chg}。',
    'take.contra': '逆势放量申购，符合国家队托底特征。',
    'take.none': '截至 {asof}，没有进行中的进出场波段，最近交易日监控池净申赎 {flow}。',
    'take.floor': '据定期报告，国家队 {date} 在池内持有约 {base}；按份额地板，此后至少已减持 {pct}',
    'take.cap': '，按 {date} 机构持有上限至少已减持 {pct}',
    'take.end': '。',
    'loadError': '数据加载失败，请先运行 {cmd} 生成 data/out/。',

    // cumulative
    'cum.h2': '累计净申赎与沪深300',
    'cum.note': '所选区间内的累计净申赎（自区间首日起算，左轴，亿元）与沪深300 指数（右轴）。色带为进出场波段。',
    'cum.lgCum': '累计净申赎（左轴）', 'cum.lgIdx': '沪深300（右轴）', 'cum.lgIn': '进场波段', 'cum.lgOut': '退出波段',
    'cum.tipCum': '区间累计 {v}', 'cum.tipDay': '当日净申赎 {v}', 'cum.tipIdx': '沪深300 {v}（{r}）',

    // calendar
    'cal.h2': '每日净申赎日历',
    'cal.note': '每格为一个交易日，颜色表示监控池当日合计净申赎（亿元）：红为净申购，绿为净赎回，加框为强进场 / 强退出信号日。悬停查看当日贡献最大的 ETF。',
    'cal.strong': '强信号日',
    'tip.flow': '净申赎 {v}',
    'tip.csi': '沪深300 {v}',
    'tip.signal': '信号：{s}',
    'tip.top': '主要贡献：',

    // pool table (merged)
    'pool.h2': '监控池明细',
    'pool.modeFlow': '资金流',
    'pool.modeHold': '官方持仓与下界',
    'pool.noteFlow': '点击表头排序。规模 = 份额 × 最新收盘价；份额单位亿份，资金流单位亿元。',
    'pool.noteHold': '基准日为最近一期可识别国家队持仓的报告期（目前为 2025-12-31），单位亿份。份额地板：当前总份额低于基准日持有量的差额必为国家队减持；机构上限：国家队持仓不超过最近一期中报的机构投资者合计持有份额。',
    'et.code': '代码', 'et.name': '名称', 'et.family': '指数族', 'et.shares': '份额（亿份）', 'et.aum': '规模（亿元）',
    'et.5d': '近 5 日', 'et.20d': '近 20 日', 'et.ytd': '今年以来',
    'ft.holders': '国家队持有人', 'ft.base': '基准日持有', 'ft.pct': '持有比例', 'ft.shares': '当前总份额',
    'ft.floor': '至少已减持（份额地板）', 'ft.breach': '跌破基准日', 'ft.inst': '中报机构持有', 'ft.cap': '至少已减持（机构上限）',
    'ft.sold': '{v}（{p}%）', 'ft.notBreached': '未跌破', 'ft.unprovable': '无法确认',

    // waves
    'ep.h2': '进出场波段',
    'ep.note': '相隔不超过 2 个交易日的同向信号日合并为一个波段。"沪深300 占比"指沪深300 四大 ETF 在波段合计资金流中的占比；汇金操作历来集中于这四只，占比越高，国家队主导的可能性越大。沪深300 涨跌按波段首日前收盘至末日收盘计算。',
    'ep.start': '开始', 'ep.end': '结束', 'ep.side': '方向', 'ep.days': '信号日',
    'ep.flow': '合计净申赎（亿元）', 'ep.peak': '单日峰值（亿元）', 'ep.hs': '沪深300 占比', 'ep.chg': '沪深300 涨跌',

    // official holdings
    'hold.h2': '官方持仓与减持下界',
    'hold.note': '定期报告披露的国家队持仓是唯一的确证数据，据此可推出两个不依赖阈值的减持下界：<b>份额地板</b>，基准日后 ETF 总份额低于国家队持有量时，差额必为国家队减持（每日更新）；<b>机构上限</b>，国家队持仓不超过中报 / 年报披露的机构投资者合计持有份额。2026 年起汇金不再出现在"单一投资者持有 ≥20%"表中，中报也不再列示前十名持有人，2026 年的持仓只能据此推断。',
    'hold.chartNote': '各期末国家队持仓市值（亿元，按期末收盘价）。最后一根柱为按 2026 年中报机构持有份额推算的上限。',
    'hold.tipDisclosed': '{d} · 定期报告披露 {v}',
    'hold.tipCap': '{d} · 机构持有上限 {v}',
    'hold.tableHint': '逐只 ETF 的持有人、基准日持仓和两个下界，见"监控池明细"表的"官方持仓与下界"视图。',
    'floor.chartNote': '基准日以来按份额地板确证的累计减持（亿元，按当日收盘价）。其他投资者的申购会推高总份额，因此该下界偏保守。',
    'floor.legend': '按份额地板确证的累计减持',
    'floor.tip': '确证减持 ≥ {v}',
    'floor.empty': '基准日之后还没有份额数据',

    // monthly
    'mon.h2': '月度净申赎：按指数族',
    'mon.note': '每月合计净申赎按指数族拆分（亿元）。汇金历来以沪深300 四大 ETF 为主要操作标的。',
    'mon.tip': '{m} · 合计 {v}',

    // small multiples
    'sm.h2': '单只 ETF 份额走势',
    'sm.note': '各 ETF 总份额（亿份），纵轴独立，按规模排序。份额阶跃式升降对应大额申赎。虚线为定期报告披露的国家队持有量，实线低于虚线的部分必为国家队减持。悬停查看当日份额与净申赎。',
    'sm.foot': '{code} · 近20日',
    'sm.tip': '份额 {s}',
    'sm.tipFlow': '当日 {f}',

    // about
    'ck.h2': '与媒体报道核对',
    'ck.note': '2026-10-27 将主要的国家队增减持报道逐项与本页数据核对。媒体多按"全部宽基 / 股票 ETF"或"四大蓝筹 ETF"统计，与本页监控池口径不同，仅比较口径一致的部分。本表为一次性人工核对记录，不随数据更新。',
    'ck.sum': '共 {n} 项：{match} 项一致，{scope} 项口径不同但量级相符，{date} 项日期归属相差一天，{blind} 项为本方法无法观测的二级市场买入。单日 / 区间资金流与报道普遍相差 1%–5%，定期报告中的汇金持仓与报道一致。',
    'ck.date': '日期', 'ck.event': '事件', 'ck.media': '媒体 / Wind', 'ck.ours': '本页数据', 'ck.verdict': '结论', 'ck.src': '来源',
    'ck.v.match': '一致', 'ck.v.scope': '口径不同', 'ck.v.date': '差一天', 'ck.v.blind': '看不到',

    // download link labels (kit.downloadLinks)
    'file.etf_summary': '各 ETF 份额与资金流', 'file.floor': '各 ETF 持仓与减持下界', 'file.pool': '入池筛选结果',
    'file.nt_history': '各期国家队持仓', 'file.floor_daily': '每日确证减持', 'file.nt_holdings': '各 ETF 各期持仓',
    'file.holders': '定期报告持有人明细',

    'a.h2': '关于本页',
    'a.what': '<b>概述</b>：跟踪"国家队"（中央汇金、汇金资管、证金公司、社保基金、国新、诚通等）重仓的 A 股宽基 ETF。根据交易所每日披露的份额变化估算净申赎，识别疑似进场与退出时点；再根据基金定期报告披露的持仓，推算国家队减持规模的下界。',
    'a.src': '<b>数据来源</b>（均为公开信息）：每日份额来自<a href="https://www.sse.com.cn/" target="_blank" rel="noopener">上交所</a>"ETF 规模"与<a href="https://www.szse.cn/market/fund/volume/etf/index.html" target="_blank" rel="noopener">深交所</a>"基金规模"；持有人来自基金定期报告（经<a href="https://fund.eastmoney.com/" target="_blank" rel="noopener">东方财富</a>基金公告获取 PDF 原文）；收盘价与沪深300 指数来自腾讯行情。',
    'a.pool': '<b>监控池</b>：扫描约 40 只宽基 ETF 自 2014 年以来的定期报告，年报前十名持有人中的汇金投资、汇金资管、证金、社保、国新、诚通等计为国家队；季报"单一投资者持有 ≥20%"表不披露名称，按持有份额与年报持有人精确匹配。国家队合计持有比例曾达到 10% 的 ETF 纳入监控池。华夏科创50 与各中证A500 ETF 的前十名持有人中没有国家队，未纳入。',
    'a.flow': '<b>资金流</b>：净申赎 = 当日总份额变化 × 当日收盘价。以收盘价近似净值，宽基 ETF 折溢价通常在 0.1% 以内。份额折算（份额与价格反向跳变，二者可能相隔一天披露，如易方达沪深300 2024-09-20 份额减半、09-23 价格翻倍）当日记为 0。',
    'a.signal': '<b>进出场信号</b>：单日合计净申赎超过前 60 个交易日绝对值中位数的 3 倍，且不低于前一日监控池规模的 0.6%，记为进场 / 退出；超过 6 倍且不低于 1.8% 记为强信号（2024–2025 年约合 100 亿 / 300 亿元）。下限按规模比例而非固定金额设定，因为监控池规模从 2015 年约 1,000 亿元增至 2025 年近 1.9 万亿元。已知事件校验：2015 年救市、2018 年 10 月、2020 年 2 月、2022 年 4 月、2023 年 8 月印花税减半、2024 年 2 月、2025 年 4 月及 2026 年 1 月减持均被识别；2023-10-23 汇金公告增持 ETF 当日池内净申购仅 +24 亿元，未达阈值。相隔不超过 2 个交易日的同向信号合并为波段。',
    'a.bounds': '<b>减持下界</b>：以最近一期可识别国家队持仓的报告期为基准。份额地板：总份额低于基准持有量的差额必为国家队减持（每日更新）；机构上限：国家队持仓不超过中报 / 年报的机构投资者合计持有份额（每半年更新）。2026 年起国家队持仓基本不再披露，这两个下界是目前推断其动向的主要依据。',
    'a.limits': '<b>局限</b>：份额变化只能反映大额申赎，无法识别申赎方。急涨中的大额申购（如 2024 年 9 月下旬）更可能来自机构与散户追涨；逆势放量、集中于沪深300 四大 ETF、尾盘成交放大同时出现时，国家队的可能性最高。定期报告的持有人名单是唯一的事后确认手段。深交所份额数据始于 2016-10-28，此前的深市 ETF（嘉实沪深300、易方达创业板等）未计入；数据接口限流时个别日期可能暂缺，补齐前不计入。',
    'a.checks': '<b>交叉验证</b>：2026 年 10 月与媒体报道、Wind 数据逐项核对，单日 / 区间资金流普遍相差 1%–5%，定期报告中的汇金持仓一致；唯一未能对应的是 2023-10-23 汇金在二级市场的买入。逐项结果见<a href="#checks">与媒体报道核对</a>。',
    'a.backtest': '<b>跟踪回测</b>：国家队在池内 ETF 上的估算收益，以及跟随国家队交易的策略回测（资金加权、分段计算），见<a href="backtest.html">跟踪回测</a>页。',

    // data values
    'v.强进场': '强进场', 'v.进场': '进场', 'v.退出': '退出', 'v.强退出': '强退出', 'v.无信号': '无信号',
    'v.进场中': '进场中', 'v.退出中': '退出中', 'v.观望': '观望',
  },

  en: {
    'page.title': 'A-Share National Team ETF Tracker',
    'bt.promo': 'How has the national team performed, and how would following its trades have done?', 'bt.promoLink': 'See the tracking backtest →',

    'nav.label': 'Page sections',
    'nav.cum': 'Cumulative', 'nav.cal': 'Calendar', 'nav.pool': 'Pool', 'nav.ep': 'Waves',
    'nav.hold': 'Official holdings', 'nav.mon': 'Monthly', 'nav.sm': 'Per ETF', 'nav.ck': 'Press check', 'nav.about': 'About',

    'k.1d': 'Net creation, latest day',
    'k.5d': 'Last 5 trading days',
    'k.20d': 'Last 20 trading days',
    'k.20d.sub': 'About one month',
    'k.ytd': 'Year to date',
    'k.ytd.sub': 'Since 1 January',
    'k.state': 'Current state',
    'k.floor': 'Confirmed national-team selling',
    'k.pool': 'Total of {n} ETFs in the pool',
    'k.th': 'Signal threshold today {v}',
    'k.floor.value': '≥ {v}',
    'k.floor.sub': 'Held {base} at end-{y}; at least {pct}% sold',
    'link.basis': 'See basis ↓',
    'take.wave': 'As of {asof}, the pool is in {state}: {days} signal days since {start}, with net creation of {flow} while the CSI 300 moved {chg}. ',
    'take.contra': 'Buying into a falling market fits the national team\'s support pattern.',
    'take.none': 'As of {asof}, there is no active entry or exit wave; net creation on the latest day was {flow}.',
    'take.floor': 'Periodic reports show the national team held about {base} in these ETFs on {date}; by the share floor, at least {pct} has been sold since',
    'take.cap': ', and by the {date} institutional-holdings cap, at least {pct}',
    'take.end': '.',
    'loadError': 'Data failed to load. Run {cmd} first to generate data/out/.',

    'cum.h2': 'Cumulative net creation vs. CSI 300',
    'cum.note': 'Cumulative net creation over the selected range (from its first day, left axis, CNY bn) and the CSI 300 index (right axis). Shaded bands are entry and exit waves.',
    'cum.lgCum': 'Cumulative net creation (left)', 'cum.lgIdx': 'CSI 300 (right)', 'cum.lgIn': 'Entry wave', 'cum.lgOut': 'Exit wave',
    'cum.tipCum': 'Range cumulative {v}', 'cum.tipDay': 'That day {v}', 'cum.tipIdx': 'CSI 300 {v} ({r})',

    'cal.h2': 'Daily net creation calendar',
    'cal.note': 'One cell per trading day, coloured by the pool\'s total net creation that day (CNY bn): red is net creation, green is net redemption, and outlined cells are strong entry or exit signal days. Hover to see the top contributing ETFs.',
    'cal.strong': 'Strong signal day',
    'tip.flow': 'Net creation {v}',
    'tip.csi': 'CSI 300 {v}',
    'tip.signal': 'Signal: {s}',
    'tip.top': 'Top contributors:',

    'pool.h2': 'Pool details',
    'pool.modeFlow': 'Flows',
    'pool.modeHold': 'Official holdings & bounds',
    'pool.noteFlow': 'Click a header to sort. AUM = units × latest close; units in bn, flows in CNY bn.',
    'pool.noteHold': 'The baseline is the latest report period with identified national-team holdings (currently 2025-12-31); units in bn. Share floor: any shortfall of total units below the baseline holding must have been sold by the national team. Institutional cap: national-team holdings cannot exceed the combined institutional holdings in the latest interim report.',
    'et.code': 'Code', 'et.name': 'Name', 'et.family': 'Index', 'et.shares': 'Units (bn)', 'et.aum': 'AUM (CNY bn)',
    'et.5d': '5-day', 'et.20d': '20-day', 'et.ytd': 'YTD',
    'ft.holders': 'National-team holders', 'ft.base': 'Held at baseline', 'ft.pct': 'Stake', 'ft.shares': 'Units outstanding',
    'ft.floor': 'Sold at least (share floor)', 'ft.breach': 'Floor breached on', 'ft.inst': 'Institutional holdings (interim)', 'ft.cap': 'Sold at least (institutional cap)',
    'ft.sold': '{v} ({p}%)', 'ft.notBreached': 'Not breached', 'ft.unprovable': 'Not provable',

    'ep.h2': 'Entry and exit waves',
    'ep.note': 'Same-direction signal days no more than 2 trading days apart are merged into one wave. "CSI 300 share" is the four large CSI 300 ETFs\' share of the wave\'s total flow; Huijin has historically concentrated on these four, so a higher share makes national-team activity more likely. CSI 300 change runs from the close before the first day to the close of the last day.',
    'ep.start': 'Start', 'ep.end': 'End', 'ep.side': 'Side', 'ep.days': 'Signal days',
    'ep.flow': 'Net creation (CNY bn)', 'ep.peak': 'Peak day (CNY bn)', 'ep.hs': 'CSI 300 share', 'ep.chg': 'CSI 300 change',

    'hold.h2': 'Official holdings and selling lower bounds',
    'hold.note': 'National-team holdings disclosed in fund reports are the only confirmed data. They yield two threshold-free lower bounds on selling. <b>Share floor</b>: once an ETF\'s total units fall below the national team\'s holding, the gap must have been sold by the national team (updated daily). <b>Institutional cap</b>: national-team holdings cannot exceed the combined institutional holdings in interim and annual reports. Since 2026 Huijin no longer appears in the "single investor ≥20%" table and interim reports no longer list the top-10 holders, so 2026 holdings can only be inferred this way.',
    'hold.chartNote': 'National-team holdings at each period end (CNY bn, at period-end close). The last bar is the upper bound implied by institutional holdings in the 2026 interim reports.',
    'hold.tipDisclosed': '{d} · disclosed in reports {v}',
    'hold.tipCap': '{d} · institutional-holdings cap {v}',
    'hold.tableHint': 'Per-ETF holders, baseline holdings and both bounds are in the "Official holdings & bounds" view of the Pool details table.',
    'floor.chartNote': 'Cumulative selling confirmed by the share floor since the baseline date (CNY bn, at daily close). Creations by other investors push total units up, so this bound is conservative.',
    'floor.legend': 'Cumulative selling confirmed by the share floor',
    'floor.tip': 'Confirmed selling ≥ {v}',
    'floor.empty': 'No share data after the baseline date yet',

    'mon.h2': 'Monthly net creation by index family',
    'mon.note': 'Monthly net creation split by index family (CNY bn). Huijin has historically traded mainly through the four large CSI 300 ETFs.',
    'mon.tip': '{m} · total {v}',

    'sm.h2': 'Units outstanding per ETF',
    'sm.note': 'Total units of each ETF (bn units), each on its own scale, sorted by AUM. Step changes mark large creations or redemptions. The dashed line is the national team\'s disclosed holding; any part of the solid line below it must reflect national-team selling. Hover for that day\'s units and net creation.',
    'sm.foot': '{code} · 20-day',
    'sm.tip': 'Units {s}',
    'sm.tipFlow': 'That day {f}',

    'ck.h2': 'Checked against press reports',
    'ck.note': 'On 2026-10-27, major reports of national-team buying and selling were checked item by item against this page\'s data. The press often counts all broad-based or equity ETFs, or the four blue-chip ETFs, which differs from this page\'s pool, so only like-for-like figures are compared. This is a one-off manual record and is not updated with the data.',
    'ck.sum': '{n} items: {match} match, {scope} differ in scope but agree in size, {date} is dated one day apart, and {blind} is a secondary-market purchase this method cannot see. Daily and period flows are typically within 1–5% of the reports, and Huijin holdings in periodic reports match the press.',
    'ck.date': 'Date', 'ck.event': 'Event', 'ck.media': 'Press / Wind', 'ck.ours': 'This page', 'ck.verdict': 'Verdict', 'ck.src': 'Source',
    'ck.v.match': 'Match', 'ck.v.scope': 'Different scope', 'ck.v.date': 'One day apart', 'ck.v.blind': 'Not visible',

    'file.etf_summary': 'Units and flows per ETF', 'file.floor': 'Holdings and selling bounds per ETF', 'file.pool': 'Pool screening',
    'file.nt_history': 'National-team holdings by period', 'file.floor_daily': 'Daily confirmed selling', 'file.nt_holdings': 'Holdings per ETF and period',
    'file.holders': 'Holders in fund reports',

    'a.h2': 'About this page',
    'a.what': '<b>Overview</b>: this page tracks A-share broad-based ETFs heavily held by the "national team" (Central Huijin, Huijin Asset Management, China Securities Finance, the social security fund, China Guoxin, China Chengtong and others). Daily unit changes disclosed by the exchanges are used to estimate net creations and identify likely entry and exit dates; holdings disclosed in fund periodic reports give lower bounds on how much the national team has sold.',
    'a.src': '<b>Data sources</b> (all public): daily units from the <a href="https://www.sse.com.cn/" target="_blank" rel="noopener">Shanghai</a> ("ETF size") and <a href="https://www.szse.cn/market/fund/volume/etf/index.html" target="_blank" rel="noopener">Shenzhen</a> ("fund size") exchanges; holders from fund periodic reports (original PDFs via <a href="https://fund.eastmoney.com/" target="_blank" rel="noopener">Eastmoney</a> fund announcements); closing prices and the CSI 300 index from Tencent quotes.',
    'a.pool': '<b>Pool construction</b>: periodic reports since 2014 for about 40 broad-based ETFs are scanned. Top-10 holders named Central Huijin, Huijin Asset Management, China Securities Finance, the social security fund, China Guoxin, China Chengtong and similar count as the national team. Quarterly "single investor ≥20%" tables carry no names, so rows are matched to annual-report holders by exact unit counts. ETFs in which the national team ever held 10% or more join the pool. ChinaAMC STAR 50 and the CSI A500 ETFs have no national-team holders and are excluded.',
    'a.flow': '<b>Flow calculation</b>: net creation = change in total units × that day\'s close. The close approximates NAV; broad-based ETFs usually trade within 0.1% of NAV. On unit splits (units and price jumping in opposite directions, possibly disclosed a day apart, as when E Fund CSI 300 halved its units on 2024-09-20 and its price doubled on 09-23) the day is set to zero.',
    'a.signal': '<b>Entry and exit signals</b>: a day whose total net creation exceeds 3× the median absolute value of the previous 60 trading days, and is at least 0.6% of the previous day\'s pool AUM, is an entry or exit; above 6× and at least 1.8% it is strong (roughly CNY 10bn / 30bn in 2024–2025). The minimum scales with pool size rather than being a fixed amount because the pool grew from about CNY 100bn in 2015 to nearly CNY 1.9tn in 2025. Checked against known events: the 2015 rescue, October 2018, February 2020, April 2022, the August 2023 stamp-duty cut, February 2024, April 2025 and the January 2026 sell-off are all detected; on 2023-10-23, when Huijin announced ETF purchases, the pool saw only +CNY 2.4bn, below the threshold. Same-direction signals no more than 2 trading days apart form a wave.',
    'a.bounds': '<b>Selling lower bounds</b>: the baseline is the latest report period with identified national-team holdings. Share floor: any shortfall of total units below the baseline holding must have been sold by the national team (daily). Institutional cap: national-team holdings cannot exceed the combined institutional holdings in interim and annual reports (half-yearly). National-team holdings have been largely undisclosed since 2026, so these bounds are now the main basis for inferring its moves.',
    'a.limits': '<b>Limitations</b>: unit changes show that large creations or redemptions happened, not who made them. Large creations during sharp rallies (such as late September 2024) more likely come from institutions and retail investors chasing the move. National-team buying is most likely when buying into a falling market, concentration in the four large CSI 300 ETFs and heavy trading near the close coincide. Holder lists in periodic reports are the only after-the-fact confirmation. Shenzhen unit data starts on 2016-10-28, so Shenzhen ETFs (Harvest CSI 300, E Fund ChiNext and others) are excluded before then; when data sources are rate-limited, some dates may be missing until filled.',
    'a.checks': '<b>Cross-checks</b>: checked item by item against press reports and Wind data in October 2026; daily and period flows are typically within 1–5%, and Huijin holdings in periodic reports match. The only mismatch is Huijin\'s secondary-market buying on 2023-10-23. See <a href="#checks">Checked against press reports</a> for each item.',
    'a.backtest': '<b>Tracking backtest</b>: the national team\'s estimated return on the pool ETFs and backtests of strategies that follow its trades (money-weighted, by period) are on the <a href="backtest.html">tracking backtest</a> page.',

    'v.强进场': 'Strong entry', 'v.进场': 'Entry', 'v.退出': 'Exit', 'v.强退出': 'Strong exit', 'v.无信号': 'No signal',
    'v.进场中': 'an entry wave', 'v.退出中': 'an exit wave', 'v.观望': 'no wave',
    'vs.进场中': 'Entry wave', 'vs.退出中': 'Exit wave', 'vs.观望': 'No wave',

    'f.沪深300': 'CSI 300', 'f.上证50/180': 'SSE 50/180', 'f.中证500': 'CSI 500', 'f.中证1000': 'CSI 1000',
    'f.创业板': 'ChiNext', 'f.科创50': 'STAR 50', 'f.中证A500': 'CSI A500', 'f.其他宽基': 'Other broad',
    'h.汇金投资': 'Central Huijin', 'h.汇金资管': 'Huijin AM', 'h.证金公司': 'CSF', 'h.社保基金': 'NSSF',
    'h.国新': 'China Guoxin', 'h.诚通': 'China Chengtong', 'h.梧桐树': 'Wutongshu',
  },
});
