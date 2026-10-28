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

Market codes: `ashare` (China A-shares), `hk` (Hong Kong), `us` (United States), `kr` (Korea), `global` (cross-market). Starting with the market keeps tools of the same market together; `_track_` leaves room for other kinds of tools.

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
