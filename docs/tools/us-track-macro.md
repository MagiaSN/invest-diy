# US Macroeconomic Tracker

Monthly US inflation, employment and interest rates, served locally at
`http://localhost:8765/us-track-macro/` and publicly at
<https://invest-diy.surge.sh/us-track-macro/>. It is the third tool on the home
page, after the PE calculator and company-profit forecast.

## Update

```bash
.venv/bin/python3 -m investdiy.us_track_macro
.venv/bin/python3 -m investdiy.us_track_macro --skip-fetch
```

The first command downloads monthly series from FRED, BLS and BEA without API keys.
The second rebuilds output from the cached snapshot, preserving its fetch time.
The shared `update.yml` workflow refreshes and publishes this tool at **09:43
Beijing time on the 2nd of each month** (`43 1 2 * *` UTC). This collects releases
made during the preceding month; observation months still differ by indicator.
Other scheduled slots reuse its cached output, unless the output is missing.
Choose `refresh_scope: us-track-macro` for a manual update of this tool; other
tools reuse valid cached outputs. Failed collection prevents publication.
Routine local synchronization imports the workflow's `site` artifact under the
repository's [data update SOP](../development.md#data-update-sop).

Raw history is saved in `investdiy/us_track_macro/data/raw/fred.json`; the page
reads `data/out/monthly.csv`. Both locations are git-ignored. A failed fetch,
invalid series or regressing latest observation aborts the refresh with a nonzero
exit code and leaves the previous snapshot and dashboard intact. All series are
validated and calculated before the snapshot or output is replaced. The CSV is
replaced atomically. FRED and BEA histories and BLS observations from 1989 are downloaded on each run to incorporate
revisions; old and new observations are not merged across snapshots.

## Sources and definitions

FRED distributes the headline series and most inflation variants. Two detailed CPI baskets come directly from the BLS public API. BEA supplies the food-only and energy-only PCE exclusions in its underlying-detail workbook.
The links below document original agencies, units and adjustment conventions.

| Measure | FRED series | Original agency | Definition |
|---|---|---|---|
| CPI | [CPIAUCSL](https://fred.stlouisfed.org/series/CPIAUCSL), [CPIAUCNS](https://fred.stlouisfed.org/series/CPIAUCNS) | BLS | All-items CPI-U, US city average; 1982–1984 = 100. Adjusted for MoM/index, unadjusted for YoY. |
| PPI | [PPIFIS](https://fred.stlouisfed.org/series/PPIFIS), [PPIFID](https://fred.stlouisfed.org/series/PPIFID) | BLS | Final demand, goods and services; November 2009 = 100. Adjusted for MoM/index, unadjusted for YoY. |
| PCE | [PCEPI](https://fred.stlouisfed.org/series/PCEPI) | BEA | Headline chain-type price index, 2017 = 100, seasonally adjusted. Not nominal spending. |
| Unemployment | [UNRATE](https://fred.stlouisfed.org/series/UNRATE) | BLS | U-3 unemployment rate, civilian labor force aged 16+, seasonally adjusted. |
| Payrolls | [PAYEMS](https://fred.stlouisfed.org/series/PAYEMS) | BLS | Total nonfarm jobs, thousands, seasonally adjusted; establishment survey. |
| Federal funds | [FEDFUNDS](https://fred.stlouisfed.org/series/FEDFUNDS) | Federal Reserve Board | Monthly average effective federal funds rate, percent, not seasonally adjusted. Not the target range or month-end rate. |

The [variant catalog](../../investdiy/us_track_macro/web/variants.json) lists the source codes used by the collector and the charts.

| Family | Additional baskets | Treatment |
|---|---|---|
| CPI-U | Excluding energy, food, both, or shelter alone. Further exclusions remove food, energy and shelter together, optionally also used cars and trucks. | Unadjusted index for YoY, adjusted index for MoM and level. The last two baskets come from the [BLS API](https://www.bls.gov/developers/) using item codes `SA0L12E` and `SA0L12E4`. |
| CPI-U | Median CPI and 16% trimmed-mean CPI | Changes calculated from the [Cleveland Fed's adjusted index levels](https://fred.stlouisfed.org/release?rid=315). |
| Final-demand PPI | Excluding energy, food, both, trade services, or food, energy and trade services | Unadjusted for YoY, adjusted for MoM and level. Trade services measure wholesale and retail margins. See the [BLS aggregation definitions](https://www.bls.gov/ppi/fd-id/ppi-final-demand-intermediate-demand-aggregation-indexes-by-title-and-series-id.htm). |
| PCE prices | Excluding food alone or energy alone | BEA [monthly table 2.4.4U](https://apps.bea.gov/national/Release/XLS/Underlying/Section2All_xls.xlsx), sheet U20404-M, accounts DPXFRG and DPXERG. The latter excludes both energy goods and services. |
| PCE prices | Core, core excluding housing, services excluding energy and housing, market-based, market-based core | Seasonally adjusted BEA price indexes. Core PCE retains food services, including restaurant meals. |
| PCE prices | Excluding energy goods only | The [St. Louis Fed index](https://fred.stlouisfed.org/series/PCEEXENERGYGOODS) retains electricity and gas services. |
| PCE inflation | Trimmed mean | The [Dallas Fed](https://www.dallasfed.org/research/pce) publishes rates. YoY uses its 12-month rate. MoM converts the published one-month annual rate `a` to `100 × ((1 + a/100)^(1/12) − 1)`. Only rate views are available. |

## Calculations and dates

- YoY = `(index[t] / index[t - 12 calendar months] - 1) * 100`.
- MoM = `(index[t] / index[t - 1 calendar month] - 1) * 100`, not annualized.
- Monthly payroll gains = `PAYEMS[t] - PAYEMS[t - 1 calendar month]`, in thousands.
- Rate changes = current minus previous month, in percentage points.
- Missing inputs produce empty CSV fields and em dashes on the page. The monthly
  grid includes gaps; charts do not connect lines across missing months. No
  interpolation, forward filling or conversion of missing values to zero.
- Source dates denote observation months, not release dates. Only completed
  months are accepted. The dashboard starts in January 1990; earlier inputs are
  retained to calculate the first displayed changes. Final-demand PPI starts in
  November 2009; its YoY series starts a year later.
- Every headline and source row carries its own latest month. PCE may lag the
  other indicators. The home-page `as_of` date is the month-end of the slowest
  source's latest observation; `fetched_at` is the UTC retrieval timestamp.
- The page flags headline observations more than 75 calendar days after their
  observation month-end. A successful fetch is not a promise of a new release.

CSV rows are newest first. Original index/rate levels, payrolls in thousands,
derived changes, `as_of`, and `fetched_at` are retained without display rounding
(derived values are rounded to six decimals). Chinese payroll displays use
ten-thousands; English displays use millions for totals and thousands for gains.

## Page behavior

Six headline cards show the latest values and monthly changes. Each of the six
charts owns its range picker (1Y, 3Y, 5Y, all, custom); ranges are never put in the
URL. Each inflation chart has its own basket and measure selectors. Changing the basket preserves the range and selects YoY if the previous measure is unavailable. Summary cards always show all items. The history table follows each selected basket and the source table identifies the series and adjustment used. Legacy headline-only CSVs still load with just the all-items basket until the next full collection.
Payrolls switch between total jobs and monthly gains. Hovering shows the month
and value, and the table provides accessible exact observations by year. The
download includes every collected basket and the entire history, independent of chart and year selections.
All assets are local; both English and Chinese are supported, including missing
data and error states.

## Validation and limitations

```bash
.venv/bin/python3 -m unittest discover -s tests -p 'test_us_macro.py'
node --check investdiy/us_track_macro/web/app.js
node --check investdiy/us_track_macro/web/strings.js
curl -s -o /dev/null -w '%{http_code}' http://localhost:8765/api/tools.json
```

Tests cover the FRED CSV contract, invalid values, incomplete months, calendar
alignment, seasonal-adjustment selection, payroll units, missing values,
asynchronous release periods, failure retention and offline rebuilds.

Historical values may change with seasonal revisions and payroll benchmarks.
This tool shows the latest available history, not what was known on a historical
release date. Consensus forecasts, release calendars and the FOMC target range are outside its scope. FRED availability and source release
delays can prevent updates. CPI/PPI derived rates can differ slightly from news
headlines due to source precision, rounding and revisions.
