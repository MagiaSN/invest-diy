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
5. Restart the server; the home page lists the new tool automatically.
6. Document the tool in `docs/tools/<slug>.md` (method, data sources, validation, limitations) and add it to the tools table in `README.md`.

Further pages of the same tool sit next to `index.html` (for example `web/backtest.html`, served at `/<slug>/backtest.html`).

## Checking changes

- `curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/api/tools.json` should print `200`.
- Open the page in both languages and at a narrow width (about 400px); tables may scroll horizontally, the page itself should not.
- `node --check <file>.js` catches syntax errors in page scripts; a broken dictionary file stops the whole page from translating.

## Static export

The site can be exported as static files and served by any static file host:

```bash
.venv/bin/python3 -m investdiy.export                 # export to investdiy/dist/
.venv/bin/python3 -m investdiy.export --out ../site   # export elsewhere (an empty folder or a previous export)
cd investdiy/dist && python3 -m http.server           # preview
```

- The snapshot is static: run each tool's update command first, then export.
- The export includes each tool's `data/out/` CSV files. Check the data providers' terms before hosting it publicly.

## Scheduled updates

`.github/workflows/update.yml` runs tools due for refresh, checks every tool's data dates and exports the site; `publish` then publishes that export to `invest-diy.surge.sh`. Only `publish` can read the surge secrets.

- **ETF**: 23:47 Monday-Friday for preliminary units of day T, and 09:37 Tuesday-Saturday for final units published on T+1 (Beijing time).
- **Gold**: 23:53 on the 7th of each month, retries on the 8th-10th only while the previous month's figures are missing, and an unconditional revision check on the 15th. These runs include weekends; ETF fetching is skipped on the gold schedule.
- **Manual and bootstrap**: "Run workflow" forces all tools to update, optionally without publication. Missing data is rebuilt on any run, including after cache eviction. Otherwise, gold uses cached output on ETF runs.


- **Secrets**: create an environment named `Publish` under Settings → Environments and add two environment secrets: `SURGE_LOGIN` (the surge account email) and `SURGE_TOKEN` (printed by `npx --yes surge@0.44.5 token`).
- **Data between runs**: `investdiy/*/data/` is kept in the Actions cache, not in git. The first run, or a run after the cache was evicted (7 days without a run), backfills from scratch and takes much longer.
- **Seeding from local data**: to skip the backfill, upload local data to a draft release (drafts are visible only to collaborators and create no tag), run the workflow by hand with "seed" checked, then delete the release:

  ```bash
  tar czf seed.tar.gz --exclude='*.tmp' investdiy/*/data
  gh release create seed-data seed.tar.gz --draft --title seed-data --notes "Seed data for the update workflow"
  gh workflow run update.yml -f seed=true
  gh release delete seed-data --yes        # after the run has saved the cache
  ```
- **Run summary**: the Actions summary lists every tool's updated date, live date and maximum allowed age. Reruns save a separate cache so a retry can retain newly fetched data.
- **Safety checks**: the run does not publish if a tool's "data as of" date is older than the live site's, and fails when a tool's data has not advanced for more than 10 days (or the tool's `max_stale_days`, such as 45 for monthly data) (fetch errors are logged but do not stop an update, so this is how a blocked data source shows up). GitHub emails the repository owner when a run fails.
- **Inactivity**: GitHub disables scheduled workflows in public repositories after 60 days without commits; re-enable it from the Actions tab.
