"""Synthetic source validation tests; no external requests or market data fixtures."""

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from investdiy.global_track_copper import fundamentals as f, mines as m, refining as rf


class AnnualTests(unittest.TestCase):
    def table(self, title='World Refined Copper Production'):
        return [{'A': title}, {'A': '(kMT copper content)'}, {'B': '2023', 'C': '2024'},
                {'A': 'TOTAL MUNDIAL / WORLD TOTAL', 'B': '20000.1', 'C': '21000.2'}]

    def test_units_world_total_and_other_tables(self):
        key, rows = f.annual_table(self.table())
        self.assertEqual(key, 'refined_production_t')
        self.assertEqual(rows, {2023: 20000100, 2024: 21000200})
        self.assertIsNone(f.annual_table(self.table('World Gold Mine Production')))

    def test_bad_units_missing_total_nonfinite_future(self):
        for mutate in [lambda r: r[1].update(A='metric tonnes'),
                       lambda r: r.pop(), lambda r: r[-1].update(B='NaN'),
                       lambda r: r[2].update(C=str(date.today().year)),
                       lambda r: r.append(dict(r[-1]))]:
            rows = self.table(); mutate(rows)
            with self.assertRaises((ValueError, KeyError)):
                f.annual_table(rows)

    def test_balance_uses_refined_supply_and_aligned_years(self):
        tables = [self.table(t) for t in f.TITLES]
        tables[0][-1].update(B='12000', C='13000')
        tables[2][-1].update(B='21000', C='20000')
        with patch.object(f, 'worksheets', return_value=tables):
            rows = f.parse_yearbook(b'')
        self.assertEqual(rows[0]['balance_t'], -999900)
        self.assertEqual(rows[1]['balance_t'], 1000200)
        self.assertNotIn('refined_minus_mined_t', rows[0])
        tables[0][2].update(C='2022')
        with patch.object(f, 'worksheets', return_value=tables), self.assertRaises(ValueError):
            f.parse_yearbook(b'')

    def test_failed_refresh_preserves_cache_and_output(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder); cache = data / 'raw/fundamentals/cochilco-2000-2025.xlsx'
            cache.parent.mkdir(parents=True); cache.write_bytes(b'old cache')
            out = data / 'out/annual.csv'; out.parent.mkdir(); out.write_text('previous')
            with patch.object(f, 'get') as get, self.assertRaises(Exception):
                get.return_value.content = b'not a spreadsheet'; f.run(data, refresh=True)
            self.assertEqual(cache.read_bytes(), b'old cache')
            self.assertEqual(out.read_text(), 'previous')


class RefiningTests(unittest.TestCase):
    TABLE = '''TABLE 1. WORLD REFINED COPPER PRODUCTION AND USAGE TRENDS
Thousand metric tonnes, copper
2020 2021 2022 2023 Jan-Aug 2024 p/ 2024 p/
2023 2024 %ch. Jul Aug
World Copper Mine Production
Primary Refined Copper Production 20,000 21,000 22,000 23,000 15,000 16,000
Secondary Refined Copper Production 3,000 4,000 5,000 6,000 3,000 4,000
World Refined Copper Production
23,000 25,000 27,001 29,000 18,000 20,000
(Primary & Secondary)
ICSG Copper Bulletin - October 2024
'''

    def test_direct_components_units_and_exclude_partial_year_columns(self):
        rows = rf.parse_table(self.TABLE, 'https://example.org/current.pdf')
        self.assertEqual([r['year'] for r in rows], [2020, 2021, 2022, 2023])
        self.assertEqual(rows[-1]['secondary_refined_t'], 6000000)
        self.assertEqual(rows[-1]['primary_refined_t'], 23000000)
        self.assertEqual(rows[2]['total_refined_t'], 27001000)
        self.assertEqual(rows[0]['publication'], '2024-10')

    def test_legacy_release_and_invalid_tables(self):
        legacy = self.TABLE.replace('TABLE 1. WORLD REFINED COPPER PRODUCTION AND USAGE TRENDS',
                                    'World Refined Copper Usage and Supply Trends')
        self.assertEqual(len(rf.parse_table(legacy, 'https://example.org/report.pdf', '2024-01')), 4)
        for before, after in [('Thousand metric tonnes', 'Metric tonnes'),
                              ('2020 2021 2022 2023', '2020 2021 2022 2022'),
                              ('27,001', '30,000'), ('Secondary Refined Copper Production', 'Scrap trade'),
                              ('3,000 4,000 5,000 6,000', '3,000 4,000 NaN 6,000'),
                              ('October 2024', 'October 2099'),
                              ('20,000 21,000 22,000 23,000', '20,000 21,000 22,000 23,000.5')]:
            with self.assertRaises(ValueError):
                rf.parse_table(self.TABLE.replace(before, after), 'https://example.org/report.pdf')

    def test_latest_edition_revises_entire_bundle_and_preserves_history(self):
        old = rf.parse_table(self.TABLE, 'https://example.org/old.pdf')
        new = rf.parse_table(self.TABLE.replace('October 2024', 'November 2024'), 'https://example.org/new.pdf')[2:]
        rows = rf.merge_editions([new, old])
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]['publication'], '2024-10')
        self.assertEqual(rows[-1]['source'], 'https://example.org/new.pdf')
        conflict = deepcopy(old); conflict[0]['secondary_refined_t'] += 1000
        with self.assertRaises(ValueError):
            rf.merge_editions([old, conflict])

    def test_failed_refresh_preserves_sources_and_output(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder); raw = data / 'raw/fundamentals/icsg'; raw.mkdir(parents=True)
            for name, _, _ in rf.SOURCES:
                (raw / f'{name}.pdf').write_bytes(b'previous PDF')
            out = data / 'out/refining.csv'; out.parent.mkdir(); out.write_text('previous output')
            with patch.object(rf, 'ensure_resolvable'), patch.object(rf, 'get') as get, self.assertRaises(Exception):
                get.return_value.content = b'not PDF'; rf.run(data, refresh=True)
            self.assertEqual(out.read_text(), 'previous output')
            self.assertEqual((raw / 'current.pdf').read_bytes(), b'previous PDF')

    def test_archives_keep_years_outside_window_and_allow_same_issue_revision(self):
        current = rf.parse_table(self.TABLE, rf.TABLE)
        historical = [dict(current[0], year=2019, publication='2023-10')]
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder); raw = data / 'raw/fundamentals/icsg'; raw.mkdir(parents=True)
            for name, _, _ in rf.SOURCES:
                (raw / f'{name}.pdf').write_bytes(b'new')
            (raw / 'table-2023-10.pdf').write_bytes(b'old')
            (raw / 'table-2024-10.pdf').write_bytes(b'superseded')
            def parse(content, *args):
                self.assertNotEqual(content, b'superseded')
                return deepcopy(historical if content == b'old' else current)
            with patch.object(rf, 'parse_pdf', side_effect=parse), patch.object(rf, 'get') as get:
                rows = rf.run(data)
                get.assert_not_called()
                self.assertEqual([r['year'] for r in rows], list(range(2019, 2024)))
                self.assertEqual((raw / 'table-2024-10.pdf').read_bytes(), b'new')
                self.assertEqual(rf.run(data), rows)


class MineTests(unittest.TestCase):
    def production(self, **changes):
        r = dict(mine_id='oyu-tolgoi', commodity='copper', metric='production', product_form='concentrate',
                 basis='contained', source_excerpt='Copper in concentrates 100', source_url='https://example.org/report.pdf',
                 confidence=.95, company='Example', calendar_period=None, time_period='Q2 2025',
                 unit='kt', value=100, unit_normalized='kt', value_normalized=100, operation='Example mine')
        return {**r, **changes}

    def test_periods_future_and_fiscal_ambiguity(self):
        self.assertEqual(m.period_end('Q2 2025'), date(2025, 6, 30))
        self.assertEqual(m.period_end('FY2025'), date(2025, 12, 31))
        self.assertIsNone(m.period_end('FY2099'))
        self.assertIsNone(m.period_end('2025 guidance'))
        self.assertIsNone(m.production_candidate(self.production(company='BHP')))

    def test_unit_conversion_and_zero(self):
        r = self.production(unit='Mlbs', value=10, value_normalized=4.535924)
        self.assertAlmostEqual(m.production_candidate(r)['production_t'], 4535.924, places=3)
        self.assertEqual(m.production_candidate(self.production(value=0, value_normalized=0))['production_t'], 0)

    def test_exclude_sales_forecasts_ore_missing_evidence_and_bad_units(self):
        for changes in [dict(metric='sales'), dict(metric='guidance'), dict(product_form='ore'),
                        dict(source_excerpt=None), dict(unit='dmt'), dict(basis='unknown'),
                        dict(value=float('nan')), dict(value_normalized=100000), dict(time_period='Q1 2099'),
                        dict(source_excerpt='2025 production guidance 100')]:
            self.assertIsNone(m.production_candidate(self.production(**changes)), changes)

    def test_conflicting_reports_not_silently_chosen_or_summed(self):
        a = self.production(); b = self.production(value=110, value_normalized=110)
        self.assertEqual(m.select_production([a, b]), {})
        self.assertEqual(m.select_production([a, deepcopy(a)])['production_t'], 100000)
        # Cathode and concentrate components do not become a guessed mine total.
        self.assertEqual(m.select_production([a, self.production(product_form='cathode')]), {})

    def test_latest_period_equity_and_original_scope(self):
        rows = [self.production(), self.production(time_period='Q3 2025', basis='equity', value=50, value_normalized=50)]
        r = m.select_production(rows)
        self.assertEqual(r['production_t'], 50000)
        self.assertEqual(r['production_basis'], 'equity')
        self.assertEqual(r['production_period'], 'Q3 2025')
        self.assertEqual(r['production_scope'], 'Example mine')

    def register(self):
        return dict(generated='2025-01-01', curated=[dict(id='cu-test', m=['Cu'], stage='mine', at=[0, 0],
                    name='Example', cc='XXX', asof='2025-01', status='prod', owners='Company', op='Operator',
                    src=[['Report', 'https://example.org']], cap='200 kt/year')])

    def test_register_filters_refineries_and_keeps_missing_output(self):
        register = self.register(); refinery = deepcopy(register['curated'][0]); refinery.update(id='refinery', stage='refine')
        register['curated'].append(refinery)
        rows = m.build(register, [], {'XXX': {'NAME_EN': 'Example', 'NAME_ZH': '示例'}})
        self.assertEqual(len(rows), 1)
        self.assertNotIn('production_t', rows[0])
        self.assertEqual(rows[0]['owners'], 'Company')

    def test_invalid_register_coordinates_dates_and_duplicates(self):
        for changes in [dict(at=[181, 0]), dict(at=[0, float('nan')]), dict(asof='2099-01'), dict(status='guess')]:
            register = self.register(); register['curated'][0].update(changes)
            with self.assertRaises(ValueError):
                m.build(register, [], {'XXX': {'NAME_EN': 'Example', 'NAME_ZH': '示例'}})
        register = self.register(); register['curated'].append(deepcopy(register['curated'][0]))
        with self.assertRaises(ValueError):
            m.build(register, [], {'XXX': {'NAME_EN': 'Example', 'NAME_ZH': '示例'}})

    def test_failed_mine_refresh_keeps_last_output(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder); raw = data / 'raw/fundamentals'; raw.mkdir(parents=True)
            (raw / 'mine-register.json').write_text(json.dumps(self.register()))
            (raw / 'mining.db').write_bytes(b'old db')
            out = data / 'out/mines.csv'; out.parent.mkdir(); out.write_text('previous')
            with patch.object(m, 'get') as get, patch.object(m, 'download_database', return_value=b'bad database'), self.assertRaises(Exception):
                get.return_value.json.return_value = self.register(); m.run(data, refresh=True)
            self.assertEqual(out.read_text(), 'previous')
            self.assertEqual((raw / 'mining.db').read_bytes(), b'old db')

    def review(self):
        return dict(id='cu-test', reviewed_on='2025-08-01', sources=['https://example.org/report.pdf'],
                    evidence='Reviewed company mine report, annual table', updates=dict(owners='Reviewed Company',
                    production_t=12345, production_period='2024', production_basis='100%',
                    production_form='concentrate', production_scope='Example whole mine', reporter='Reviewed Company',
                    production_source='https://example.org/report.pdf', production_evidence='Copper in concentrate: 12,345 t'))

    def test_review_fills_missing_and_is_repeatable_without_mutating_input(self):
        rows = [dict(id='cu-test', name='Example', owners='')]
        result = m.apply_reviews(rows, [self.review()])
        self.assertEqual(result[0]['production_t'], 12345)
        self.assertEqual(result[0]['owners'], 'Reviewed Company')
        self.assertNotIn('production_t', rows[0])
        self.assertEqual(m.apply_reviews(result, [self.review()]), result)
        self.assertEqual(json.loads(result[0]['details_sources']), ['https://example.org/report.pdf'])

    def test_old_review_keeps_newer_output_and_status_but_fills_ownership(self):
        row = dict(id='cu-test', name='Example', production_t=10, production_period='Q2 2025',
                   production_scope='New report', status='prod', status_asof='2025-09')
        review = self.review(); review['updates'].update(status='cons', status_asof='2025-01', production_scope_zh='旧范围')
        result = m.apply_reviews([row], [review])[0]
        self.assertEqual(result['production_t'], 10)
        self.assertEqual(result['production_scope'], 'New report')
        self.assertNotIn('production_scope_zh', result)
        self.assertEqual(result['status'], 'prod')
        self.assertEqual(result['owners'], 'Reviewed Company')

    def test_review_rejects_unverified_or_incomplete_observations_atomically(self):
        mutations = [lambda r: r.update(id='unknown'), lambda r: r.update(reviewed_on='2099-01-01'),
                     lambda r: r.update(sources=[]), lambda r: r.update(sources=['file:///etc/passwd']),
                     lambda r: r.update(evidence=''), lambda r: r['updates'].pop('production_basis'),
                     lambda r: r['updates'].update(production_t=float('nan')),
                     lambda r: r['updates'].update(production_t=-1),
                     lambda r: r['updates'].update(production_t=True),
                     lambda r: r['updates'].update(production_form='ore'),
                     lambda r: r['updates'].update(production_period='2099'),
                     lambda r: r['updates'].update(production_source='https://unreviewed.org'),
                     lambda r: r['updates'].update(status='ramp'),
                     lambda r: r['updates'].update(latitude=100),
                     lambda r: r['updates'].update(owners='')]
        for mutate in mutations:
            rows = [dict(id='cu-test', name='Example', owners='Original')]
            review = self.review(); mutate(review)
            with self.assertRaises(ValueError):
                m.apply_reviews(rows, [review])
            self.assertEqual(rows[0]['owners'], 'Original')
        with self.assertRaises(ValueError):
            m.apply_reviews([dict(id='cu-test', name='Example')], [self.review(), self.review()])

    def test_review_supports_explicit_zero_and_stockpile_status(self):
        review = self.review(); review['updates'].update(production_t=0, status='stockpile', status_asof='2025-01')
        result = m.apply_reviews([dict(id='cu-test', name='Example')], [review])[0]
        self.assertEqual(result['production_t'], 0)
        self.assertEqual(result['status'], 'stockpile')


if __name__ == '__main__':
    unittest.main()
