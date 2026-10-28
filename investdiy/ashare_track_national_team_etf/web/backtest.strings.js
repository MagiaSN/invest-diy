/* Tracking backtest page: Chinese / English dictionary (loaded with strings.js, reusing page.title, nav.label etc.).
   The 2024 split matches SPLIT in backtest.py; change both together. */
i18n.add({
  zh: {
    'bt.title': '国家队收益与跟踪回测',
    'bt.crumb': '跟踪回测',
    'bt.nav.sum': '收益率', 'bt.nav.pnl': '盈亏与持仓', 'bt.nav.year': '逐年', 'bt.nav.ev': '信号之后', 'bt.nav.about': '关于回测',

    'bt.name.nt': '国家队实际', 'bt.name.mr': '次日镜像', 'bt.name.bench': '沪深300全收益指数',
    'bt.p.all': '全区间', 'bt.p.pre': '2015–2023', 'bt.p.post': '2024 至今',

    'bt.take.nt': '国家队实际（估算）的资金加权年化：全区间 {all}，2015–2023 年 {pre}，2024 年至今 {post}；同期沪深300全收益指数分别为 {ball}、{bpre}、{bpost}。',
    'bt.take.mr': '「次日镜像」（每晚估计国家队仓位、次日收盘跟上）：全区间 {all}，2015–2023 年 {pre}，2024 年至今 {post}。',
    'bt.take.read': '2024 年以前国家队池内持仓仅数百亿元，收益接近零、跑输指数；2024 年起持仓扩大至上万亿元，择时收益显著跑赢指数。',

    'bt.sum.h2': '收益率对比',
    'bt.sum.note': '收益率均按资金加权（IRR）计算：每笔买卖按发生时点计入，持仓越大的时期权重越高，因此能反映低买高卖的择时效果；时间加权收益假设始终满仓，无法反映这一点。资金加权的缺点是结果由持仓大的年份主导，而国家队池内持仓在 2024 年前后相差数十倍，因此分段计算。各段期初持仓视为期初投入，期末持仓视为期末收回。基准为沪深300全收益指数（分红再投资、不扣费用，即沪深300 ETF 跟踪的指数），视为一次性买入持有，其资金加权收益即普通年化收益。',
    'bt.sum.acct': '账户', 'bt.sum.irr': '资金加权年化', 'bt.sum.pnl': '累计盈亏', 'bt.sum.avg': '平均持仓',
    'bt.sum.unit': '金额单位：亿元。次日镜像按国家队估计持仓等比例跟随，规模与之一致。',

    'bt.why.h3': '为什么次日镜像有时赚得比国家队多',
    'bt.why.size': '<b>盈亏金额更大</b>：镜像把信号日的申赎都算成国家队的，其他资金也被算了进来，估出的持仓比实际大（2015–2023 年平均约 2.7 倍）。本金多，涨时赚得多、跌时也亏得多，并不代表收益率更高。',
    'bt.why.mix': '<b>个别年份收益率更高</b>（如 2017、2019、2020、2025 年）：主要是持有的 ETF 不同，而不是买卖时点更好。混进来的其他资金让镜像的持仓偏离国家队：2020 年前少配上证50、多配沪深300 和创业板，2025 年少配沪深300、多配中证500 / 1000 和创业板，碰巧这些品种当年涨得更多。',
    'bt.why.miss': '<b>国家队真正大举买卖时镜像落后</b>：2015 年救市时在高位多买，2024 年低点买得不够、多配的中证1000 涨得少，2026 年初卖得不够。这几年明显跑输国家队，所以全区间镜像的资金加权年化仍低于国家队。',
    'bt.rule.nt': '国家队实际（估算）：以定期报告披露的持仓为锚点，两期之间按信号日申赎推断买卖时点；使用了事后公布的报告，反映国家队的实际操作。',
    'bt.rule.mr': '次日镜像（策略）：初始持仓与 2014 年报的国家队持仓对齐；此后每晚仅用当时可得的数据估计国家队当日买卖（信号日的同向净申赎），次日收盘将各 ETF 持仓调整至相同比例，单边成本 0.05%。',

    'bt.pnl.h2': '累计盈亏与持仓',
    'bt.pnl.note': '所选区间内各账户的资金加权收益、每日累计盈亏（自区间首日起算）与持仓市值。虚线为 2024 年分段点。次日镜像与国家队实际持仓线的差距，即仅凭申赎估计国家队仓位的误差。',
    'bt.pnl.h3': '累计盈亏（亿元）', 'bt.hold.h3': '持仓市值（亿元）',
    'bt.r.irr': '资金加权年化', 'bt.r.pnl': '累计盈亏', 'bt.r.buy': '买入', 'bt.r.sell': '卖出', 'bt.r.v0': '期初持仓', 'bt.r.v1': '期末持仓', 'bt.r.avg': '平均持仓',
    'bt.r.unit': '金额单位：亿元。',
    'bt.tip.pnl': '{n} 累计盈亏 {v}', 'bt.tip.hold': '{n} 持仓 {v}', 'bt.split': '2024',

    'bt.year.h2': '逐年拆解',
    'bt.year.note': '按自然年分别计算：上年末持仓视为年初投入，年末持仓视为年末收回，收益为当年资金加权收益（不年化）。盈亏与平均持仓单位为亿元；本年截至最新数据日。',
    'bt.year.year': '年份', 'bt.year.ret': '收益', 'bt.year.pnl': '盈亏', 'bt.year.avg': '平均持仓',

    'bt.ev.h2': '信号之后的表现',
    'bt.ev.all': '2015 年至今', 'bt.ev.recent': '2024 年以来',
    'bt.ev.note': '以各进出场波段首日为信号日，统计自次一交易日收盘起持有沪深300全收益指数 N 个交易日的平均收益，括号内为正收益占比。"所有交易日"为任意一天买入的平均收益，用作对照，检验信号是否包含额外信息。"逆势"指信号日沪深300 低于 5 个交易日前的水平。',
    'bt.ev.group': '信号', 'bt.ev.n': '次数', 'bt.ev.h': '{h} 日后',
    'bt.ev.g.entry': '进场波段', 'bt.ev.g.entry_contra': '其中逆势', 'bt.ev.g.entry_trend': '其中顺势',
    'bt.ev.g.exit': '退出波段', 'bt.ev.g.all_days': '所有交易日（对照）',

    'bt.a.h2': '关于回测',
    'bt.a.mwr': '<b>为什么用资金加权</b>：本页关注国家队的投入时点与规模。时间加权收益（基金净值法）剔除了资金进出的影响，相当于始终满仓；国家队的时间加权年化与沪深300 接近，无法体现择时效果。资金加权保留了这部分，代价是持仓大的年份权重更高，因此分段计算。',
    'bt.a.nt': '<b>国家队账户</b>：为估算值，非官方数据。持仓数量取自定期报告（年报 / 中报前十名，季报中识别出的大额持有人），较为可靠；两期之间的买卖时点按信号日申赎推断。2023 年 10 月这类在二级市场直接买入、份额不变的操作，只能由下一期报告补齐。2026 年起持仓不再披露，减持规模按退出信号日的赎回估算（持仓以中报机构持有份额为上限）。仅统计监控池内的 ETF，不含其他宽基 ETF 与个股。',
    'bt.a.mr': '<b>次日镜像</b>：交易所在 T 日收盘后公布份额，因此按 T+1 收盘价成交。由于无法实时获知国家队真实持仓，信号日的同向净申赎全部计为国家队操作：2015 年与 2024 年的申购中混有其他资金，估计持仓偏高；2026 年的减持则被低估。这是与国家队实际的主要差距，延迟一天成交的影响很小。',
    'bt.a.price': '<b>价格</b>：各 ETF 以基金净值和东方财富提供的含分红日增长率构建全收益序列，分红再投资。场内价格与净值的偏离通常在 0.1% 以内，忽略不计。基准沪深300全收益指数（H00300）取自中证指数公司官网。ETF 净值已扣除管理费并含跟踪误差，指数则不然，因此 ETF 每年约落后指数 0.5 个百分点（2015 年以来 510300 年化 2.80%，指数 3.34%），比较时对各账户略为不利。',
    'bt.a.bias': '<b>偏差</b>：① 监控池依据事后的定期报告筛选"国家队曾重仓"的 ETF，存在后视偏差；② 信号阈值经已知事件校准；③ 深交所份额数据始于 2016-10-28；④ 次日镜像的初始持仓对齐使用了 2014 年报，该报告于 2015 年 3 月才公布。',
    'bt.a.read': '<b>如何解读</b>：资金加权收益衡量投入资金的平均年化收益，不等于固定本金的收益——跟随者需随国家队追加或撤回资金。',
  },
  en: {
    'bt.title': 'National Team Returns and Tracking Backtest',
    'bt.crumb': 'Tracking backtest',
    'bt.nav.sum': 'Returns', 'bt.nav.pnl': 'P&L and holdings', 'bt.nav.year': 'By year', 'bt.nav.ev': 'After signals', 'bt.nav.about': 'About',

    'bt.name.nt': 'National team, actual', 'bt.name.mr': 'Next-day mirror', 'bt.name.bench': 'CSI 300 Total Return',
    'bt.p.all': 'Full period', 'bt.p.pre': '2015–2023', 'bt.p.post': '2024 to date',

    'bt.take.nt': 'The national team\'s money-weighted annual return (estimated): {all} over the full period, {pre} in 2015–2023 and {post} since 2024. The CSI 300 Total Return index returned {ball}, {bpre} and {bpost}.',
    'bt.take.mr': 'Next-day mirror (estimate the national team\'s position each evening, follow at the next close): {all} over the full period, {pre} in 2015–2023 and {post} since 2024.',
    'bt.take.read': 'Before 2024 the national team held only tens of billions of yuan in the pool and earned close to nothing, trailing the index; from 2024, with holdings above a trillion yuan, its timing clearly beat the index.',

    'bt.sum.h2': 'Returns compared',
    'bt.sum.note': 'All returns are money-weighted (IRR): each trade counts at the time it happens, and periods with larger holdings carry more weight, so timing (buying low, selling high) shows up. A time-weighted return assumes the account is always fully invested and misses this. The drawback is that years with larger holdings dominate; the national team\'s pool holdings differ by dozens of times before and after 2024, so returns are computed by period. Holdings at the start of each period count as invested at the start, and holdings at the end as returned at the end. The benchmark is the CSI 300 Total Return index (dividends reinvested, no fees; the index CSI 300 ETFs track), treated as a single buy-and-hold investment, so its money-weighted return equals its ordinary annual return.',
    'bt.sum.acct': 'Account', 'bt.sum.irr': 'Annual (MW)', 'bt.sum.pnl': 'P&L', 'bt.sum.avg': 'Avg holdings',
    'bt.sum.unit': 'MW = money-weighted. Amounts in ¥bn. The next-day mirror follows the estimated national-team holdings proportionally, at the same scale.',

    'bt.why.h3': 'Why the next-day mirror sometimes earns more than the national team',
    'bt.why.size': '<b>Larger P&L</b>: the mirror counts all signal-day creations and redemptions as the national team\'s, other investors\' money included, so its estimated holdings are larger than the real ones (about 2.7 times on average in 2015–2023). More capital earns more in rising markets and loses more in falling ones; it does not mean a higher return.',
    'bt.why.mix': '<b>Higher returns in some years</b> (e.g. 2017, 2019, 2020, 2025): mostly because it held different ETFs, not because it traded at better times. The other money pulls the mirror away from the national team\'s mix: before 2020 less SSE 50 and more CSI 300 and ChiNext, in 2025 less CSI 300 and more CSI 500 / 1000 and ChiNext, which happened to rise more in those years.',
    'bt.why.miss': '<b>It falls behind when the national team really moves</b>: it bought too much near the top during the 2015 rescue, too little at the 2024 lows (and more CSI 1000, which lagged), and sold too little in early 2026. It clearly trailed the national team in those years, so its full-period money-weighted return is still lower.',
    'bt.rule.nt': 'National team, actual (estimated): holdings disclosed in periodic reports serve as anchors, and the timing of trades between reports is inferred from creations and redemptions on signal days. It uses reports published later and reflects what the national team actually did.',
    'bt.rule.mr': 'Next-day mirror (strategy): starts aligned with the national team\'s holdings in the 2014 annual reports; after that, each evening it uses only data visible that evening to estimate the national team\'s trades (same-direction net creations and redemptions on signal days), and at the next close sets its holding in each ETF to the same proportion. Trading cost is 0.05% each way.',

    'bt.pnl.h2': 'Cumulative P&L and holdings',
    'bt.pnl.note': 'Money-weighted returns for each account over the selected range, with daily cumulative P&L (from the first day of the range) and holdings value. The dashed line marks the 2024 split. The gap between the next-day mirror\'s and the national team\'s holdings lines is the error from estimating the national team\'s position from creations and redemptions alone.',
    'bt.pnl.h3': 'Cumulative P&L (¥bn)', 'bt.hold.h3': 'Holdings value (¥bn)',
    'bt.r.irr': 'Money-weighted annual', 'bt.r.pnl': 'Cumulative P&L', 'bt.r.buy': 'Bought', 'bt.r.sell': 'Sold', 'bt.r.v0': 'Holdings at start', 'bt.r.v1': 'Holdings at end', 'bt.r.avg': 'Average holdings',
    'bt.r.unit': 'Amounts in ¥bn.',
    'bt.tip.pnl': '{n} cumulative P&L {v}', 'bt.tip.hold': '{n} holdings {v}', 'bt.split': '2024',

    'bt.year.h2': 'Year by year',
    'bt.year.note': 'Each calendar year on its own: holdings at the previous year-end count as invested at the start and holdings at the year-end as returned; the return is that year\'s money-weighted return (not annualised). P&L and average holdings are in ¥bn. This year runs to the latest data date.',
    'bt.year.year': 'Year', 'bt.year.ret': 'Return', 'bt.year.pnl': 'P&L', 'bt.year.avg': 'Avg holdings',

    'bt.ev.h2': 'What happened after signals',
    'bt.ev.all': '2015 to date', 'bt.ev.recent': 'Since 2024',
    'bt.ev.note': 'Taking the first day of each entry or exit wave as the signal day, the average return from holding the CSI 300 Total Return index for N trading days from the next day\'s close; the share of positive outcomes is in brackets. "All trading days" is the average from buying on any day, as a control for whether signals add information. "Contrarian" means the CSI 300 was below its level 5 trading days before the signal.',
    'bt.ev.group': 'Signal', 'bt.ev.n': 'Count', 'bt.ev.h': 'After {h} days',
    'bt.ev.g.entry': 'Entry waves', 'bt.ev.g.entry_contra': 'of which contrarian', 'bt.ev.g.entry_trend': 'of which with the trend',
    'bt.ev.g.exit': 'Exit waves', 'bt.ev.g.all_days': 'All trading days (control)',

    'bt.a.h2': 'About this backtest',
    'bt.a.mwr': '<b>Why money-weighted</b>: this page is about when and how much the national team invests. A time-weighted return (the fund NAV method) strips out the effect of money coming in and out, as if always fully invested; the national team\'s time-weighted return is close to the CSI 300\'s and shows no timing effect. A money-weighted return keeps it, at the cost of weighting years with larger holdings more heavily, hence the separate periods.',
    'bt.a.nt': '<b>National team account</b>: an estimate, not a figure the national team publishes. Holdings come from periodic reports (top-ten holders in annual and interim reports, large holders identified in quarterly reports) and are fairly reliable; the timing of trades between reports is inferred from creations and redemptions on signal days. Purchases made directly on the secondary market with no change in units, as in October 2023, are picked up only by the next report. There is no disclosure from 2026 on, so sales are estimated from redemptions on exit-signal days (capped by institutional holdings in the interim report). Only ETFs in the monitored pool count, not other broad-based ETFs or individual stocks.',
    'bt.a.mr': '<b>Next-day mirror</b>: exchanges publish unit counts only after the close on day T, so trades happen at the close of T+1. The national team\'s true holdings are not visible in real time, so all same-direction net creations and redemptions on signal days count as the national team\'s: other money mixed into creations in 2015 and 2024 pushes the estimated holdings too high, and sales in 2026 are underestimated. This is the main gap to the actual account; trading a day late matters little.',
    'bt.a.price': '<b>Prices</b>: for each ETF, a total-return series built from its NAV and Eastmoney\'s dividend-inclusive daily returns, with dividends reinvested. The gap between market price and NAV is usually under 0.1% and is ignored. The benchmark, the CSI 300 Total Return index (H00300), comes from China Securities Index. ETF NAVs are net of fees and include tracking error while the index does not, so an ETF trails the index by about 0.5 percentage points a year (510300 returned 2.80% a year since 2015, the index 3.34%), which slightly penalises each account in the comparison.',
    'bt.a.bias': '<b>Biases</b>: (1) the pool consists of ETFs that later periodic reports showed the national team once held heavily, so there is hindsight bias; (2) the signal thresholds were calibrated against known events; (3) Shenzhen unit data starts on 2016-10-28; (4) the mirror\'s starting alignment uses the 2014 annual reports, published only in March 2015.',
    'bt.a.read': '<b>How to read it</b>: a money-weighted return measures the average annual return on the money invested; it is not what a fixed amount of capital would earn, since a follower has to add and withdraw money along with the national team.',
  },
});
