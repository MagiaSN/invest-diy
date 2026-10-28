"""One-command update: fetch units -> scan periodic reports (build the pool) -> compute -> backtest.

.venv/bin/python3 -m investdiy.ashare_track_national_team_etf [--start YYYY-MM-DD] [--skip-fetch] [--skip-holders]
"""

import argparse

from . import analyze, backtest, fetch, holders

ap = argparse.ArgumentParser(description="Fetch ETF units, scan periodic reports and recompute the dashboard data")
ap.add_argument("--start", default=fetch.DEFAULT_START)
ap.add_argument("--end", default=None)
ap.add_argument("--skip-fetch", action="store_true", help="do not fetch units / prices")
ap.add_argument("--skip-holders", action="store_true", help="do not scan periodic reports (parsed reports are cached; a normal run adds ~40 list requests)")
a = ap.parse_args()
if not a.skip_fetch:
    fetch.run(a.start, a.end)
if not a.skip_holders:
    holders.main()
analyze.main()
backtest.main()
