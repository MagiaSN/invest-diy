# Global Copper Market Tracker

Local dashboard at `/global-track-copper/` for COMEX, LME and SHFE copper prices, exchange inventories, relative price premiums, annual global supply/demand and a copper mine map. English and Chinese pages use the shared local assets. This tool has `visibility: local` and is excluded from public export and publication workflows.

## Run

From the repository root, using the existing environment:

```bash
.venv/bin/python -m investdiy.global_track_copper
.venv/bin/python -m investdiy.server
# Open http://localhost:8765/global-track-copper/
```

Restart an existing server after adding the tool. Run the updater again to merge new observations and revisions, then refresh the browser. Each chart has its own range picker; no range is stored in the URL. Legend buttons toggle markets. The SHFE VAT selector changes both normalized prices and premiums. Premiums can be displayed as percentages or absolute USD/tonne spreads.

```bash
.venv/bin/python -m investdiy.global_track_copper --start 2020-01-01
.venv/bin/python -m investdiy.global_track_copper --skip-fetch
.venv/bin/python -m investdiy.global_track_copper --strict
```

The default requested start date is 2020-01-01. Actual history varies by endpoint: a requested date does not imply complete coverage. The 99qh page exposes up to 400 observations; the MetalCharts public chart exposes one year. Updates preserve older locally collected history. SHFE candidates include Fridays and the last trading day of shortened weeks. Unavailable official archives remain empty; warehouse receipts cannot substitute for stocks. A partial update keeps successful sources and valid cached observations. Known mislabeled SHFE warrants are quarantined even if replacement fetching fails. `--strict` exits nonzero on missing/stale data, fetch errors or excluded primary mirror observations, while still writing usable output. An empty dataset always exits nonzero.

COMEX inventory extension uses the normal public chart in an optional local browser. Install it once:

```bash
.venv/bin/pip install playwright
.venv/bin/python -m playwright install chromium
```

On Linux, install Chromium system dependencies if Playwright requests them. Without the browser, valid cached COMEX stocks and the primary mirror remain usable; the missing extension is recorded as a partial result. No MetalCharts account or paid API is required.

## Sources and definitions

| Series | Public provider | Native unit and definition |
|---|---|---|
| COMEX price | [Eastmoney HG00Y](https://quote.eastmoney.com/globalfuture/HG00Y.html), `push2his.eastmoney.com` daily bars, market 101 | USD/lb, continuous copper futures close; provider-selected rolling contract |
| LME price | [Sina CAD](https://finance.sina.com.cn/futures/quotes/CAD.shtml), `GlobalFuturesService.getGlobalFuturesDailyKLine` | USD/tonne, three-month copper reference; the provider labels its overseas quote CFD, not official LME settlement |
| SHFE price | [Sina CU0](https://finance.sina.com.cn/futures/quotes/CU0.shtml), `InnerFuturesNewService.getDailyKLine` | CNY/tonne, VAT-inclusive main continuous futures close |
| COMEX inventory | [99qh COMEX copper](https://www.99qh.com/data/stockOut?productId=100), supplemented by the [MetalCharts public copper chart](https://metalcharts.org/comex/copper) and COCHILCO historical gap filling | Short tons, total stocks; chart rows require registered + eligible to reconcile within one short ton |
| LME inventory | [Westmetall copper stock history](https://www.westmetall.com/en/markdaten.php?action=table&field=LME_Cu_stock) | Metric tonnes, total stocks on the provider publication date; warrant components are not added again |
| SHFE inventory | [SHFE official weekly report](https://www.shfe.com.cn/data/tradedata/future/stockdata/weeklystock_20261113/ZH/all.html), dated `weeklystock_YYYYMMDD/ZH/all.html` archives, with COCHILCO historical gap filling | Metric tonnes, copper current-week grand total, including bonded and duty-paid stocks; not the adjacent warrant column |
| USD/CNY | [ECB daily euro reference rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html), public SDMX CSV | Same-date CNY/EUR divided by USD/EUR; replaces the former Fed fixing across fetched history |

Contract references: [CME copper specifications](https://www.cmegroup.com/markets/metals/base/copper.contractSpecs.html), [LME copper specifications](https://www.lme.com/en/Metals/Non-ferrous/LME-Copper/Contract-specifications). The [SHFE warehouse receipt manual](https://otc.shfe.com.cn/uploadss/20230515/1684112889349.pdf) lists the copper VAT rate. These references describe units and methodology; the fetched market series use the providers above.

An HTTP success does not imply accurate observations. The former 99qh SHFE series contained warrant quantities rather than total stocks and is removed by source identity, with a local backup before repair. The official parser checks the report date, copper section, current-week columns, weekly changes and bonded/duty-paid reconciliation. For example, 2026-11-13 total stocks are 27,642 tonnes, while warrants are 2,270 tonnes.

MetalCharts rows before 2026-06-12 are excluded because research found inconsistent dates and totals in its older history. Later rows must have nonnegative registered/eligible components that reconcile, a weekday report date and no conflict with the primary series. Valid chart rows fill missing dates; they do not override conflicting primary observations. Rejections are saved locally. Missing or unverified zero placeholders from 99qh are excluded. These checks cannot guarantee detection of every upstream error.

Westmetall matched all 165 overlapping Jin10 stock observations in the audited trailing year and supplied 88 missing dates. Its dates match the former mirror's publication dates. Official LME monthly closing-stock workbooks use an earlier business date; those dates are not spliced into this series. ECB rates are converted only when both currency legs exist on the same date. On successful migration, legacy Fed rows (including Fed-only holiday observations) are removed; a failed fetch preserves prior FX history. Explicit user imports remain supported.

The local repair on 2026-11-14 added 85 COMEX and 88 LME inventory observations in the 2025-11-14–2026-11-13 window. SHFE now has 52 official weekly reports in that window: 50 corrected observations and two additions (2025-12-26 and 2026-04-30). All seven series reach 2026-11-13. ECB restores 11 SHFE USD-price dates; same-date FX remains absent on 2025-12-25, 2025-12-26 and 2026-04-03. Unverified COMEX gaps remain empty. Older mislabeled SHFE history is backed up and removed where no official replacement was available. The Eastmoney request failed during this repair; already validated price history through 2026-11-13 was retained.

## Calculation and date alignment

- COMEX USD/tonne = USD/lb × `1000 / 0.45359237`.
- COMEX metric tonnes = short tons × `0.90718474`.
- SHFE gross USD/tonne = CNY/tonne ÷ same-date CNY per USD.
- SHFE net USD/tonne = gross USD/tonne ÷ `(1 + VAT)`.
- VAT is 13% from 2019-04-01, 16% from 2018-05-01 through 2019-03-31, and 17% before that. The default fetch window starts after the most recent change. Historical imports extending earlier use this schedule; it is not a general tax engine for arbitrarily old dates.
- For A/B, absolute spread = `A - B`, percentage premium = `(A / B - 1) * 100`. The three pairs are COMEX/LME, SHFE/LME and SHFE/COMEX. Positive means A is more expensive.

The price chart offers USD/tonne (default), USD/lb and CNY/tonne. USD/lb divides the normalized USD/tonne value by `1000 / 0.45359237`; CNY/tonne multiplies COMEX/LME USD/tonne by same-date CNY per USD. In CNY mode SHFE uses its native CNY quote, divided by `(1 + VAT)` for the net basis, without an FX round trip. The selected unit applies to chart axes and tooltips; USD/lb tooltips use four decimals and tonne quotes use two. Switching units preserves the range and hidden series. Snapshot cards and absolute premium spreads continue to state their own USD/tonne units.

Currency conversion requires prices and FX to share an observation date. There is no forward fill, nearest-date match or future-date lookup. COMEX/LME dollar prices remain available without FX; their CNY conversions do not. SHFE dollar conversions and cross-market premiums require same-date FX, but its native CNY chart does not. Unavailable conversions leave gaps instead of zero prices. The union of dates is retained in the daily CSV with blank cells for missing observations. Current UTC-date bars are excluded conservatively because they may still be in progress. Equal dates do not imply synchronized quote times across time zones.

Stocks remain at their reported daily/weekly dates; publication dates need not equal the preceding warehouse activity date. The inventory chart includes a togglable three-exchange total (`total_stock_t` in `daily.csv`): COMEX, LME and SHFE stocks are converted to metric tonnes and summed only when all three have observations on the same date. Missing components leave the total blank; verified zero stocks are valid components. The total is mainly weekly because SHFE reports weekly, and gaps longer than 14 days break its line. No stocks are carried across dates or extrapolated to today. Equal publication dates do not imply synchronized warehouse activity, and this total does not represent all global inventories. Native CSV observations remain available locally so the conversions can be audited.

Freshness is evaluated against the observation date: seven calendar days for prices, daily inventories and ECB FX; fourteen for weekly SHFE stocks. Detailed coverage, provenance and fetch status remain in local CSV files and are not displayed in a frontend source table. The home-page `as_of` is the oldest of the seven latest observation dates, and is blank if any series is entirely absent. Thus a new price cannot mask an old stock series.

## Storage and CSV import

All files under `investdiy/global_track_copper/data/` are ignored by Git:

| File | Content |
|---|---|
| `history.csv` | Persistent native observations, merged by `(series, date)` |
| `raw/<series>.txt` | Most recent successfully parsed price / primary COMEX response |
| `raw/lme-stock-<year>.html`, `raw/shfe/<date>.html` | Validated stock reports; recent periods refresh on updates |
| `raw/cochilco/<year>-<month>.html` | Validated historical stock reports used by the optional backfill |
| `out/backfill-audit.csv`, `out/backfill-status.csv` | Backfill additions, retained overlaps/conflicts, quarantines and month coverage |
| `raw/usdcny.csv`, `raw/comex-metalcharts.json` | ECB reference-rate CSV and public chart response |
| `raw/comex-rejected.csv`, `raw/shfe-missing.json` | Quarantined COMEX candidates and unavailable SHFE reports (404s retried weekly) |
| `backups/history-<timestamp>.csv` | Full native history before legacy SHFE / FX migration |
| `out/observations.csv` | Downloadable native history with units and row-level provenance |
| `out/daily.csv` | Native values, normalized prices/stocks, VAT rate, pair spreads and premiums |
| `out/sources.csv` | Last fetch attempt, outcome, date coverage and raw error/quality details |
| `out/summary.csv` | Conservative overall data date and newest observation date |
| `out/repair-audit.json` | One-time before/after coverage audit for the 2026-11-14 local repair |
| `manual/copper-capacity-events.json` | Disabled prototype: reviewed mine/phase milestones and separate event/capacity evidence |
| `out/capacity-events.csv`, `out/capacity-annual.csv` | Disabled prototype: offline event register and known subtotals; not loaded by the dashboard or built by normal updates |

CSV writes use temporary files and atomic replacement. Failed parsing does not overwrite a valid report snapshot or remove valid history. Old successful SHFE reports and completed Westmetall years are cached; remove the corresponding raw file to request a historical revision. Recent SHFE reports (14 days) and the current Westmetall year refresh on updates. Repeated updates are idempotent except for provider revisions and fetch timestamps. Do not run concurrent updaters against the same data directory. Back up this directory separately from the repository.

To supplement history from a verified export, create a UTF-8 CSV with the exact header `series,date,value,unit,source`. Each row must use an ISO date, a finite numeric value and a nonempty provenance label or URL. Exact units are required:

| `series` | `unit` |
|---|---|
| `cme_price` | `USD/lb` |
| `lme_price` | `USD/t` |
| `shfe_price` | `CNY/t` |
| `cme_stock` | `short ton` |
| `lme_stock`, `shfe_stock` | `t` |
| `usdcny` | `CNY/USD` |

```bash
.venv/bin/python -m investdiy.global_track_copper --skip-fetch --import-csv /path/to/verified-copper.csv
```

The entire import is validated before changes. Conflicting duplicate keys, future dates, wrong units, missing provenance, nonfinite values, negative stocks and nonpositive prices/FX are rejected. Verified zero inventories are allowed through imports. Imports overwrite matching cached dates; later successful fetches may revise those same dates again. Importing does not pretend that a network fetch succeeded: `out/sources.csv` continues to describe the last real attempt, while coverage and provenance come from actual observations. No synthetic sample data is written to the dashboard.

## Interpretation limits

Continuous contracts can jump at rolls. The LME reference is a three-month series while COMEX and SHFE rolling maturities differ. Close times and holidays differ, and the FX series is published with a lag. The computed premium is a reference-price comparison, not an executable arbitrage margin or a physical spot premium. Transport, tariffs, financing, delivery grade and regional basis are not included. Excluding VAT is a comparison convention, not a complete import-parity calculation.

Exchange total inventory has a different scope from registered warrants, cancelled warrants, eligible stocks, bonded warehouses or total social inventory. Warehouse stocks are not all immediately deliverable. Mirror data can be delayed, discontinued or erroneous even when parsing succeeds. The UI retains interpretation limits; detailed source coverage and fetch diagnostics remain in local files and this document.

## Five-year stock backfill

Fill missing stock observations from [COCHILCO monthly bulletin, table 4.2](https://boletin.cochilco.cl/productos/boletin.asp?anio=2024&mes=11&tabla=tabla4_2):

```bash
.venv/bin/python -m investdiy.global_track_copper --skip-fetch --start 2021-11-14 --backfill-stocks
```

This optional pass uses completed monthly reports, preserves every existing observation, backs up history before adding records, and exports recalculated totals. Run after fetching prices so the SHFE trading calendar is available. Drop `--skip-fetch` to update current sources first. Cached reports live in `raw/cochilco/YYYY-MM.html`; remove a file to re-download it. Parsing checks the requested month, column layout, metric-tonne unit, dates, duplicates and component sums. Spanish thousands separators, holiday markers and independently missing exchange values are handled explicitly.

COMEX observations use the table's daily dates. COCHILCO publishes metric tonnes, converted to short tons for the existing native schema; this does not increase the source's tonne-level precision. SHFE values are sampled only on the last trading date of each ISO week, including shortened weeks. The source repeats weekly stocks across daily rows and sometimes changes before the local report date; those repeated or early values are not imported as additional observations. Prices, FX and existing LME inventories are unchanged.

Conflicting existing values retain priority and are logged. Unverified zero stocks and isolated spikes/dropouts are quarantined for independent review. A spike is flagged when it differs by more than 30% from both neighboring observations, whose values differ by less than 15%, within 7 days for COMEX or 21 days for SHFE. This screen is conservative and cannot certify every historical value. Confirmed values can be supplied with the existing `--import-csv` option before backfilling. `--strict` fails on incomplete monthly downloads or unresolved quarantines; retained conflicts are audit entries rather than failed updates.

The 2026-11-14 backfill read all 60 reports from November 2021 through October 2026. The production parser extracted 1,298 dated rows, including two COMEX observations on LME holidays omitted by the preliminary research script. It added 860 COMEX observations and 201 SHFE weekly observations, retaining all earlier history. Two flagged SHFE jumps were independently confirmed and imported: [2021-12-31, 38,182 tonnes](https://www.mysteel.com/hot/1332541.html) and [2022-10-21, 89,566 tonnes](https://www.crainternational.com.cn/infor/view?id=43696). The other 199 SHFE additions came directly through the backfill pass. The three-exchange total now has 248 observations from 2021-11-19 to 2026-11-13; dates without all three components remain blank.

Six conflicts with existing observations were retained in favor of existing history (five COMEX, one SHFE). These include a zero COMEX value on 2026-07-07 and a SHFE mismatch on 2025-12-31. Raw research and the two independently verified import rows remain in the ignored `data/research/cochilco-5y/` directory. Detailed decisions and the latest run summary are stored in `out/backfill-audit.csv` and `out/backfill-status.csv`; these files are not shown in the frontend. Repeated backfills add no duplicate observations, and subsequent current-source updates preserve historical backfill rows unless an upstream observation revises the same date.

## Annual supply and demand

Inventory charts (including the three-exchange total), inventory snapshot cards, annual supply/demand lines (including secondary refining), and the refined balance chart display **10,000 metric tonnes**. Axes, tooltips and summaries use this same scale: stored tonnes divided by 10,000. Source and output CSVs retain their original tonne units; price units and mine-map production units are unchanged.

The current edition uses [COCHILCO's 2000–2025 statistical yearbook](https://www.cochilco.cl/web/download/1036/2026/16850/base-de-datos-anuario-de-estadisticas-cochilco-2000-2025.xlsx), tables 8.1 (mine production), 8.2 (refined production) and 8.10 (refined consumption). The workbook attributes world statistics to WBMS and Chilean figures to COCHILCO. This is one consistent publication; it is not spliced with ICSG totals, which can differ in methodology and revisions. The ICSG 2026 Factbook was also researched, but its PDF download returned HTTP 403 locally and is not a runtime dependency.

There are 26 complete annual observations, 2000–2025. The parser checks the English table identity, copper-content kilotonne units, a unique world-total row, matching years across all three tables, finite positive totals and completed years. It reads cached XLSX cell values without executing spreadsheet formulas. Values are converted to metric tonnes. Supply means refined production, including secondary refined copper; demand means refined consumption. These series do not measure every end-use application or direct-melt scrap use. Mine output is an upstream measure and is not added to refined supply. The former refined-minus-mined line has been removed: it was a residual, not a measured recycling series. The **global annual copper supply/demand** chart includes directly reported secondary refined copper from scrap as its fourth line, sharing the annual range picker, legend toggles and tooltip. The separate refining-composition chart has been removed. The secondary series uses ICSG statistics while the other lines use COCHILCO/WBMS: their statistical scope and revisions differ. Compare trends, but do not add secondary refining to an already-inclusive refined total or use cross-source subtraction to decompose the gap. Primary and total ICSG observations remain in the local data for validation, without additional chart lines.

The secondary refined series currently covers **2018–2025** and is joined to the annual chart by year. Earlier years remain missing for this line; the other annual lines retain their full history. It reads the four annual columns of the [January 2023 ICSG release](https://icsg.org/download/2023-01-20-monthly-press-release/) (2018–2021) and [ICSG Table 1](https://icsg.org/wp-content/uploads/Table1.pdf) (October 2026 edition: 2022–2025). The parser excludes year-to-date/monthly columns, forecasts and incomplete years; validates table identity, kilotonne units, annual alignment, publication date and `primary + secondary ≈ total` within two kilotonnes of published rounding; and converts figures to tonnes. Published preliminary full-year figures are included. Newer editions replace observations as complete bundles. Accepted rolling tables are archived to retain years that later leave the four-year window. Unverified years are not interpolated or plotted as zero.

Secondary refining recovers copper from new manufacturing scrap and old/end-of-life scrap. Primary refining processes mined feed, including SX-EW. Thus `refined − mined = secondary refined + (primary refined − mined)`, subject to rounding. The second term is not a measured recycling flow: feedstock inventories, processing lags, losses and statistical scope can contribute. Direct-melt scrap used by fabricators is outside this secondary-refining measure; see [ICSG recycling definitions](https://icsg.org/copper-recycling/). No invented inventory-release or processing-loss series is plotted.

The separate balance chart calculates **refined production minus refined consumption**. It has its own range picker. This statistical difference is not a change in exchange inventory or a forecast of a physical shortage.

The annual chart also has an optional **Show institutional forecast (to 2040)** switch, enabled by default when valid forecast data is available. It overlays the 2026–2040 annual projections from [S&P Global, *Copper in the Age of AI*, January 2026](https://www.spglobal.com/en/research-insights/special-reports/copper-in-the-age-of-ai), Appendix B, Figures 83 and 84 (printed page 111). Demand is the all-sector end-use total; supply is the reported baseline total of primary and secondary copper, with project risk adjustments. These are separate series, not continuations or revisions of WBMS refined supply/consumption. The unconstrained scenario in Figure 85 is not mixed into the baseline. The report contains annual figures, so no interpolation or chart digitization is necessary. Dashed lines, gap shading, tooltips and 2030/2035/2040 summaries use the same forecast edition. Balance is supply minus demand, negative for a deficit. Published values are rounded to 0.1 million tonnes; computed gaps inherit that precision and are not certain outcomes. Historical and forecast views remember separate date selections; other charts keep their own ranges. Hiding either forecast line also hides the gap shading. Missing or invalid forecast CSVs disable the switch without removing historical charts.

The reviewed input is `data/manual/copper-forecast-spglobal-2026.json`; output is `data/out/forecasts.csv`, with tonnes, signed balance, component checks, scenario, publication, source table, URL, review date and precision. Both are ignored market data. The publisher's PDF was readable through the web research reader, but direct local download returned HTTP 403. The reviewed table transcription is therefore local input, not a silently refreshed scraper. `--refresh-fundamentals` revalidates this input; it does **not** claim to download a new forecast edition. To recreate it on another machine, copy the reviewed local data file or transcribe the publisher's Appendix B: metadata must specify `publication: "2026-01"`, `scenario: "spglobal-2026-baseline"`, `unit: "MMt Cu"`, `source_table: "Appendix B, Figures 83 and 84"`, `scope: "Total copper demand; baseline primary plus secondary supply"`, the exact PDF `source` URL defined in `forecasts.py`, and an ISO `reviewed_at` date. The `observations` array requires each 2024–2040 year exactly once in ascending order, with `year`, `supply_mmt`, `demand_mmt`, `primary_mmt`, and `secondary_mmt`. The two baseline years are validated but not exported as forecasts. A new edition requires explicit review and adapter changes, preventing accidental scenario/edition mixing. Validation rejects mismatched units/years, nonfinite values, excess precision and inconsistent supply components before replacing output; failed reviews preserve the last valid CSV.

```bash
# Build annual fundamentals, refining components and mines from cached inputs.
.venv/bin/python -m investdiy.global_track_copper --skip-fetch --fundamentals
# Explicitly refresh their external sources, preserving valid output on failures.
.venv/bin/python -m investdiy.global_track_copper --skip-fetch --refresh-fundamentals
```

Normal updates also build these additions, using cached fundamental sources. The refining adapter uses the existing `pdfplumber` dependency. `--skip-fetch` alone only rebuilds the original daily series; combine it with `--fundamentals` to rebuild these additions without updating daily market sources. The yearbook URL pins a publication edition: upgrading to a future edition requires reviewing its tables and updating the URL. `--refresh-fundamentals` downloads revisions to that edition and the latest mine register/production snapshot and ICSG refining tables. `--strict` fails if any requested fundamental update fails. A failure in one addition does not block the other or overwrite its last valid CSV.

## Annual mine capacity events

**Disabled as of 2026-11-15: missing a verified, accessible, complete global data source for annual permanent retirement, commissioning and physical construction-start capacity.** The section, navigation entry and script loading are commented out in `web/index.html`; normal updates no longer invoke `capacity.py`. The adapter, reviewed local inputs and prototype renderer remain available for offline research. No sample totals or missing-data placeholder are displayed.

The source review found useful candidates, but did not establish a replacement covering all three annual event series:

| Source | Available information | Why it is not connected |
| --- | --- | --- |
| [ICSG Directory description and historical sample](https://icsg.org/wp-content/uploads/2024/01/Directory%20of%20Mines%2C%20Smelters%20and%20Refineries%20Description.pdf), [current map/database access](https://icsg.org/map-mines-smelters-refineries/) | Mine capacities, status, start-up/closure dates and capacity forecasts; historical capacity database back to 1995 is an additional subscriber product. | The public description does not establish complete historical physical construction-start events. The sample's developing status includes projects about to begin construction, so status alone cannot date a start. Full data requires subscription and field/coverage review. |
| [GlobalData Mines & Projects](https://www.globaldata.com/marketplace/dataset/mining-projects/) | Proprietary global project tracking from exploration to closure, historical coverage from 2000 and API delivery. | Public metadata does not establish completeness of dated copper-capacity events for all three categories, or separation of permanent closure from suspension. No licensed dataset was available for validation. |
| [S&P Global Metals & Mining product description](https://www.spglobal.com/content/dam/spglobal/mi/en/documents/general/SPGMI011-Metals---Mining-CV-Flyer-Sales-Slick_SSfNov2017.pdf) | Property profiles, capacity/costs, development stage and activity status. | These fields are candidates for project research, not evidence of a complete annual event history. Historical construction dates, closure definitions and export coverage still need verification in the licensed product. |
| [Wood Mackenzie Copper Product Suite](https://www.woodmac.com/industry/metals-and-mining/copper-product-suite/) | Mine-level models and analysis for more than 500 copper mines. | Broad asset coverage does not establish complete historical gross capacity flows. The public product material does not supply a downloadable, validated three-series event dataset. |
| [USGS World Minerals Outlook through 2030](https://pubs.usgs.gov/publication/sir20265081/full) | Historical production, estimated capacity and capacity outlook informed by expansions, closures and projects. | Aggregate capacity stocks and forecasts do not supply the three required annual gross event series. |

This is a finding about accessible, verified coverage, not a claim that no commercial provider can supply it. Re-enable only after reviewing an obtainable dataset's historical coverage and missingness, actual event dates, permanent-closure classification, copper-metal capacity units and incremental expansion scope. Annual changes in total capacity cannot recover separate commissioning and retirement flows, and construction starts are not operating capacity additions. An absent event must not be converted to a global zero. Company announcements can validate individual projects but cannot establish that every global event was captured.

The retained, disabled prototype is described below for future work.

The disabled **Annual copper mine capacity changes (reviewed projects)** chart has three independent legend toggles: permanently retired capacity, newly commissioned capacity and new construction capacity. Each value is an annual sum of capacity attached to events occurring in that calendar year, expressed as **10,000 tonnes of copper per year**. It is neither a cumulative capacity stock nor actual production in that year. All three magnitudes are positive. Construction and commissioning can describe the same project at different times and must not be added together. Its range picker and selected-year project table are independent of all other charts.

The initial local register contains 17 events across 13 project phases, with annual display rows for 2018–2026, reviewed on 2026-11-15. This is a deliberately incomplete public-evidence sample, **not a global census**. The current year contains events to the review date only and is not annualized. A zero means no event of that category was recorded in this register; it does not imply zero worldwide. Years beyond an old review date are never appended as zeros. Unknown event capacities remain blank; known amounts in the same year form a labelled subtotal, and years with only unquantified events have a gap and a question mark. The project table and tooltip expose these distinctions without adding a source/coverage panel.

The reviewed definitions are:

- **Permanent retirement:** exhausted or permanently closed copper mines, dated when mining permanently ceased. Temporary suspension, care and maintenance, strikes, power outages and lower ore grades are excluded. Stockpile processing and a continuing downstream smelter do not prevent an exhausted upstream mine from being classified as retired. DeGrussa's exhausted underground mine is distinct from its processing plant's later care-and-maintenance status; Mount Isa's underground copper mines are distinct from its continuing smelter and zinc/lead operations.
- **Commissioning:** first copper from a new mine or incremental phase, including a documented trial-production milestone. Reaching full output in a later year does not count again. Restarts and acquisitions are not new commissioning. Whole-project nameplate/design/steady-state annual copper capacity is used; reported annual production, copper equivalent, ore throughput and smelting/refining capacity are excluded. Some designs specify an initial multi-year average; those are identified in the project notes rather than treated as exact constant future output.
- **Construction start:** first verified physical mine/phase development, including a mine-access box cut or main plant civil works. A feasibility study, board approval, permit, procurement order or preparatory camp/road alone is insufficient. Restarting suspended construction does not create a second event. Capacity uses the phase design verified at the review date and is not a real-time forecast available in the original construction year.
- **Expansions:** incremental phase capacity only. A reported whole-site total cannot be counted as the addition. If comparable before/after capacity is available, the adapter checks their difference. Julong Phase 2 has confirmed construction and commissioning events, but the reviewed disclosure gives a total future output range and previous actual output, not a single comparable capacity increment; it remains unquantified. The initial QB2 record similarly preserves the commissioning event without treating copper-equivalent headlines or a production guidance range as a precise capacity point.

Evidence comes from company reports and official statistical tables. The [USGS Australia 2024 industry structure table](https://pubs.usgs.gov/myb/vol3/2024/myb3-2024-australia.pdf), page 14, supplies estimated mine copper capacities, separately from the [Sandfire 2023 report](https://www.sandfire.com.au/wp-content/uploads/2023/09/2023-Annual-Report-2023.pdf) and [Glencore closure announcement](https://www.glencore.com.au/media-and-insights/news/mount-isa-copper-operations-celebrating-a-legacy-of-more-than-70-years) establishing the events. Commissioning/construction evidence also includes [Ivanhoe's 2022 AIF](https://ivanhoemines.com/wp-content/uploads/2022_annual_Information_form.pdf), [Phase 3 announcement](https://www.ivanhoemines.com/wp-content/uploads/20240819-Kamoa-Kakula-Phase-3-update-VF2.pdf), [CMOC's 2023 interim report](https://en.cmoc.com/uploadfile/2023/1110/20231110072214374.pdf), [Zijin's Julong Phase 1 announcement](https://www.zijinmining.com/sustainable/esg-message-detail-119220.htm), [Anglo American's Quellaveco announcement](https://www.angloamerican.com/media/press-releases/2022/26-09-2022), and [Southern Copper's 2025 filing](https://www.sec.gov/Archives/edgar/data/1001838/000110465926021492/scco-20251231x10k.htm). Per-event sources and paraphrased evidence are retained locally; these are reviewed transcriptions, not a claim of automated comprehensive news collection. Dates with conflicting or insufficient evidence are omitted pending review, including Zhunuo's first construction year in this initial register.

To reproduce or extend the offline prototype, copy the ignored `data/manual/copper-capacity-events.json` file or create a reviewed register with `schema: 1`, `unit: "t Cu/year"`, `coverage: "reviewed-projects-not-global-total"`, `start_year`, ISO `as_of`, and an `events` array. Each event requires `id`, a stable mine-and-phase `project_id`, `year`, `kind` (`retired`, `commissioned`, `started`), and the corresponding `milestone` (`permanent_closure`, `first_production`, `physical_construction_start`). Supply bilingual `project_en/zh`, `country_en/zh`, `note_en/zh`, plus `event_source`, `capacity_source`, `event_evidence`, and `capacity_evidence`. `ownership_basis` must be `100%`; `scope` is `whole_project` or `incremental_phase`; `capacity_tpa` is a positive finite copper-capacity value or null, with `basis` of `design`, `official_estimate`, or `unquantified` respectively. Optional `before_tpa` and `after_tpa` must reconcile an incremental phase. Use separate phase identifiers to avoid double-counting entire mines. For an explicit offline review, call `capacity.run(Path("investdiy/global_track_copper/data"))` after importing `Path` from `pathlib` and `capacity` from `investdiy.global_track_copper`. Normal CLI updates, including `--fundamentals` and `--refresh-fundamentals`, skip this prototype. Generating its CSVs does not enable the chart. New annual data is not committed to Git.

Validation rejects duplicates, future event years, unsupported units/bases, temporary closures, inconsistent expansion arithmetic, missing evidence and construction after first production of the same phase. All validation completes before either output is replaced. The outputs share a content digest; the browser rejects mismatched generations and also reconciles totals/counts with the underlying event rows. Invalid or missing capacity files leave all other sections available. The map register is intentionally separate: its latest status and output cannot establish historical capacity changes.

## Copper mine map

The map uses [Critical Minerals Map's public site register](https://criticalmineralsmap.com/data/sites.json) ([methodology](https://criticalmineralsmap.com/methods/)), selecting entries with copper among their commodities and `stage=mine`. Refineries, smelters and historical geological occurrence layers are excluded. The 2026-11-14 local build contains **41 mines, projects or mine districts in 21 countries**, After primary-source review, this includes 29 operating sites, four construction projects, six planned/development projects, one commissioning/ramp-up site and one site processing stockpiled ore under preservation and safe management. This is a curated international register, not a complete census of every copper mine. Multi-mine districts remain identifiable as districts and are not split into invented individual production figures.

The register supplies initial names, coordinates, country, operating company, listed owners, status and the status-confirmation month. Reviewed primary disclosures supplement or correct these fields through a persistent local overlay. Statuses and ownership are compiled from linked company/government announcements and other reporting; this tool does not independently certify every entry or imply real-time mine operation. Shareholder lists may be incomplete. Status dates remain visible, with a warning after a year. The register download date is never substituted for a status date. Future dates, unsupported statuses, invalid coordinates, missing evidence and duplicate identifiers reject the update. Country names are bilingual; reviewed Chinese mine/company names are displayed when available and are searchable in either language. Other proper names remain as reported.

Mine output comes from [World Mining Monitor's public production database](https://github.com/kadoa-org/world-mining-monitor), which extracts company reports and retains source-document evidence. Explicit, reviewed ID mappings join it to the register: there is no fuzzy-name or proximity matching and no separate dots for each shareholder. After the November 2026 review, the local build includes reported output for **23 sites** (previously 16) and owner/company information for **40 of 41 entries**. Reporting periods and scopes vary; these are not 23 directly comparable annual figures. For Escondida, Collahuasi, Chuquicamata and El Teniente, COCHILCO table 2.3 supplies whole-operation 2025 output in preference to shareholder-only records. Other sites show the latest accepted reporting period, often a quarter, with the product form and reported scope. This is not necessarily a whole-mine calendar-year number.

The review adds seven previously missing production observations from primary disclosures:

| Mine / operation | Reporting period | Copper output (tonnes) | Primary evidence and scope |
|---|---|---:|---|
| Julong (Qulong) | 2025 | 193,820 | [Zijin results](https://www.zijinmining.com/investor/2025-newyeji.htm), whole-operation mined copper; not the attributable-output column. Listed direct/indirect interest is 58.16%. |
| Dexing | 2025 | 152,200 | [Jiangxi Copper annual report](https://www.hkexnews.hk/listedco/listconews/sehk/2026/0327/2026032700133_c.pdf), printed pp.27–28, copper in concentrate, including Fujiawu. |
| Riotinto | 2025 | 51,139 | [Atalaya operating table](https://atalayamining.com/operations/riotinto-district/riotinto-15-mtpa-plant/), contained copper, not payable copper or concentrate mass. |
| KGHM Polish copper belt | 2025 | 401,100 | [KGHM annual results](https://media.kghm.com/en/news-and-press-releases/higher-net-profit-costs-control-and-ambitious-plans-for-the-future-kghm-summarises-2025), three Polish mining operations, copper in concentrate; excludes overseas mines and refined production. |
| Kamoto / KCC | 2025 | 188,700 | [Glencore production report](https://www.glencore.com/.rest/api/v1/documents/static/a8114247-02e8-4bd8-bc04-81f411ba631c/GLEN_2025-FY-Production-Report.pdf), p.10, copper metal, 100% basis. |
| Voisey’s Bay | 2025 | 18,600 | [Vale production report](https://filemanager-cdn.mziq.com/published/53207d1c-63b4-48f1-96b7-19869fae19fe/c4dceca9-6ed8-408a-8065-b6f7e86810da_0127_relatorio_de_producao_i.pdf), p.5, finished copper by feed source. |
| Cobre Panama | Q3 2026 | 13,229 | [First Quantum quarterly results](https://www.first-quantum.com/es/news/first-quantum-minerals-publica-los-resultados-del-tercer-trimestre-de-2026/), authorised stockpile processing; mining has not been assumed to restart. |

The 32 reviewed records also fill shareholder information and distinguish acquisitions from conditional earn-in options. Notable corrections include Boliden's ownership of Neves-Corvo, the DRC State's 5% interest in Mutanda, CMOC's 71.25% direct/indirect KFM interest, and Global Panduro/RCF's completed acquisition of Las Cruces. Skouries is shown as commissioning/ramp-up after first concentrate in September 2026, not as already in commercial production. Source dates and contextual bilingual notes are retained; a review date does not make every observation current to that day.

Reviewed observations live in ignored `data/manual/mine-details.json`, a JSON list. Each item requires `id`, ISO `reviewed_on`, nonempty HTTP(S) `sources`, `evidence`, and an `updates` object. Only existing mine IDs and an explicit field allowlist are accepted. A production update must include all of `production_t`, `production_period`, `production_basis`, `production_form`, `production_scope`, `reporter`, `production_source` and `production_evidence`. The production URL must appear in the reviewed source list. Annual periods are calendar years; do not relabel a June fiscal year as a calendar year. Status changes require both `status` and its source-supported `status_asof` month. Optional `name_zh`, `owners_zh`, `operator_zh`, `production_scope_zh`, `note_en` and `note_zh` provide localized detail.

Both cached builds and `--refresh-fundamentals` reapply this file after upstream imports. All reviews are validated before replacement; unknown/duplicate IDs, missing evidence, future periods, invalid units/forms, nonfinite output or partial production bundles reject the update and preserve the prior CSV. Older reviewed production/status cannot replace a more recent accepted upstream observation. Keep this local file when migrating or backing up data: a fresh clone does not contain these manually researched observations. To extend the review, add or replace an entry with primary evidence and rerun `--skip-fetch --fundamentals --strict`.

Production filters require a copper production metric, recognized original units, a completed reporting period, source evidence and provider confidence of at least 0.9. Original unit conversion is cross-checked against the provider's normalized value. Sales, ore quantities/grades, forecasts, guidance, capacity, unknown product forms and unsupported units are excluded. June-year reporters require an explicit calendar-period mapping. Calendar-year FY values for the current year are rejected conservatively. Conflicting observations or ambiguous product components remain blank; quantities from different products or shareholders are never summed. The database's confidence and normalization checks do not independently prove the company-report extraction is correct. Preserve the source excerpt for review.

The map does not replace missing production with zero, repeat a group total at individual mines, infer status from an old production number, or multiply quarterly output into an annual estimate. Some companies disclose combined operations rather than individual mines; those fields stay missing. In particular, CMOC's combined TFM/KFM annual output is not assigned to either mine, and Copper South Australia's group output is not assigned to Olympic Dam. A missing output for a development project is also not an assertion of zero production. Production dates, ownership basis and product form must be checked before comparing mines.

Map marker sizes use reported-period **monthly average copper output**: calendar-year output divided by 12, half-year by 6, quarter by 3 and nine-month output by 9. The original tonnage, period, product and ownership basis remain visible; the monthly value is a display normalization, not a production forecast. Equity output is not inflated to a guessed whole-mine figure. Different reporting years/product bases still limit comparisons.

The fixed square-root radius scale (24 px at 125,000 tonnes/month) makes circle area proportional to output. A 2.5 px minimum keeps small observations visible; explicit zero is a hollow point. Missing output or an unrecognized period uses a **question mark**. The size legend includes sample monthly values and explains the convention. Filtering retains the scale, selection adds a separate outline, and zoom keeps symbols the same size. Large bubbles render below small ones; every mine remains accessible through the table.

Search covers mine names, companies and countries; filters cover country and status. Buttons zoom and reset the map, dragging pans it, and optional labels show mine names. Ctrl+wheel also zooms without capturing normal page scrolling. A paginated keyboard-accessible table provides the same mine selection as map points. No online map tiles, geocoding calls, analytics or CDNs are used. The vendored [Natural Earth 1:110m country geometry](https://www.naturalearthdata.com/about/terms-of-use/) is public domain; its license/provenance note is stored beside the asset. All browser data requests are local.

Additional ignored files:

| File | Content |
|---|---|
| `raw/fundamentals/cochilco-2000-2025.xlsx` | Official annual and Chile mine production workbook |
| `raw/fundamentals/mine-register.json` | Dated mine status, ownership and linked evidence |
| `raw/fundamentals/mining.db` | Public production snapshot; downloaded with version-checked HTTP ranges |
| `manual/mine-details.json` | Persistent reviewed primary observations, ownership, bilingual names/notes and evidence |
| `raw/fundamentals/review-2026-11-14/` | Archived company documents used in the review |
| `raw/fundamentals/icsg/` | ICSG source PDFs, including accepted dated rolling-table editions |
| `out/refining.csv` | Reported primary, secondary and total refining, secondary share, publication and provenance |
| `out/annual.csv` | Annual mine/refined production, refined consumption, balance and provenance |
| `out/mines.csv` | Map records, missing values, reporting periods/bases/forms, source URLs and evidence |

Fundamental data and source documents remain ignored by Git. Only source adapters, UI code, tests and the static geographic base map belong in the repository. Detailed provenance and coverage remain in CSVs and this document; there is no new frontend source/coverage panel.

## Validation

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_copper*.py'
node --check investdiy/global_track_copper/web/app.js
node --check investdiy/global_track_copper/web/strings.js
node --check investdiy/global_track_copper/web/fundamentals.js
node --check investdiy/global_track_copper/web/fundamentals-strings.js
node --check investdiy/global_track_copper/web/capacity.js
node --check investdiy/global_track_copper/web/capacity-strings.js
curl -s -o /dev/null -w '%{http_code}' http://localhost:8765/api/tools.json
```

Tests use synthetic fixtures to verify unit conversion, VAT boundaries, premium signs, missing-day alignment, parser identity checks, zero placeholders, stock-component reconciliation, report dates, paired ECB cross rates, bad-history quarantine, FX migration, import validation, revisions, empty exports and preservation of valid cached history on source failure. Browser checks cover both languages, narrow layouts, range independence, tax/metric switches, legend toggles and empty/error states.
