# Development guide

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python3 -m investdiy.server            # http://localhost:8765/
.venv/bin/python3 -m investdiy.server --port 9000 --host 0.0.0.0
```

Run every command from the repository root; the Python package is `investdiy`. Pass `--host 0.0.0.0` to reach the server from other devices on the network.

Restart the server after changing `investdiy/server.py`, `investdiy/registry.py`, any `TOOL` dict, or after adding a tool. Pages and data files are read on every request, so a browser refresh is enough for those. See [Architecture](architecture.md) for how the pieces fit together.

## Conventions

- **One tool, one sub-package** under `investdiy/`. Do not add other top-level directories for tools.
- **Shared code goes in shared places**: logic used by two or more tools belongs in `investdiy/common/` (Python) or `investdiy/web/static/` (front end), not copied between tools.
- **No CDNs**: pages load only local files. Third-party libraries are vendored under `investdiy/web/static/vendor/` with a version number in the file name.
- **Bilingual pages**: every page, including new ones, must work in English and Chinese (see [Bilingual pages](architecture.md#bilingual-pages)).
- **Disclaimer in one place**: `site.js` adds the disclaimer to every footer, so pages do not repeat it. A page's "About" section describes what the page does, where the data comes from, how it is computed and its limitations.
- **Charts**: each time-series chart has its own range picker; ranges are not stored in the URL.
- **Data is not committed**: `investdiy/*/data/` and `investdiy/dist/` are git-ignored and can be rebuilt with each tool's update command.
- **English first**: code comments and documentation are written in English. Translations of reader-facing documents go in `docs/i18n/` (for example `docs/i18n/README.zh-CN.md`).

### Naming trackers

Tools that fetch data on a schedule and show trends and signals are named "market + track + topic":

| Field | Rule | Example |
|---|---|---|
| `title` (Chinese) | `<market><topic>数据跟踪` | A股国家队宽基ETF数据跟踪 |
| `title_en` | `<Market> <Topic> Tracker` | A-Share National Team ETF Tracker |
| `kind` / `kind_en` | `数据跟踪` / `Tracker` | |
| package | `<market>_track_<topic>` | `ashare_track_national_team_etf` |
| `slug` | package name with hyphens | `ashare-track-national-team-etf` |

Market codes: `ashare` (China A-shares), `cn` (China, outside the stock market: macro and official data such as the central bank's reserves), `hk` (Hong Kong), `us` (United States), `kr` (Korea), `global` (cross-market). Starting with the market keeps tools of the same market together; `_track_` leaves room for other kinds of tools.

## Adding a tool

1. Create `investdiy/<package>/__init__.py` with a `TOOL` dict:

   ```python
   TOOL = {
       "slug": "ashare-track-xxx",             # URL segment; not api / static / common / web
       "visibility": "local",                # local (default) or public; only public tools are exported
       "title": "A股xxx数据跟踪",
       "description": "一句话说明",
       "kind": "数据跟踪",
       "title_en": "A-Share xxx Tracker",
       "description_en": "One-line description",
       "kind_en": "Tracker",
       "update": "python -m investdiy.<package>",
       "asof_file": "data/out/xxx.csv",        # optional: first row's as_of column, shown as "data as of"
       "max_stale_days": 45,                   # optional: days before the scheduled update fails on stale data (default 10; for monthly data)
   }
   ```

2. Add `__main__.py` so that `python -m investdiy.<package>` fetches and recomputes everything, writing page data to `data/out/`.
3. Add `web/index.html` with the shared assets in the order listed in [Architecture](architecture.md#front-end-kit), plus `web/strings.js` (dictionary) and `web/app.js` (page code). Read data with relative paths, e.g. `kit.csv('data/xxx.csv')`.
4. Reuse shared helpers with relative imports: `from ..common import net, market, fund_reports`.
5. Choose `visibility`: use `"local"` for local access only, or explicitly set `"public"` to include the tool in static exports and the Surge update/publish workflow. Missing visibility defaults to local; unknown values fail discovery. Insert the tool's slug at the desired position in the `HOME_TOOLS` list in `investdiy/server.py`, then restart the server.
6. Document the tool in `docs/tools/<slug>.md` (method, data sources, validation, limitations) and add it to the tools table in `README.md`.

Further pages of the same tool sit next to `index.html` (for example `web/backtest.html`, served at `/<slug>/backtest.html`).

## Checking changes

- `curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/api/tools.json` should print `200`.
- Open the page in both languages and at a narrow width (about 400px); tables may scroll horizontally, the page itself should not.
- `node --check <file>.js` catches syntax errors in page scripts; a broken dictionary file stops the whole page from translating.

## Data update SOP

When the user asks to update data, follow this order: **pull the latest available GitHub Actions data first, then update tools not covered by Actions locally**. Apply this to all tools unless the request names a narrower scope. A routine local refresh does not trigger workflows or publish the site.

### 1. Check coverage and prerequisites

Read `.github/workflows/` and the tools returned by `investdiy.registry.discover()` before deciding which tools need local fetching. Coverage depends on the workflow's actual collection logic, not just a tool's `visibility`: a local tool can have a dedicated workflow. Use the repository's default branch unless the user specifies another branch. Run commands from the repository root using `.venv/bin/python3`; Actions downloads require authenticated `gh` with repository/Actions read access.

Current coverage:

| Tool | Data source for a routine refresh |
|---|---|
| `ashare-track-national-team-etf` | `update.yml` → `site` artifact |
| `cn-track-pboc-gold` | `update.yml` → `site` artifact |
| `global-track-container-freight` | `sse-update.yml` → `sse-history-encrypted` artifact, imported with the existing sync command |
| `cn-track-battery-schedule` | Local update command for TD market estimates and reviewed CATL reports |
| `global-track-gold` | Local update command; no Actions coverage |
| `global-track-copper` | Local update command; no Actions coverage |
| `company-profit` | `update.yml` → `site` artifact; metal prices and FX snapshot |
| `us-track-macro` | `update.yml` → `site` artifact; monthly US macroeconomic observations |
| `financial-calendar` | `update.yml` → `site` artifact with daily macro schedules and constituent earnings |
| `pe-calculator` | Browser-only; no data update needed |

### 2. Pull Actions data

**Public tools:** select the newest retained `site` artifact from a completed `update.yml` run on the default branch. The existing helper checks the workflow, repository, branch and artifact expiry. For example, inspect the selected run with:

```bash
.venv/bin/python3 - <<'PY'
from investdiy.common.github_actions import latest_artifact
artifact = latest_artifact("MagiaSN/invest-diy", "update.yml", "site")
print("Run ID:", artifact["workflow_run"]["id"])
print("Run URL:", artifact["run_url"])
print("Conclusion:", artifact["run_conclusion"])
PY
```

Download that run's artifact into a new staging directory, substituting the printed run ID:

```bash
refresh_stage=$(mktemp -d /tmp/invest-diy-refresh.XXXXXX)
gh run download RUN_ID --repo MagiaSN/invest-diy --name site --dir "$refresh_stage"
```

Inspect the staged `api/tools.json` and each requested tool's `<slug>/data/` files. Confirm required CSVs, headers and data dates against the local tool before installing anything. Back up the existing `investdiy/<package>/data/out/` outside the data directory, then copy the validated `<slug>/data/` snapshot into that tool's `data/out/`. Preserve newer local data and local-only history; if dates or coverage regress, keep the local copy and report the discrepancy. Keep each tool's outputs consistent rather than mixing files from different snapshots. Do not copy artifact pages or scripts over source files, or replace raw data/cache directories: `site` contains dashboard outputs, not the complete Actions cache.

The `site` artifact is currently retained for seven days. A failed publication job can still leave valid exported data; check the update/export jobs and artifact contents instead of rejecting a run solely because publication failed. Record the run URL and imported data dates. `git pull` does not retrieve these ignored data files.

**Shipping:** use the existing importer, which downloads, decrypts, merges local history and rebuilds outputs:

```bash
.venv/bin/python3 -m investdiy.global_track_container_freight.sync
```

This requires `gpg` and the local key file `~/.local/share/invest-diy/sse-data-passphrase`; never print the key or put it on the command line. See [shipping synchronization](tools/global-track-container-freight.md#pull-actions-data-to-the-local-dashboard) for overrides, backup behavior and validation. The importer can retain successful source updates from a partially failed collection run; report those failures along with source dates/status.

Missing/expired artifacts, authentication failures or a missing decryption key are synchronization failures, not evidence that a tool lacks Actions coverage. Preserve existing data, continue with independent tools, and report the failure. Do not silently fall back to a full local fetch for an Actions-covered tool; follow an explicit user request for such a fallback.

### 3. Update uncovered tools locally

After attempting the Actions imports, run the `TOOL["update"]` command for each uncovered tool in scope, replacing its Python executable with `.venv/bin/python3` and preserving any arguments. With the current coverage, run each requested local update independently even if another fails:

```bash
.venv/bin/python3 -m investdiy.cn_track_battery_schedule
.venv/bin/python3 -m investdiy.global_track_gold
.venv/bin/python3 -m investdiy.global_track_copper
```

Skip tools without an update command. Do not refetch ETF, PBoC gold, company-profit or shipping merely because their imported data uses a different release cadence. Recheck this list whenever workflows or tools change.

### 4. Verify and report

Inspect each updated tool's output dates and source status; a zero exit code alone does not prove every source refreshed successfully. Distinguish the last check time from the actual observation period, and report retained older data or partial failures. Start the local server if needed and verify that `curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/api/tools.json` prints `200`. Data-only changes need a page refresh, not a server restart.

Report which tools were imported from Actions (with run links), which were updated locally, which needed no update, and any failures or stale sources. Keep downloaded data and backups out of git; inspect `git status --short` before finishing.

## Static export

Only tools with `TOOL["visibility"] = "public"` are exported as static files for Surge or another static host. The local server continues to serve both public and local tools:

```bash
.venv/bin/python3 -m investdiy.export                 # export to investdiy/dist/
.venv/bin/python3 -m investdiy.export --out ../site   # export elsewhere (an empty folder or a previous export)
cd investdiy/dist && python3 -m http.server           # preview
```

- The snapshot is static: run each public tool's update command first, then export.
- The export includes public tools' pages, scripts and `data/out/` CSV files only. Local tools are also absent from `/api/tools.json`; direct URLs to their pages or data cannot resolve in the export.
- Rebuilding clears the previous export, including tools newly marked local. Source directories and local data are retained. The maintainer's `local/publish.py` uses this same filtered exporter.
- A visibility change affects the hosted site only after the next deployment. Merely exporting does not change an existing Surge deployment.

## Scheduled updates

Only tools explicitly marked `visibility: public` enter the public export and publication workflow. Missing visibility defaults to local. ETF, China PBoC gold reserves, US macroeconomic data, the financial calendar, the PE calculator and company-profit are public; global gold, copper and the SSE shipping tracker are local. Browser-only tools without an update command skip data refresh and freshness checks. The shipping tracker's [separate collection workflow](tools/global-track-container-freight.md#publication-times-and-scheduled-collection) runs at 09:37, 13:37, 15:37, 17:37 and 20:37 Beijing time, saves encrypted history, and does not publish pages to Surge.

`.github/workflows/update.yml` runs tools due for refresh, checks every public tool's data dates and exports the site; `publish` then publishes that export to `invest-diy.surge.sh`. Only `publish` can read the surge secrets.

- **ETF**: 23:47 Monday-Friday for preliminary units of day T, and 09:37 Tuesday-Saturday for final units published on T+1 (Beijing time).
- **Gold**: 23:53 on the 7th of each month, retries on the 8th-10th only while the previous month's figures are missing, and an unconditional revision check on the 15th. These runs include weekends; ETF fetching is skipped on the gold schedule.
- **Company profit**: 09:17 and 16:17 Monday–Friday (Beijing time) refresh all four metal quotes and FX, then publish. These slots do not refetch ETF or PBoC gold with complete cached outputs; company-profit uses its cache on their slots. Its historical baseline bootstraps from a checksum-pinned public release asset, so CI needs no private research checkout.
- **US macro**: 09:43 on the 2nd of each month (Beijing time; `43 1 2 * *` UTC) refreshes the headline and inflation variant series from FRED, BLS and BEA and publishes. Other slots reuse cached output. Each indicator retains its own observation month; this monthly run collects releases made during the preceding month.
- **Financial calendar** runs daily at 08:33 Beijing time (`33 0 * * *` UTC). It collects US economic release and meeting dates and company earnings. Other slots reuse the two cached snapshots or rebuild them if either is missing or their update dates differ.
- **Manual and bootstrap**: "Run workflow" defaults to refreshing all public data tools; choose `company-profit`, `us-track-macro` or `financial-calendar` as the refresh scope to refresh only the selected tool while reusing other tools’ valid cached outputs. Publication can be disabled independently. Missing data is rebuilt on any run, including after cache eviction. Otherwise, gold uses cached output on ETF runs.


- **Secrets**: create an environment named `Publish` under Settings → Environments and add two environment secrets: `SURGE_LOGIN` (the surge account email) and `SURGE_TOKEN` (printed by `npx --yes surge@0.44.5 token`).
- **Data between runs**: `investdiy/*/data/` is kept in the Actions cache, not in git. The first run, or a run after the cache was evicted (7 days without a run), backfills from scratch and takes much longer. Local tools such as the freight tracker are not updated by this publication workflow. The freight tracker has a separate [SSE collection workflow](tools/global-track-container-freight.md#publication-times-and-scheduled-collection), with encrypted history artifacts and no publishing job. Local data folders still need independent backups.
- **Seeding from local data**: to skip the backfill, upload local data to a draft release (drafts are visible only to collaborators and create no tag), run the workflow by hand with "seed" checked, then delete the release:

  ```bash
  tar czf seed.tar.gz --exclude='*.tmp' investdiy/*/data
  gh release create seed-data seed.tar.gz --draft --title seed-data --notes "Seed data for the update workflow"
  gh workflow run update.yml -f seed=true
  gh release delete seed-data --yes        # after the run has saved the cache
  ```
- **Run summary**: the Actions summary lists every tool's updated date, live date and maximum allowed age. Reruns save a separate cache so a retry can retain newly fetched data.
- **Safety checks**: the run does not publish if a tool's "data as of" date is older than the live site's, and fails when a tool's data has not advanced for more than 10 days (or the tool's `max_stale_days`, such as 45 for monthly data) (some legacy collectors log source failures without stopping; company-profit fails immediately if any quote or FX collection fails). GitHub emails the repository owner when a run fails.
- **Inactivity**: GitHub disables scheduled workflows in public repositories after 60 days without commits; re-enable it from the Actions tab.
