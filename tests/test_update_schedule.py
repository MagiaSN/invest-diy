"""Keep independent collection schedules separate while supporting cache recovery."""
from datetime import date
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from investdiy.common.update_schedule import (
    due_for_refresh, ETF_SCHEDULES, PROFIT_SCHEDULES, GOLD_SCHEDULE, REQUIRED_OUTPUTS,
)


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name)
        for names in REQUIRED_OUTPUTS.values():
            for name in names:
                (self.data / name).touch()

    def due(self, slug, schedule, *, asof="2026-10-31", day=19, event="schedule", update="python -m tool", refresh_scope="all"):
        tool = SimpleNamespace(slug=slug, data=self.data, update=update, asof=lambda _: asof)
        return due_for_refresh(tool, {}, event=event, schedule=schedule, today=date(2026, 11, day), refresh_scope=refresh_scope)

    def test_scoped_manual_refresh_reuses_other_outputs_but_still_bootstraps_missing_data(self):
        options = dict(event="workflow_dispatch", refresh_scope="company-profit")
        self.assertTrue(self.due("company-profit", "", **options))
        for slug in ("cn-track-pboc-gold", "ashare-track-national-team-etf"):
            self.assertFalse(self.due(slug, "", **options))
            self.assertTrue(self.due(slug, "", asof="", **options))

    def test_schedules_refresh_only_their_own_tool_with_a_complete_cache(self):
        schedules = ETF_SCHEDULES | PROFIT_SCHEDULES | {GOLD_SCHEDULE}
        for schedule in schedules:
            with self.subTest(schedule=schedule):
                self.assertEqual(self.due("company-profit", schedule), schedule in PROFIT_SCHEDULES)
                self.assertEqual(self.due("ashare-track-national-team-etf", schedule), schedule in ETF_SCHEDULES)
                self.assertEqual(self.due("cn-track-pboc-gold", schedule, day=7), schedule == GOLD_SCHEDULE)

    def test_gold_retries_only_missing_months_but_revision_day_always_refreshes(self):
        self.assertFalse(self.due("cn-track-pboc-gold", GOLD_SCHEDULE, day=8))
        self.assertTrue(self.due("cn-track-pboc-gold", GOLD_SCHEDULE, day=8, asof="2026-09-30"))
        self.assertTrue(self.due("cn-track-pboc-gold", GOLD_SCHEDULE, day=15))

    def test_manual_and_missing_dates_force_all_data_tools(self):
        for slug in ("company-profit", "cn-track-pboc-gold", "ashare-track-national-team-etf"):
            self.assertTrue(self.due(slug, "", event="workflow_dispatch"))
            self.assertTrue(self.due(slug, "", asof=""))
        self.assertFalse(self.due("pe-calculator", "", event="workflow_dispatch", update=""))

    def test_each_missing_company_output_bootstraps_on_an_etf_run(self):
        for name in REQUIRED_OUTPUTS["company-profit"]:
            with self.subTest(name=name):
                path = self.data / name
                path.unlink()
                self.assertTrue(self.due("company-profit", next(iter(ETF_SCHEDULES))))
                path.touch()


if __name__ == "__main__":
    unittest.main()
