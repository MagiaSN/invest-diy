"""Unattended collection must report failures without exposing historical values."""

import contextlib
import io
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from investdiy.global_track_container_freight import collect
from investdiy.global_track_container_freight.indices import INDEX_NAMES, MONTHLY, frequency


class CollectionTests(unittest.TestCase):
    started = datetime(2026, 11, 5, 9, 37, tzinfo=timezone.utc)

    def statuses(self):
        return [dict(index=index, status="ok", available="1", date="2026-10-30",
                     last_success=self.started.isoformat()) for index in INDEX_NAMES]

    def test_partial_components_and_non_publication_days_are_valid(self):
        rows = self.statuses()
        for row in rows:
            row["status"] = "partial"
            if row["index"] in MONTHLY:
                row["date"] = "2026-09-01"
        self.assertEqual(collect.check_status(rows, self.started), [])
        self.assertEqual(frequency("cdi"), "daily")

    def test_missing_failed_and_reused_status_cannot_pass(self):
        rows = self.statuses()
        rows.pop(0)
        rows[0]["status"] = "error"
        rows[1]["last_success"] = "2026-11-04T09:37:00+00:00"
        self.assertEqual(collect.check_status(rows, self.started), ["ccfi", "scfi", "scfis"])

    def test_stopped_feeds_and_empty_or_invalid_status_fail(self):
        rows = self.statuses()
        rows[0]["date"] = "2026-10-01"
        rows[1]["available"] = "0"
        rows[2]["last_success"] = "invalid"
        monthly = next(row for row in rows if row["index"] in MONTHLY)
        monthly["date"] = "2026-01-01"
        self.assertEqual(collect.check_status(rows, self.started),
                         ["ccfi", "scfi", "scfis", monthly["index"]])

    def test_beijing_period_is_not_in_the_future_after_utc_midnight_offset(self):
        started = datetime(2026, 11, 4, 17, tzinfo=timezone.utc)
        rows = self.statuses()
        for row in rows:
            row.update(date="2026-11-05", last_success=started.isoformat())
        self.assertEqual(collect.check_status(rows, started), [])

    def test_collector_uses_latest_only_and_does_not_log_values(self):
        out = io.StringIO()
        with patch.object(collect.fetch, "run", side_effect=lambda **kw: print("value=1234.56")) as run, \
                patch.object(collect.analyze, "main") as analyze, \
                patch.object(collect, "read_rows", return_value=self.statuses()), \
                patch.object(collect, "check_status", return_value=[]), contextlib.redirect_stdout(out):
            self.assertEqual(collect.main(), 0)
        run.assert_called_once_with(latest_only=True)
        analyze.assert_called_once()
        self.assertNotIn("1234.56", out.getvalue())
        self.assertIn("Checked all 24", out.getvalue())

    def test_failure_is_nonzero_and_exception_details_are_private(self):
        out = io.StringIO()
        with patch.object(collect.fetch, "run", side_effect=ValueError("private-value")), \
                contextlib.redirect_stdout(out):
            self.assertEqual(collect.main(), 1)
        self.assertIn("ValueError", out.getvalue())
        self.assertNotIn("private-value", out.getvalue())

    def test_source_validation_failure_is_nonzero(self):
        with patch.object(collect.fetch, "run"), patch.object(collect.analyze, "main"), \
                patch.object(collect, "read_rows", return_value=[]), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(collect.main(), 1)


if __name__ == "__main__":
    unittest.main()
