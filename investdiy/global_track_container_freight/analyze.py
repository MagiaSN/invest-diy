"""Turn data/observations.csv into the datasets read by the page.

Changes are measured against the observation of the same series about 1, 4 and 52 weeks earlier
(within 3 days of that date); when no observation is close enough the change is left blank, which is
common before weekly collection started because archive snapshots are sparse.

Outputs (data/out/):
  history.csv  every observation: index, series, date, value, source (sse = live page, archive = Wayback snapshot)
  latest.csv   per series: latest value and its changes over 1 / 4 / 52 weeks, number of observations
  kpi.csv      one row: as_of (latest publication date of any index), sse_since (first CCFI period read from
               the live page), updated

Usage: .venv/bin/python3 -m investdiy.global_track_container_freight.analyze
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from ..common.csvio import read_rows, write_rows
from .fetch import FIELDS, OBS_CSV
from .indices import SERIES

OUT = Path(__file__).resolve().parent / "data" / "out"
TOLERANCE = 3   # days


def _change(points: list[tuple[date, float]], d: date, v: float, weeks: int) -> str:
    target = d - timedelta(weeks=weeks)
    near = [(abs((p - target).days), pv) for p, pv in points if p < d and abs((p - target).days) <= TOLERANCE]
    if not near:
        return ""
    base = min(near)[1]
    return f"{(v / base - 1) * 100:.2f}"


def main() -> None:
    obs = read_rows(OBS_CSV)
    if not obs:
        raise SystemExit(f"{OBS_CSV} is empty; run the fetch step first")
    write_rows(OUT / "history.csv", obs, FIELDS, sort_by=("index", "series", "date"))

    by_series: dict[tuple[str, str], list[tuple[date, float]]] = defaultdict(list)
    for r in obs:
        by_series[(r["index"], r["series"])].append((date.fromisoformat(r["date"]), float(r["value"])))

    latest = []
    for index, series in SERIES.items():
        for key, _, name, name_en in series:
            pts = sorted(by_series.get((index, key), []))
            if not pts:
                continue
            d, v = pts[-1]
            prev = pts[-2] if len(pts) > 1 else None
            latest.append({
                "index": index, "series": key, "name": name, "name_en": name_en,
                "date": d.isoformat(), "value": f"{v:.2f}",
                "prev_date": prev[0].isoformat() if prev else "", "prev": f"{prev[1]:.2f}" if prev else "",
                "chg_1w": _change(pts, d, v, 1), "chg_4w": _change(pts, d, v, 4), "chg_52w": _change(pts, d, v, 52),
                "n": len(pts), "first": pts[0][0].isoformat(),
            })
    write_rows(OUT / "latest.csv", latest, list(latest[0]))

    # weekly collection starts with the CCFI page (the SCFIS trace page reaches four weeks back)
    sse_dates = [r["date"] for r in obs if r["source"] == "sse" and r["index"] == "ccfi"]
    kpi = {
        "as_of": max(r["date"] for r in latest),
        "sse_since": min(sse_dates) if sse_dates else "",
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    write_rows(OUT / "kpi.csv", [kpi], list(kpi))
    print(f"  {len(obs)} observations, {len(latest)} series, as of {kpi['as_of']} -> {OUT.relative_to(OUT.parent.parent)}")


if __name__ == "__main__":
    main()
