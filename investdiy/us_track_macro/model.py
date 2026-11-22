"""Calendar-aligned monthly calculations; missing observations stay missing."""

from __future__ import annotations

import calendar
import csv
from datetime import date
import io
import json
import math
from pathlib import Path

HEADLINE_SERIES = {
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
LEGACY_FIELDS = ["month", *HEADLINE_SERIES.values(), *DERIVED, "as_of", "fetched_at"]
VARIANTS = json.loads((Path(__file__).parent / "web" / "variants.json").read_text(encoding="utf-8"))
SERIES = HEADLINE_SERIES.copy()
PROVIDERS = {}
INDEX_PAIRS = {
    "cpi": ("CPIAUCSL", "CPIAUCNS"),
    "ppi": ("PPIFIS", "PPIFID"),
    "pce": ("PCEPI", "PCEPI"),
}
RATE_SERIES = set()
variant_fields = []
for family, variants in VARIANTS.items():
    for key, spec in variants.items():
        prefix = f"{family}_{key}"
        for mode in ("index", "nsa", "yoy", "annualized_mom"):
            if mode in spec:
                sid = spec[mode]
                SERIES[sid] = f"{prefix}_{mode}"
                PROVIDERS[sid] = spec.get("provider", "fred")
                variant_fields.append(SERIES[sid])
        if "index" in spec:
            INDEX_PAIRS[prefix] = (spec["index"], spec.get("nsa", spec["index"]))
            variant_fields.append(f"{prefix}_yoy")
        else:
            RATE_SERIES.update((spec["yoy"], spec["annualized_mom"]))
        variant_fields.append(f"{prefix}_mom")
FIELDS = [*LEGACY_FIELDS, *variant_fields]


def observation_value(raw, series_id):
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError(f"{series_id}: non-finite observation {raw}")
    if series_id in RATE_SERIES:
        if value <= -100:
            raise ValueError(f"{series_id}: invalid price change {raw}")
    elif value < 0 or (value == 0 and series_id not in ("UNRATE", "FEDFUNDS")):
        raise ValueError(f"{series_id}: invalid value {raw}")
    return value


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
        value = observation_value(raw, series_id)
        # Only completed observation months are displayed, including FEDFUNDS.
        if d < today.replace(day=1):
            result[d.strftime("%Y-%m")] = value
    if not result:
        raise ValueError(f"{series_id}: no completed monthly observations")
    return result


def build_monthly(series: dict, fetched_at: str, start: str = "1990-01") -> list[dict]:
    legacy = series.keys() == HEADLINE_SERIES.keys()
    if (not legacy and series.keys() != SERIES.keys()) or not all(series.values()):
        raise ValueError("Incomplete macroeconomic snapshot")
    latest = max(max(values) for values in series.values())
    common_latest = min(max(values) for values in series.values())
    year, month = map(int, common_latest.split("-"))
    as_of = date(year, month, calendar.monthrange(year, month)[1]).isoformat()

    def change(sid, m, lag, percent=True):
        current, previous = series[sid].get(m), series[sid].get(offset(m, -lag))
        if current is None or previous is None or (percent and previous == 0):
            return None
        return round((current / previous - 1) * 100 if percent else current - previous, 6)

    source_fields = HEADLINE_SERIES if legacy else SERIES
    rows = []
    m = max(start, min(min(values) for values in series.values()))
    while m <= latest:
        row = {"month": m, "as_of": as_of, "fetched_at": fetched_at}
        row.update({field: series[sid].get(m) for sid, field in source_fields.items()})
        for name, (sa, yoy) in INDEX_PAIRS.items():
            if sa not in series:
                continue
            row[f"{name}_yoy"] = change(yoy, m, 12)
            row[f"{name}_mom"] = change(sa, m, 1)
        if not legacy:
            annualized = row["pce_trimmed_annualized_mom"]
            row["pce_trimmed_mom"] = (
                None if annualized is None else round(100 * math.expm1(math.log1p(annualized / 100) / 12), 6)
            )
        row["payrolls_change_k"] = change("PAYEMS", m, 1, False)
        row["unemployment_change_pp"] = change("UNRATE", m, 1, False)
        row["fed_funds_change_pp"] = change("FEDFUNDS", m, 1, False)
        rows.append(row)
        m = offset(m, 1)
    if not rows:
        raise ValueError("No observations in the display period")
    return list(reversed(rows))
