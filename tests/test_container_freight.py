"""Regression coverage for SSE's mixed units, missing cells and independent updates."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from investdiy.common.csvio import read_rows, write_rows
from investdiy.global_track_container_freight import analyze, fetch
from investdiy.global_track_container_freight.parse import CURRENT_FIELDS, parse_page


def table(rows, title=""):
    return f'<div class="title2">{title}</div><table>' + ''.join(
        '<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>' for row in rows) + '</table>'


class ParsingTests(unittest.TestCase):
    def test_scfi_empty_previous_does_not_shift_weight_or_change(self):
        html = table([
            ['航线', '单位', '权重', '上期 2026-10-23', '本期 2026-10-30', '与上期比涨跌'],
            ['欧洲 20ft', 'USD/TEU', '5.0%', '', '1,234.567', '-9.1'],
            ['欧洲 40ft', 'USD/FEU', '15.0%', '900', '', ''],
        ])
        a, b = parse_page('scfi', html)
        self.assertEqual((a['prev'], a['value'], a['weight']), ('', '1234.567', '5.0%'))
        self.assertEqual((b['prev'], b['value']), ('900', ''))
        self.assertNotEqual(a['series'], b['series'])
        self.assertEqual(fetch.parse('scfi', 'single', html), [
            (a['series'], '2026-10-30', 1234.567), (b['series'], '2026-10-23', 900.0)])

    def test_spans_keep_tanker_units_in_their_columns(self):
        html = '''<div class="title2">原油 2026-11-04</div><table>
        <tr><td>航线</td><td>单位</td><td>本期</td><td>涨跌</td></tr>
        <tr><td rowspan="2">CT1</td><td>点</td><td>150</td><td>2</td></tr>
        <tr><td>美元/吨</td><td>13.350</td><td>-0.220</td></tr></table>'''
        a, b = parse_page('ctfi', html)
        self.assertEqual((a['unit'], b['unit'], b['value']), ('points', 'USD/tonne', '13.350'))
        self.assertNotEqual(a['series'], b['series'])
        html = '''<div class="title2">租金2026-11-03发布</div><table>
        <tr><td>船型</td><td>载重吨</td><td>单位</td><td>指数/日租金</td><td>涨跌</td></tr>
        <tr><td colspan="2">综合指数</td><td>点</td><td>1000</td><td>1</td></tr></table>'''
        self.assertEqual(parse_page('cdi', html)[0]['value'], '1000')

    def test_vessel_sizes_and_parent_groups_are_distinct(self):
        rows = parse_page('cbfi', table([
            ['航线', '参考船型', '本期 2026-10-30', '涨跌'],
            ['秦皇岛-广州', '5-6万DWT', '100', '0'], ['秦皇岛-广州', '6-7万DWT', '200', '0']]))
        self.assertNotEqual(rows[0]['series'], rows[1]['series'])
        rows = parse_page('srfi', table([
            ['指数', '权重', '本期', '与上期比涨跌 (%)'],
            ['“海上丝绸之路”进口集装箱运价指数', '20%', '100', '1'], ['欧洲航线', '40%', '90', '1'],
            ['“海上丝绸之路”出口集装箱运价指数', '40%', '200', '1'], ['欧洲航线', '40%', '110', '2'],
        ], '上海航运交易所2026-10-28发布'))
        self.assertNotEqual(rows[1]['series'], rows[3]['series'])

    def test_two_independent_csi_column_groups(self):
        rows = parse_page('csi', table([
            ['指数项目', '当期指数 2026-11-04', '涨跌 (%)'] * 2,
            ['欧洲', '0.00', '-100', '亚洲', '400', '2']]))
        self.assertEqual([r['value'] for r in rows], ['0.00', '400'])

    def test_monthly_and_script_values_ignore_search_placeholder(self):
        html = '<input placeholder="2026-11-04">' + table([
            ['公司', '到离港', '', '收发货', ''], ['本期', '涨跌', '本期', '涨跌'],
        ], '2026-09班轮公司准班率')
        html += "<script>row = []; row[0]='Carrier'; row[1]='32.31'; row[2]='-2.1'; row[3]='37.23'; row[4]='0'; arr[0] = row;</script>"
        a, b = parse_page('gcspi_ca', html)
        self.assertEqual((a['date'], a['period'], a['value'], a['change_unit']), ('2026-09-01', '2026-09', '32.31', 'pp'))
        self.assertEqual(b['value'], '37.23')

    def test_brcvi_literals_are_decoded_without_running_scripts(self):
        import json
        html = table([['指数', '权重', '本期', '涨跌 (%)'], ['综合指数', '', '200', '1']], '2026-10-28')
        fragment = '<tr><td>中国（上海）出口量</td><td>70%</td><td>240.46</td><td>17.9</td></tr>'
        html += '<script>$("#table_row").after($(' + json.dumps(fragment) + '))</script>'
        rows = parse_page('brcvi', html)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]['value'], '240.46')

    def test_trace_and_legacy_identifiers_survive(self):
        html = table([['日期', '欧洲航线', '美西航线'], ['2026-11-02', '2000', '4000']])
        self.assertEqual(fetch.parse('scfis', 'trace', html), [('europe', '2026-11-02', 2000), ('uswc', '2026-11-02', 4000)])
        html = table([['航线', '上期 2026-10-23', '本期 2026-10-30', '涨跌 (%)'], ['欧洲航线', '100', '110', '10']])
        self.assertEqual(parse_page('ccfi', html)[0]['series'], 'europe')


class PipelineTests(unittest.TestCase):
    def test_merge_keeps_precision_and_live_precedence(self):
        base = dict(index='cdfi', series='route', date='2026-11-04')
        rows = fetch.merge([{**base, 'value': '13.358', 'source': 'sse'}], [{**base, 'value': '13.35', 'source': 'archive'}])
        self.assertEqual(rows[0]['value'], '13.358')

    def test_changes_skip_zero_and_missing_bases(self):
        d = date(2026, 10, 30)
        self.assertEqual(analyze._change([(date(2026, 10, 23), 0)], d, 100, 1), '')
        self.assertEqual(analyze._change([(date(2026, 1, 1), 100)], d, 110, 1), '')
        self.assertEqual(analyze._change([(date(2026, 10, 23), 100)], d, 110, 1), '10.00')

    def test_fetch_failure_preserves_only_failed_index_and_records_status(self):
        with tempfile.TemporaryDirectory() as folder:
            current, status = Path(folder) / 'current.csv', Path(folder) / 'status.csv'
            old = parse_page('ccfi', table([['航线', '本期 2026-10-23'], ['综合指数', '100']]))
            write_rows(current, old, CURRENT_FIELDS)
            html = table([['航线', '本期 2026-10-30'], ['综合指数', '200']])
            def get(url, **kwargs):
                if 'ccfi' in url:
                    raise TimeoutError('request failed')
                return SimpleNamespace(text=html)
            with patch.multiple(fetch, CURRENT_CSV=current, STATUS_CSV=status, PAGES={
                'ccfi': [('single', '/?indexType=ccfi')], 'scfi': [('single', '/?indexType=scfi')]}), patch.object(fetch.net, 'get', side_effect=get):
                rows = fetch.fetch_live()
            self.assertEqual([r['index'] for r in rows], ['scfi'])
            self.assertEqual(len(read_rows(current)), 2)
            states = {r['index']: r['status'] for r in read_rows(status)}
            self.assertEqual(states, {'ccfi': 'error', 'scfi': 'ok'})

    def test_latest_only_does_not_download_archives(self):
        with tempfile.TemporaryDirectory() as folder, patch.multiple(fetch, DATA=Path(folder), OBS_CSV=Path(folder)/'obs.csv'), \
             patch.object(fetch, 'fetch_live', return_value=[]), patch.object(fetch, 'read_published', return_value=[]), \
             patch.object(fetch, 'read_archive', return_value=[]), patch.object(fetch, 'update_archive') as archive:
            fetch.run(latest_only=True)
            archive.assert_not_called()

    def test_unavailable_current_is_not_filled_with_history_and_daily_cannot_mask_weekly(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            obs = [dict(index=i, series=s, date=d, value='100', source='sse') for i,s,d in [
                ('ccfi','composite','2026-10-23'), ('scfi','composite','2026-10-30'),
                ('scfis','europe','2026-11-02'), ('scfis','uswc','2026-11-02'), ('fdi','route','2026-11-04')]]
            meta = parse_page('scfi', table([['航线', '上期 2026-10-23', '本期 2026-10-30'], ['欧洲 20ft', '123', '']]))
            obs.append(dict(index='scfi',series=meta[0]['series'],date='2026-10-23',value='123',source='sse'))
            write_rows(folder/'obs.csv', obs, fetch.FIELDS)
            write_rows(folder/'current.csv', meta, CURRENT_FIELDS)
            with patch.multiple(analyze, OBS_CSV=folder/'obs.csv', CURRENT_CSV=folder/'current.csv', STATUS_CSV=folder/'status.csv', OUT=folder/'out'), patch.object(analyze, 'read_archive_metadata', return_value=[]):
                analyze.main()
            row = next(r for r in read_rows(folder/'out/latest.csv') if r['series'] == meta[0]['series'])
            self.assertEqual((row['value'], row['current'], row['reported_date'], row['availability']), ('123', '', '2026-10-30', 'unavailable'))
            self.assertEqual(read_rows(folder/'out/kpi.csv')[0]['as_of'], '2026-10-23')


if __name__ == '__main__':
    unittest.main()
