"""PDCI composite history from Panasia, with the official Xinhua chart as fallback."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from ..common import net
from .parse import CURRENT_FIELDS, number

PANASIA_PAGE = "https://www.epanasia.com/epanasia/freightIndex/"
PANASIA_API = "https://www.epanasia.com/epanasia/gateway/api/web/commonUrl/freight/epanBdFreightIndex"
XINHUA_PAGE = "https://indices.cnfin.com/3318271/index.html?idx=2"
XINHUA_CHART = "https://api.cnfin.com/chart.mult.html?ids=12549&type=1"
XINHUA_API = "https://api.cnfin.com/roll/charts/getContent"


def _observations(records: list, date_key: str, value_key: str, source: str) -> list[dict]:
    """Validate a whole response before allowing it to replace saved data."""
    if not isinstance(records, list) or not records:
        raise ValueError("empty PDCI history")
    today = datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Shanghai")).date()
    points = {}
    for record in records:
        d = date.fromisoformat(record[date_key].strip().replace("/", "-"))
        value = number(str(record[value_key]))
        if not value or float(value) <= 0 or not date(2015, 6, 5) <= d <= today:
            raise ValueError("invalid PDCI observation")
        value = format(float(value), ".12g")
        if d in points and points[d] != value:
            raise ValueError("conflicting PDCI observations")
        points[d] = value
    return [dict(index="pdci", series="composite", date=d.isoformat(), value=v, source=source)
            for d, v in sorted(points.items())]


def fetch_panasia() -> list[dict]:
    response = net.post(PANASIA_API, json={"indexType": "multiple", "count": None},
                        headers={"Referer": PANASIA_PAGE, "Cache-Control": "no-cache"}, timeout=25, retries=2).json()
    if response.get("code") != 0:
        raise ValueError("Panasia query failed")
    # Use the plain records supplied by the source, not its encoded chart values.
    records = response["data"]["bdFreightIndexMaps"]["baseBdFreightIndexDTOS"]
    return _observations(records, "indexDate", "indexValue", "panasia")


def fetch_xinhua() -> list[dict]:
    response = net.post(XINHUA_API, data={"ids": "12549", "type": "1"},
                        headers={"Referer": XINHUA_CHART, "Cache-Control": "no-cache"}, timeout=25, retries=2).json()
    if response.get("status") != 1:
        raise ValueError("Xinhua query failed")
    charts = response["data"]["list"]
    chart = next(c for c in charts if str(c["id"]) == "12549")
    records = json.loads(chart["content"])
    return _observations(records, "x", "y", "xinhua")


def fetch() -> tuple[list[dict], str]:
    """Only query the fallback when the primary request or validation fails."""
    try:
        return fetch_panasia(), PANASIA_PAGE
    except Exception as exc:
        print(f"  ! pdci Panasia: {type(exc).__name__}; trying Xinhua", flush=True)
    return fetch_xinhua(), XINHUA_PAGE


def snapshot(rows: list[dict]) -> list[dict]:
    rows = sorted(rows, key=lambda r: r["date"])
    latest = rows[-1]
    previous = rows[-2] if len(rows) > 1 else {}
    row = dict.fromkeys(CURRENT_FIELDS, "")
    row.update(index="pdci", series="composite", name="综合指数", name_en="Composite", unit="points",
               date=latest["date"], value=latest["value"], prev_date=previous.get("date", ""),
               prev=previous.get("value", ""), period=latest["date"])
    # The APIs supply levels, not a separately published change.
    return [row]
