# CLAUDE.md

Guidance for AI coding agents working in this repository. Human contributors should start with [README.md](README.md) and [docs/development.md](docs/development.md).

## Project

invest-diy is a toolbox of self-hosted market dashboards built on public data. Each tool is a sub-package of `investdiy/` that fetches data, writes CSV files to its `data/out/` folder and serves bilingual pages through a standard-library HTTP server. See [docs/architecture.md](docs/architecture.md).

## Commands

Run from the repository root with the project's virtual environment:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python3 -m investdiy.server                              # http://localhost:8765/
.venv/bin/python3 -m investdiy.<package>                           # update one tool's data
.venv/bin/python3 -m investdiy.export                              # export the static site to investdiy/dist/
```

## Rules

- **Data refresh requests follow the [Data update SOP](docs/development.md#data-update-sop)**: first pull the latest available GitHub Actions data, including separate collection workflows; then run local updates only for tools not covered by Actions. Skip tools without an update command and report synchronization failures instead of silently treating covered tools as uncovered.
- **Company profit model and backtests:** Use sales volume as the quantity input and company production guidance for its presets. Selling prices and unit sales costs are also user inputs. The model maps those inputs to earnings. Default to the latest five complete fiscal years, with the preceding annual report as the first baseline. For model error, use reported full-year sales volumes, realized prices and unit sales costs from the original annual report, freeze the other model parameters at the prior baseline, and compare estimated and reported earnings for that same period. Evaluate input forecasts separately from model accuracy.
- **One tool, one sub-package** under `investdiy/`; shared logic goes in `investdiy/common/` (Python) or `investdiy/web/static/` (front end).
- **Pages are local only**: no CDNs; vendor libraries under `investdiy/web/static/vendor/`.
- **Every page is bilingual** (English and Chinese): static text via `data-i18n` keys, dynamic text via `i18n.t()`, metadata via `title_en` / `description_en` / `kind_en`.
- **The disclaimer lives only in `investdiy/web/static/site.js`**; pages describe method, sources and limitations, not disclaimers.
- **Each time-series chart has its own range picker**; ranges are not stored in the URL.
- **Trackers follow the naming scheme** in [docs/development.md](docs/development.md#naming-trackers).
- **Comments and documentation are in English.** Translations of reader-facing documents go in `docs/i18n/`; when `README.md` changes, update `docs/i18n/README.zh-CN.md` too.
- **Tool documentation** lives in `docs/tools/<slug>.md`, not in the package.
- **Do not commit data**: `investdiy/*/data/` and `investdiy/dist/` are git-ignored.

## After changing a tool

- Check the local server: `curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/api/tools.json` must print `200`. Start it if it is not running, and restart it after changing `investdiy/server.py`, `investdiy/registry.py`, a `TOOL` dict or adding a tool (pages and data files are read on each request).
- Run `node --check` on edited JavaScript files; check pages in both languages.
- When editing long documents with scripts, compare the list of headings before and after so that no section is lost.
