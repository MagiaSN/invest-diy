# China PBoC Gold Reserves Tracker

Package `investdiy/cn_track_pboc_gold/`, served at `/cn-track-pboc-gold/`.

The People's Bank of China (PBoC) reports its gold reserves once a month, as part of the official reserve assets published by the State Administration of Foreign Exchange (SAFE). This tool collects the whole history since 1977 and shows:

- **holdings** in tonnes and ounces at each month-end, with the lump disclosures before 2015 and the monthly buying phases since;
- **monthly and yearly changes**, the current **buying streak** and additions so far this year;
- the **value** of the gold at month-end valuation, its **share of official reserve assets** and the **implied gold price** (value ÷ ounces), from June 2015;
- a table of **buying phases and disclosures** with the tonnes added and a rough estimate of what they cost.

## Pages

| Page | Content |
|---|---|
| `/cn-track-pboc-gold/` | headline figures, holdings (tonnes), monthly changes, changes by year, value and gold share of reserves, buying phases and disclosures |

## Running

```bash
.venv/bin/python3 -m investdiy.cn_track_pboc_gold                  # fetch + compute (a few seconds)
.venv/bin/python3 -m investdiy.cn_track_pboc_gold --skip-fetch     # recompute only
.venv/bin/python3 -m investdiy.cn_track_pboc_gold.fetch --full     # refetch the IMF series and every SAFE year
```

SAFE publishes the figures for month M around the 7th of month M+1 (for example the September 2026 figures on 2026-10-07). A normal run refetches SAFE's current and previous year (four requests) and the IMF series when the local copy is more than seven days old. "Data as of" is the last day of the latest month, so it is normally 7 to 38 days old; the tool sets `max_stale_days: 45` so that the scheduled update only fails when a release is clearly missing.

| Module | Role |
|---|---|
| `fetch.py` | IMF International Liquidity series and SAFE yearly tables → `data/{imf,safe,safe_pages}.csv` |
| `analyze.py` | merges the two, computes changes, phases, years and headline figures → `data/out/*.csv` |
| `web/` | dashboard (`index.html`, `strings.js`, `app.js`) |

## Scheduled updates

The shared [GitHub Actions workflow](../../.github/workflows/update.yml) refreshes gold at 23:53 Beijing time on the 7th of each month, including weekends. It retries at the same time on the 8th-10th only if the previous month's figures are still missing, and checks again unconditionally on the 15th for delayed releases or revisions. ETF runs reuse cached gold output. Manual runs force a refresh; missing output is rebuilt on any run after cache eviction.

Each run restores cached source data, fetches and computes the latest figures, validates freshness, exports the whole site and publishes it to Surge. Publication stops if any tool fails or its data regresses; this tool allows a maximum data age of 45 days. The Actions summary shows the updated and live dates. Manual runs support disabling publication for inspection; the exported site is retained as an artifact for seven days. See [setup and credentials](../development.md#scheduled-updates).

## Data sources

All sources are free and need no login.

| Data | Endpoint | Notes |
|---|---|---|
| SAFE official reserve assets (2018 onwards) | listing `www.safe.gov.cn/safe/whcb/index.html` → yearly page titled `官方储备资产（YYYY年）` → its `html` link (a page with one table) | months in columns (`YYYY.MM`), each with USD 100m and SDR 100m; rows `1. 外汇储备`, `4. 黄金` followed by a row of `NNNN万盎司`, and `合计`. Unpublished months are empty. Years before 2018 (from 2015-06) are only `.xls` / `.xlsx` files in several layouts and are not parsed; the IMF covers them. The page's `发布日期` is the date of the latest release |
| IMF International Liquidity (history) | `api.imf.org/external/sdmx/2.1/data/IMF.STA,IL/CHN.RGV_REVS+RGOLDNV_REVS+RXF11FX_REVS+TRGMV_REVS.FTO+USD.M` with `Accept: application/vnd.sdmx.data+csv;version=1.0.0` | `RGV_REVS` gold in fine troy ounces, `RGOLDNV_REVS` gold at national valuation (USD), `RXF11FX_REVS` foreign currency reserves, `TRGMV_REVS` total reserves including gold. From 1977-12, quarterly until 1980-03, monthly from 1980-06. About three months behind SAFE (in October 2026 it ended at 2026-06). Values are in plain units even though `SCALE` says 6 |

### Other sources considered

| Source | Why it is not used |
|---|---|
| PBoC statistics, "黄金和外汇储备" (`www.pbc.gov.cn/diaochatongjisi/116219/116319/`) | the same figures as SAFE, but the site redirects scripted requests through an anti-bot check and serves yearly spreadsheets |
| Eastmoney data centre, `datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_ECONOMY_GOLD_CURRENCY` | easy JSON from 2008, but only the USD value of gold (`GOLD_RESERVES`, USD 100m) and foreign exchange reserves, not the volume |
| World Gold Council, gold reserves by country | quarterly, compiled from the IMF, and its terms restrict redistribution |
| News reports | useful to check single months, not as a data source |

## Method

- **Merge**: SAFE's figures are used for every month it publishes (2018-01 onwards); the IMF fills the rest. Both sources publish the gold volume in 10,000 ounces, rounded.
- **Tonnes**: 1 tonne = 32,150.7466 troy ounces. Rounding to 10,000 ounces leaves about ±0.2 t of uncertainty per figure.
- **Changes**: change = this month-end minus the previous reported period (a quarter before 1980).
- **Valuation**: until May 2015 China carried gold at historical cost (about USD 35–52/oz until 2000, USD 190–211/oz in 2001–2009, USD 290/oz in 2009–2015). From June 2015 it is valued at market prices, so the value, the share of reserves and the implied price are computed from 2015-06 only. The implied price (value ÷ ounces) is the price SAFE used for the month-end valuation; it is close to the London price but not identical.
- **Disclosures before July 2015**: the volume changed only in occasional lump disclosures, each the result of years of buying: 2001-12 (+3.40m oz), 2002-12 (+3.21m oz), 2009-04 (1,054 t, 454 t added since 2003) and 2015-06 (1,658 t, 604 t added since 2009, announced on 2015-07-17). They appear as one-off rows in the phase table and as single bars in the charts; they are not purchases made in those months. Changes below 100,000 ounces before July 2015 are left out of the table: the IMF series flips between 16.08m and 16.10m oz several times in 2002, which is rounding in the source.
- **Buying phases** (from 2015-07): consecutive months with additions; one unchanged month in between (such as 2016-05) does not end a phase, two unchanged months or a decrease do. The estimated amount of a phase is Σ monthly addition × that month's implied price.
- **Buying streak**: counted strictly, month by month, as the press reports it (for example "23 straight months" in September 2026).

## Validation

- **IMF vs SAFE**: in October 2026 both sources covered the 102 months from 2018-01 to 2026-06. Gold volumes, gold values and foreign currency reserves agreed in every month to within rounding (`data/out/compare.csv`). Total reserves differ by up to about USD 1bn, because the IMF's total is defined differently from SAFE's `合计`; the page uses SAFE's total where it exists.
- **Press reports**: the computed figures match the reported ones: 7,544 万盎司 at end-June 2026 (+48 from May), 7,419 万盎司 at end-January 2026 (+4), 77.47m oz at end-September 2026 (+0.74m oz, about 23 t, the 23rd straight month) and about 103 t added in 2026 by September.
- **Known history**: the phases found are 2015-07 to 2016-10, 2018-12 to 2019-09, 2022-11 to 2024-04 and 2024-11 onwards. Between them are the known pauses: 2016-11 to 2018-11, 2019-10 to 2022-10 and 2024-05 to 2024-10.

## Limitations

- The official figures cover only gold counted in official reserve assets. Some analysts estimate further, undisclosed buying from trade data; this page cannot check those estimates.
- Month-end figures do not show when within the month gold was bought or at what price, so the estimated amounts are approximate.
- SAFE's site is the only source of the latest months. If it cannot be reached, the page falls back to the IMF series, which is about three months behind, and the stale-data notice appears once the latest month is about six weeks old.
