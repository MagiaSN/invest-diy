"""One-command update: fetch the SSE pages (and new archive snapshots once a week) -> compute.

.venv/bin/python3 -m investdiy.global_track_container_freight [--skip-fetch] [--refresh-archive]
"""

import argparse

from . import analyze, fetch

ap = argparse.ArgumentParser(description="Fetch all SSE shipping indices and recompute the dashboard data")
ap.add_argument("--skip-fetch", action="store_true", help="recompute only")
ap.add_argument("--refresh-archive", action="store_true", help="look for new archive snapshots now (otherwise weekly)")
ap.add_argument("--latest-only", action="store_true", help="fetch latest SSE periods without archive downloads")
a = ap.parse_args()
if not a.skip_fetch:
    fetch.run(a.refresh_archive, a.latest_only)
analyze.main()
