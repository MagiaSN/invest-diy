# invest-diy

**English** | [简体中文](docs/i18n/README.zh-CN.md)

A small toolbox of self-hosted market dashboards built entirely on public data. Each tool fetches data, computes indicators and serves a bilingual (English / Chinese) web page from a local server; the whole site can also be exported as a static snapshot.

Live snapshot: <https://invest-diy.surge.sh/>

> Everything here is an organisation of public information. It is not investment advice.

## Tools

| Tool | What it does |
|---|---|
| [A-Share National Team ETF Tracker](docs/tools/ashare-track-national-team-etf.md) | Estimates daily net creations and redemptions of the broad-based ETFs held by China's "national team" (Central Huijin, China Securities Finance and others) from exchange-published unit counts, flags entry and exit waves, derives hard lower bounds on its selling from fund reports, and backtests a strategy that follows its estimated position one day later. |
| [China PBoC Gold Reserves Tracker](docs/tools/cn-track-pboc-gold.md) | Tracks the People's Bank of China's official gold reserves month by month since 1977 (SAFE's monthly tables, with IMF data for the earlier history): holdings in tonnes and ounces, monthly additions, the buying streak and buying phases, and gold's value and share of official reserves. |

## Features

- **No framework, no build step**: a standard-library Python HTTP server and plain HTML / JavaScript pages
- **Fully local front end**: charts use a vendored copy of d3; pages load nothing from CDNs
- **Bilingual pages**: every page ships English and Chinese text and picks one from the browser language, with a switch in the top bar
- **Static export**: one command exports the whole site as static files that any static host can serve
- **Pluggable tools**: a tool is a Python sub-package with a metadata dict and a `web/` folder; the home page discovers it automatically

## Quick start

Requires Python 3.10+.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/python3 -m investdiy.ashare_track_national_team_etf   # fetch data and compute (first run takes ~10 minutes)
.venv/bin/python3 -m investdiy.server                            # open http://localhost:8765/
```

## Project layout

```
invest-diy/
├── investdiy/
│   ├── server.py        local HTTP server
│   ├── registry.py      discovers tool sub-packages
│   ├── export.py        static export
│   ├── common/          shared Python helpers (HTTP, CSV, market data, fund reports)
│   ├── web/             home page and shared front-end assets
│   └── <tool>/          one sub-package per tool
└── docs/                detailed documentation
```

## Documentation

- [Architecture](docs/architecture.md): server, tool discovery, front-end kit, static export
- [Development guide](docs/development.md): setup, conventions, adding a tool, static export
- Tools: [A-Share National Team ETF Tracker](docs/tools/ashare-track-national-team-etf.md), [China PBoC Gold Reserves Tracker](docs/tools/cn-track-pboc-gold.md)

## Contributing

Issues and pull requests are welcome. Please read the [development guide](docs/development.md) first; new pages must be bilingual and must not load third-party scripts from CDNs.

## Disclaimer

The data comes from public sources (stock exchanges, fund periodic reports, official statistics, market data providers) and may contain errors, omissions or delays. Attributions such as "national-team buying" are inferences from public data, not official confirmations. Nothing in this project is investment advice.

The repository contains no market data; each tool fetches it from the original providers when you run it. Check the providers' terms before redistributing fetched data.

## Third-party software

- [d3](https://d3js.org/) v7.9.0, vendored in `investdiy/web/static/vendor/`, ISC License (see `investdiy/web/static/vendor/LICENSE-d3.txt`)

## License

[MIT](LICENSE)
