"""One-command update: fetch IMF history and SAFE monthly tables -> compute.

.venv/bin/python3 -m investdiy.cn_track_pboc_gold [--skip-fetch]
"""

import argparse

from . import analyze, fetch

ap = argparse.ArgumentParser(description="Fetch China's official gold reserves and recompute the dashboard data")
ap.add_argument("--skip-fetch", action="store_true", help="recompute from the local data only")
a = ap.parse_args()
if not a.skip_fetch:
    fetch.run()
analyze.main()
