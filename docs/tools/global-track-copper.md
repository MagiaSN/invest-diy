# Global Copper Market Tracker

Local dashboard at `/global-track-copper/` for COMEX, LME and SHFE copper prices, exchange inventories and relative price premiums. English and Chinese pages use the shared local assets. This tool has `visibility: local` and is excluded from public export and publication workflows.

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

Prices and FX must share an observation date. There is no forward fill, nearest-date match or future-date lookup. COMEX/LME remains available without FX; each SHFE comparison requires same-date FX. The union of dates is retained in the daily CSV with blank cells for missing observations. Current UTC-date bars are excluded conservatively because they may still be in progress. Equal dates do not imply synchronized quote times across time zones.

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

## Validation

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_copper.py'
node --check investdiy/global_track_copper/web/app.js
node --check investdiy/global_track_copper/web/strings.js
curl -s -o /dev/null -w '%{http_code}' http://localhost:8765/api/tools.json
```

Tests use synthetic fixtures to verify unit conversion, VAT boundaries, premium signs, missing-day alignment, parser identity checks, zero placeholders, stock-component reconciliation, report dates, paired ECB cross rates, bad-history quarantine, FX migration, import validation, revisions, empty exports and preservation of valid cached history on source failure. Browser checks cover both languages, narrow layouts, range independence, tax/metric switches, legend toggles and empty/error states.
