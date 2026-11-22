"""Fetch a complete monthly snapshot before replacing any dashboard data."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
import json
from pathlib import Path

from openpyxl import load_workbook
from requests.utils import default_user_agent

from ..common import csvio, net
from .model import (FIELDS, HEADLINE_SERIES, LEGACY_FIELDS, PROVIDERS, SERIES,
                    build_monthly, observation_value, parse_series)

DATA = Path(__file__).resolve().parent / "data"
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


def fetch_series(series_id):
    # FRED's CSV endpoint can time out with the shared browser User-Agent.
    response = net.get(URL, params={"id": series_id}, headers={"User-Agent": default_user_agent()}, retries=2, timeout=30)
    return parse_series(response.text, series_id)


BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BEA_URL = "https://apps.bea.gov/national/Release/XLS/Underlying/Section2All_xls.xlsx"


def fetch_bls(ids):
    """The unregistered BLS API accepts batches covering up to ten calendar years."""
    today = date.today()
    cutoff = today.strftime("%Y-%m")
    result = {sid: {} for sid in ids}
    last_year = (today.replace(day=1) - timedelta(days=1)).year
    for start in range(1989, last_year + 1, 10):
        end = min(start + 9, last_year)
        response = net.post(BLS_URL, json={"seriesid": ids, "startyear": str(start), "endyear": str(end)}).json()
        if response["status"] != "REQUEST_SUCCEEDED" or response.get("message"):
            raise ValueError(f"BLS {start}–{end}: {response.get('message')}")
        batch = response["Results"]["series"]
        if {item["seriesID"] for item in batch} != set(ids) or len(batch) != len(ids):
            raise ValueError(f"Incomplete BLS response for {start}–{end}")
        for item in batch:
            sid = item["seriesID"]
            for obs in item["data"]:
                if obs["period"] == "M13":  # annual average
                    continue
                d = datetime.strptime(obs["year"] + obs["period"], "%YM%m")
                month = d.strftime("%Y-%m")
                if month >= cutoff or obs["value"] == "-":
                    continue
                if not start <= d.year <= end or month in result[sid]:
                    raise ValueError(f"{sid}: unexpected or duplicate BLS month {month}")
                result[sid][month] = observation_value(obs["value"], sid)
    return result


def fetch_bea(ids):
    """Read the monthly price-index sheet by account code, independent of row ordering."""
    workbook = load_workbook(BytesIO(net.get(BEA_URL, timeout=90).content), read_only=True, data_only=True)
    try:
        rows = workbook["U20404-M"].values
        header = next(row for row in rows if row[0] == "Line")
        months = {i: datetime.strptime(cell, "%YM%m").strftime("%Y-%m")
                  for i, cell in enumerate(header) if i >= 3 and cell}
        if len(set(months.values())) != len(months) or not months:
            raise ValueError("Invalid BEA monthly price-index header")
        cutoff = date.today().strftime("%Y-%m")
        result = {}
        for row in rows:
            sid = row[2]
            if sid in ids:
                if sid in result:
                    raise ValueError(f"{sid}: duplicate BEA account")
                result[sid] = {m: observation_value(row[i], sid) for i, m in months.items()
                               if m < cutoff and row[i] is not None}
        return result
    finally:
        workbook.close()


def collect_series():
    series = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {}
        for provider, collector in (("bls", fetch_bls), ("bea", fetch_bea)):
            ids = [sid for sid in SERIES if PROVIDERS.get(sid) == provider]
            jobs[pool.submit(collector, ids)] = (provider, ids)
        for sid in SERIES:
            if PROVIDERS.get(sid, "fred") == "fred":
                jobs[pool.submit(fetch_series, sid)] = ("fred", [sid])
        for job in as_completed(jobs):
            provider, ids = jobs[job]
            try:
                values = job.result()
                batch = {ids[0]: values} if provider == "fred" else values
                if set(batch) != set(ids) or not all(batch.values()):
                    raise ValueError("missing source observations")
                series.update(batch)
            except Exception as exc:
                raise RuntimeError(f"Refresh failed for {', '.join(ids)}. Existing data retained: {exc}") from exc
    return series


def run(data_dir: Path = DATA, *, skip_fetch=False):
    snapshot_path = data_dir / "raw" / "fred.json"
    previous = json.loads(snapshot_path.read_text(encoding="utf-8")) if snapshot_path.exists() else None
    if skip_fetch:
        if previous is None:
            raise ValueError("No cached snapshot; run without --skip-fetch first")
        snapshot = previous
    else:
        series = collect_series()
        if previous:
            for sid, old in previous["series"].items():
                if sid in series and max(series[sid]) < max(old):
                    raise RuntimeError(f"{sid}: latest observation regressed. Existing data retained.")
        snapshot = {"fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "series": series}
    rows = build_monthly(snapshot["series"], snapshot["fetched_at"])
    if not skip_fetch:
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = snapshot_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
        temporary.replace(snapshot_path)
    fields = LEGACY_FIELDS if snapshot["series"].keys() == HEADLINE_SERIES.keys() else FIELDS
    csvio.atomic_csv(data_dir / "out" / "monthly.csv", rows, fields)
    print(f"Wrote {len(rows)} months; all sources available through {rows[0]['as_of']}; fetched {snapshot['fetched_at']}")
    return rows
