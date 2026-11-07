# Global Shipping Index Tracker

Package `investdiy/global_track_container_freight/`, served at `/global-track-container-freight/`. The existing package and URL remain compatible with earlier installations. This is a **local tool** (`visibility: local`): the local server lists it, but public exports and Surge deployments exclude its pages, scripts and data.

The tracker reads all **24 sections in SSE's index navigation**, including their routes, vessel sizes and other components. Each section uses its latest published period; the source publishes daily, weekly and monthly series on different schedules.

| Coverage | Index sections |
|---|---|
| Container freight | CCFI, SCFI, SCFIS, CICFI, TWFI, SEAFI |
| Schedule reliability | GCSPI trade lanes, GCSPI_CA carriers/alliances, GCSPI_PORT ports |
| Coastal bulk and hire | CBFI, CBCFI, CBOFI, CBGFI, CCTFI_COASTAL, CDI |
| Dry bulk and crude oil | FDI, CDFI, CTFI |
| Shipping and trade | CSI, BRSTI, BRTVI, BRCVI, SRFI |
| Crew remuneration | CCRI indices and pay tables by position and ship type |

## Why this tool is not published

**Decision recorded on 2026-11-05:** keep the shipping tracker `visibility: local`. Continue the separately enabled SSE collection workflow and encrypted backups, but exclude the dashboard, raw data and accumulated history from Surge and other public exports. This records a project distribution decision, not a finding that collection or publication is necessarily lawful or unlawful.

The public index pages provide a limited recent window; historical queries and some components require a subscription. Accumulating those releases and offering a freely accessible historical chart or CSV could become a substitute for SSE's historical data service. That substitution risk is the reason for withholding this tool from the public site, even though the observations were collected over time from visible pages. The precise window varies by index; it is not always exactly two periods.

SSE's [official index copyright statement](https://www.sse.net.cn/indexIntro?indexName=copyright), dated 2026-06-18, claims rights in its indices and related content and calls for written authorization for publication and use, including public redistribution. It also requires authorized users to stay within the licensed scope and attribute the source. These are the provider's stated claims; their wording alone does not establish the legal protection of every individual number.

The relevant risks are:

- **Copyright and compilations.** An isolated numerical fact is not automatically a protected work. Original text, charts, or the selection and arrangement of a compilation may qualify. Publicly copying a substantial historical dataset needs a separate assessment; attribution, a free site, or an investment disclaimer does not itself confer permission. Articles 3, 15 and 24 of the [PRC Copyright Law](https://www.ncac.gov.cn/xxfb/flfg/flfg_532/202103/t20210309_50530.html) distinguish protected works and compilations and place conditions on exceptions, including personal study. A public dashboard should not be assumed to fall within a personal-use exception.
- **Terms and licensing.** An enforceable account, subscription or data-use agreement may restrict automated access, retention or redistribution independently of copyright. A public URL or a paid login is not evidence of a redistribution license. The terms actually accepted and the scope of any authorization must be checked; this project has not established that SSE has granted such a license.
- **Unfair competition and data interests.** A systematic public replacement for a paid history service could invite a claim concerning another operator's data investment or service. This is a risk assessment, not a conclusion that all public-page scraping is unlawful. Articles 2 and 13 of the [2025-revised Anti-Unfair Competition Law](https://ipc.court.gov.cn/zh-cn/news/view-6249.html), effective 2025-10-15, address business conduct and improper data acquisition/use, including deception or bypassing technical management measures. Applicability depends on the activity, collection method, harm and other facts; a noncommercial label alone does not resolve those questions.

Possible consequences include demands to stop use or remove data, account/access restrictions, and litigation or liability if a claim is established. Local use and encryption reduce public exposure; they do not grant data rights or eliminate collection, retention or contractual risk. GitHub Actions still processes and stores data in the cloud: `local` describes the tool's publication category, not a guarantee that all processing stays on a workstation.

The implementation therefore keeps SSE values out of public exports and logs, stores only encrypted history artifacts, and keeps recovery keys outside git. It must not bypass access controls or treat `SSE_COOKIE` as permission beyond the account's entitlement. Publishing the source code does not license the underlying SSE data to recipients. These controls do not replace reviewing the provider's applicable terms.

Before changing this tool to public, obtain and record written authorization covering the intended automated collection, historical retention, public charts/downloads and hosting, or document an independently reviewed legal basis for the exact proposed use. Recheck the current terms at that time. This maintainer decision belongs in repository documentation; the dashboard keeps its SSE attribution without adding this legal discussion to the page.

## Page

The headline index cards remain fixed. Below them, the page initially shows **one CCFI composite chart**. “Add chart” creates another independent chart; users can remove charts while keeping at least one. The first selector chooses the index (CCFI, SCFI, etc.); the second lists that index's composite and components, including unavailable and archive-only series. Each chart shows exactly one series and owns its own date range, defaulting to the latest year of available data. New charts and series changes also default to one year; changing a series resets only that chart's date range. Charts added during a visit are not persisted across reloads.

`web/chart.js` exposes the reusable `FreightChart` component. Each instance owns its DOM, selectors, plot, range picker and expandable source details. `app.js` owns the chart list and the minimum-one rule. Removal disposes of the component and its range picker's language listener.

Expandable details retain the source unit, weight, current period/value, published change, last available observation/date and calendar 1/4/52-week changes. Missing current cells remain unavailable, even if an older observation exists. The component selector moves entries whose last observation is at least one calendar year old to the end, preserving the existing order within each group. Those entries alone are labeled “Historical data · no update for at least a year”; selecting one also shows its last available date. The cutoff uses today in Beijing time, including leap-year anniversaries. Recent entries and entries without any observation date have no status suffix, even if the current request returned a blank value or the component is absent from the current source catalog. This is an age-based display rule, not a declaration that SSE has permanently discontinued a series. Source labels without an official English name remain in their original language; controls and explanations are bilingual.

Each index has its own publication/period date, last check, last successful fetch, coverage count and fetch status. This distinguishes a successful request with restricted components from a failed request retaining saved data. The header's weekly coverage date is the oldest of the four headline series (CCFI composite, SCFI composite, SCFIS Europe and US West Coast); fresh daily data cannot hide stale weekly data.

## Running

```bash
.venv/bin/python3 -m investdiy.global_track_container_freight --latest-only      # latest SSE periods + compute
.venv/bin/python3 -m investdiy.global_track_container_freight --skip-fetch       # recompute saved data
.venv/bin/python3 -m investdiy.global_track_container_freight --refresh-archive  # also look for historical snapshots
```

Run this tool locally; the public update workflow skips it. A separate, dedicated collection workflow is described below. `--latest-only` skips archive network requests and still merges existing history, cached snapshots and any history from an existing authorized source configured by `INVESTDIY_SITE`. New freight history is no longer published to Surge, so keep a local backup. Without this flag, the earlier weekly archive lookup behavior remains available. Archive downloads are slow and rate limited; they are not needed to fetch the latest week.

SSE requests use four workers, finite timeouts and retries, and request fresh pages. A failing index keeps its previous snapshot and records an error independently of successful indices. SCFIS additionally reads the trace page for its last four periods. Observations are merged by `(index, series, date)`, so rerunning the command does not duplicate history.

If an existing authorized SSE session is available, the optional `SSE_COOKIE` environment variable supplies its Cookie header to SSE requests only. It is not required for public values and is never written to CSV or logs. This does not grant access to data outside that session's entitlement.

| Module / output | Role |
|---|---|
| `indices.py` | 24 index names, frequencies and compatible keys for the original container series |
| `parse.py` | span-aware tables, dated columns, embedded literal data, component identities and units |
| `fetch.py` | live sources, archive and published history merge |
| `data/observations.csv` | nonempty historical observations, preserving source precision |
| `data/current.csv` | current component metadata and values, including unavailable cells |
| `data/status.csv` | independent source update results |
| `analyze.py` | `data/out/{history,latest,status,kpi}.csv` |
| `web/` | bilingual dashboard and CSV downloads |

## Publication times and scheduled collection

Checked against SSE's official documentation on **2026-11-05**. All times below are **Beijing time (UTC+8)**. These are normal publication rules, not a guarantee that every release appears on time. Holiday notices and exceptional postponements take precedence. The [official index overview](https://www.sse.sh.cn/servicesintro/indexIntro?indexName=intro) lists the publication frequencies.

| Index sections | Normal publication | Official timing reference |
|---|---|---|
| CCFI | Friday; exact clock time not specified in the introduction | [CCFI introduction](https://www.sse.sh.cn/md/ccfiintro.md) |
| SCFI | Friday, 15:00 | [SSE FAQ](https://www1.sse.net.cn/index/faqnew.jsp) |
| SCFIS | Monday, 15:05; holiday arrangements may change the release day | [Compilation rules, June 2026 revision](https://www.sse.net.cn/files/pdf/buildingRule.pdf) |
| CICFI, TWFI | Wednesday; TWFI specifies afternoon | [CICFI introduction](https://www.sse.sh.cn/md/cicfiintro.md), [TWFI introduction](https://www.sse.sh.cn/md/twfiintro.md) |
| SEAFI, CCTFI_COASTAL | Friday; no exact time confirmed here | [Index overview](https://www.sse.sh.cn/servicesintro/indexIntro?indexName=intro) |
| CBCFI | Working days, 15:00 | [SSE FAQ](https://www1.sse.net.cn/index/faqnew.jsp) |
| CBFI, CBGFI | Friday, 17:00 | [CBFI introduction](https://www.sse.sh.cn/md/cbfiintro.md), [CBGFI introduction](https://www.sse.sh.cn/md/cbgfiintro.md) |
| CBOFI | Monday, Wednesday and Friday, 17:00 | [CBOFI introduction](https://www.sse.sh.cn/md/cbofiintro.md) |
| CDI, FDI, CDFI, CTFI | Working days, 17:00 | [CDI introduction](https://www.sse.sh.cn/md/cdiintro.md), [FDI introduction](https://www.sse.sh.cn/md/fdiintro.md), [SSE FAQ](https://www1.sse.net.cn/index/faqnew.jsp) |
| GCSPI, GCSPI_CA, GCSPI_PORT | Early each month, for the preceding month; no fixed day/time stated | [GCSPI introduction](https://www.sse.sh.cn/md/gcspiintro.md) |
| BRSTI, BRTVI, BRCVI, SRFI | Wednesday in the last week of each month, adjusted for holidays | [BRSTI introduction](https://www.sse.sh.cn/md/brstiintro.md) |
| CCRI | Monthly; introduction specifies last Tuesday working day, 15:00 **during trial operation** | [CCRI introduction](https://www.sse.sh.cn/md/ccriintro.md) |
| CSI | Monthly; no precise date/time confirmed here | [Index overview](https://www.sse.sh.cn/servicesintro/indexIntro?indexName=intro) |

### GitHub Actions workflow

[`.github/workflows/sse-update.yml`](../../.github/workflows/sse-update.yml) is separate from the public update/publish pipeline. Its schedule is configured, and its job requires repository variable `SSE_COLLECTION_ENABLED` to equal `true`. Both scheduled and manual runs skip collection when this opt-in is absent or disabled. Runs are restricted to the repository's default branch.

The cron is `37 1,5,7,9,12 * * *` in UTC: **09:37, 13:37, 15:37, 17:37 and 20:37 Beijing time every day**. The morning and midday runs recheck public components that were unavailable on release day; the afternoon and evening runs follow the main publication windows. Weekends are included so Friday releases can be completed on Saturday. These are requested start times: [GitHub documents that scheduled events may be delayed or dropped under load](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule). There is no guarantee of an exact next execution or a complete public response.

Each run invokes `python -m investdiy.global_track_container_freight.collect`, fetches all 24 sections with `latest_only=True`, merges observations, and recomputes the local dashboard outputs. The collector accepts restricted/blank components but fails on missing sources, failed requests, reused success statuses, or stalled feeds. Staleness limits are 17 days for daily/weekly sections and 100 days for monthly sections; these deliberately allow holidays and monthly period labels and **do not certify that a release has arrived at its exact deadline**. Successful source updates are saved even if another source fails. The next scheduled run retries the pages.

History is carried across runners as the `sse-history-encrypted` artifact, encrypted using GPG AES256 and repository secret `SSE_DATA_PASSPHRASE`. Only ciphertext is uploaded; plaintext data is not committed, cached, included in the public site, or attached to workflow runs. Public logs and job summaries contain trigger/cron details, actual UTC and Beijing start times, source check times, period dates, status and available/total counts, not observed values. A decrease in coverage produces a warning without discarding partial results. Persistently restricted components do not by themselves fail every run. Optional secret `SSE_COOKIE` supplies an existing authorized SSE session. No Surge secrets or publish job are used.

The restore step chooses the newest unexpired snapshot from this workflow and branch, including snapshots saved during partially failed collections. Decryption failures stop the run before fetching. Missing history also stops the run unless `initialize` was explicitly selected. Artifacts request 90-day retention (subject to repository limits); this is rolling persistence, **not a permanent backup**. Download encrypted snapshots periodically and retain the passphrase separately. Losing it makes those snapshots unrecoverable. Do not replace it without first re-encrypting the saved history.

The schedule was revised after checking actual encrypted snapshots on **2026-11-07**:

| Run (Beijing time) | Trigger | CCFI current coverage | CBFI current coverage |
|---|---|---|---|
| [2026-11-05 17:53](https://github.com/MagiaSN/invest-diy/actions/runs/42006022104) | Manual initialization | 13/13 for October 30 | 27/27 for October 30 |
| [2026-11-06 04:15](https://github.com/MagiaSN/invest-diy/actions/runs/42101594331) | Scheduled, actual fetch time | 13/13 for October 30 | 27/27 for October 30 |
| [2026-11-06 23:22](https://github.com/MagiaSN/invest-diy/actions/runs/42242387965) | Scheduled, actual fetch time | 1/13 for November 6 | 1/27 for November 6 |
| [2026-11-07 13:04](https://github.com/MagiaSN/invest-diy/actions/runs/42341157717) | Manual diagnostic rerun, same collector | 13/13 for November 6 | 27/27 for November 6 |

These observations establish that the same GitHub collector could read the missing CCFI/CBFI components on the following day. They do not establish the exact time those values became public or a universal delay for every index. The [current SSE subscription FAQ](https://www.sse.net.cn/md/ccfiFAQ.md) promises non-subscribers the latest composite indices; it does not specify a fixed public release time for all components. SCFI remained at 1/21 in the diagnostic rerun. Morning/noon polling improves the opportunity to collect delayed public values but cannot unlock restricted data. The earlier afternoon-only schedule would next request a run at 15:37 on November 7, subject to GitHub delays. The old logs did not retain the triggering cron occurrence, so a precise per-event queue delay cannot be reconstructed.

To configure collection in a new repository:

1. Merge the workflow onto the default branch. Add a strong, randomly generated `SSE_DATA_PASSPHRASE` Actions secret and set repository variable `SSE_COLLECTION_ENABLED=true`.
2. Dispatch once with `initialize=true` to start from the periods currently visible on SSE. This does not import an existing workstation's historical data. `initialize` only permits an empty start when no snapshot exists; it never bypasses a decryption error or discards a found snapshot.
3. Confirm that collection and encrypted snapshot upload succeed. The existing `schedule` block runs automatically while the opt-in variable remains enabled.
4. Leave `initialize=false` for subsequent manual runs. To pause collection, remove the opt-in variable or set it to `false`.

To use an Actions snapshot locally, download its artifact ZIP, unzip it, then decrypt with GPG (which prompts for the passphrase) and extract into a staging directory:

```bash
gpg --output sse-history.tar.gz --decrypt sse-history.tar.gz.gpg
mkdir -p sse-history-restored
tar xzf sse-history.tar.gz --directory sse-history-restored
```

Back up the existing local `data/` directory before replacing it with the restored files. Do not overwrite newer local observations; if both copies have advanced independently, merge `observations.csv` by `(index, series, date)` before recomputing. GitHub Actions does not synchronize a workstation automatically.

## Data sources

| Source | Coverage |
|---|---|
| [SSE index pages](https://www.sse.net.cn/index/singleIndex?indexType=ccfi) | Latest period and any public previous-period observations for all 24 sections |
| [SSE SCFI page](https://www.sse.net.cn/index/singleIndex?indexType=scfi) | Composite plus all listed routes, box sizes, units and weights; restricted route values stay unavailable |
| [SSE SCFIS trace](https://www.sse.net.cn/index/scfisTrace) | Europe and US West Coast, last four periods |
| [SSE schedule reliability](https://www.sse.net.cn/index/singleIndex?indexType=gcspi) | Lane, carrier/alliance and port metrics; some tables store literal data in page scripts |
| [Wayback Machine](https://web.archive.org/) | Sparse historical snapshots for CCFI, SCFI and SCFIS |
| Published `history.csv` at `INVESTDIY_SITE` | Recovery of accumulated observations after a local cache is lost |

The latest public pages do not expose all numeric components or full history. Historical queries and some current components require an SSE subscription. The source pages carry a copyright notice restricting republication and commercial use; check those terms before publicly hosting exports.

## Method

- **Columns and spans**: expand `rowspan` and `colspan` before locating date, unit and weight columns. An empty previous/current cell never shifts a later numeric cell into its position. Weights and changes cannot be mistaken for observations.
- **Page variants**: handle dates in headers or page titles, monthly periods, two independent CSI column groups, multi-unit CTFI routes, CCRI pay tables, and literal GCSPI/BRCVI script data. Scripts are decoded as data, never executed.
- **Identity**: preserve the original CCFI/SCFI composite/SCFIS keys. Additional keys derive from the component label, vessel details, parent group and unit. Opposite-direction trade groups and different box sizes stay separate.
- **Precision and blanks**: retain source numeric precision, including three-decimal dry-bulk rates and valid zeroes. Empty cells are retained in snapshots but never inserted into numeric history. No restricted values are inferred from weights or changes.
- **Dates**: use source dates rather than the date in the query form or the fetch date. A monthly `YYYY-MM` period is stored as the month's first day for charting, with the original month shown in the table. Other tables retain their explicit publication dates.
- **Precedence**: live SSE observations win over local history, which wins over published history, which wins over archive snapshots. Archive disagreements are reported.
- **Changes**: calendar 1/4/52-week changes compare the same series with an observation within three days of the target date. Missing or zero bases leave the result blank. Published changes remain separate and retain their point, percent, percentage-point or currency unit.
- **Charts**: compare only matching units. Gaps longer than 17 days break lines; isolated and short historical runs appear as dots. The CCFI/SCFI comparison has different index bases and should be read as direction and size of moves, not comparable levels.
- **Freshness**: source status is per index. The headline weekly coverage date tracks the four core weekly series; each chart also flags old data, allowing for delayed monthly releases. This local tool is excluded from public CI freshness checks.

## Validation

```bash
.venv/bin/python3 -m unittest discover -s tests -v
node --check investdiy/global_track_container_freight/web/app.js
node --check investdiy/global_track_container_freight/web/chart.js
node --check investdiy/global_track_container_freight/web/strings.js
```

Regression tests cover blank dated cells, numeric weights, mixed units, merged cells, repeated routes with different vessel sizes or parent groups, CSI side-by-side columns, monthly and embedded script data, legacy series identifiers, precision, failed-source retention, latest-only updates, zero bases, and preventing fresh daily data from masking stale weekly data.

A live check on 2026-11-04 read all 24 sections and identified 721 current components plus 15 additional historical CCFI/SCFI components. CCFI and SCFI reported 2026-10-30; SCFIS reported 2026-11-02; several daily indices reported 2026-11-04. These are source publication periods, not a promise that all components are public or have the same date.

## Limitations

- Full coverage of the latest index pages means every listed component is represented, including unavailable ones. It does not provide restricted numeric values, full historical coverage, or every interactive historical/directional query.
- Before collection begins, most additional indices have only the periods exposed by their current page. Cached CCFI/SCFI/SCFIS archive snapshots remain sparse and uneven.
- SSE layout or label changes may require parser changes. Empty/invalid results and ambiguous component identities mark that index as failed while retaining saved data.
- Network or login failures can leave individual indices behind. Inspect the selected index's date and status rather than assuming the dashboard fetch timestamp is its publication date.
- The site is a static dashboard: run the local update command to fetch new data, then reload the local page. Public exports exclude this tool.
