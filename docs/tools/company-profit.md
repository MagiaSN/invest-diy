# Company Profit Forecast

The calculator at `/company-profit/` estimates attributable profit for Zijin Mining and CMOC. Each company has its own reported production, realized prices, costs and historical backtests. Both tabs support production guidance, price presets, editable profit bridges, price sensitivity, scenario JSON and backtest CSV downloads.

A prominent bilingual notice above the page title states that estimates may be wrong, accuracy is not guaranteed, and users bear responsibility for their decisions. Its text and mounting logic are centralized in the shared `investdiy/web/static/site.js`; the page opts in with `data-site-disclaimer="profit-forecast"`.

Zijin Mining opens first. Switching companies retains edits, price units, selected presets and invalid drafts for the current visit. Both models also work in the standalone HTML.

## Build and run

The default Zijin historical baseline is a checksum-pinned [GitHub release asset](https://github.com/MagiaSN/invest-diy/releases/tag/company-profit-baseline-v1), containing the reviewed numerical data and public report references extracted from the company research record. It contains no research prose. A fresh checkout downloads this baseline into ignored `data/raw/`; subsequent builds verify and reuse it. Each update fetches the latest available metal quotes and FX reference rates, then rebuilds the page and offline artifact:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m investdiy.company_profit
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m investdiy.server
```

Use `--source /absolute/path/to/company/CLAUDE.md` to explicitly override the Zijin baseline with a research record containing `PROFIT_MODEL_DATA_START`. Both paths verify the profit attribution, tax, unit conversion and bridge reconciliations, then create ignored files under `investdiy/company_profit/data/out/`:

- `history.json` contains both verified company histories and their source fingerprints. `history.js` provides Zijin data and the shared metal and FX snapshot to the browser. `cmoc-history.js` supplies the CMOC report inputs.
- `market-status.csv`: collection time and each metal/FX observation date; `as_of` is the oldest observation date for homepage and publication freshness checks.
- `company-profit.html`: a self-contained HTML file with inline CSS, JavaScript, translations and historical data. It works without a server or network connection.

Do not commit these generated data files. A fresh checkout needs network access and the build command; a separate research checkout is not required. No CDN is used. Scenario inputs are not persisted; the shared language preference is saved in localStorage when available. Scenario calculations run in the browser. The browser reads the saved market snapshot and never fetches prices or FX from an external service. There is no live price API endpoint. Both module entry points (`investdiy.company_profit` and `investdiy.company_profit.build`) refresh the snapshot during builds; page reloads read the existing snapshot. Public export includes the page, scripts and generated outputs. Zijin baseline revisions require a new release asset and an updated SHA-256 pin in `build.py`.

On first load, the Zijin model initializes costs and advanced parameters from reported 9M 2026, applies the 2026 production target (gold 105 t, copper 120 ×10,000 t, silver 520 t), then applies the latest saved four-metal prices. Zinc remains the baseline volume because the production target does not disclose zinc separately from lead; it still needs an explicit annual assumption. Until all production volumes cover the same period, the initial output should not be described as a complete FY 2026 forecast. If a snapshot is missing, the page reports that state and retains manually editable baseline prices. Historical presets include FY 2020–2025, H1 2026 and 9M 2026. Applying a historical preset replaces model input values with that period, retains the selected display units, and clears applied production/market provenance; it does not reapply the startup defaults. Same-period reproduction is a reconciliation, not validation.

Sales volume, cost and advanced fields are initially rounded to four decimal places. Price displays use four decimals (six for USD/lb), while retaining the canonical CNY value until manually edited so unit switching does not alter earnings. Manually entered prices are converted from the selected unit. The historical backtest retains the original full-precision parameters. JSON exports include the complete current inputs, outputs, baseline and source fingerprint.

## CMOC

The 2026 guidance presets use the lower bound, arithmetic midpoint and upper bound for copper (760,000–820,000 t), cobalt (100,000–120,000 t), molybdenum (11,500–14,500 t), tungsten (6,500–7,500 t), niobium (10,000–11,000 t), gold (6–8 t annualized) and phosphate fertilizer (1.05–1.25 million t). The default midpoint uses costs and monthly associate income from 9M 2026, with forecast tax pooled from FY 2023–2025. Gold uses 31.1034768 grams per troy ounce. Copper, cobalt and fertilizer output display in 10,000 tonnes, while other output displays in tonnes. [2025 annual report](https://static.cninfo.com.cn/finalpage/2026-04-02/1225072765.PDF)

The Sales volume field accepts units sold. Its presets use company production guidance directly. Selling price and unit sales cost are user inputs. The earnings model starts with those inputs and computes product gross profit, pre-tax profit, tax and attributable earnings. Guidance and quotes provide editable scenario defaults. Copper and gold use saved SHFE quotes. Other selling prices initialize from the latest modeled report’s product revenue divided by sales. Historical presets use the selected report’s actuals. The copper/cobalt sensitivity matrix varies the two prices independently.

Each full-year test uses sales volumes from the original target annual report. Dividing product revenue and cost of sales by reported units sold gives the realized unit price and cost. Gross profit therefore reconciles by product. Financial parameters use reports through the preceding full year. Reported attributable profit enters the error calculation.

| FY | Parameter year | Estimated parent profit | Reported parent profit | Previous error | Revised error |
| --- | --- | ---: | ---: | ---: | ---: |
| 2021 | 2020 | 61.13 | 51.06 | +33.64% | +19.72% |
| 2022 | 2021 | 54.31 | 60.67 | −19.72% | −10.48% |
| 2023 | 2022 | 83.98 | 82.50 | +10.30% | +1.80% |
| 2024 | 2023 | 144.48 | 135.32 | +5.11% | +6.77% |
| 2025 | 2024 | 194.09 | 203.39 | −8.11% | −4.57% |

Amounts are in CNY 100m. On the same annual sales, prices and costs, five-year MAPE falls from 15.38% to 8.67%. Maximum absolute error falls from 33.64% to 19.72%. FY 2024 deteriorates by 1.65 percentage points using unrounded errors. All five years were examined during model development.

In FY 2021 the previous formula underestimated group tax expense by 21.63. Its tax rate came from FY 2020 alone (13.83%). The new forecast divides total tax expense by total pre-tax profit over the three most recent completed fiscal years available at the baseline. For FY 2021 the pooled rate is 23.15%; the reported outcome was 38.01%. FY 2018 and 2019 seed only the tax history using the consolidated income statement published in the 2019 annual report. Forecast rates outside the supported 0–60% range or a nonpositive pooled denominator fall back to the baseline effective rate. Historical scenario presets load the selected report’s tax rate for reconciliation. [FY 2019 annual report](https://static.cninfo.com.cn/finalpage/2020-03-30/1207423515.PDF)

Associate and JV income now uses the prior report’s monthly earnings times scenario months. CMOC’s investments include Huayue nickel/cobalt and the Chinese molybdenum joint venture. Their earnings can vary independently of consolidated copper margins. In FY 2023 the copper-linked formula overstated associate income by 13.79. A monthly run rate still leaves exposure to new investments and project ramp-ups. [FY 2022 annual report](https://static.cninfo.com.cn/finalpage/2023-03-18/1216148712.PDF)

The revised FY 2021 estimate still understates tax expense by 13.68. For FY 2022 the tax-expense error falls from a 5.61 overestimate to a 0.35 underestimate, while other pre-tax items and associate income remain 8.06 and 6.48 below reported amounts. In FY 2023 the associate-income overestimate falls to 2.70. Other pre-tax items are still 28.09 too high and minority profit is 27.92 too high, so those two errors nearly offset in attributable profit.

The FY 2020–2022 records preserve copper/cobalt, molybdenum/tungsten and niobium/phosphate group economics. For each pair, combined reported tonnes multiplied by the blended unit price or cost recovers the disclosed group revenue or cost of sales. The 2020 niobium and phosphate financial lines are summed for comparability. Australian NPM stays in the residual, as in subsequent years. The grouped reports appear in the validation audit and sources. Interactive single-product presets begin in 2023. [2020 annual report](https://static.cninfo.com.cn/finalpage/2021-03-23/1209426961.PDF) · [2021 annual report](https://static.cninfo.com.cn/finalpage/2022-03-19/1212626342.PDF) · [2022 annual report](https://static.cninfo.com.cn/finalpage/2023-03-18/1216148712.PDF)

The bridge scales other net pre-tax items by mining product revenue at the baseline ratio. Trading, eliminations and expenses can move differently from mining margins. For example, a higher unit sales cost now reduces mining gross profit while leaving this revenue-based line unchanged.

The model allocates group net profit up to the comparable baseline amount at the baseline parent share. Additional profit uses the change in attributable profit divided by the change in group net profit between the two most recent consecutive annual reports available at the baseline. The baseline share also applies to losses and substitutes for an unavailable or out-of-range incremental share. The FY 2024 test uses the baseline share because the 2022–2023 incremental share exceeds 100%. For FY 2025 the incremental share is 76.24%, versus 87.53% on baseline earnings. The FY 2025 minority-profit estimate is 37.59 against 36.89 reported. The revised total still contains offsetting errors.

Scenario months scale the baseline group net profit to the modeled period. Applying annual guidance sets 12 months. Historical presets use their own duration, including the two 2026 interim reports. Those reports remain available for scenario reconciliation. Scenario exports include the two allocation rates and the baseline net profit per month.

## Parameter presets and actuals

On the Zijin tab, the preset cards are ordered **Sales volume parameters → Price parameters → Historical parameters**. Sales volume and historical selections apply when their button is clicked. The price dropdown contains only **Latest snapshot**, with an apply button to restore that saved set after edits. Separate **+10%** and **−10%** buttons immediately compound on the current selling prices. The source-period label and JSON export continue to refer to the last applied historical preset, even when another period is selected. This label identifies the parameter origin, not a claim that edited costs and ratios still equal the original values. The groups have separate scopes:

- **Sales volume parameters:** set gold, copper and silver sales volumes from the selected annual guidance. Preserve zinc, all selling prices, costs and other profit assumptions. Annual guidance sets the scenario duration to 12 months. When starting from an interim historical preset, the retained zinc volume still needs an explicit annual assumption.
- **Price parameters:** restore the latest saved four-metal selling-price assumptions, or use the immediate ±10% buttons. All price actions preserve sales volumes, costs and advanced parameters and honor active display units. Snapshot dates and source details remain available on the page.
- **Historical parameters:** load reported sales volumes, realized prices, unit sales costs, tax, attribution and profit bridge parameters together.

Historical estimate-versus-actual results are shown in the rolling validation section, with annual error metrics and CSV export. Current scenario inputs and estimated profits are displayed without a separate baseline-actual comparison card or parameter-difference table. Invalid drafts suppress current results until corrected.

### Production guidance

Source: Zijin announcement 2026-012, dated 9 February 2026, PDF p3, provided in the adjacent research repository as `紫金矿业-601899_关于三年（2026—2028年）主要矿产品产量规划和2035年远景目标纲要的公告.pdf`. The table was checked in both extracted text and the rendered PDF. An [official English version](https://www.zijinmining.com/upload/file/2026/02/09/c08d3f959bdd4800a9c30c15e6afaab5.pdf) is linked from the page.

| Preset | Gold, t | Copper, 10,000 t | Silver, t |
|---|---:|---:|---:|
| 2026 target | 105 | 120 | 520 |
| 2028 lower bound | 130 | 150 | 600 |
| 2028 midpoint scenario | 135 | 155 | 650 |
| 2028 upper bound | 140 | 160 | 700 |

The midpoint is an arithmetic scenario assumption, not a separately disclosed company target. The announcement has no 2027 target, so no 2027 preset is offered. Zinc/lead guidance is combined (400,000 t in 2026; 400,000–450,000 t in 2028) and cannot replace zinc-only production. Lithium carbonate and molybdenum guidance remain outside this four-metal model and are not added to the residual bridge again.

### Current-price quotes

Build-time collection retrieves all four metals from the [SHFE delayed-quote page](https://www.shfe.com.cn/reports/marketdata/delayedquotes/) through its public data endpoints:

```text
https://www.shfe.com.cn/data/tradedata/future/delaymarket/delaymarket_{au|cu|zn|ag}.dat
```

The collector selects the valid contract with greatest open interest on the latest available observation date for each metal. This is a selection rule, not an exchange designation of a main contract. Quotes are delayed about 30 minutes and may remain at the last session during closures. Quotes over seven days old, future timestamps beyond five minutes, missing prices and nonfinite values are rejected during collection.

FX comes from the [ECB daily reference-rate XML](https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml). Same-date CNY/EUR divided by USD/EUR gives CNY per USD. The FX observation date is retained separately from metal observation times and the build timestamp. The collector rejects missing, duplicate, nonpositive, nonfinite, future or more-than-seven-day-old FX references. It does not fabricate a same-date market/FX match: the UI shows both dates.

Every build fetches the four metal feeds and the FX feed afresh. A collection or validation failure stops the build before replacing output files, preserving the previous data and offline page while reporting the failure. The shared `update.yml` workflow collects and publishes this snapshot at **09:17 and 16:17 Beijing time, Monday–Friday**, independently of the ETF and PBoC gold schedules. Manual workflow runs default to all public data tools, with a `refresh_scope: company-profit` option to refresh only this tool; missing outputs also trigger rebuilding on any schedule. GitHub may delay scheduled starts. Collection failures or publication freshness checks stop deployment and preserve the live site. Routine local data refreshes import the workflow’s `site` artifact first, as described in the [data update SOP](../development.md#data-update-sop). Ordinary page reloads and all browser interactions use saved data, including offline; an older saved snapshot remains usable. The snapshot label shows the collection date, while the expanded table shows each actual quote time and the FX reference date. The Latest snapshot option means the latest saved set, not current live market prices.

The saved selling-price assumptions use gold VAT 0%, copper/zinc/silver VAT 13%, and 100% realization. Gold quotes are CNY/g, copper and zinc CNY/t, and silver CNY/kg. Silver is divided by 1,000 to match CNY/g; copper, zinc and silver are also divided by 1.13. These are conversion assumptions, not company-specific realized prices; treatment charges and other discounts can be reflected by manually editing the resulting inputs. Unit switching never repeats this VAT conversion.

Gold selling prices support **CNY/g** and **USD/troy oz**; copper supports **CNY/t**, **USD/t** and **USD/lb**. Sales volume units and cost fields retain their original units. The current snapshot's CNY/USD rate is used for display and input conversion, including when historical presets are selected; these USD equivalents are not historical FX observations or separate overseas exchange quotes.

```text
gold CNY/g = USD/troy oz * CNY per USD / 31.1034768
copper CNY/t = USD/t * CNY per USD
copper CNY/t = USD/lb * (1000 / 0.45359237) * CNY per USD
```

The model retains canonical CNY prices while a user switches units, avoiding cumulative rounding and profit changes. Manual entries in USD convert back to CNY before calculation; resetting presets, applying the latest snapshot and sensitivity selections honor the chosen display unit. Without a valid FX rate, USD selectors are disabled while CNY inputs remain usable. Historical backtests keep their original parameters and units.

JSON scenario exports include canonical CNY inputs, chosen display-price units, the FX value/source/date, the last applied historical and production presets, and any last applied market snapshot with its conversion assumptions. Current inputs remain authoritative after manual edits. No network access is needed for the standalone HTML's latest-price preset or unit conversion.

## Model

In the Zijin model, gold and silver production is in tonnes and price/cost in CNY per gram. For copper and zinc, production is in 10,000 tonnes and price/cost in CNY per tonne. All output profits are CNY 100 million. Historical realized prices and costs are sales-weighted across gold bullion/concentrate and copper concentrate/electrodeposited/electrolytic products.

```text
consolidated sales (t) = quantity entered in Sales volume * volume_to_t
metal gross profit (CNY 100m) = consolidated sales (t) * (selling price - sales cost) * price_units_per_t / 1e8
associate earnings = copper GP * associate earnings ratio
other net pre-tax items = baseline residual / baseline months * scenario months
pre-tax profit = four-metal GP + associate earnings + other net pre-tax items
tax = max(pre-tax profit, 0) * effective tax rate
group net profit = pre-tax profit - tax
core attributable profit = group net profit * attributable share
scenario attributable profit = core attributable profit + incremental net adjustment
```

In these formulas, prices and costs use the canonical CNY units above. `volume_to_t` is 1 for gold/silver and 10,000 for copper/zinc; `price_units_per_t` is 1,000,000 for gold/silver and 1 for copper/zinc. Ratios are decimals in the formulas; the corresponding editable fields display percentages.

Annual tests use consolidated sales. Manually entered quantities and production guidance are treated as sold in full, including when a guidance figure contains equity-accounted output. Associate earnings are explicitly modeled separately, using copper GP as a simplified driver for all associates.

The residual other net pre-tax bridge is determined by baseline pre-tax profit less four-metal GP and associate earnings. It includes other mining products, refining/trading, eliminations, operating/financing expenses, resource taxes, impairments and other income. The formula carries forward the net monthly amount. Administrative and financing costs, eliminations and other activities can move independently of mining margins. Changes in the size or mix of those activities remain a source of error. Tax is an effective group rate, not an additional statutory tax on individual associate profits. Unit sales costs already include depreciation/amortization and transport; neither depreciation nor capex is deducted again.

The incremental adjustment is **attributable, after-tax** and only includes contributions beyond those already implied by the bridge. It is not added to displayed group profit or NCI. It is not backtested. Use it carefully for incremental lithium/molybdenum projects, acquisitions, hedging and one-offs; do not add all already consolidated Zangge earnings again.

## Historical validation

Both tabs default to the latest five complete fiscal years in the report history. The table, input audit, metrics, error band and exports use that window. FY 2021–2025 uses FY 2020 as the opening parameter anchor. The local annual supplement extends the pinned Zijin release with original FY 2020 and 2021 mining sales, unit costs and consolidated earnings. Target-year reported sales volumes, realized selling prices and unit sales costs enter the calculation. Prior-year reports supply the profit-bridge parameters.

Configured thresholds: annual MAPE ≤15% and maximum annual absolute percentage error ≤25%. Signed error is `100 * (estimated / actual - 1)`; MAPE is the unweighted mean of absolute annual percentage errors.

| Test period | Parameter year | Estimated attributable, CNY 100m | Actual, CNY 100m | Previous error | Revised error |
| --- | --- | ---: | ---: | ---: | ---: |
| 2021 | 2020 | 147.18 | 156.73 | −24.24% | −6.09% |
| 2022 | 2021 | 196.92 | 200.42 | −6.06% | −1.74% |
| 2023 | 2022 | 206.02 | 211.19 | −3.01% | −2.45% |
| 2024 | 2023 | 326.03 | 320.51 | −6.55% | +1.72% |
| 2025 | 2024 | 515.52 | 517.77 | −6.49% | −0.44% |

Five-year MAPE falls from 9.27% to 2.49% and maximum absolute percentage error from 24.24% to 6.09%. In FY 2021 the old formula deducted 105.77 of other pre-tax items versus 66.89 reported. The duration-based projection deducts 58.35. Associate earnings remain 11.21 below the reported amount. Meeting the configured thresholds describes these historical conditional tests; it is not an external certification or a future error guarantee. Model design had access to these years, so they are not a blind holdout; actual future production and prices are unknown. Prior-year annual reports also become available only after publication in the following year.

Original 2022 group production was visually checked in its own annual report: gold 56,360 kg, copper 877,317 t, zinc 402,321 t (excluding lead), silver 387,458 kg. Later 2023 comparatives change some of these figures, and are deliberately not used in the 2022 parameter anchor. Product sales and costs were visually cross-checked on PDF pp50–51; production on pp30, 33 and 53. Subsequent annual and interim source locations and links are included in the HTML and authoritative record.

The 2021 backtest has the largest absolute percentage error. Pre-tax items, tax and attribution can offset one another. Five annual observations are too few to estimate a statistical confidence interval. The UI's reference band merely applies the largest annual absolute error to the current estimate. It is suppressed for large scenario changes, nonzero manual adjustments or weak gross profits.

## Limits

The Zijin model is a calibrated group bridge, not a mine-level model. It does not forecast market-to-realized-price discounts, FX, inventory, product mix, new mines, ownership changes or acquisitions separately. Other businesses, including lithium, are implicit in the baseline residual and are not given a separate unvalidated volume-price forecast. Fixed costs do not disappear at zero production, making extreme low-output/low-margin scenarios unreliable. The no-tax-asset rule avoids automatic recognition of a benefit on losses, but mine-by-mine taxes and NCI attribution can still differ materially.

## Verification

```bash
node --test tests/test_company_profit.cjs
.venv/bin/python3 -m unittest discover -s tests -p test_company_profit_prices.py
node --check investdiy/company_profit/web/model.js
node --check investdiy/company_profit/web/presets.js
node --check investdiy/company_profit/web/strings.js
node --check investdiy/company_profit/web/app.js
curl -s -o /dev/null -w '%{http_code}' http://localhost:8765/api/tools.json
```

Tests check independent unit arithmetic, historical income/tax reconciliation, interim annualization, use of target unit costs and exclusion of target profits and bridge parameters, threshold acceptance, price sensitivity, loss tax handling, adjustment separation, invalid inputs, and self-contained HTML. Browser QA should cover both languages, a 390px screen, invalid drafts, sensitivity selection, exports and offline use with network requests blocked.

The current checks cover metal quote selection, ECB cross-rate arithmetic and validation, complete snapshot collection on each build, preservation of previous outputs after failed updates, snapshot embedding in offline artifacts, and removal of the live API. Model checks include troy-ounce and pound conversion, unit round trips, explicit tax conversion and incomplete-snapshot rejection. Browser QA covers both languages, desktop/mobile, offline use with network blocked, price-unit switching, USD input, preset field isolation, sensitivity selection, invalid drafts, JSON provenance and unchanged historical validation.
