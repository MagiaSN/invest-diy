# Company Profit Forecast

A public calculator at `/company-profit/`, listed second on the toolbox home page after the PE Valuation Calculator. The tool is organized around company-specific profit models rather than a single industry; future models may cover coal, oil and gas, or container shipping. The implemented company model is **Zijin Mining**: its baseline parameters, historical data and validation remain specific to that company. The Python package is `investdiy.company_profit`; the page route is `/company-profit/`. It estimates attributable net income from mined gold, copper, zinc (excluding lead) and silver production and VAT-exclusive realized selling prices. It supports editable sales costs, consolidation conversion, tax, attribution, associate earnings and other profit bridge assumptions. The gold/copper sensitivity matrix applies a selected scenario to the inputs. Current assumptions and results can be downloaded as JSON; historical validation can be downloaded as CSV.

A prominent bilingual notice above the page title states that estimates may be wrong, accuracy is not guaranteed, and users bear responsibility for their decisions. Its text and mounting logic are centralized in the shared `investdiy/web/static/site.js`; the page opts in with `data-site-disclaimer="profit-forecast"`.

The company tab bar currently contains one selected tab, **Zijin Mining**, linked to its forecast panel. Additional company models are not yet available. The page offers JSON scenario and CSV validation downloads; the standalone HTML remains a build artifact without a page download button.

## Build and run

The default historical baseline is a checksum-pinned [GitHub release asset](https://github.com/MagiaSN/invest-diy/releases/tag/company-profit-baseline-v1), containing the reviewed numerical data and public report references extracted from the company research record. It contains no research prose. A fresh checkout downloads this baseline into ignored `data/raw/`; subsequent builds verify and reuse it. Each update fetches the latest available metal quotes and FX reference rates, then rebuilds the page and offline artifact:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m investdiy.company_profit
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3 -m investdiy.server
```

Use `--source /absolute/path/to/company/CLAUDE.md` to explicitly override the public baseline with a research record containing `PROFIT_MODEL_DATA_START`. Both paths verify the profit attribution, tax, unit conversion and bridge reconciliations, then creates ignored files under `investdiy/company_profit/data/out/`:

- `history.json` and `history.js`: verified company data, source-block SHA-256, and a dated `market` snapshot of four metal quotes, FX and conversion assumptions.
- `market-status.csv`: collection time and each metal/FX observation date; `as_of` is the oldest observation date for homepage and publication freshness checks.
- `company-profit.html`: a self-contained HTML file with inline CSS, JavaScript, translations and historical data. It works without a server or network connection.

Do not commit these generated data files. A fresh checkout needs network access and the build command; a separate research checkout is not required. No CDN is used. Scenario inputs are not persisted; the shared language preference is saved in localStorage when available. Scenario calculations run in the browser. The browser reads the saved market snapshot and never fetches prices or FX from an external service. There is no live price API endpoint. Both module entry points (`investdiy.company_profit` and `investdiy.company_profit.build`) refresh the snapshot during builds; page reloads read the existing snapshot. Public export includes the page, scripts and generated outputs. Historical baseline revisions require a new release asset and an updated SHA-256 pin in `build.py`.

On first load, the page initializes costs and advanced parameters from reported 9M 2026, applies the 2026 production target (gold 105 t, copper 120 ×10,000 t, silver 520 t), then applies the latest saved four-metal prices. Zinc remains the baseline volume because the production target does not disclose zinc separately from lead; it still needs an explicit annual assumption. Until all production volumes cover the same period, the initial output should not be described as a complete FY 2026 forecast. If a snapshot is missing, the page reports that state and retains manually editable baseline prices. Historical presets include FY 2022–2025, H1 2026 and 9M 2026. Applying a historical preset replaces model input values with that period, retains the selected display units, and clears applied production/market provenance; it does not reapply the startup defaults. Same-period reproduction is a reconciliation, not validation.

Production, cost and advanced fields are initially rounded to four decimal places. Price displays use four decimals (six for USD/lb), while retaining the canonical CNY value until manually edited so unit switching does not alter earnings. Manually entered prices are converted from the selected unit. The historical backtest retains the original full-precision parameters. JSON exports include the complete current inputs, outputs, baseline and source fingerprint.

## Parameter presets and actuals

The preset cards are ordered **Production parameters → Price parameters → Historical parameters**. Production and historical selections apply when their button is clicked. The price dropdown contains only **Latest snapshot**, with an apply button to restore that saved set after edits. Separate **+10%** and **−10%** buttons immediately compound on the current selling prices. The source-period label and JSON export continue to refer to the last applied historical preset, even when another period is selected. This label identifies the parameter origin, not a claim that edited costs and ratios still equal the original values. The groups have separate scopes:

- **Production parameters:** replace gold, copper and silver output with the selected annual guidance. Preserve zinc, all selling prices, costs and advanced parameters. When starting from an interim historical preset, the retained zinc volume still needs an explicit annual assumption.
- **Price parameters:** restore the latest saved four-metal selling-price assumptions, or use the immediate ±10% buttons. All price actions preserve production, costs and advanced parameters and honor active display units. Snapshot dates and source details remain available on the page.
- **Historical parameters:** load reported production, realized prices, sales costs, consolidation ratios, tax, attribution and profit bridge parameters together.

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

Every build fetches the four metal feeds and the FX feed afresh. A collection or validation failure stops the build before replacing output files, preserving the previous data and offline page while reporting the failure. The shared `update.yml` workflow collects and publishes this snapshot at **09:17 and 16:17 Beijing time, Monday–Friday**, independently of the ETF and PBoC gold schedules. Manual workflow runs refresh all public data tools; missing outputs also trigger rebuilding on any schedule. GitHub may delay scheduled starts. Collection failures or publication freshness checks stop deployment and preserve the live site. Routine local data refreshes import the workflow’s `site` artifact first, as described in the [data update SOP](../development.md#data-update-sop). Ordinary page reloads and all browser interactions use saved data, including offline; an older saved snapshot remains usable. The snapshot label shows the collection date, while the expanded table shows each actual quote time and the FX reference date. The Latest snapshot option means the latest saved set, not current live market prices.

The saved selling-price assumptions use gold VAT 0%, copper/zinc/silver VAT 13%, and 100% realization. Gold quotes are CNY/g, copper and zinc CNY/t, and silver CNY/kg. Silver is divided by 1,000 to match CNY/g; copper, zinc and silver are also divided by 1.13. These are conversion assumptions, not company-specific realized prices; treatment charges and other discounts can be reflected by manually editing the resulting inputs. Unit switching never repeats this VAT conversion.

Gold selling prices support **CNY/g** and **USD/troy oz**; copper supports **CNY/t**, **USD/t** and **USD/lb**. Production units and cost fields retain their original units. The current snapshot's CNY/USD rate is used for display and input conversion, including when historical presets are selected; these USD equivalents are not historical FX observations or separate overseas exchange quotes.

```text
gold CNY/g = USD/troy oz * CNY per USD / 31.1034768
copper CNY/t = USD/t * CNY per USD
copper CNY/t = USD/lb * (1000 / 0.45359237) * CNY per USD
```

The model retains canonical CNY prices while a user switches units, avoiding cumulative rounding and profit changes. Manual entries in USD convert back to CNY before calculation; resetting presets, applying the latest snapshot and sensitivity selections honor the chosen display unit. Without a valid FX rate, USD selectors are disabled while CNY inputs remain usable. Historical backtests keep their original parameters and units.

JSON scenario exports include canonical CNY inputs, chosen display-price units, the FX value/source/date, the last applied historical and production presets, and any last applied market snapshot with its conversion assumptions. Current inputs remain authoritative after manual edits. No network access is needed for the standalone HTML's latest-price preset or unit conversion.

## Model

For gold and silver, production is in tonnes and price/cost in CNY per gram. For copper and zinc, production is in 10,000 tonnes and price/cost in CNY per tonne. All output profits are CNY 100 million. Historical realized prices and costs are sales-weighted across gold bullion/concentrate and copper concentrate/electrodeposited/electrolytic products.

```text
consolidated sales (t) = group production * volume_to_t * sales/output conversion
metal gross profit (CNY 100m) = consolidated sales (t) * (selling price - sales cost) * price_units_per_t / 1e8
associate earnings = copper GP * associate earnings ratio
other net pre-tax items = total four-metal GP * other items ratio
pre-tax profit = four-metal GP + associate earnings + other net pre-tax items
tax = max(pre-tax profit, 0) * effective tax rate
group net profit = pre-tax profit - tax
core attributable profit = group net profit * attributable share
scenario attributable profit = core attributable profit + incremental net adjustment
```

In these formulas, prices and costs use the canonical CNY units above. `volume_to_t` is 1 for gold/silver and 10,000 for copper/zinc; `price_units_per_t` is 1,000,000 for gold/silver and 1 for copper/zinc. Ratios are decimals in the formulas; the corresponding editable fields display percentages.

Group production includes equity-accounted operations such as Kamoa. The conversion ratio handles consolidated sales scope and inventory changes; it is not an ownership ratio. Noncontrolled copper output must not be counted as consolidated revenue. Associate earnings are explicitly modeled separately, using copper GP as a simplified driver for all associates.

The residual other net pre-tax bridge is determined by baseline pre-tax profit less four-metal GP and associate earnings. It includes other mining products, refining/trading, eliminations, operating/financing expenses, resource taxes, impairments and other income. It scales with GP, which is an empirical simplification, not a full expense budget. Tax is an effective group rate, not an additional statutory tax on individual associate profits. Unit sales costs already include depreciation/amortization and transport; neither depreciation nor capex is deducted again.

The incremental adjustment is **attributable, after-tax** and only includes contributions beyond those already implied by the bridge. It is not added to displayed group profit or NCI. It is not backtested. Use it carefully for incremental lithium/molybdenum projects, acquisitions, hedging and one-offs; do not add all already consolidated Zangge earnings again.

## Historical validation

The annual validation uses 2022→2023, 2023→2024 and 2024→2025. Parameters are frozen at the previous full year; only target realized prices and production enter the prediction. Target costs, sales, tax, profits and bridge parameters are not used. H1 and 9M 2026 are additional checks anchored to 2025, excluded from annual metrics because they overlap.

Configured thresholds: annual MAPE ≤15% and maximum annual absolute percentage error ≤25%. Signed error is `100 * (estimated / actual - 1)`; MAPE is the unweighted mean of absolute annual percentage errors.

| Test period | Parameter year | Estimated attributable, CNY 100m | Actual, CNY 100m | Signed error |
| --- | --- | ---: | ---: | ---: |
| 2023 | 2022 | 248.41 | 211.19 | +17.62% |
| 2024 | 2023 | 314.08 | 320.51 | −2.01% |
| 2025 | 2024 | 508.81 | 517.77 | −1.73% |
| H1 2026 | 2025 | 391.90 | 391.70 | +0.05% |
| 9M 2026 | 2025 | 581.75 | 575.26 | +1.13% |

Annual MAPE is approximately 7.12%; maximum absolute percentage error is 17.62%. Meeting the configured thresholds describes these historical conditional tests; it is not an external certification or a future error guarantee. Model design had access to these years, so they are not a blind holdout; actual future production and prices are unknown. Prior-year annual reports also become available only after publication in the following year.

Original 2022 group production was visually checked in its own annual report: gold 56,360 kg, copper 877,317 t, zinc 402,321 t (excluding lead), silver 387,458 kg. Later 2023 comparatives change some of these figures, and are deliberately not used in the 2022 parameter anchor. Product sales and costs were visually cross-checked on PDF pp50–51; production on pp30, 33 and 53. Subsequent annual and interim source locations and links are included in the HTML and authoritative record.

The 2023 backtest overestimates earnings. Changes in costs and production/consolidated-sales scope affect this model, but the displayed backtest does not decompose their contributions to the error. Small errors in 2024–2025 can also reflect offsetting errors and should not be extrapolated uncritically. Three annual observations are too few to estimate a statistical confidence interval. The UI's reference band merely applies the largest annual absolute error to the current estimate. It is suppressed for large scenario changes, nonzero manual adjustments or weak gross profits.

## Limits

This is a calibrated group bridge, not a mine-level model. It does not forecast market-to-realized-price discounts, FX, inventory, product mix, new mines, ownership changes or acquisitions separately. Other businesses, including lithium, are implicit in the baseline residual and are not given a separate unvalidated volume-price forecast. Fixed costs do not disappear at zero production, making extreme low-output/low-margin scenarios unreliable. The no-tax-asset rule avoids automatic recognition of a benefit on losses, but mine-by-mine taxes and NCI attribution can still differ materially.

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

Tests check independent unit arithmetic, historical income/tax reconciliation, interim annualization, no target-profit/cost leakage into the prediction, threshold acceptance, price sensitivity, loss tax handling, adjustment separation, invalid inputs, and self-contained HTML. Browser QA should cover both languages, a 390px screen, invalid drafts, sensitivity selection, exports and offline use with network requests blocked.

The current checks cover metal quote selection, ECB cross-rate arithmetic and validation, complete snapshot collection on each build, preservation of previous outputs after failed updates, snapshot embedding in offline artifacts, and removal of the live API. Model checks include troy-ounce and pound conversion, unit round trips, explicit tax conversion and incomplete-snapshot rejection. Browser QA covers both languages, desktop/mobile, offline use with network blocked, price-unit switching, USD input, preset field isolation, sensitivity selection, invalid drafts, JSON provenance and unchanged historical validation.
