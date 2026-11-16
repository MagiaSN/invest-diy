# Global Gold Tracker

Local page: <http://localhost:8765/global-track-gold/>. Package: `investdiy.global_track_gold`. The tool is **local only** and is excluded from the public export and scheduled publication workflow.

## Run

```bash
.venv/bin/python3 -m investdiy.global_track_gold
.venv/bin/python3 -m investdiy.global_track_gold --offline
.venv/bin/python3 -m investdiy.server
```

The normal command refreshes all sources. `--offline` rebuilds from validated raw downloads without network requests. Raw files and generated CSVs live in the ignored `investdiy/global_track_gold/data/` directory. No API key is required. Run the updater monthly after the World Bank release; IMF figures and WGC stock anchors arrive at different frequencies. This tool does not create a new scheduled workflow.

## Coverage

| View | Frequency and initial live coverage | Meaning |
|---|---|---|
| Cumulative mined gold | Year-end estimates from 2014, plus available quarter-ends in the latest year | Above-ground stocks as a proxy for cumulative mined gold; historical backcasts and the published anchor are distinguished |
| Gold value versus US debt | Monthly from December 2014; annual December observations | Estimated above-ground gold value versus gross federal debt and debt held by the public |
| Gold/oil | Monthly from 1960; WTI starts later where available | Barrels of Brent or WTI per troy ounce of gold |
| Gold/silver | Monthly from 1960 | Troy ounces of silver per troy ounce of gold |
| Annual demand by sector | Complete years from 2010; OTC-inclusive coverage from 2022 | Diverging stacked bars for jewellery fabrication, technology, bars/coins, ETF net flows and official net purchases; optional OTC and other |
| Official holdings and changes | Monthly from 2000, subject to country coverage | Tonnes, change from the preceding calendar month, and change from the same month a year earlier |
| Reserve ratios | Monthly where same-month components exist | Market-valued gold divided by total reserves or foreign exchange alone |

Economies: United States, Germany, Italy, France, China, Russia, Switzerland, India, Japan, Türkiye, Netherlands, Poland, United Kingdom, Saudi Arabia, Spain, Brazil, South Korea and Canada. This is an explicit comparison group, not a global total or an automatically maintained ranking. Euro-area national holdings are not added to an ECB or regional aggregate.

Each time-series chart has an independent range picker. Country buttons affect the holdings and reserve-ratio charts together. The latest-report table includes every covered economy regardless of chart selection. It shows separate holdings and ratio dates, and marks dates older than 120 days as delayed. Gaps stay missing in calculations and chart paths; zero holdings remain valid observations.

The cumulative mined-gold chart reads `stocks.csv` independently of prices and debt. It connects the available stock endpoints, without adding monthly observations. Gold points identify historical backcasts and a blue point identifies the published stock anchor; hover details repeat this distinction. The latest-anchor caption stays independent of the chart range. Its total approximates cumulative mined gold using above-ground stocks, so it excludes underground deposits, ignores losses and does not count recycled gold again.

The stock chart also shows the selected period's compound annual growth rate (CAGR): `(ending stock / starting stock)^(1 / years) - 1`, where `years = elapsed days / 365.25`. It uses the first and last finite, positive stock observations inside the selected range and displays their actual dates, which may differ from the range boundaries. Periods shorter than a year are compounded to an annual rate. Fewer than two distinct valid dates produce an unavailable value. The result inherits the stock series' estimation limitations.

## Sources

- [World Bank Commodity Markets](https://www.worldbank.org/en/research/commodity-markets): the updater discovers the current `CMO-Historical-Data-Monthly.xlsx` link rather than pinning a yearly download URL. It validates Gold and Silver in USD/troy ounce and Brent and WTI in USD/barrel. Only completed monthly observations are used.
- [WGC above-ground stock](https://www.gold.org/goldhub/data/how-much-gold): the publicly visible, explicitly dated quarter-end or year-end tonnage is the stock anchor. The login-gated historical workbook is not used.
- [WGC Gold Demand Trends](https://www.gold.org/goldhub/research/gold-demand-trends/gold-demand-trends-full-year-2025/supply): annual supply tables from the 2016 report onward provide two years of mine production per release. Reports are processed in ascending edition order so later annual revisions replace earlier values. For a partial current year, the latest quarterly report's rolling table supplies the year-to-date quarters, including its revisions. Recycling and producer hedging are excluded.
- [US Treasury Debt to the Penny](https://fiscaldata.treasury.gov/datasets/debt-to-the-penny/debt-to-the-penny): the Fiscal Data v2 API supplies `tot_pub_debt_out_amt`, `debt_held_public_amt` and `intragov_hold_amt`. The updater validates pagination and reconciliation of the selected month-end components.
- [IMF International Liquidity](https://data.imf.org/en/datasets/IMF.STA:IL): the public SDMX 2.1 API supplies monthly fine troy ounces and US dollars. `OBS_VALUE` is already in full units; `SCALE` is display metadata and is not applied as a multiplier.

## Gold market value and US debt

The value-comparison view includes a dashed reference line equal to gross US debt multiplied by 0.4, in the same USD-trillion units. It follows the annual/monthly selection and chart range, with values in the tooltip; unavailable debt observations remain gaps.

One metric tonne contains `1,000,000 / 31.1034768` fine troy ounces.

The stock anchor is all above-ground gold, including jewellery, bars, coins, ETFs, official and other mined gold. It excludes underground deposits and is not a measure of immediately available trading inventory.

Historical year-end stock is **reconstructed**, not downloaded from WGC's official historical stock series:

```text
stock at an earlier period end = public stock anchor − subsequent mine production
monthly stock = linear interpolation between the surrounding stock endpoints
estimated gold value = stock in tonnes × troy ounces per tonne × monthly average gold price
```

This assumes mined gold remains above ground, ignores losses and differences between historical statistical vintages, and inherits rounding and revisions in the public stock anchor. It can differ from previously published historical stock totals. The annual table uses December monthly average gold prices, not full-year average prices or December's last daily close. Monthly interpolation is an estimate, not an observed physical inventory. The model does not extrapolate beyond the latest stock anchor. Incomplete years appear only in the monthly view, not as completed annual observations.

Debt is the last reported balance in the same calendar month, at most four calendar days before month-end. Months without a sufficiently recent observation remain missing. Gross federal debt includes publicly held and intragovernmental debt; it is not marketable Treasuries alone and is measured at outstanding face value, not secondary-market value. Gold's monthly average valuation and debt's month-end balance have different timing conventions, disclosed on the page. The comparison ratio uses gross federal debt as its denominator.

## Price ratios

```text
gold / oil = monthly average gold USD/troy oz ÷ same-month oil USD/barrel
gold / silver = monthly average gold USD/troy oz ÷ same-month silver USD/troy oz
```

Gold/oil is barrels per troy ounce; gold/silver is ounces per ounce. Ratios of monthly average prices are not monthly averages of daily ratios. No futures contract stitching or exchange-rate conversion is involved. Missing prices or nonpositive denominators do not produce a ratio.

## Annual demand by sector

The demand chart reads `demand.csv` independently of stock estimates, prices, debt and individual-country reserves. It shows complete calendar years in tonnes, with its own range picker and two scopes: five core categories excluding OTC, or six categories including OTC and other. The latter displays only years with that field available; missing OTC is never inferred to be zero.

- Jewellery uses fabrication rather than retail consumption. Technology is the aggregate of electronics, other industrial uses and dentistry.
- Bars/coins and ETF net flows are the components of investment. The investment subtotal is validated but is not stacked again.
- Central banks and other official institutions are net purchases, not holdings or gross purchases. This global series is not computed by summing the 18 tracked economies.
- Negative ETF, official or OTC flows extend below zero. Positive stack height is therefore not net demand; a dark line with dots marks the source's net aggregate.
- OTC and other includes stock movements and residual items. It is not solely an estimate of OTC investment.

The baseline is the [2022 annual report's public chart](https://www.gold.org/goldhub/research/gold-demand-trends/gold-demand-trends-full-year-2022), covering 2010–2022 in whole tonnes. Its JSON configuration is decoded from the public chart feed without executing downloaded JavaScript. Later [annual HTML tables](https://www.gold.org/goldhub/research/gold-demand-trends/gold-demand-trends-full-year-2025) replace overlapping years as complete rows, including totals, precision and source attribution. Consequently, earlier years retain the 2022 edition rather than claiming to have all subsequent revisions. The chart is local and loads no remote scripts.

Units, year headers, all categories, investment subtotals and both aggregate identities are validated before saving. Rounding tolerances follow source precision: up to 3 tonnes for the whole-tonne chart and 0.3 tonne for the one-decimal tables. The updater rejects partial-year or malformed tables and preserves previous output on failure. Only a 404 for the newest, never-cached annual report is accepted as not yet published; an unavailable previously downloaded report remains an error. Offline rebuilding uses the downloaded reports. CSV rows include the report edition, page URL and data URL, also reflected in hover details. Annual source observations use a 450-day delay threshold rather than the monthly sources' 120-day threshold.

## Official reserve calculations

| IMF indicator | Meaning |
|---|---|
| `RGV_REVS`, `FTO` | Gold holdings in fine troy ounces |
| `TRGMV_REVS`, `USD` | Total reserves including gold at market value |
| `RXF11_REVS`, `USD` | Total reserves excluding gold |
| `RXF11FX_REVS`, `USD` | Foreign exchange reserves only |

```text
gold tonnes = RGV_REVS / troy ounces per tonne
market gold value = TRGMV_REVS − RXF11_REVS
gold share of total reserves (%) = market gold value / TRGMV_REVS × 100
gold / FX reserves (%) = market gold value / RXF11FX_REVS × 100
```

The first denominator includes gold, foreign exchange, SDRs and the IMF reserve position. The second excludes gold, SDRs and the IMF reserve position, can exceed 100%, and is a ratio between asset values rather than a portfolio weight. All components must belong to the same country and month. If positive holdings accompany a zero market-value residual, the valuation and ratios are treated as unavailable rather than zero; the latest-ratio table then uses an earlier valid month. The residual market valuation avoids mixing different national book-price conventions; no national book gold value is substituted for market gold value.

Monthly and annual changes require the exact previous calendar month or same month a year earlier. A reporting gap is not treated as zero flow or as a change over one month. Ratio movements reflect holdings, gold prices, exchange rates and changes in other reserve assets; they cannot by themselves identify central-bank trading. Country definitions and revisions can differ from WGC-adjusted official holdings, particularly for Türkiye. Russia and other late reporters may have substantially older data.

## Outputs and failure handling

`data/out/` contains `prices.csv`, `stocks.csv`, `market.csv`, `annual.csv`, `demand.csv`, `reserves.csv`, `sources.csv` and `summary.csv`. Market CSVs preserve the actual debt observation date, stock method and interpolation endpoints. Stock rows identify the anchor date and distinguish the published anchor from backcasts. Raw source tables remain in `data/raw/` for audit.

Each raw download is parsed and validated before atomic replacement. Derived CSVs are also replaced atomically. Sources refresh independently; an unsuccessful source retains the previous affected outputs, records an error and causes the updater to exit nonzero. The gold/debt comparison refreshes only when all three required source groups succeed together. The page loads sections independently, displays source status and dates, and shows an unavailable-data message when a first download is missing. A failed source never receives a new successful-fetch timestamp. Offline rebuilds are marked as cached and preserve the preceding successful-fetch timestamp.

## Validation

```bash
.venv/bin/python3 -m unittest discover -s tests -p 'test_gold*.py'
node --check investdiy/global_track_gold/web/app.js
node --check investdiy/global_track_gold/web/strings.js
curl -s -o /dev/null -w '%{http_code}' http://localhost:8765/api/tools.json
```

Tests use synthetic observations and verify source units, price-column alignment, duplicate rejection, missing values, period matching, stock backcasting and interpolation, debt pagination and component reconciliation, reserve denominators, and preservation of previous output when a source fails. The shared standard-library XLSX reader is also used by the copper fundamentals adapter, whose existing tests should pass after changes to that helper. Check both languages, chart controls, missing-data states and a 400px viewport in the browser.
