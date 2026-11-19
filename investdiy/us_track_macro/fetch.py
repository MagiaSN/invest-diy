"""Fetch a complete FRED snapshot before replacing any dashboard data."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path

from requests.utils import default_user_agent

from ..common import csvio, net
from .model import FIELDS, SERIES, build_monthly, parse_series

DATA = Path(__file__).resolve().parent / "data"
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


def fetch_series(series_id):
    # FRED's CSV endpoint can time out with the shared browser User-Agent.
    response = net.get(URL, params={"id": series_id}, headers={"User-Agent": default_user_agent()}, retries=2, timeout=30)
    return parse_series(response.text, series_id)


def run(data_dir: Path = DATA, *, skip_fetch=False):
    snapshot_path = data_dir / "raw" / "fred.json"
    previous = json.loads(snapshot_path.read_text(encoding="utf-8")) if snapshot_path.exists() else None
    if skip_fetch:
        if previous is None:
            raise ValueError("No cached snapshot; run without --skip-fetch first")
        snapshot = previous
    else:
        series, errors = {}, []
        with ThreadPoolExecutor(max_workers=4) as pool:
            jobs = {pool.submit(fetch_series, sid): sid for sid in SERIES}
            for job in as_completed(jobs):
                sid = jobs[job]
                try:
                    series[sid] = job.result()
                    if previous and max(series[sid]) < max(previous["series"][sid]):
                        raise ValueError("latest observation regressed")
                    print(f"{sid}: {len(series[sid])} months, latest {max(series[sid])}", flush=True)
                except Exception as exc:
                    errors.append(f"{sid}: {exc}")
        if errors:
            raise RuntimeError("Refresh failed; existing snapshot and dashboard retained.\n" + "\n".join(errors))
        snapshot = {"fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "series": series}
    rows = build_monthly(snapshot["series"], snapshot["fetched_at"])
    if not skip_fetch:
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = snapshot_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
        temporary.replace(snapshot_path)
    csvio.atomic_csv(data_dir / "out" / "monthly.csv", rows, FIELDS)
    print(f"Wrote {len(rows)} months; all sources available through {rows[0]['as_of']}; fetched {snapshot['fetched_at']}")
    return rows
