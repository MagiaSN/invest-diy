# Global Container Freight Tracker

Package `investdiy/global_track_container_freight/`, served at `/global-track-container-freight/`.

Container freight rates out of China are a widely watched gauge of global trade, shipping-line earnings and goods inflation. The Shanghai Shipping Exchange (SSE) publishes the reference indices every week. This tool collects:

- the **CCFI** (China Containerized Freight Index): spot and contract rates from 10 major Chinese ports, composite and 12 trade lanes, base 1998-01-01 = 1000, published on Fridays;
- the **SCFI** (Shanghai Containerized Freight Index): spot rates out of Shanghai, composite only, base 2009-10-16 = 1000, published on Fridays;
- the **SCFIS** (Shanghai Containerized Freight Index, Settlement): settled spot rates for Europe and the US West Coast, base 2020-06-01 = 1000, published on Mondays. The Europe lane is the settlement basis of the Shanghai International Energy Exchange container freight (Europe) futures.

## Page

| Page | Content |
|---|---|
| `/global-track-container-freight/` | latest values and week-on-week changes, SCFI and CCFI composites, CCFI lanes (selectable) with a table of 1 / 4 / 52-week changes, SCFIS Europe and US West Coast |

## Running

```bash
.venv/bin/python3 -m investdiy.global_track_container_freight                     # fetch + compute
.venv/bin/python3 -m investdiy.global_track_container_freight --skip-fetch        # recompute only
.venv/bin/python3 -m investdiy.global_track_container_freight --refresh-archive   # look for new archive snapshots now
```

The SSE pages are read on every run (a few seconds). Archive snapshots are looked up once a week; the first run downloads about 170 of them, six seconds apart, which takes about 20 minutes. The Wayback Machine answers "429 Too Many Requests" or refuses connections for up to an hour after bursts of requests, so a pass stops after three failures in a row and the next run carries on.

| Module | Role |
|---|---|
| `indices.py` | indices and series, with the labels used to find them in the pages |
| `fetch.py` | SSE pages, archive snapshots and the published copy → `data/observations.csv` |
| `analyze.py` | `data/out/{history,latest,kpi}.csv` |
| `web/` | dashboard (`index.html`, `strings.js`, `app.js`) |

## Data sources

| Source | What it gives | Access |
|---|---|---|
| [SSE CCFI page](https://www.sse.net.cn/index/singleIndex?indexType=ccfi) | CCFI composite and 12 lanes, current and previous period | public |
| [SSE SCFI page](https://www.sse.net.cn/index/singleIndex?indexType=scfi) | SCFI composite, current and previous period; lane rates (USD per box) are blank | public |
| [SSE SCFIS trace](https://www.sse.net.cn/index/scfisTrace) | SCFIS Europe and US West Coast, last four periods | public |
| SSE single-date and multi-period queries (`/index/mutipleIndex`) | full history and SCFI lanes | paid SSE account ("对不起你没有登陆!" otherwise) |
| [Wayback Machine](https://web.archive.org/) snapshots of the three pages above (plus the SCFIS single page) | a few dozen snapshots per page since 2016, each with one to four periods | public |

Other places checked in October 2026, none of which had usable CCFI / SCFI history: the Eastmoney data centre (`RPT_INDUSTRY_INDEX` only carries the Baltic indices), AkShare (no CCFI / SCFI function; its Drewry WCI function covers one year), StockQ (about 20 recent dates without values), and third-party chart sites that load data from private endpoints.

Because full history is behind a subscription, history builds up from the weekly runs. To keep it when the local data folder is lost (such as an evicted Actions cache), every run merges the published `history.csv` from the live site given in `INVESTDIY_SITE`; the scheduled workflow sets it to the surge.sh domain.

The SSE pages carry the notice "上海航运交易研究所(筹)版权所有，未经许可，不得转载或者用于任何形式的商业用途" (all rights reserved; no reproduction or commercial use without permission). Check this before hosting the export publicly.

## Method

- **Parsing**: tables are read with the standard-library HTML parser. On single-period pages the header row names the dates ("上期 <date>", "本期 <date>"); each series row is found by a keyword in its first cell (`indices.py`) and its first numeric cells are the values for those dates. On the SCFIS trace page the header names the lanes and each row is a date. The same code reads the live pages and the archived snapshots, whose layout has not changed since 2016.
- **Precedence**: for one (index, series, date), a value from the live SSE page wins over stored rows, then over the published copy, then over archive snapshots. Archive values that differ from SSE values are printed.
- **Changes**: against the period of the same series about 1, 4 and 52 weeks earlier, within 3 days because holidays move publication dates (for example Wednesday 2026-09-30 before the National Day holiday). Blank when there is no such period.
- **Charts**: periods at most 17 days apart are joined by a line (so a skipped holiday week stays joined); short runs such as archive pairs are drawn as dots.
- **Staleness**: `as_of` is the latest publication date of any series. The page shows a notice after 8 weekdays, and the scheduled update fails after 17 days (`max_stale_days`), which allows for one skipped week.

## Validation

- Every archived CCFI snapshot downloaded so far (2016–2026) parses into 13 series × 2 periods with consecutive publication dates, including the Spring Festival gap 2026-02-13 → 2026-02-27; SCFI snapshots give the composite for 2 periods.
- Week-on-week changes computed from the stored values match the changes printed on the SSE pages (for example CCFI 2026-10-23: −2.41% computed, −2.4% published; SCFI: +1.76 points published, 3679.58 → 3681.34).
- Values seen on the live page and in an archive snapshot for the same period are compared on every run and differences are printed.

## Limitations

- SCFI lane rates are not public and are not included.
- Before weekly collection started, history is limited to archive snapshots, which are unevenly spread (2020 has one per page), so highs and lows of those years cannot be read from the page.
- A redesign of the SSE pages may break parsing. The fetch step prints a warning when a page yields no values, and the scheduled update fails once the data is older than 17 days.
- The SSE site may be slow or unreachable from some networks, including overseas CI runners; the update then keeps the existing data.
