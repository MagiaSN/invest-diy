"""Synthetic fixtures for units, date alignment, source parsing and cache safety."""

import json
from datetime import date
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import requests

from investdiy.common.csvio import read_rows
from investdiy.global_track_copper import fetch
from investdiy.global_track_copper import sources
from investdiy.global_track_copper import backfill
from investdiy.global_track_copper.model import (
    FIELDS, SERIES, atomic_csv, compute, export, merge, observation, validate, vat_rate,
)


def obs(series, value, day='2025-01-06'):
    return observation(series, day, value, 'synthetic test fixture')


class CopperCalculationTests(unittest.TestCase):
    def test_units_vat_and_pair_direction(self):
        row = compute([obs('cme_price', 4.5359237), obs('lme_price', 10000),
                       obs('shfe_price', 87010), obs('usdcny', 7),
                       obs('cme_stock', 1000)])[0]
        self.assertAlmostEqual(row['cme_usd_t'], 10000)
        self.assertAlmostEqual(row['cme_stock_t'], 907.18474)
        self.assertAlmostEqual(row['shfe_net_usd_t'], 11000)
        self.assertAlmostEqual(row['shfe_lme_net_spread'], 1000)
        self.assertAlmostEqual(row['shfe_lme_net_pct'], 10)
        self.assertAlmostEqual(row['shfe_cme_gross_pct'], 24.3)

    def test_no_cross_date_matching_or_fx_forward_fill(self):
        rows = compute([obs('lme_price', 10000), obs('usdcny', 7),
                        obs('shfe_price', 79100, '2025-01-07'), obs('cme_price', 4, '2025-01-07')])
        self.assertNotIn('shfe_net_usd_t', rows[1])
        self.assertNotIn('cme_lme_net_pct', rows[1])
        self.assertNotIn('lme_usd_t', rows[1])

    def test_cme_lme_comparison_does_not_require_fx(self):
        row = compute([obs('cme_price', 4), obs('lme_price', 10000)])[0]
        self.assertLess(row['cme_lme_net_pct'], 0)
        self.assertEqual(row['cme_lme_net_pct'], row['cme_lme_gross_pct'])

    def test_inventory_total_converts_units_and_requires_all_same_date_components(self):
        rows = compute([
            obs('cme_stock', 1000), obs('lme_stock', 2000), obs('shfe_stock', 0),
            obs('cme_stock', 1100, '2025-01-07'), obs('lme_stock', 2100, '2025-01-07'),
            obs('shfe_stock', 3000, '2025-01-08'),
        ])
        self.assertAlmostEqual(rows[0]['total_stock_t'], 2907.18474)
        self.assertNotIn('total_stock_t', rows[1])
        self.assertNotIn('total_stock_t', rows[2])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            atomic_csv(root / 'history.csv', [obs('cme_stock', 1000), obs('lme_stock', 2000), obs('shfe_stock', 0)], FIELDS)
            export(root)
            self.assertAlmostEqual(float(read_rows(root / 'out/daily.csv')[0]['total_stock_t']), 2907.18474)

    def test_effective_vat_dates(self):
        self.assertEqual(vat_rate('2018-04-30'), .17)
        self.assertEqual(vat_rate('2018-05-01'), .16)
        self.assertEqual(vat_rate('2019-03-31'), .16)
        self.assertEqual(vat_rate('2019-04-01'), .13)

    def test_validation_rejects_wrong_units_nan_zero_price_and_duplicates(self):
        for value in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                obs('cme_price', value)
        with self.assertRaises(ValueError):
            observation('cme_price', '2025-01-06', 400, 'test', 'US cents/lb')
        with self.assertRaises(ValueError):
            validate([obs('lme_price', 10000), obs('lme_price', 11000)])
        with self.assertRaises(ValueError):
            obs('usdcny', 7, '2099-01-01')
        self.assertEqual(obs('cme_stock', 0)['value'], 0)

    def test_merge_revises_without_erasing_older_history(self):
        old = [obs('lme_price', 10000), obs('lme_price', 10100, '2025-01-07')]
        new = [obs('lme_price', 10200, '2025-01-07')]
        merged = merge(old, new)
        self.assertEqual([r['value'] for r in merged], [10000, 10200])
        self.assertEqual(merge(merged, new), merged)

    def test_export_empty_and_incomplete_history_does_not_claim_freshness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(export(root), [])
            atomic_csv(root / 'history.csv', [obs('lme_price', 10000)], FIELDS)
            export(root)
            self.assertEqual(read_rows(root / 'out/summary.csv')[0]['as_of'], '')
            self.assertEqual(read_rows(root / 'out/daily.csv')[0]['cme_usd_t'], '')


class CopperBackfillTests(unittest.TestCase):
    @staticmethod
    def report(day_rows):
        rows = [['Monthly Report', '', 'January 2025', ''], ['TABLA / TABLE 4.2'], ['(TM / MT)'],
                ['Daily Closings', 'BML/LME', 'COMEX', 'SHFE']]
        rows.extend(day_rows)
        return '<table>' + ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>' for row in rows) + '</table>'

    def test_report_locale_holidays_units_date_and_components(self):
        text = self.report([
            ['06', '', '', '', '1.000', '', '2.000', '', '3.000', '', '6.000', ''],
            ['07', '', '', '', 'Feriado', '', '-', '', '-', '', '-', ''],
            ['08', '', '', '', 'Feriado', '', '2.000', '', '3.000', '', '5.000', ''],
        ])
        rows = backfill.parse_report(text, 2025, 1)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['date'], '2025-01-06')
        self.assertEqual(rows[0]['cme'], 2000)
        self.assertIsNone(rows[1]['lme'])
        self.assertEqual(rows[1]['cme'], 2000)
        for bad in (text.replace('(TM / MT)', '(short tons)'), text.replace('6.000', '7.000'),
                    text.replace('January 2025', 'January 2024')):
            with self.assertRaises(ValueError):
                backfill.parse_report(bad, 2025, 1)
        with self.assertRaises(ValueError):
            backfill.report_number('2,000.0')

    def test_gap_fill_preserves_existing_and_samples_shortened_trading_week(self):
        history = [obs('shfe_price', 70000, '2025-01-06'), obs('shfe_price', 70000, '2025-01-08'),
                   obs('shfe_stock', 500, '2025-01-08'), obs('shfe_price', 70000, '2025-01-17')]
        reports = [dict(date=d, cme=1000, shfe=2000, source='fixture')
                   for d in ['2025-01-06', '2025-01-08', '2025-01-09', '2025-01-17']]
        added, audit = backfill.select_additions(history, reports, '2025-01-01', '2025-01-31')
        self.assertEqual([r['date'] for r in added if r['series'] == 'shfe_stock'], ['2025-01-17'])
        self.assertAlmostEqual(next(r['value'] for r in added if r['series'] == 'cme_stock'), 1000 / .90718474)
        self.assertTrue(any(r['reason'].startswith('Conflicting') for r in audit))
        again, _ = backfill.select_additions(merge(history, added), reports, '2025-01-01', '2025-01-31')
        self.assertEqual(again, [])

    def test_zero_and_isolated_spike_are_quarantined(self):
        reports = [dict(date=d, cme=v, shfe=None, source='fixture') for d, v in
                   [('2025-01-06', 1000), ('2025-01-07', 10000), ('2025-01-08', 1010), ('2025-01-09', 0)]]
        added, audit = backfill.select_additions([], reports, '2025-01-01', '2025-01-31')
        self.assertEqual([r['date'] for r in added], ['2025-01-06', '2025-01-08'])
        self.assertEqual(sum(r['decision'] == 'quarantined' for r in audit), 2)

    def test_failed_month_preserves_history_and_records_incomplete_backfill(self):
        class Today(date):
            @classmethod
            def today(cls):
                return cls(2025, 2, 1)
        original = [obs('shfe_price', 70000), obs('cme_stock', 1000)]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            atomic_csv(root / 'history.csv', original, FIELDS)
            with patch.object(backfill, 'date', Today), patch.object(backfill.net, 'get', side_effect=ValueError('outage')):
                status = backfill.run('2025-01-01', root)
            self.assertEqual(status['months_loaded'], 0)
            self.assertIn('outage', status['errors'])
            self.assertEqual(validate(read_rows(root / 'history.csv')), original)


class CopperParserTests(unittest.TestCase):
    def test_cme_dollars_per_pound_and_contract_identity(self):
        payload = {'data': {'code': 'HG00Y', 'market': 101, 'klines': ['2025-01-06,4.2,4.3,4.4,4.1,100']}}
        self.assertEqual(fetch.parse_cme(json.dumps(payload))[0]['value'], 4.3)
        payload['data']['code'] = 'GC00Y'
        with self.assertRaises(ValueError):
            fetch.parse_cme(json.dumps(payload))

    def test_sina_parses_json_without_executing_scripts(self):
        payload = '/*<script>ignored</script>*/ var _copper=([{"d":"2025-01-06","c":"79000"}]);'
        self.assertEqual(fetch.parse_sina(payload, 'shfe_price')[0]['value'], 79000)
        with self.assertRaises(ValueError):
            fetch.parse_sina('<html>Blocked</html>', 'lme_price')

    def test_inventory_identity_and_unverified_zero(self):
        data = {'defaultVariety': 100, 'defaultVarietyUnit': '短吨',
                'positionTrendChartListData': {'list': [['2025-01-06', 4, 100], ['2025-01-07', 4, 0]]}}
        def html():
            return '<script id="__NEXT_DATA__" type="application/json">' + json.dumps({'props': {'pageProps': {'data': data}}}) + '</script>'
        rows, skipped = fetch.parse_inventory(html(), 'cme_stock')
        self.assertEqual(skipped, 1)
        self.assertEqual(rows[0]['unit'], 'short ton')
        data['defaultVarietyUnit'] = '吨'
        with self.assertRaises(ValueError):
            fetch.parse_inventory(html(), 'cme_stock')
        with self.assertRaises(ValueError):
            fetch.parse_inventory(html(), 'shfe_stock')

    def test_west_uses_stock_not_cash_price_and_rejects_wrong_year(self):
        text = '<table><tr><th>date</th><th>LME Copper stock</th><th>cash</th><th>3m</th></tr><tr><td>13. November 2026</td><td>329,100</td><td>13,610.00</td><td>13,545.00</td></tr></table>'
        rows = sources.parse_west(text, 2026)
        self.assertEqual(rows[0]['value'], 329100)
        self.assertEqual(rows[0]['date'], '2026-11-13')
        with self.assertRaises(ValueError):
            sources.parse_west(text, 2025)

    def test_shfe_uses_copper_total_including_bonded_not_warrants_or_other_metals(self):
        def tr(cells):
            return '<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>'
        text = '<table>' + ''.join(tr(r) for r in [
            ['2025-11-14 2025年 第(44)期'], ['本周库存', '小计', '期货'], ['铜', '单位：吨'],
            ['合计', 999, 0, 1000, 100, 1, 100, 0, 0, 0],
            ['保税商品总计', 18, 0, 18, 0, 0, 0, 0, 0, 0],
            ['完税商品总计', 110000, 50000, 109389, 49830, -611, -170, 0, 0, 0],
            ['总计', 110018, 50000, 109407, 49830, -611, -170, 0, 0, 0],
            ['铝', '单位：吨'], ['总计', 1, 1, 1, 1, 0, 0, 0, 0, 0],
        ]) + '</table>'
        self.assertEqual(sources.parse_shfe(text, '2025-11-14')['value'], 109407)
        with self.assertRaises(ValueError):
            sources.parse_shfe(text, '2025-11-13')
        with self.assertRaises(ValueError):
            sources.parse_shfe(text.replace('109407', '109408'), '2025-11-14')

    def test_ecb_requires_both_same_day_rates_and_correct_base(self):
        text = 'FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX,TIME_PERIOD,OBS_VALUE\nD,CNY,EUR,SP00,A,2025-01-06,7.7\nD,USD,EUR,SP00,A,2025-01-06,1.1\nD,CNY,EUR,SP00,A,2025-01-07,7.8\nD,USD,EUR,SP00,A,2025-01-08,1.2\n'
        rows = sources.parse_ecb(text)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['date'], '2025-01-06')
        self.assertAlmostEqual(rows[0]['value'], 7)
        with self.assertRaises(ValueError):
            sources.parse_ecb(text.replace('EUR', 'GBP'))
        with self.assertRaises(ValueError):
            sources.parse_ecb(text.replace(',1.1', ',0'))

    def test_comex_quarantines_bad_totals_dates_and_overlapping_conflicts(self):
        data = {'success': True, 'symbol': 'HG', 'count': 6, 'data': [
            {'date': '2026-06-12', 'total': 300, 'registered': 100, 'eligible': 200},
            {'date': '2026-06-15', 'total': 301, 'registered': 100, 'eligible': 201},
            {'date': '2026-06-16', 'total': 30, 'registered': None, 'eligible': None},
            {'date': '2026-06-17', 'total': 302, 'registered': 100, 'eligible': 100},
            {'date': '2026-06-13', 'total': 300, 'registered': 100, 'eligible': 200},
            {'date': '2026-03-02', 'total': 300, 'registered': 100, 'eligible': 200},
        ]}
        text = json.dumps(data)
        rows, rejected = sources.parse_metalcharts(text)
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rejected), 4)
        with tempfile.TemporaryDirectory() as tmp:
            primary = [obs('cme_stock', 310, '2026-06-12')]
            merged = sources.extend_comex(primary, text, Path(tmp))
            self.assertEqual([r['value'] for r in merged], [310, 301])
            self.assertEqual(len(read_rows(Path(tmp) / 'raw/comex-rejected.csv')), 5)

    def test_bad_shfe_history_is_quarantined_even_if_replacement_fails(self):
        wrong = observation('shfe_stock', '2025-01-03', 100, fetch.OLD_SHFE)
        verified = obs('shfe_stock', 200, '2025-01-10')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            atomic_csv(root / 'history.csv', [wrong, verified], FIELDS)
            with patch.object(fetch.net, 'ensure_resolvable'), patch.object(fetch, 'fetch_one', side_effect=ValueError('outage')):
                fetch.run(data_dir=root)
            self.assertEqual(validate(read_rows(root / 'history.csv')), [verified])
            backup = next((root / 'backups').glob('history-*.csv'))
            self.assertEqual(validate(read_rows(backup)), [wrong, verified])

    def test_ecb_migration_removes_fed_only_holidays_and_keeps_manual_imports(self):
        fed = [observation('usdcny', '2025-01-06', 7, fetch.FED), observation('usdcny', '2025-01-07', 7, fetch.FED)]
        imported = obs('usdcny', 7, '2024-01-02')
        ecb = observation('usdcny', '2025-01-06', 7.1, sources.ECB)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            atomic_csv(root / 'history.csv', fed + [imported], FIELDS)
            def get_series(series, start, data_dir):
                if series == 'usdcny':
                    self.assertEqual(start, '2025-01-06')
                    return [ecb], ''
                raise ValueError('outage')
            with patch.object(fetch.net, 'ensure_resolvable'), patch.object(fetch, 'fetch_one', side_effect=get_series):
                fetch.run(start='2026-01-01', data_dir=root)
            self.assertEqual(validate(read_rows(root / 'history.csv')), [imported, ecb])

    def test_shfe_short_week_report_retries_timeout_but_not_missing_archive(self):
        class Today(date):
            @classmethod
            def today(cls):
                return cls(2025, 1, 10)
        calls = []
        def get(url, **kwargs):
            calls.append(url)
            if '20250108' in url:
                if calls.count(url) == 1:
                    raise requests.Timeout('transient outage')
                return SimpleNamespace(text='validated fixture', encoding='utf-8')
            response = requests.Response()
            response.status_code = 404
            raise requests.HTTPError(response=response)
        with tempfile.TemporaryDirectory() as tmp:
            row = obs('shfe_stock', 200, '2025-01-08')
            with patch.object(sources, 'date', Today), patch.object(sources.net, 'get', side_effect=get), patch.object(sources, 'parse_shfe', return_value=row):
                rows, detail = sources.fetch_shfe('2025-01-06', Path(tmp), ['2025-01-06', '2025-01-08'])
            self.assertEqual(rows, [row])
            self.assertEqual(detail, '')
            self.assertEqual(sum('20250108' in u for u in calls), 2)
            self.assertEqual(sum('20250110' in u for u in calls), 1)

    def test_invalid_fx_replacement_does_not_erase_legacy_history(self):
        fed = observation('usdcny', '2025-01-06', 7, fetch.FED)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            atomic_csv(root / 'history.csv', [fed], FIELDS)
            def get_series(series, start, data_dir):
                if series == 'usdcny':
                    return [{**fed, 'value': 'nan'}], ''
                raise ValueError('outage')
            with patch.object(fetch.net, 'ensure_resolvable'), patch.object(fetch, 'fetch_one', side_effect=get_series):
                fetch.run(data_dir=root)
            self.assertEqual(validate(read_rows(root / 'history.csv')), [fed])

    def test_fetch_failure_retains_history_and_marks_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = [obs('lme_price', 10000)]
            atomic_csv(root / 'history.csv', original, FIELDS)
            with patch.object(fetch.net, 'ensure_resolvable'), patch.object(fetch, 'fetch_one', side_effect=ValueError('fixture outage')):
                statuses = fetch.run(data_dir=root)
            self.assertEqual(len(statuses), len(SERIES))
            self.assertTrue(all(s['status'] == 'error' for s in statuses))
            self.assertEqual(validate(read_rows(root / 'history.csv')), original)


if __name__ == '__main__':
    unittest.main()
