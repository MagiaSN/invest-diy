"""Calendar-aligned monthly calculations; missing observations stay missing."""

from __future__ import annotations

import calendar
import csv
from datetime import date
import io
import math

SERIES = {
    "CPIAUCSL": "cpi_sa",
    "CPIAUCNS": "cpi_nsa",
    "PPIFIS": "ppi_sa",
    "PPIFID": "ppi_nsa",
    "PCEPI": "pce",
    "UNRATE": "unemployment",
    "PAYEMS": "payrolls_k",
    "FEDFUNDS": "fed_funds",
}
DERIVED = ["cpi_yoy", "cpi_mom", "ppi_yoy", "ppi_mom", "pce_yoy", "pce_mom",
           "payrolls_change_k", "unemployment_change_pp", "fed_funds_change_pp"]
FIELDS = ["month", *SERIES.values(), *DERIVED, "as_of", "fetched_at"]


def offset(month: str, n: int) -> str:
    year, m = map(int, month.split("-"))
    year, m = divmod(year * 12 + m - 1 + n, 12)
    return f"{year:04d}-{m + 1:02d}"


def parse_series(text: str, series_id: str, today: date | None = None) -> dict[str, float]:
    """Accept FRED's current and legacy date headers, with strict monthly units."""
    today = today or date.today()
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    headers = reader.fieldnames or []
    date_key = next((k for k in ("observation_date", "DATE") if k in headers), None)
    if not date_key or series_id not in headers:
        raise ValueError(f"{series_id}: unexpected CSV headers")
    result = {}
    seen = set()
    for row in reader:
        d = date.fromisoformat(row[date_key])
        if d.day != 1 or d in seen:
            raise ValueError(f"{series_id}: non-monthly or duplicate date {d}")
        seen.add(d)
        raw = row[series_id]
        if raw in ("", "."):
            continue
        value = float(raw)
        if not math.isfinite(value) or value < 0 or (series_id not in ("UNRATE", "FEDFUNDS") and value == 0):
            raise ValueError(f"{series_id}: invalid value {raw}")
        # Only completed observation months are displayed, including FEDFUNDS.
        if d < today.replace(day=1):
            result[d.strftime("%Y-%m")] = value
    if not result:
        raise ValueError(f"{series_id}: no completed monthly observations")
    return result


def build_monthly(series: dict, fetched_at: str, start: str = "1990-01") -> list[dict]:
    if set(series) != set(SERIES) or any(not v for v in series.values()):
        raise ValueError("All eight source series are required")
    latest = max(max(values) for values in series.values())
    common_latest = min(max(values) for values in series.values())
    year, month = map(int, common_latest.split("-"))
    as_of = date(year, month, calendar.monthrange(year, month)[1]).isoformat()

    def change(sid, m, lag, percent=True):
        current, previous = series[sid].get(m), series[sid].get(offset(m, -lag))
        if current is None or previous is None or (percent and previous == 0):
            return None
        return round((current / previous - 1) * 100 if percent else current - previous, 6)

    rows = []
    m = max(start, min(min(values) for values in series.values()))
    while m <= latest:
        row = {"month": m, "as_of": as_of, "fetched_at": fetched_at}
        row.update({field: series[sid].get(m) for sid, field in SERIES.items()})
        for name, sa, yoy in [("cpi", "CPIAUCSL", "CPIAUCNS"), ("ppi", "PPIFIS", "PPIFID"),
                               ("pce", "PCEPI", "PCEPI")]:
            row[f"{name}_yoy"] = change(yoy, m, 12)
            row[f"{name}_mom"] = change(sa, m, 1)
        row["payrolls_change_k"] = change("PAYEMS", m, 1, False)
        row["unemployment_change_pp"] = change("UNRATE", m, 1, False)
        row["fed_funds_change_pp"] = change("FEDFUNDS", m, 1, False)
        rows.append(row)
        m = offset(m, 1)
    if not rows:
        raise ValueError("No observations in the display period")
    return list(reversed(rows))
