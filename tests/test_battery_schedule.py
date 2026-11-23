"""A survey's company ranking and a reported lower bound must not become point estimates."""
import unittest
from unittest.mock import patch

from investdiy.cn_track_battery_schedule.__main__ import catl_rows, citi_a_rows, followup_fields, market_rows
from investdiy.cn_track_battery_schedule.sources import CATL_FOLLOWUPS, CITI_A_REPORT, Report


class ScheduleTests(unittest.TestCase):
    def test_january_revision_belongs_to_previous_year(self):
        report = Report("2026-01", "2025-12-25", "td", "https://example.com/release")
        text = ("预计1月中国锂电全市场（储能+动力+消费）总排产约80GWh。"
                "锂电池A排产量45GWh。12月中国锂电全市场实际总排产从上月报告的78GWh下修至72GWh附近。")
        current, producer, revision = market_rows(report, text)
        self.assertEqual((producer["month"], producer["attribution"], producer["gwh"]), ("2026-01", "survey_a", "45"))
        self.assertEqual((current["month"], current["gwh"]), ("2026-01", "80"))
        self.assertEqual((revision["month"], revision["gwh"], revision["previous_plan_gwh"],
                          revision["qualifier"]), ("2025-12", "72", "78", "revised_approx"))

    def test_named_company_bounds_and_anonymous_figures(self):
        report = Report("2026-05", "2026-05-27", "caiwen", "https://example.com/company")
        row, = catl_rows(report, "宁德时代（300750.SZ）发布新品。5月排产首次突破80GWh")
        self.assertEqual((row["gwh"], row["qualifier"]), ("80", "above"))
        with self.assertRaises(ValueError):
            catl_rows(report, "5月锂电池A排产量80GWh。宁德时代发布新品。")

    def test_multiple_months_in_a_single_company_report(self):
        body = ("CATL一家，下半年预期上升。逐月排产如下：8月110GWh（7月才95GWh），"
                "9月120GWh，10月和11月双双站上130GWh。")
        expected = ["95", "110", "120", "130", "130"]
        for month, value in zip(range(7, 12), expected):
            with self.subTest(month=month):
                report = Report(f"2026-{month:02d}", "2026-08-18", "citi_ze", "https://example.com/report")
                row, = catl_rows(report, body)
                self.assertEqual((row["month"], row["gwh"]), (report.month, value))

    def test_market_total_requires_consumer_batteries_and_china_scope(self):
        report = Report("2025-03", "2025-03-01", "td", "https://example.com/report")
        other = "2025年3月中国电池厂动力+储能产量88GWh。2025年3月全球市场动力+储能+消费类电池排产量130GWh。"
        with self.assertRaises(ValueError):
            market_rows(report, other)
        row, = market_rows(report, other + "2025年3月中国市场动力+储能+消费类电池排产量99GWh。")
        self.assertEqual(row["gwh"], "99")

    def test_named_revision_and_chemistry_totals(self):
        report = Report("2026-11", "2026-11-22", "autosupplier", "https://example.com/company")
        body = "宁德时代将2026年11月产量计划由月初的80GWh（20GWh三元+60GWh磷酸铁锂）下调至77GWh（20GWh三元+57GWh磷酸铁锂）"
        row, = catl_rows(report, body)
        self.assertEqual((row["gwh"], row["prior_lfp_gwh"], row["lfp_gwh"], row["ncm_gwh"]), ("77", "60", "57", "20"))
        with self.assertRaises(ValueError):
            catl_rows(report, body.replace("57GWh", "58GWh"))

    def test_followup_requires_named_forecast(self):
        report = CATL_FOLLOWUPS[1]
        sector = "已下调2026年10月电池产量管道预测，前五大电池厂商环比仅升1%。"
        with self.assertRaises(ValueError):
            followup_fields(report, sector)
        fields = followup_fields(report, sector + "该行下调宁德时代(03750)、中创新航及EVE的产量管道预测。")
        self.assertEqual(fields["followup_kind"], "cut")
        self.assertNotIn("gwh", fields)

    def test_survey_a_is_bound_to_the_target_month_in_a_compilation(self):
        report = Report("2025-07", "2025-10-22", "tiger", "https://example.com/review")
        june = "2025年6月中国市场动力+储能+消费类电池排产量60GWh，锂电池A排产量22GWh。"
        july = "2025年7月中国市场动力+储能+消费类电池排产量80GWh。"
        august = "2025年8月中国电池厂动力+储能产量90GWh；锂电池A排产量31GWh。"
        self.assertEqual(len(market_rows(report, june + july + august)), 1)
        _, row = market_rows(report, june + july + "锂电池A排产量27GWh。" + august)
        self.assertEqual((row["series"], row["month"], row["attribution"], row["gwh"]),
                         ("catl", "2025-07", "survey_a", "27"))

    def test_citi_company_a_has_its_own_attribution_and_chemistry(self):
        body = "排产表里老大（图注匿名化处理为A公司）8月排产从70GWh升到80GWh"
        parts = [{"month": "2026-08", "lfp_gwh": "60", "ncm_gwh": "20"}]
        with patch("investdiy.common.csvio.read_rows", return_value=parts):
            july, august = citi_a_rows(CITI_A_REPORT, body)
            self.assertEqual((july["month"], july["gwh"], july["attribution"]), ("2026-07", "70", "citi_a"))
            self.assertEqual((august["month"], august["lfp_gwh"], august["ncm_gwh"]), ("2026-08", "60", "20"))
            with self.assertRaises(ValueError):
                citi_a_rows(CITI_A_REPORT, body.replace("80GWh", "81GWh"))
