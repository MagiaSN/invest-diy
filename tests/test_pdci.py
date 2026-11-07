"""PDCI provider fallback, validation, provenance and saved-data retention."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests

from investdiy.common.csvio import read_rows, write_rows
from investdiy.global_track_container_freight import analyze, fetch, pdci, sync


def observation(day="2020-01-10", value="1027", source="panasia"):
    return dict(index="pdci", series="composite", date=day, value=value, source=source)


def panasia_payload(records=None):
    return {"code": 0, "data": {"bdFreightIndexMaps": {"baseBdFreightIndexDTOS": records or [
        {"indexDate": "2020/01/10", "indexValue": "1027 "},
        {"indexDate": "2020/01/03", "indexValue": "1017"},
    ]}}}


def xinhua_payload():
    return {"status": 1, "data": {"list": [{"id": "12549", "content": json.dumps([
        {"x": "2020/01/10", "y": "1027."}, {"x": "2020/01/03", "y": "1017."},
    ])}]}}


class ProviderTests(unittest.TestCase):
    def test_primary_plain_history_is_sorted_and_normalized_without_fallback(self):
        with patch.object(pdci.net, "post", return_value=Mock(json=lambda: panasia_payload())) as post:
            rows, url = pdci.fetch()
        self.assertEqual([r["date"] for r in rows], ["2020-01-03", "2020-01-10"])
        self.assertEqual(rows[-1], observation())
        self.assertEqual(url, pdci.PANASIA_PAGE)
        post.assert_called_once()
        self.assertEqual(post.call_args.kwargs["json"], {"indexType": "multiple", "count": None})

    def test_network_and_invalid_primary_responses_use_official_fallback(self):
        for failure in [requests.Timeout(), Mock(json=lambda: {"code": 401}),
                        Mock(json=lambda: panasia_payload([{"indexDate": "2020/01/10", "indexValue": "NaN"}]))]:
            with self.subTest(failure=type(failure).__name__), patch.object(pdci.net, "post", side_effect=[
                    failure, Mock(json=xinhua_payload)]) as post:
                rows, url = pdci.fetch()
                self.assertEqual(rows[-1], observation(source="xinhua"))
                self.assertEqual(url, pdci.XINHUA_PAGE)
                self.assertEqual(post.call_args.args[0], pdci.XINHUA_API)
                self.assertEqual(post.call_args.kwargs["data"], {"ids": "12549", "type": "1"})

    def test_invalid_dates_values_and_duplicate_conflicts_reject_entire_response(self):
        for records in [[], [{"x": "2020/02/30", "y": "1000"}],
                        [{"x": "9999/01/01", "y": "1000"}],
                        [{"x": "2014/01/01", "y": "1000"}],
                        [{"x": "2020/01/03", "y": v} for v in ["1000", "1001"]],
                        *[[{"x": "2020/01/03", "y": v}] for v in ["", "0", "-1", "inf", "NaN"]]]:
            with self.subTest(records=records), self.assertRaises(ValueError):
                pdci._observations(records, "x", "y", "xinhua")

    def test_wrong_xinhua_chart_and_bad_status_fail(self):
        for payload in [{"status": 0}, {"status": 1, "data": {"list": [{"id": "other"}]}}]:
            with patch.object(pdci.net, "post", return_value=Mock(json=lambda: payload)):
                with self.assertRaises((ValueError, StopIteration)):
                    pdci.fetch_xinhua()

    def test_snapshot_does_not_invent_a_published_change(self):
        rows = [observation("2020-01-03", "1017"), observation()]
        snapshot = pdci.snapshot(rows)[0]
        self.assertEqual((snapshot["date"], snapshot["prev_date"], snapshot["prev"]),
                         ("2020-01-10", "2020-01-03", "1017"))
        self.assertEqual((snapshot["change"], snapshot["change_unit"]), ("", ""))


class PipelineTests(unittest.TestCase):
    def test_primary_wins_over_live_fallback_and_recovers_from_saved_fallback(self):
        primary = observation(value="1027")
        fallback = observation(value="999", source="xinhua")
        for layers in [(primary, fallback), (fallback, primary)]:
            self.assertEqual(fetch.merge(*[[r] for r in layers]), [primary])

    def test_failover_and_total_failure_retain_newer_primary_history_and_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            with patch.multiple(fetch, DATA=data, OBS_CSV=data / "observations.csv",
                                CURRENT_CSV=data / "current.csv", STATUS_CSV=data / "status.csv",
                                PAGES={"pdci": [("json", pdci.PANASIA_PAGE)]}), \
                 patch.object(fetch, "read_published", return_value=[]), \
                 patch.object(fetch, "read_archive", return_value=[]), \
                 patch.object(analyze, "read_archive_metadata", return_value=[]):
                primary = [observation("2020-01-03", "1017"), observation()]
                with patch.object(pdci, "fetch_panasia", return_value=primary):
                    fetch.run(latest_only=True)
                original_current = read_rows(fetch.CURRENT_CSV)
                original_status = read_rows(fetch.STATUS_CSV)[0]
                fallback = [observation("2020-01-03", "999", "xinhua")]
                with patch.object(pdci, "fetch_panasia", side_effect=requests.Timeout), \
                     patch.object(pdci, "fetch_xinhua", return_value=fallback):
                    fetch.run(latest_only=True)
                self.assertEqual(read_rows(fetch.OBS_CSV), primary)
                self.assertEqual(read_rows(fetch.CURRENT_CSV), original_current)
                state = read_rows(fetch.STATUS_CSV)[0]
                self.assertEqual((state["status"], state["date"], state["url"]),
                                 ("ok", "2020-01-03", pdci.XINHUA_PAGE))
                # Repeated same-date fallback checks cannot replace saved primary values.
                with patch.object(pdci, "fetch", return_value=([
                        observation(value="998", source="xinhua")], pdci.XINHUA_PAGE)):
                    fetch.run(latest_only=True)
                    fetch.run(latest_only=True)
                self.assertEqual(read_rows(fetch.CURRENT_CSV), original_current)
                successful = read_rows(fetch.STATUS_CSV)[0]
                with patch.object(pdci, "fetch_panasia", side_effect=requests.Timeout), \
                     patch.object(pdci, "fetch_xinhua", side_effect=requests.Timeout):
                    fetch.run(latest_only=True)
                self.assertEqual(read_rows(fetch.OBS_CSV), primary)
                self.assertEqual(read_rows(fetch.CURRENT_CSV), original_current)
                state = read_rows(fetch.STATUS_CSV)[0]
                self.assertEqual(state["status"], "error")
                self.assertEqual(state["last_success"], successful["last_success"])
                self.assertEqual(state["url"], pdci.XINHUA_PAGE)
                analyze.main(data_dir=data)
                latest = next(r for r in read_rows(data / "out/latest.csv") if r["index"] == "pdci")
                self.assertEqual((latest["n"], latest["value"], latest["current"], latest["unit"]),
                                 ("2", "1027", "1027", "points"))
                self.assertEqual(latest["chg_1w"], "0.98")
                self.assertEqual(original_status["url"], pdci.PANASIA_PAGE)

    def test_sync_prefers_primary_and_preserves_local_pdci_when_cloud_has_only_sse(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            primary, fallback = observation(), observation(value="999", source="xinhua")
            write_rows(data / "observations.csv", [primary], fetch.FIELDS)
            cloud = {"observations.csv": [fallback], "current.csv": pdci.snapshot([fallback]), "status.csv": []}
            merged, _, _ = sync.merge_snapshot(cloud, data)
            self.assertEqual(merged["observations.csv"], [primary])
            self.assertEqual(merged["current.csv"][0]["value"], primary["value"])
            cloud["observations.csv"] = []
            merged, _, _ = sync.merge_snapshot(cloud, data)
            self.assertEqual(merged["observations.csv"], [primary])
            write_rows(data / "observations.csv", [fallback], fetch.FIELDS)
            cloud["observations.csv"] = [primary]
            merged, _, _ = sync.merge_snapshot(cloud, data)
            self.assertEqual(merged["observations.csv"], [primary])


if __name__ == "__main__":
    unittest.main()
