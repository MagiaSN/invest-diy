"""Build history, per-series latest values, current shipping snapshots and source status.

Missing current cells stay missing even when historical observations exist.
Calendar changes use observations within three days of the target date; the
published change and the change from the previous observation are separate.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from ..common.csvio import read_rows, write_rows
from .fetch import FIELDS, OBS_CSV, CURRENT_CSV, STATUS_CSV, STATUS_FIELDS, read_archive_metadata
from .indices import SERIES, INDEX_NAMES, frequency, source_url

OUT = Path(__file__).resolve().parent / "data" / "out"
TOLERANCE = 3
LATEST_FIELDS = ["index", "series", "name", "name_en", "unit", "weight", "date", "value", "prev_date", "prev",
                 "chg_prev", "chg_1w", "chg_4w", "chg_52w", "n", "first", "reported_date", "current", "period",
                 "change", "change_unit", "availability"]


def _pct(value: float, base: float) -> str:
    return f"{(value / base - 1) * 100:.2f}" if base else ""


def _change(points: list[tuple[date, float]], d: date, v: float, weeks: int) -> str:
    target = d - timedelta(weeks=weeks)
    near = [(abs((p - target).days), p, pv) for p, pv in points if p < d and abs((p - target).days) <= TOLERANCE]
    return _pct(v, min(near)[2]) if near else ""


def main(data_dir: Path | None = None) -> None:
    """Compute outputs in place, or in a staging directory before importing a backup."""
    obs_csv = data_dir / "observations.csv" if data_dir is not None else OBS_CSV
    current_csv = data_dir / "current.csv" if data_dir is not None else CURRENT_CSV
    status_csv = data_dir / "status.csv" if data_dir is not None else STATUS_CSV
    out = data_dir / "out" if data_dir is not None else OUT
    obs = read_rows(obs_csv)
    if not obs:
        raise ValueError("No observations; fetch or restore data before computing outputs")
    write_rows(out / "history.csv", obs, FIELDS, sort_by=("index", "series", "date"))
    by_series = defaultdict(list)
    for r in obs:
        by_series[(r["index"], r["series"])].append((date.fromisoformat(r["date"]), float(r["value"])))

    metadata = {(r["index"], r["series"]): r for r in read_archive_metadata()
                if (r["index"], r["series"]) in by_series}
    for index, series in SERIES.items():
        for key, _, name, name_en in series:
            metadata[(index, key)] = {"index": index, "series": key, "name": name, "name_en": name_en, "unit": "points"}
    for r in read_rows(current_csv):
        metadata[(r["index"], r["series"])] = r
    # Preserve unknown historical series from published data as well.
    for index, key in by_series:
        metadata.setdefault((index, key), {"index": index, "series": key, "name": key, "name_en": key, "unit": ""})

    latest = []
    for (index, key), meta in metadata.items():
        pts = sorted(by_series.get((index, key), []))
        d, v = pts[-1] if pts else (None, None)
        prev = pts[-2] if len(pts) > 1 else None
        current = meta.get("value", "")
        row = {f: "" for f in LATEST_FIELDS}
        row.update({f: meta.get(f, "") for f in ["index", "series", "name", "name_en", "unit", "weight", "change", "change_unit"]})
        row.update(date=d.isoformat() if d else "", value=format(v, ".12g") if pts else "",
                   prev_date=prev[0].isoformat() if prev else "", prev=format(prev[1], ".12g") if prev else "",
                   chg_prev=_pct(v, prev[1]) if prev else "", n=len(pts), first=pts[0][0].isoformat() if pts else "",
                   reported_date=meta.get("date", ""), current=current,
                   period=meta.get("period", ""), availability=("historical" if "date" not in meta
                                                                             else "available" if current else "unavailable"))
        for weeks in (1, 4, 52):
            row[f"chg_{weeks}w"] = _change(pts, d, v, weeks) if pts else ""
        latest.append(row)
    write_rows(out / "latest.csv", latest, LATEST_FIELDS)
    statuses = {r["index"]: r for r in read_rows(status_csv)}
    for index, names in INDEX_NAMES.items():
        statuses.setdefault(index, dict(zip(STATUS_FIELDS, [index, *names, frequency(index), "", "", "", "not_fetched", 0, 0,
                                                          source_url(index)])))
    write_rows(out / "status.csv", list(statuses.values()), STATUS_FIELDS)
    core_dates = [r["date"] for r in latest if (r["index"], r["series"]) in
                  {("ccfi", "composite"), ("scfi", "composite"), ("scfis", "europe"), ("scfis", "uswc")}]
    sse_dates = [r["date"] for r in obs if r["source"] == "sse" and r["index"] == "ccfi"]
    kpi = {
        # Use the oldest headline series, so a fresh daily index cannot hide stale weekly data.
        "as_of": min(core_dates) if len(core_dates) == 4 and all(core_dates) else "",
        "latest_date": max(r["date"] for r in obs),
        "sse_since": min(sse_dates) if sse_dates else "",
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    write_rows(out / "kpi.csv", [kpi], list(kpi))
    print(f"  {len(obs)} observations, {len(latest)} series, weekly coverage through {kpi['as_of']} -> {out}")


if __name__ == "__main__":
    main()
