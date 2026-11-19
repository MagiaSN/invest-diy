"""Monthly source parsing, calendar alignment, units and snapshot failure safety."""

from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from investdiy.us_track_macro import fetch, model


def fixture():
    series = {sid: {"2023-01": 100., "2023-12": 110., "2024-01": 121., "2024-03": 125.}
              for sid in model.SERIES}
    series["CPIAUCNS"]["2024-01"] = 120.
    series["PPIFID"]["2024-01"] = 115.
    series["PAYEMS"] = {"2023-12": 157000., "2024-01": 157250., "2024-03": 157400.}
    series["UNRATE"] = {"2023-12": 3.7, "2024-01": 3.9, "2024-03": 4.}
    series["FEDFUNDS"] = {"2023-12": 5.33, "2024-01": 5.25, "2024-03": 5.25}
    return series


class ModelTests(unittest.TestCase):
    def test_source_contract_missing_and_incomplete_month(self):
        for header in ["observation_date", "DATE"]:
            text = f"{header},UNRATE\n2024-01-01,0\n2024-02-01,.\n2024-03-01,\n2024-04-01,4.1\n"
            self.assertEqual(model.parse_series(text, "UNRATE", date(2024, 4, 30)), {"2024-01": 0.})

    def test_reject_bad_headers_values_dates_and_empty_responses(self):
        for body in ["<html>error</html>", "DATE,OTHER\n2024-01-01,1\n", "DATE,UNRATE\n",
                     "DATE,UNRATE\n2024-01-02,3\n", "DATE,UNRATE\n2024-01-01,3\n2024-01-01,4\n"]:
            with self.subTest(body=body), self.assertRaises(ValueError):
                model.parse_series(body, "UNRATE", date(2025, 1, 1))
        for value in ["NaN", "inf", "-1", "garbage"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                model.parse_series(f"DATE,UNRATE\n2024-01-01,{value}\n", "UNRATE")

    def test_yoy_uses_unadjusted_mom_uses_adjusted_and_pce_is_price(self):
        rows = {r["month"]: r for r in model.build_monthly(fixture(), "2024-04-01", start="2024-01")}
        row = rows["2024-01"]
        self.assertEqual(row["cpi_yoy"], 20.)
        self.assertEqual(row["ppi_yoy"], 15.)
        self.assertEqual(row["pce_yoy"], 21.)
        for key in ["cpi_mom", "ppi_mom", "pce_mom"]:
            self.assertEqual(row[key], 10.)
        self.assertEqual(row["payrolls_k"], 157250.)
        self.assertEqual(row["payrolls_change_k"], 250.)
        self.assertEqual(row["unemployment_change_pp"], .2)
        self.assertEqual(row["fed_funds_change_pp"], -.08)

    def test_missing_months_are_not_bridged_or_replaced_with_zero(self):
        rows = {r["month"]: r for r in model.build_monthly(fixture(), "2024-04-01", start="2024-01")}
        self.assertIsNone(rows["2024-02"]["payrolls_k"])
        self.assertIsNone(rows["2024-03"]["payrolls_change_k"])
        self.assertIsNone(rows["2024-03"]["cpi_mom"])
        self.assertIsNone(rows["2024-03"]["cpi_yoy"])

    def test_asof_uses_slowest_source_and_keeps_later_months(self):
        series = fixture()
        del series["PCEPI"]["2024-03"]
        rows = model.build_monthly(series, "2024-04-15T00:00:00+00:00", start="2024-01")
        self.assertEqual(rows[0]["month"], "2024-03")
        self.assertEqual(rows[0]["as_of"], "2024-01-31")
        self.assertIsNone(rows[0]["pce"])
        self.assertEqual(rows[0]["fed_funds"], 5.25)

    def test_calendar_offsets_cross_year_and_need_exact_prior_year(self):
        self.assertEqual(model.offset("2024-01", -1), "2023-12")
        self.assertEqual(model.offset("2024-01", -12), "2023-01")
        series = fixture()
        del series["CPIAUCNS"]["2023-01"]
        rows = model.build_monthly(series, "2024-04-01", start="2024-01")
        self.assertIsNone(rows[-1]["cpi_yoy"])


class FetchTests(unittest.TestCase):
    def test_failed_or_regressing_source_preserves_both_files(self):
        for regression in (False, True):
            with self.subTest(regression=regression), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                with patch.object(fetch, "fetch_series", side_effect=lambda sid: fixture()[sid]):
                    fetch.run(root)
                files = [root / "raw/fred.json", root / "out/monthly.csv"]
                before = [p.read_bytes() for p in files]

                def bad(sid):
                    if sid == "PCEPI":
                        if regression:
                            return {"2023-01": 100.}
                        raise ValueError("source unavailable")
                    return fixture()[sid]

                with patch.object(fetch, "fetch_series", side_effect=bad), self.assertRaises(RuntimeError):
                    fetch.run(root)
                self.assertEqual([p.read_bytes() for p in files], before)

    def test_offline_rebuild_retains_fetch_timestamp_and_blank_cells(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(fetch, "fetch_series", side_effect=lambda sid: fixture()[sid]):
                fetch.run(root)
            original = (root / "out/monthly.csv").read_bytes()
            with patch.object(fetch, "fetch_series", side_effect=AssertionError("offline")):
                fetch.run(root, skip_fetch=True)
            self.assertEqual((root / "out/monthly.csv").read_bytes(), original)
            snapshot = json.loads((root / "raw/fred.json").read_text())
            self.assertIn(snapshot["fetched_at"].encode(), original)
            self.assertIn(b",,", original)


if __name__ == "__main__":
    unittest.main()
