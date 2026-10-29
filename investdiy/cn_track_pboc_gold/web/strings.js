/* China PBoC Gold Reserves Tracker: Chinese / English dictionary.
   Volumes are "吨 / 万盎司" in Chinese and "t / m oz" in English, values "亿美元" and "USD bn" (converted in app.js).
   The disclaimer is not here: the shared /static/site.js adds it to the footer. */
i18n.add({
  zh: {
    'page.title': '中国央行黄金储备数据跟踪',

    // section navigation
    'nav.label': '页面目录',
    'nav.hold': '持有量', 'nav.chg': '每月增减', 'nav.year': '年度', 'nav.value': '价值与占比', 'nav.ph': '增持阶段', 'nav.about': '关于本页',

    // header
    'k.hold': '黄金储备', 'k.hold.sub': '{oz} · {m} 末',
    'k.chg': '当月增减', 'k.chg.sub': '{oz}，较 {m} 末',
    'k.streak': '连续增持', 'k.streak.value': '{n} 个月', 'k.streak.sub': '自 {m} 起', 'k.streak.none': '本月未增持',
    'k.ytd': '今年以来', 'k.ytd.sub': '近 12 个月 {t}',
    'k.value': '黄金储备价值', 'k.value.sub': '较上月 {c} · 占储备 {s}',
    'k.price': '隐含金价（每盎司）', 'k.price.sub': '较上月 {c}（储备价值 ÷ 盎司数）',
    'take.now': '截至 {m} 末，中国人民银行黄金储备 {oz}（约 {t}），',
    'take.up': '较上月增加 {chg}，已连续 {n} 个月增持（自 {start} 起）；',
    'take.flat': '与上月持平，暂停增持；',
    'take.down': '较上月减少 {chg}；',
    'take.ytd': '今年以来累计增持 {ytd}。按月末估值，黄金储备价值 {usd}，占官方储备资产的 {share}。',
    'take.src': '最新数据来自国家外汇管理局 {d} 发布的官方储备资产表，通常每月 7 日前后公布上月末数据。',
    'take.srcImf': '最新数据来自 IMF International Liquidity 数据库（国家外汇管理局数据暂时无法获取）。',
    'loadError': '数据加载失败，请先运行 {cmd} 生成 data/out/。',

    // holdings
    'hold.h2': '黄金储备持有量',
    'hold.note': '各月末官方黄金储备（吨）。2015 年 7 月之前只有零星披露，阶梯式跳升是多年累计增持的一次性公布；此后按月公布。色带为 2015 年以来的月度增持阶段。',
    'hold.lgLine': '黄金储备（吨）', 'hold.lgBand': '月度增持阶段',
    'tip.hold': '持有 {t} · {oz}', 'tip.chg': '较上期 {t}（{oz}）', 'tip.src.imf': '来源：IMF', 'tip.src.safe': '来源：国家外汇管理局',

    // monthly changes
    'chg.h2': '每月增减',
    'chg.note': '每月末较上月末的变化（吨），红为增持，绿为减少。2015-06 之前的柱为一次性披露，不代表当月买入；1980 年之前 IMF 为季度数据。',

    // annual
    'year.h2': '年度增减',
    'year.note': '各年净增减（吨）。2015 年包含 6 月一次性披露的 604 吨；当年未结束时柱色较浅。悬停查看增持月数和年末持有量。',
    'tip.year': '{y} 年{partial}', 'tip.partial': '（至 {m}）', 'tip.yearChg': '净增减 {t}', 'tip.yearMonths': '增持月数 {n}', 'tip.yearEnd': '年末持有 {t}',

    // value and share
    'val.h2': '储备价值与黄金占比',
    'val.note': '2015 年 6 月起黄金按市价估值，此前按历史成本入账，因此只展示 2015-06 以来的数据。价值随金价波动，与持有量的变化方向不一定一致。',
    'val.usd': '黄金储备价值（亿美元）',
    'val.share': '黄金占官方储备资产的比例（%）',
    'tip.usd': '价值 {v}', 'tip.price': '隐含金价 {p}', 'tip.share': '占储备 {s}', 'tip.total': '官方储备资产 {v}',

    // phases
    'ph.h2': '增持阶段与历次披露',
    'ph.note': '2015-07 起按月计：连续增持的月份合为一个阶段，中间单月持平不打断。估算金额 = Σ 当月增量 × 当月隐含金价，仅为粗略估计。2015-07 之前的行为一次性披露的累计增量。',
    'ph.kind': '类型', 'ph.start': '开始', 'ph.end': '结束', 'ph.months': '跨度（月）', 'ph.addMonths': '增持月数',
    'ph.added': '增减（吨）', 'ph.addedOz': '增减（万盎司）', 'ph.endT': '期末持有（吨）', 'ph.cost': '估算金额（亿美元）', 'ph.avg': '平均隐含金价（美元/盎司）',
    'ph.ongoing': '进行中',
    'v.buying': '月度增持', 'v.disclosure': '一次性披露', 'v.decrease': '减少',

    // downloads
    'file.monthly': '月度数据', 'file.annual': '年度增减', 'file.phases': '增持阶段', 'file.compare': 'IMF 与外汇局逐月核对',

    // about
    'a.h2': '关于本页',
    'a.what': '<b>概述</b>：跟踪中国人民银行持有的官方黄金储备：月末持有量（吨 / 万盎司）、每月增减、连续增持月数与增持阶段，以及按月末估值计算的黄金储备价值和占官方储备资产的比例。',
    'a.src': '<b>数据来源</b>（均为公开信息）：2018 年以来来自<a href="https://www.safe.gov.cn/safe/whcb/index.html" target="_blank" rel="noopener">国家外汇管理局</a>"官方储备资产"月度表（含黄金万盎司数与美元价值，每月 7 日前后公布）；更早的历史来自<a href="https://data.imf.org/" target="_blank" rel="noopener">国际货币基金组织</a> International Liquidity 数据库（1977 年末起，1980 年之前为季度数据），它比官方发布晚约 3 个月。同一数据也见于<a href="http://www.pbc.gov.cn/diaochatongjisi/116219/116319/index.html" target="_blank" rel="noopener">中国人民银行</a>"黄金和外汇储备"统计表和<a href="https://www.gold.org/goldhub/data/gold-reserves-by-country" target="_blank" rel="noopener">世界黄金协会</a>各国央行黄金储备表。',
    'a.merge': '<b>合并</b>：两个来源都有的月份取外汇局数值，其余月份取 IMF 数值。',
    'a.check': '<b>交叉验证</b>：{from} 至 {to} 共 {n} 个月两个来源都有数据，黄金盎司数与美元价值{result}。',
    'a.checkOk': '逐月一致（差异在舍入范围内）',
    'a.checkBad': '有 {k} 个月不一致，见下载的核对表',
    'a.calc': '<b>计算</b>：1 吨 = 32,150.7466 金衡盎司。外汇局按万盎司取整公布，换算成吨约有 ±0.2 吨的舍入误差。隐含金价 = 黄金储备价值 ÷ 盎司数，反映月末估值所用金价，与伦敦金价接近但不完全相同。2015 年 6 月之前黄金按历史成本入账（2009–2015 年约 290 美元/盎司），因此价值、占比和隐含金价只从 2015-06 起计算。',
    'a.phase': '<b>增持阶段</b>：2015-07 起连续增持的月份合为一个阶段，中间单月持平（如 2016-05）不打断，连续两个月持平或出现减少即结束；"连续增持"指标严格按逐月计算，与媒体口径一致。2015-07 之前只有零星披露：2001-12（+340 万盎司）、2002-12（+321 万盎司）、2009-04（公布 2003 年以来累计增持 454 吨）、2015-06（2015-07-17 公布 2009 年以来累计增持 604 吨），这些增量是多年累计后的一次性公布，不能视为当月买入。',
    'a.limits': '<b>局限</b>：官方数据只反映计入官方储备资产的黄金。部分市场机构根据进口等数据估计央行另有未公布的买入，本页只使用官方数据，无法验证这类估计。月末数据看不出月内的买入时点和价格，估算金额只是近似值。2002 年 IMF 数据中 1,608 / 1,610 万盎司的来回变化为原始数据的舍入差异，未列入披露表。',
  },
  en: {
    'page.title': 'China PBoC Gold Reserves Tracker',

    'nav.label': 'Sections',
    'nav.hold': 'Holdings', 'nav.chg': 'Monthly changes', 'nav.year': 'By year', 'nav.value': 'Value and share', 'nav.ph': 'Buying phases', 'nav.about': 'About',

    'k.hold': 'Gold reserves', 'k.hold.sub': '{oz} · end of {m}',
    'k.chg': 'Change this month', 'k.chg.sub': '{oz} vs end of {m}',
    'k.streak': 'Buying streak', 'k.streak.value': '{n} months', 'k.streak.sub': 'since {m}', 'k.streak.none': 'no addition this month',
    'k.ytd': 'Year to date', 'k.ytd.sub': 'last 12 months {t}',
    'k.value': 'Value of gold reserves', 'k.value.sub': '{c} m/m · {s} of reserves',
    'k.price': 'Implied gold price (per oz)', 'k.price.sub': '{c} m/m (value ÷ ounces)',
    'take.now': 'At the end of {m}, the People\'s Bank of China held {oz} of gold (about {t}), ',
    'take.up': 'up {chg} from the previous month, making {n} straight months of additions (since {start}); ',
    'take.flat': 'unchanged from the previous month, a pause in buying; ',
    'take.down': 'down {chg} from the previous month; ',
    'take.ytd': 'it has added {ytd} so far this year. At month-end valuation the gold is worth {usd}, {share} of official reserve assets.',
    'take.src': 'The latest figures come from the official reserve assets table published by SAFE on {d}; SAFE publishes each month-end around the 7th of the next month.',
    'take.srcImf': 'The latest figures come from the IMF International Liquidity database (SAFE data could not be fetched).',
    'loadError': 'Data failed to load. Run {cmd} first to generate data/out/.',

    'hold.h2': 'Gold holdings',
    'hold.note': 'Official gold reserves at each month-end (tonnes). Before July 2015 holdings were disclosed only occasionally, so each step is a one-off disclosure of years of buying; monthly figures start in July 2015. Bands mark the monthly buying phases since 2015.',
    'hold.lgLine': 'Gold reserves (t)', 'hold.lgBand': 'Monthly buying phase',
    'tip.hold': 'Holding {t} · {oz}', 'tip.chg': 'Change {t} ({oz})', 'tip.src.imf': 'Source: IMF', 'tip.src.safe': 'Source: SAFE',

    'chg.h2': 'Monthly changes',
    'chg.note': 'Change from the previous month-end (tonnes); red is an addition, green a decrease. Bars before 2015-06 are one-off disclosures, not that month\'s purchases; IMF data is quarterly before 1980.',

    'year.h2': 'Changes by year',
    'year.note': 'Net change per year (tonnes). 2015 includes the 604 t disclosed in June; the current, incomplete year is drawn lighter. Hover for the number of months with additions and the year-end holding.',
    'tip.year': '{y}{partial}', 'tip.partial': ' (to {m})', 'tip.yearChg': 'Net change {t}', 'tip.yearMonths': 'Months with additions {n}', 'tip.yearEnd': 'Year-end holding {t}',

    'val.h2': 'Value and share of reserves',
    'val.note': 'Gold has been valued at market prices since June 2015 and at historical cost before, so only data from 2015-06 is shown. The value moves with the gold price and need not follow the holdings.',
    'val.usd': 'Value of gold reserves (USD bn)',
    'val.share': 'Gold as a share of official reserve assets (%)',
    'tip.usd': 'Value {v}', 'tip.price': 'Implied price {p}', 'tip.share': 'Share of reserves {s}', 'tip.total': 'Official reserve assets {v}',

    'ph.h2': 'Buying phases and disclosures',
    'ph.note': 'Monthly from 2015-07: consecutive months with additions form a phase, and a single unchanged month does not end it. Estimated amount = Σ monthly addition × that month\'s implied price, a rough estimate. Rows before 2015-07 are one-off disclosures of accumulated additions.',
    'ph.kind': 'Type', 'ph.start': 'Start', 'ph.end': 'End', 'ph.months': 'Span (months)', 'ph.addMonths': 'Months with additions',
    'ph.added': 'Change (t)', 'ph.addedOz': 'Change (m oz)', 'ph.endT': 'Holding at end (t)', 'ph.cost': 'Est. amount (USD bn)', 'ph.avg': 'Avg implied price (USD/oz)',
    'ph.ongoing': 'ongoing',
    'v.buying': 'Monthly buying', 'v.disclosure': 'One-off disclosure', 'v.decrease': 'Decrease',

    'file.monthly': 'Monthly data', 'file.annual': 'Changes by year', 'file.phases': 'Buying phases', 'file.compare': 'IMF vs SAFE by month',

    'a.h2': 'About this page',
    'a.what': '<b>Overview</b>: this page tracks the official gold reserves of the People\'s Bank of China: month-end holdings (tonnes / ounces), monthly changes, the buying streak and buying phases, and the value of the gold at month-end valuation and its share of official reserve assets.',
    'a.src': '<b>Data sources</b> (all public): from 2018, the monthly official reserve assets table of the <a href="https://www.safe.gov.cn/safe/whcb/index.html" target="_blank" rel="noopener">State Administration of Foreign Exchange</a> (SAFE), with the gold volume in 10,000 ounces and its USD value, published around the 7th of each month; earlier history from the <a href="https://data.imf.org/" target="_blank" rel="noopener">IMF</a> International Liquidity database (from end-1977, quarterly before 1980), which trails the official release by about three months. The same figures appear in the <a href="http://www.pbc.gov.cn/diaochatongjisi/116219/116319/index.html" target="_blank" rel="noopener">People\'s Bank of China</a> "gold and foreign exchange reserves" table and the <a href="https://www.gold.org/goldhub/data/gold-reserves-by-country" target="_blank" rel="noopener">World Gold Council</a> table of central bank gold reserves.',
    'a.merge': '<b>Merging</b>: months covered by both sources use SAFE\'s figures; the other months use the IMF\'s.',
    'a.check': '<b>Cross-check</b>: both sources cover the {n} months from {from} to {to}; their gold volumes and USD values {result}.',
    'a.checkOk': 'agree in every month (within rounding)',
    'a.checkBad': 'differ in {k} months, see the downloadable comparison',
    'a.calc': '<b>Calculation</b>: 1 tonne = 32,150.7466 troy ounces. SAFE publishes whole 10,000s of ounces, so tonnes carry a rounding error of about ±0.2 t. Implied price = value of gold reserves ÷ ounces, the price used for the month-end valuation; it is close to, but not exactly, the London price. Until May 2015 gold was carried at historical cost (about USD 290/oz in 2009–2015), so value, share and implied price are computed only from 2015-06.',
    'a.phase': '<b>Buying phases</b>: from 2015-07, consecutive months with additions form a phase; a single unchanged month (such as 2016-05) does not end it, two unchanged months or a decrease do. The buying streak is counted strictly month by month, as the press counts it. Before 2015-07 there were only occasional disclosures: 2001-12 (+3.40m oz), 2002-12 (+3.21m oz), 2009-04 (454 t added since 2003) and 2015-06 (604 t added since 2009, announced on 2015-07-17). These were accumulated over years and published at once, not purchases made in those months.',
    'a.limits': '<b>Limitations</b>: the official data covers only gold counted in official reserve assets. Some market analysts estimate further, undisclosed central-bank buying from import and other data; this page uses only official figures and cannot verify such estimates. Month-end figures do not show when within the month gold was bought or at what price, so the estimated amounts are approximate. The back-and-forth between 16.08m and 16.10m oz in the IMF data for 2002 is rounding in the source and is left out of the disclosure table.',
  },
});
