# Architecture

invest-diy is a set of independent tools that share one local web server, one front-end kit and one export step. Nothing needs a build: the server is standard-library Python and the pages are plain HTML and JavaScript.

```
fetch (tool modules) ──► investdiy/<tool>/data/          raw data, caches
compute (tool modules) ─► investdiy/<tool>/data/out/      CSV files read by the pages
serve  (investdiy/server.py) ► http://localhost:8765/     home page + /<slug>/ per tool
export (investdiy/export.py) ► investdiy/dist/                static snapshot for any static host
```

## Tool discovery

`investdiy/registry.py` scans the sub-packages of `investdiy/`. A sub-package is a tool when:

- its `__init__.py` defines a `TOOL` dict, and
- it has `web/index.html`.

`TOOL` holds the slug (the URL segment), titles, descriptions and kinds in Chinese and English, the update command, and optionally `asof_file`, a CSV whose first row has an `as_of` column shown on the home page as "data as of", and `max_stale_days`, how old that date may get before the scheduled update fails (default 10, longer for monthly data). Slugs must be unique and cannot be `api`, `static`, `common` or `web`.

Discovery runs once when the server starts, so a new tool or a changed `TOOL` dict needs a server restart. Page files and data files are read on every request.

## Server routes

`investdiy/server.py` (`ThreadingHTTPServer`, default `127.0.0.1:8765`):

| Path | Content |
|---|---|
| `/` | home page (`investdiy/web/index.html`), lists every tool |
| `/api/tools.json` | tool list as JSON, used by the home page |
| `/static/<path>` | shared front-end assets (`investdiy/web/static/`) |
| `/<slug>/` | tool page (`investdiy/<package>/web/index.html`) |
| `/<slug>/<path>` | the tool's own front-end files (`investdiy/<package>/web/<path>`) |
| `/<slug>/data/<file>` | the tool's output data (`investdiy/<package>/data/out/<file>`) |

All paths are resolved inside their base directory, so `../` cannot escape it. Responses carry `Cache-Control: no-cache` because data changes daily.

Check that a running server is healthy with `curl http://localhost:8765/api/tools.json`; checking `/` alone is not enough, since an outdated process can still serve the home page.

## Front-end kit

Every page loads the shared assets in this order:

```html
<link rel="stylesheet" href="/static/base.css">
<script src="/static/vendor/d3.v7.9.0.min.js"></script>
<script src="/static/i18n.js"></script>
<script src="/static/site.js"></script>
<script src="/static/kit.js"></script>
<script src="strings.js"></script>   <!-- the page's dictionary -->
<script src="app.js"></script>       <!-- the page's code -->
```

| File | Role |
|---|---|
| `base.css` | design tokens for light and dark themes (colours follow the A-share convention: red = up / inflow, green = down / outflow) and base components: top bar, cards, tables, tooltips, segmented buttons |
| `vendor/d3.v7.9.0.min.js` | d3, vendored so that pages load nothing from CDNs |
| `i18n.js` | language detection and switching (`window.i18n`), static text via `data-i18n` attributes, dynamic text via `i18n.t()` |
| `site.js` | site frame; appends the footer disclaimer to every page |
| `kit.js` | `window.kit`: CSV loading, unit-aware formatting, colours, tooltips, redraw scheduling and page components |

Main `kit` components:

- `kit.csv(url)`: fetch a CSV and return row objects (strings)
- `kit.amt(v)`, `kit.shares(v)`, `kit.yi(v)`, `kit.axisYi(v)`: format amounts and unit counts given in yi (100 millions) as "亿元 / 亿份" in Chinese and "¥…bn / …bn units" in English
- `kit.rangePicker(el, {min, max, initial, onChange})`: a per-chart range selector (1Y / 3Y / 5Y / All / custom); `.get()` returns `[start, end]`
- `kit.sectionNav(el)`: section links built from every `<section>` with an `id` and `data-nav="<dictionary key>"`
- `kit.downloadLinks(base)`: renders `<span class="dl" data-files="a b">` as CSV download links, labelled by the page's `file.<name>` i18n keys
- `kit.markStale(el, asof, minDays = 3)`: shows a notice when the data is `minDays` or more weekdays old (monthly tools pass a longer threshold)
- `kit.tip(card)`: a tooltip positioned inside a card
- `kit.onRedraw(fn)`: calls `fn` on resize, colour-scheme change and language switch

## Bilingual pages

- Language: the user's choice (stored in `localStorage`), otherwise Chinese when the browser language starts with `zh`, otherwise English. The switch button is inserted into the top bar automatically.
- Each page registers a dictionary with `i18n.add({zh: {...}, en: {...}})`; shared entries (`common.*`) live in `i18n.js`.
- Static text: `data-i18n="key"` (text) or `data-i18n-html="key"` (with markup such as `<b>`); attributes via `data-i18n-title` and `data-i18n-aria-label`. Text inside the tags is only a placeholder until the scripts run.
- Dynamic text: `i18n.t('key', {n: 3})`; `i18n.rich()` wraps placeholder values in `<b>` for summary sentences.
- Data values stored in Chinese (signal labels, index families, holder groups) are translated through dictionary entries such as `v.进场` (checked with `i18n.has`); names get a separate `name_en` column in the data files.

## Static export

`investdiy/export.py` copies `investdiy/web/` and each tool's `web/` and `data/out/` into `investdiy/dist/` (or `--out`), writes `/api/tools.json` as a static file and adds a 404 page, so the snapshot behaves like the local server and can be served by any static file host. See the [development guide](development.md#static-export).
