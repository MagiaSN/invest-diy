# A-Share National Team ETF Tracker

Package `investdiy/ashare_track_national_team_etf/`, served at `/ashare-track-national-team-etf/`.

China's "national team" (Central Huijin Investment, Huijin Asset Management, China Securities Finance, the National Social Security Fund, China Reform Holdings, China Chengtong and similar state-backed investors) supports and exits the stock market largely through broad-based ETFs. It rarely announces how much it trades. This tool estimates its moves from data published every day:

- **daily net creations and redemptions** of the broad-based ETFs it holds, computed from the unit counts published by the Shanghai and Shenzhen stock exchanges;
- **entry and exit signals**, merged into waves, when the pool's combined flow is unusually large;
- **official holdings** from fund periodic reports and the **lower bounds on its selling** they imply after disclosure stopped;
- a **tracking backtest** of the national team's own account and of a strategy that follows its estimated position one day later.

## Pages

| Page | Content |
|---|---|
| `/ashare-track-national-team-etf/` | headline figures, cumulative flow vs the CSI 300, calendar heatmap, pool table, entry / exit waves, official holdings and selling bounds, monthly flows, per-ETF charts, checks against press reports |
| `/ashare-track-national-team-etf/backtest.html` | money-weighted returns of the national team and of the next-day mirror by period, cumulative P&L and holdings, year by year, performance after signals |

## Running

```bash
.venv/bin/python3 -m investdiy.ashare_track_national_team_etf                  # fetch + compute (about 10 minutes the first time, seconds afterwards)
.venv/bin/python3 -m investdiy.ashare_track_national_team_etf --skip-fetch     # recompute only
.venv/bin/python3 -m investdiy.ashare_track_national_team_etf.holders          # scan periodic reports only (cached after the first run)
.venv/bin/python3 -m investdiy.ashare_track_national_team_etf.fetch --start 2023-01-03   # fetch only, from a given date
```

The exchanges publish the units for day T as a preliminary figure on the evening of T and as the final figure on the morning of T+1. Running after 9:00 on T+1 is the safest; `fetch.py` always refetches the latest trading day.

| Module | Role |
|---|---|
| `pool.py` | candidate ETFs (about 40 broad-based ETFs) and the keywords that identify national-team holders |
| `fetch.py` | units and prices of every candidate → `data/*.csv` |
| `holders.py` | parses periodic reports → national-team holdings and the monitored pool → `data/out/{holders,nt_holdings,pool}.csv` |
| `analyze.py` | flows, signals, waves, selling bounds → `data/out/*.csv` |
| `backtest.py` | national-team account and next-day mirror, money-weighted by period, plus performance after signals → `data/out/bt_*.csv` |
| `web/` | dashboard (`index.html`, `strings.js`, `app.js`, `checks.js`) and backtest page (`backtest.html`, `backtest.strings.js`, `backtest.js`) |

## Data sources

All sources are free and need no login.

| Data | Endpoint | Notes |
|---|---|---|
| Shanghai ETF units | `query.sse.com.cn/commonQuery.do?sqlId=COMMON_SSE_ZQPZ_ETFZL_XXPL_ETFGM_SEARCH_L&STAT_DATE=YYYY-MM-DD` | needs `Referer: https://www.sse.com.cn/`; returns every Shanghai ETF for one day (`TOT_VOL`, in 10,000 units); the `SEC_CODE` filter is ignored; history from 2015; on days without data the API falls back to the latest day, so rows must be filtered by `STAT_DATE` |
| Shenzhen ETF units | `www.szse.cn/api/report/ShowReport/data?SHOWTYPE=JSON&CATALOGID=scsj_fund_jjgm&TABKEY=tab1&jjlb=ETF&txtDm=<code>&txtStart=&txtEnd=&PAGENO=` | one code over a date range of at most 6 months; 20 rows per page (`metadata.pagecount`); `current_size` in 10,000 units with thousands separators; history from 2016-10-28. `CATALOGID=1945` (ETF list) has current units only |
| Fund periodic reports | `api.fund.eastmoney.com/f10/JJGG?fundcode=<code>&type=3` (list, needs a Referer), PDF at `pdf.dfcfw.com/pdf/H2_<id>_1.pdf` | parsed by `investdiy/common/fund_reports.py` |
| CSI 300 Total Return index (backtest benchmark) | `www.csindex.com.cn/csindex-home/perf/index-perf?indexCode=H00300&startDate=YYYYMMDD&endDate=YYYYMMDD` | the index provider; the whole range in one request (needs a Referer); non-trading days may repeat the previous close. Read by `common.market.csindex_history` |
| Total-return NAV (backtest) | `fund.eastmoney.com/pingzhongdata/<code>.js`, `Data_netWorthTrend` | full NAV history plus dividend-inclusive daily returns; chained into a total-return series by `common.market.fund_total_return` |
| Closing prices, CSI 300 index | Tencent `web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh510300,day,<start>,<end>,2000,` | unadjusted, up to 2,000 bars per request. Its adjusted ETF prices are unreliable (they start in 2018 and the factors jump), hence the Eastmoney NAVs for total returns |

## Method

### Flows

```
net creation (CNY 100m) = (units_T - units_T-1) (10,000 units) x close_T / 10,000
```

- The close approximates the NAV: broad-based ETFs usually trade within 0.1% of NAV. Creations settle at NAV on day T, so the close tracks fund size better than an intraday average price. On days with total flow of CNY 10bn or more, using the typical price (high + low + close) / 3 instead changed flows by a median 0.33% (90th percentile 1.13%, maximum 3.0% on the 2024-09-30 / 10-08 rally days) and changed no signal.
- **Unit splits**: a unit jump and the opposite price jump can be published a day apart (E Fund CSI 300 halved its units on 2024-09-20, but its price doubled only on 09-23). Left alone, this would show as a CNY −95bn "exit". `analyze.py` looks for an offsetting price jump on T−1, T or T+1 and sets that day's flow to zero.

### Signals and waves

- Thresholds float with the market: an **entry / exit** needs a pool total of at least max(previous day's pool AUM × 0.6%, 3 × the median absolute total flow of the previous 60 trading days); a **strong** signal needs max(× 1.8%, 6 ×). Scaling the floor with pool size matters because the pool grew from about CNY 100bn in 2015 to almost CNY 1.9tn in 2025; 0.6% / 1.8% is roughly CNY 10bn / 30bn in 2024–2025.
- Thresholds use only data up to the signal day.
- Same-direction signals at most 2 trading days apart merge into one **wave**; a wave that ended within the last 3 trading days counts as ongoing.
- Each wave also reports the share of the four large CSI 300 ETFs in its flow. Huijin has historically concentrated there, so a high share makes national-team buying more likely.
- Calibration against nine known events (the 2015 rescue, October 2018, February 2020, April 2022, August 2023, February 2024, April 2025, the January 2026 selling and the 2023-10-23 announcement) detects eight; on 2023-10-23 the pool's units rose by only CNY 2.4bn (see the validation section).

### The monitored pool

- `holders.py` parses the periodic reports of every candidate since the 2014 annual report. An ETF joins the pool when identified national-team holdings reached 10% of the fund in any report. ETFs the national team later sold out of stay in the pool so the exit remains visible.
- National-team holders are identified by name in top-ten holder tables (Central Huijin Investment, Huijin Asset Management, China Securities Finance, the social security fund, China Reform Holdings, China Chengtong, Wutongshu Investment).
- Quarterly reports only have an unnamed "single investor holding 20% or more" table. Its rows are linked to named rows by exactly equal unit counts: within a period (closing units equal a top-ten row) and across periods (opening units equal an earlier closing figure, or the reverse). Rows that cannot be linked do not count as national team.
- Shanghai data starts on 2015-01-05 and Shenzhen data on 2016-10-28; Shenzhen ETFs are left out before that.

## Official holdings and selling bounds

From 2026 official disclosure of national-team holdings almost stopped:

- Huijin no longer appears in the "single investor ≥ 20%" tables of quarterly reports, even for ETFs it held 40–80% of at the start of the year, while other ≥ 20% holders are still disclosed.
- The 2026 interim reports dropped the top-ten holder table that the 2024 and 2025 interim reports had.

Two hard bounds that need no threshold are derived instead (`analyze.holdings_bounds`), with the latest report period in which a national-team holding was identified as the baseline H:

| Bound | Logic | Frequency |
|---|---|---|
| Share floor | if total units S fall below H, the national team sold at least H − S | daily |
| Institutional cap | national-team holdings cannot exceed the units held by all institutions (I) in the interim / annual holder structure, so at least H − I was sold | half-yearly |

The share floor is looser than the cap because creations by other investors keep total units up; when the floor falls after a peak, the net creations behind it may come from the national team buying back or from anyone else.

## Validation

### Core checks

| Check | This project | External source |
|---|---|---|
| Huatai-PB CSI 300 units, 2025-12-31 / 2026-01-21 | 88.830 / 71.978bn units | Q4 report 88.830bn, press 71.978bn |
| Huijin selling in January 2026 | pool total −CNY 937.1bn | Wind: CNY 939.7bn net outflow from 12 broad-based ETFs that month |
| National-team holdings on 2025-06-30 | CNY 1.256tn in the pool | Wind: CNY 1.28tn of Huijin ETF holdings |
| Period-end units | exchange units match each report's "total units at period end" | e.g. Huatai-PB CSI 300 at 18.915bn units on 2026-06-30 in both |

### Press reports

Major reports of national-team buying and selling were checked one by one on 2026-10-27; the same list, with links to the sources, is on the dashboard ("Checked against press reports", data in `web/checks.js`). The press often counts all broad-based ETFs or the four blue-chip ETFs, so only like-for-like figures are compared.

| Event | Press / Wind | This project | Verdict |
|---|---|---|---|
| 2015-06-29 ~ 07-01 rescue, four blue-chip ETFs (daily) | CNY 9.45 / 15.56 / 13.43bn | 9.34 / 16.36 / 0.45bn; 13.42bn on 07-02 | one day apart on the third day |
| Huijin in Huatai-PB CSI 300, H2 2023 | 2.424 → 6.247bn units | 2.424 → 6.247bn units | match |
| 2023-10-23 Huijin announces ETF purchases | heavy trading near the close, CNY 9.59bn turnover | pool units +CNY 2.4bn, no signal | not visible (secondary-market buying) |
| Q1 2024 Huijin buys 5 ETFs (press estimate) | CNY 313.9bn | same 5 ETFs CNY 281.3bn | different scope; gap = other holders' redemptions |
| Huijin in Huatai-PB CSI 300, 2024-03-31 | about CNY 115bn | 32.603bn units × NAV ≈ CNY 115bn | match |
| Huatai-PB CSI 300, 2024-09-24 ~ 10-14 | +CNY 46.53bn | +CNY 47.11bn | match (1.3%) |
| CSI 300 ETFs, 2025-04-08 | +CNY 53.42bn (Wind) | +CNY 53.73bn | match (0.6%) |
| Four major broad-based ETFs, 2025-04-07 ~ 04-11 | over CNY 150bn | pool +CNY 158.7bn | match |
| Broad-based ETF outflow, 2026-01-01 ~ 01-26 | CNY 738.2bn (all broad-based ETFs) | pool −CNY 674.4bn | different scope (pool ≈ 90%) |
| Single days 2026-01-22 / 23 / 26 | CNY 77.0 / 87.1 / 116.5bn | −71.0 / −87.5 / −113.8bn | match |
| 11 rescue ETFs, 2026-01-15 ~ 02-02 | CNY 947.1bn, peak 138.4bn on 01-28 | −952.3bn, −143.9bn on 01-28 | match |
| Minimum Huijin sale in Huatai-PB CSI 300, 2026-01-26 | 73.513 − 60.517 ≈ 13.0bn units | same inputs | match (same share-floor method) |
| E Fund CSI 300, 2026-10-15 | +CNY 18.8bn | +CNY 18.79bn | match |
| Huatai-PB CSI 300, 2026-09-28 ~ 10-23 | +CNY 47.50bn | +CNY 47.64bn | match |

Daily and period flows are typically within 1–5% of the reports, and Huijin holdings in periodic reports match. The systematic blind spot is buying on the secondary market (2023-10-23), which leaves units unchanged; the 2015-07-01 difference is most likely about which day the preliminary and final figures are dated.

## Tracking backtest

`backtest.py` and `web/backtest.html` compare two accounts, all amounts in CNY on the national team's scale:

- **National team, actual (estimated)**: each pool ETF's holding is rolled forward daily with its total-return NAV and anchored to the holdings disclosed in periodic reports. The net amount traded between two reports is spread across that window's signal days in proportion to the ETF's same-direction flows. After disclosure stopped, same-direction flows on signal days count as national-team trades, capped by the institutional holdings of the next interim report. This uses reports published later and represents what the national team actually did.
- **Next-day mirror (strategy)**: starts aligned with the holdings of the 2014 annual reports (published in March 2015, a small look-ahead). Each evening it uses only data visible that evening, counting same-direction net creations on signal days as national-team trades (sales capped at the estimated holding), and at the next close sets its units in each ETF to match. One-way cost 0.05%.
- **Benchmark**: the CSI 300 Total Return index (H00300: dividends reinvested, no fees), the index the large CSI 300 ETFs track. ETF NAVs are net of fees and tracking error, so an ETF trails the index by roughly 0.5 percentage points a year (510300: 2.80% a year since 2015 against 3.34%); the comparison is slightly conservative for both accounts. The after-signals table uses the same index.

Returns are **money-weighted (IRR)**. The question is whether buying low and selling high pays, i.e. when how much money goes in; a time-weighted return treats the account as always fully invested and removes exactly that. (The national team's time-weighted return is close to the CSI 300's.) Because money-weighted returns give more weight to periods with more money, and the national team's pool holdings grew dozens of times from 2024, every account is reported for the full period, 2015–2023 and 2024 to date. Each period treats the holdings at its start as invested and the holdings at its end as returned.

Results as of 2026-10-27 (money-weighted annual return / cumulative P&L / average holdings, CNY 100m):

| Account | Full period | 2015–2023 | 2024 to date |
|---|---|---|---|
| National team, actual | 15.11% / +4,739 / 2,474 | −0.24% / −12 / 672 | 24.32% / +4,752 / 8,263 |
| Next-day mirror | 10.08% / +5,149 / 4,241 | −1.21% / −167 / 1,849 | 18.99% / +5,316 / 11,931 |
| CSI 300 Total Return | 3.34% | 1.50% | 9.50% |

- Before 2024 the national team held only tens of billions of yuan in the pool and its timing earned nothing; from 2024, with holdings above a trillion yuan, it clearly beat the index.
- The gap between the mirror and the actual account comes mostly from estimating holdings from flows alone: creations by other investors in 2015 and 2024 push the estimate too high, and sales in 2026 are underestimated. Trading one day late costs only about 0.2 percentage points a year.
- The mirror sometimes earns more than the national team, for the same reason. Its overestimated holdings (about 2.7 times the real ones on average in 2015–2023) mean a larger P&L in rising markets, not a higher return; in years when its return was higher (2017, 2019, 2020, 2025) the gap comes from a different ETF mix, tilted by other investors' money towards what happened to rise more, not from better timing. It falls behind exactly when the national team trades heavily (2015, 2024, early 2026).
- A money-weighted return is what each yuan invested earned; a follower would need to add and withdraw capital along with the national team to achieve it.

Possible improvements to the position estimate: re-anchor to each report on its publication date, count only flows above normal levels, use ETFs on the same index that the national team does not hold as a control, and calibrate the attribution ratio on past disclosures, validating each method against the next report.

## Limitations

- Unit changes show that large creations or redemptions happened, not who made them. Large creations during sharp rallies (such as late September 2024) more likely come from institutions and retail investors. National-team buying is most likely when buying into a falling market, concentration in the four large CSI 300 ETFs and heavy trading near the close coincide.
- Holder lists in periodic reports are the only after-the-fact confirmation, and they arrived with a delay of months even before disclosure stopped.
- Purchases on the secondary market do not change units and are invisible.
- The pool is built from later reports (ETFs the national team once held heavily), which introduces hindsight in the backtest; the signal thresholds were calibrated on known events.
- `data/sse_shares.csv` keeps every Shanghai ETF (about 18 MB) so the pool can grow without refetching.

## Related projects

Other public trackers of national-team ETF flows, for comparison:

- [国家队ETF动向追踪](https://etf.maomaoci-a.com/): 16 broad-based ETFs, flows as unit change × daily average price, plus index-futures positions and a holdings baseline table.
- [etf-radar](https://github.com/H-Jett/etf-radar): sector and theme ETFs and top shareholders of stocks, collected daily with GitHub Actions.
- [etf-national-tracker](https://github.com/kitaki-Ciallo/etf-national-tracker): Flask + PostgreSQL, Shanghai units and top-ten holders.

Index-futures positions of the largest brokerage seats (CFFEX daily rankings) were considered and left out: they aggregate all clients of a broker and attribute far less clearly than ETF units.
