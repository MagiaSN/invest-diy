"""Monthly source parsing, calendar alignment, units and snapshot failure safety."""

from datetime import date
import json
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from openpyxl import Workbook

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

    def test_variants_use_their_own_bases_and_published_rate_units(self):
        series = fixture()
        series["WPUFD49107"]["2024-01"] = 130.
        series["DPXERG"]["2024-01"] = 99.
        series["DPXFRG"]["2024-01"] = 105.
        series["PCETRIM12M159SFRBDAL"]["2024-01"] = -1.
        series["PCETRIM1M158SFRBDAL"]["2024-01"] = 100 * (0.99 ** 12 - 1)
        row = model.build_monthly(series, "2024-04-01", start="2024-01")[-1]
        self.assertEqual(set(row), set(model.FIELDS))
        self.assertEqual(row["ppi_ex_energy_yoy"], 30.)
        self.assertEqual(row["ppi_ex_energy_mom"], 10.)
        self.assertEqual(row["pce_ex_energy_yoy"], -1.)
        self.assertEqual(row["pce_ex_food_yoy"], 5.)
        self.assertEqual(row["pce_trimmed_yoy"], -1.)
        self.assertEqual(row["pce_trimmed_mom"], -1.)
        self.assertNotIn("pce_trimmed_index", row)
        self.assertEqual(model.parse_series("DATE,PCETRIM12M159SFRBDAL\n2024-01-01,-1.0\n",
                                           "PCETRIM12M159SFRBDAL"), {"2024-01": -1.})


class FetchTests(unittest.TestCase):
    def setUp(self):
        for collector in ("fetch_bea", "fetch_bls"):
            self.enterContext(patch.object(fetch, collector, side_effect=lambda ids: {sid: fixture()[sid] for sid in ids}))

    def test_legacy_snapshot_rebuild_and_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = fixture()
            legacy = {sid: data[sid] for sid in model.HEADLINE_SERIES}
            (root / "raw").mkdir()
            (root / "raw/fred.json").write_text(json.dumps({"fetched_at": "2024-04-01", "series": legacy}))
            old = fetch.run(root, skip_fetch=True)
            self.assertEqual(set(old[0]), set(model.LEGACY_FIELDS))
            with patch.object(fetch, "fetch_series", side_effect=data.__getitem__):
                new = fetch.run(root)
            self.assertEqual(set(new[0]), set(model.FIELDS))
            self.assertIsNone(new[1]["pce_core_index"])

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


class ProviderTests(unittest.TestCase):
    def test_bea_matches_account_codes_and_month_columns(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "U20404-M"
        sheet.append(["Line", None, None, "2024M01", None, "2024M02", "2999M01"])
        sheet.append([2, "Food exclusion", "DPXFRG", 90, None, 91, 92])
        sheet.append([1, "Energy exclusion", "DPXERG", 80, None, None, 81])
        content = BytesIO()
        workbook.save(content)
        with patch.object(fetch.net, "get", return_value=Mock(content=content.getvalue())):
            series = fetch.fetch_bea(["DPXERG", "DPXFRG"])
        self.assertEqual(series, {"DPXFRG": {"2024-01": 90, "2024-02": 91}, "DPXERG": {"2024-01": 80}})

    def test_bls_batches_keep_missing_months_and_ignore_annual_average(self):
        def response(url, *, json):
            start, end = int(json["startyear"]), int(json["endyear"])
            self.assertLessEqual(end - start, 9)
            data = [{"year": str(start), "period": p, "value": v} for p, v in
                    (("M01", "123.4"), ("M02", "-"), ("M13", "130.2"))]
            return Mock(json=lambda: {"status": "REQUEST_SUCCEEDED", "Results": {"series": [
                {"seriesID": sid, "data": data} for sid in json["seriesid"]]}})
        with patch.object(fetch.net, "post", side_effect=response):
            result = fetch.fetch_bls(["CUSR0000SA0L12E"])
        self.assertEqual(result["CUSR0000SA0L12E"]["1989-01"], 123.4)
        self.assertNotIn("1989-02", result["CUSR0000SA0L12E"])


if __name__ == "__main__":
    unittest.main()
