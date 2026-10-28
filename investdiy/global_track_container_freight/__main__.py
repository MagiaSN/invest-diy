"""One-command update: fetch the SSE pages (and new archive snapshots once a week) -> compute.

.venv/bin/python3 -m investdiy.global_track_container_freight [--skip-fetch] [--refresh-archive]
"""

import argparse

from . import analyze, fetch

ap = argparse.ArgumentParser(description="Fetch CCFI / SCFI / SCFIS and recompute the dashboard data")
ap.add_argument("--skip-fetch", action="store_true", help="recompute only")
ap.add_argument("--refresh-archive", action="store_true", help="look for new archive snapshots now (otherwise weekly)")
a = ap.parse_args()
if not a.skip_fetch:
    fetch.run(a.refresh_archive)
analyze.main()
