"""Latest-only collection with strict status checks for unattended runs."""

from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
from zoneinfo import ZoneInfo

from investdiy.common.csvio import read_rows
from . import analyze, fetch
from .indices import INDEX_NAMES, MONTHLY


def check_status(rows: list[dict], started: datetime) -> list[str]:
    """Accept restricted cells, but reject failures, reused status and stale periods.

    These age limits detect stopped feeds, not precise publication deadlines.
    Monthly observation dates can precede publication by several weeks.
    """
    statuses = {row["index"]: row for row in rows}
    errors = []
    for index in INDEX_NAMES:
        row = statuses.get(index, {})
        try:
            checked = datetime.fromisoformat(row["last_success"])
            period = datetime.fromisoformat(row["date"]).date()
            age = (started.astimezone(ZoneInfo("Asia/Shanghai")).date() - period).days
            valid = (row["status"] in {"ok", "partial"}
                     and checked >= started and int(row["available"]) > 0
                     and 0 <= age <= (100 if index in MONTHLY else 17))
        except (KeyError, ValueError, TypeError):
            valid = False
        if not valid:
            errors.append(index)
    return errors


def report_status(rows: list[dict], previous: list[dict]) -> None:
    """Report dates and coverage counts without exposing the index values."""
    old = {row["index"]: row for row in previous}
    summary = ["## SSE source coverage", "",
               "| Index | Period | Current values | Previous coverage | Status | Checked (UTC) |",
               "|---|---|---|---|---|---|"]
    for row in rows:
        index = row["index"]
        if index not in INDEX_NAMES:
            continue
        before = old.get(index, {})
        coverage = f"{row.get('available', 0)}/{row.get('total', '?')}"
        prior = f"{before.get('available', 0)}/{before.get('total', '?')}"
        print(f"{index}: {row['date']} ({row['status']}), current values {coverage}, previous {prior}")
        summary.append(f"| {index} | {row['date']} | {coverage} | {prior} | {row['status']} | {row.get('checked_at', '')} |")
        if (row["status"] == "partial" and before.get("last_success")
                and int(row.get("available") or 0) < int(before.get("available") or 0)):
            message = f"{index}: coverage fell from {prior} to {coverage}; later scheduled runs will check for delayed public components."
            print(("::warning::" if os.environ.get("GITHUB_ACTIONS") == "true" else "Warning: ") + message)
    summary.extend(["", "Partial coverage is retained and checked again on later runs. "
                    "A successful run does not mean every component is publicly available.", ""])
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as report:
            report.write("\n".join(summary))


def main() -> int:
    started = datetime.now(timezone.utc).replace(microsecond=0)
    previous = read_rows(fetch.STATUS_CSV)
    # Detailed output can include historical values. Keep it out of public CI logs.
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as log:
        try:
            with redirect_stdout(log), redirect_stderr(log):
                fetch.run(latest_only=True)
                analyze.main()
        except Exception as exc:
            print(f"Collection failed ({type(exc).__name__}); saved observations are retained.")
            return 1
    rows = read_rows(fetch.STATUS_CSV)
    errors = check_status(rows, started)
    report_status(rows, previous)
    if errors:
        print("Missing, failed or stale sources: " + ", ".join(errors))
        return 1
    print(f"Checked all {len(INDEX_NAMES)} SSE sections; history merged without duplicate periods.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
