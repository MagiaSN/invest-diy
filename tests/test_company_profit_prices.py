"""Quote/FX parsing, complete update snapshots and removal of live HTTP fetching."""
from datetime import datetime, timedelta
import csv
import hashlib
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import tempfile
from threading import Thread
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

from investdiy.server import Handler
from investdiy.company_profit import prices, build


def quote(symbol="au", **changes):
    row = dict(contractname=symbol + "2702", instrumentid=symbol, lastprice="800",
               openinterest="100", volume="200", updatetime="2026-11-19 14:59:03")
    return {**row, **changes}


class QuoteTests(unittest.TestCase):
    now = datetime(2026, 11, 19, 16, tzinfo=prices.SHANGHAI)

    def test_pinned_baseline_bootstraps_without_external_research_and_uses_verified_cache(self):
        baseline = json.loads((build.PACKAGE/'data/out/history.json').read_text())
        baseline.pop('market')
        raw = json.dumps(baseline).encode()
        digest = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as directory, patch.object(build, 'PACKAGE', Path(directory)), \
                patch.object(build, 'BASELINE_SHA256', digest), \
                patch.object(build.net, 'get', return_value=SimpleNamespace(content=raw)) as get:
            self.assertEqual(build.load_baseline(), baseline)
            self.assertEqual(build.load_baseline(), baseline)
            get.assert_called_once_with(build.BASELINE_URL)
            cached = Path(directory)/'data/raw'/f'baseline-{digest}.json'
            cached.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                build.load_baseline()

    def test_corrupt_download_is_rejected_before_caching_or_fetching_prices(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(build, 'PACKAGE', Path(directory)), \
                patch.object(build.net, 'get', return_value=SimpleNamespace(content=b'{}')), \
                patch.object(build, 'fetch_snapshot') as fetch:
            with self.assertRaisesRegex(ValueError, 'checksum'):
                build.build()
            fetch.assert_not_called()
            self.assertFalse((Path(directory)/'data').exists())

    def test_selects_largest_open_interest_on_latest_day_not_largest_volume(self):
        rows = [quote(contractname="au2612", openinterest="80", volume="9999"), quote(),
                quote(contractname="au2704", openinterest="999", updatetime="2026-11-18 15:00:00"),
                quote(contractname="au2706", lastprice="0", openinterest="9999")]
        result = prices.parse_quote({"delaymarket":rows}, "gold", self.now)
        self.assertEqual(result["contract"], "au2702")
        self.assertEqual(result["price"], 800)
        self.assertEqual(result["quoted_at"], "2026-11-19T14:59:03+08:00")
        self.assertEqual(result["unit"], "CNY/g")

    def test_invalid_and_stale_prices_fail_instead_of_becoming_current(self):
        changes = [{"lastprice":p} for p in ("NaN", "inf", "-1", "", "0", "10000001")]
        changes += [{"updatetime":"2026-11-10 15:00:00"}, {"updatetime":"2026-11-20 15:00:00"},
                    {"updatetime":"bad"}, {"instrumentid":"cu"}, {"contractname":"au2702C1000"},
                    {"openinterest":"NaN"}, {"volume":"0"}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                prices.parse_quote({"delaymarket":[quote(**change)]}, "gold", self.now)

    def test_recent_closed_market_quote_is_timestamped_and_flagged(self):
        result = prices.parse_quote({"delaymarket":[quote()]}, "gold", self.now + timedelta(days=2))
        self.assertTrue(result["older_than_day"])
        self.assertEqual(result["quoted_at"], "2026-11-19T14:59:03+08:00")

    def test_ecb_cross_rate_uses_same_day_and_rejects_invalid_rates(self):
        xml = '<Cube><Cube time="2026-11-18"><Cube currency="USD" rate="1.2"/><Cube currency="CNY" rate="8.4"/></Cube></Cube>'
        fx = prices.parse_fx(xml, self.now)
        self.assertAlmostEqual(fx["cny_per_usd"], 7)
        self.assertEqual(fx["as_of"], "2026-11-18")
        for bad in [xml.replace('8.4','NaN'), xml.replace('8.4','0'), xml.replace('8.4','-1'),
                    xml.replace('2026-11-18','2026-11-01'), xml.replace('2026-11-18','2026-11-20'),
                    xml.replace('currency="CNY"','currency="EUR"'), xml.replace('</Cube></Cube>', '<Cube currency="USD" rate="2"/></Cube></Cube>')]:
            with self.subTest(xml=bad), self.assertRaises(ValueError): prices.parse_fx(bad, self.now)

    def test_each_update_fetches_all_prices_and_fx_without_cache(self):
        now = datetime.now(prices.SHANGHAI)
        stamp = now.strftime("%Y-%m-%d %H:%M:%S")
        xml = f'<Cube><Cube time="{now.date()}"><Cube currency="USD" rate="1.2"/><Cube currency="CNY" rate="8.4"/></Cube></Cube>'
        def response(url, **kwargs):
            if url == prices.FX_URL: return SimpleNamespace(text=xml)
            symbol = url.rsplit("_",1)[1].split(".")[0]
            return SimpleNamespace(json=lambda:{"delaymarket":[quote(symbol,updatetime=stamp)]})
        with patch.object(prices.net,"get",side_effect=response) as get:
            first = prices.fetch_snapshot()
            self.assertEqual(len(first["quotes"]),4)
            self.assertAlmostEqual(first["fx"]["cny_per_usd"],7)
            prices.fetch_snapshot()
            self.assertEqual(get.call_count,10)
            get.side_effect = lambda url, **kw: (_ for _ in ()).throw(TimeoutError("FX failed")) if url == prices.FX_URL else response(url)
            with self.assertRaises(TimeoutError): prices.fetch_snapshot()

    def test_build_failure_preserves_previous_snapshot_and_offline_page(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory)
            out = package / 'data/out'; out.mkdir(parents=True)
            for name in ('history.json','history.js','cmoc-history.js','company-profit.html','market-status.csv'): (out/name).write_text('previous version')
            history = json.loads((build.PACKAGE/'data/out/history.json').read_text())
            source = package/'source.md'
            source.write_text('<!-- PROFIT_MODEL_DATA_START -->\n```json\n'+json.dumps(history)+'\n```')
            with patch.object(build,'PACKAGE',package), patch.object(build,'fetch_snapshot',side_effect=TimeoutError('upstream failed')):
                with self.assertRaises(TimeoutError): build.build(source)
            for name in ('history.json','history.js','cmoc-history.js','company-profit.html','market-status.csv'): self.assertEqual((out/name).read_text(),'previous version')

    def test_build_embeds_the_same_snapshot_in_server_data_and_offline_page(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory)
            shutil.copytree(build.PACKAGE/'web',package/'web')
            history = json.loads((build.PACKAGE/'data/out/history.json').read_text())
            market = history.pop('market')
            source = package/'source.md'
            source.write_text('<!-- PROFIT_MODEL_DATA_START -->\n```json\n'+json.dumps(history)+'\n```')
            with patch.object(build,'PACKAGE',package), patch.object(build,'fetch_snapshot',return_value=market) as fetch:
                destination = build.build(source)
            self.assertEqual(fetch.call_count,1)
            saved = json.loads((package/'data/out/history.json').read_text())
            self.assertEqual(saved['market'],market)
            cmoc_script = (package/'data/out/cmoc-history.js').read_text()
            self.assertIn(json.dumps(saved['cmoc'], ensure_ascii=False), cmoc_script)
            self.assertIn(cmoc_script, destination.read_text())
            with (package/'data/out/market-status.csv').open() as handle:
                status = next(csv.DictReader(handle))
            self.assertEqual(status['as_of'], min([q['quoted_at'][:10] for q in market['quotes']] + [market['fx']['as_of']]))
            self.assertEqual(status['fetched_at'], market['fetched_at'])
            self.assertIn(json.dumps(market,ensure_ascii=False), destination.read_text())
            self.assertNotIn('/api/prices', destination.read_text())

    def test_removed_live_endpoint_returns_404_without_fetching(self):
        class QuietHandler(Handler):
            tools = {"company-profit":(SimpleNamespace(web=build.PACKAGE/'web'),{})}
            def log_message(self, *args): pass
        server=ThreadingHTTPServer(("127.0.0.1",0),QuietHandler)
        worker=Thread(target=server.serve_forever,daemon=True); worker.start()
        try:
            url=f"http://127.0.0.1:{server.server_port}/company-profit/api/prices"
            with patch.object(prices.net,"get") as get:
                with self.assertRaises(HTTPError) as failure: urlopen(url)
                self.assertEqual(failure.exception.code,404)
                get.assert_not_called()
        finally:
            server.shutdown(); server.server_close(); worker.join()


if __name__ == "__main__": unittest.main()
