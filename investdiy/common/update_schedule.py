"""Select public-tool refreshes for the shared update/publish workflow."""
import json
from datetime import date, timedelta

ETF_SCHEDULES = {"47 15 * * 1-5", "37 1 * * 2-6"}
PROFIT_SCHEDULES = {"17 1 * * 1-5", "17 8 * * 1-5"}
GOLD_SCHEDULE = "53 15 7-10,15 * *"
US_MACRO_SCHEDULE = "43 1 2 * *"
CALENDAR_SCHEDULE = "33 0 * * *"
REQUIRED_OUTPUTS = {
    "financial-calendar": ("events.csv", "earnings.json"),
    "cn-track-pboc-gold": ("kpi.csv", "monthly.csv", "annual.csv", "phases.csv"),
    "company-profit": ("history.json", "history.js", "cmoc-history.js", "cnooc-history.js", "catl-history.js", "company-profit.html", "market-status.csv"),
    "us-track-macro": ("monthly.csv",),
}


def due_for_refresh(tool, meta: dict, *, event: str, schedule: str, today: date,
                    refresh_scope: str = "all") -> bool:
    """Selected manual refreshes and missing outputs override normal schedules."""
    if not tool.update:
        return False
    asof = tool.asof(meta)
    manual = event == "workflow_dispatch"
    if (manual and refresh_scope in ("all", tool.slug)) or not asof or not all(
            (tool.data / name).exists() for name in REQUIRED_OUTPUTS.get(tool.slug, ())):
        return True
    if tool.slug == "financial-calendar":
        # Failed runs also save their cache. Rebuild a mixed pair before the next export.
        earnings = json.loads((tool.data / "earnings.json").read_text(encoding="utf-8"))
        return earnings.get("as_of") != asof or (not manual and schedule == CALENDAR_SCHEDULE)
    if manual:
        return False
    if tool.slug == "company-profit":
        return schedule in PROFIT_SCHEDULES
    if tool.slug == "us-track-macro":
        return schedule == US_MACRO_SCHEDULE
    if tool.slug == "cn-track-pboc-gold":
        target = (today.replace(day=1) - timedelta(days=1)).isoformat()
        return schedule == GOLD_SCHEDULE and (today.day in (7, 15) or asof < target)
    return schedule in ETF_SCHEDULES
