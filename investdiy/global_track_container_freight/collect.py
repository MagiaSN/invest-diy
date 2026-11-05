"""Latest-only collection with strict status checks for unattended runs."""

from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
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


def main() -> int:
    started = datetime.now(timezone.utc).replace(microsecond=0)
    # Detailed output can include historical values. Keep it out of public CI logs.
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as log:
        try:
            with redirect_stdout(log), redirect_stderr(log):
                fetch.run(latest_only=True)
                analyze.main()
        except Exception as exc:
            print(f"Collection failed ({type(exc).__name__}); saved observations are retained.")
            return 1
    errors = check_status(read_rows(fetch.STATUS_CSV), started)
    for row in read_rows(fetch.STATUS_CSV):
        # Log only index identities, dates and status, never observed values.
        if row["index"] in INDEX_NAMES:
            print(f"{row['index']}: {row['date']} ({row['status']})")
    if errors:
        print("Missing, failed or stale sources: " + ", ".join(errors))
        return 1
    print(f"Checked all {len(INDEX_NAMES)} SSE sections; history merged without duplicate periods.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
