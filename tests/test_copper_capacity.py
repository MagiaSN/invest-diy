"""Capacity event semantics and aggregation using synthetic observations only."""

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest

from investdiy.global_track_copper import capacity as c


class CapacityTests(unittest.TestCase):
    def event(self, project='mine-a', kind='started', year=2022, value=12000):
        return dict(id=f'{project}-{kind}', project_id=project, year=year, kind=kind,
                    milestone=c.KINDS[kind], project_en='Mine A', project_zh='矿 A',
                    country_en='Example', country_zh='示例', scope='whole_project', ownership_basis='100%',
                    capacity_tpa=value, basis='design' if value is not None else 'unquantified',
                    note_en='Synthetic design', note_zh='模拟设计',
                    event_source='https://example.org/event', capacity_source='https://example.org/design',
                    event_evidence='Physical milestone confirmed in the year.', capacity_evidence='Copper capacity, 100% basis.')

    def payload(self):
        return dict(schema=1, unit='t Cu/year', coverage='reviewed-projects-not-global-total',
                    start_year=2021, as_of='2024-06-30', events=[self.event(),
                    self.event(kind='commissioned', year=2023),
                    self.event('mine-b', 'retired', 2024, 5000)])

    def test_annual_flows_not_stocks_and_positive_retirement(self):
        events, start, asof = c.validate(self.payload())
        rows = c.aggregate(events, start, asof)
        self.assertEqual([r['year'] for r in rows], [2021, 2022, 2023, 2024])
        self.assertEqual(rows[1]['started_tpa'], 12000)
        self.assertEqual(rows[2]['started_tpa'], 0)
        self.assertEqual(rows[2]['commissioned_tpa'], 12000)
        self.assertEqual(rows[-1]['retired_tpa'], 5000)
        self.assertEqual(rows[-1]['partial_year'], 1)
        self.assertEqual(rows[0]['partial_year'], 0)
        self.assertEqual({r['dataset_id'] for r in rows + events}, {rows[0]['dataset_id']})

    def test_unquantified_not_zero_and_known_subtotal(self):
        p = self.payload(); p['events'] += [self.event('mine-c', 'commissioned', 2024, None),
                                          self.event('mine-d', 'retired', 2024, None)]
        rows = c.aggregate(*c.validate(p))
        self.assertIsNone(rows[-1]['commissioned_tpa'])
        self.assertEqual(rows[-1]['commissioned_unknown'], 1)
        self.assertEqual(rows[-1]['retired_tpa'], 5000)
        self.assertEqual(rows[-1]['retired_count'], 2)
        self.assertEqual(rows[-1]['retired_unknown'], 1)
        self.assertEqual(rows[0]['commissioned_tpa'], 0)

    def test_reject_temporary_exits_plans_equity_and_wrong_units(self):
        for key, value in [('milestone', 'care_and_maintenance'), ('milestone', 'approved'),
                           ('kind', 'restart'), ('basis', 'actual_production'), ('basis', 'ore_throughput'),
                           ('basis', 'copper_equivalent'), ('scope', 'whole_site_expansion'),
                           ('ownership_basis', 'equity'), ('year', 2025), ('capacity_tpa', 0),
                           ('capacity_tpa', -1), ('capacity_tpa', float('nan')), ('capacity_tpa', True),
                           ('capacity_tpa', None), ('event_source', 'file:///tmp/data'), ('event_evidence', '')]:
            p = self.payload(); p['events'][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError): c.validate(p)
        p = self.payload(); p['unit'] = 't ore/year'
        with self.assertRaises(ValueError): c.validate(p)

    def test_duplicate_phase_and_impossible_chronology(self):
        p = self.payload(); p['events'].append(deepcopy(p['events'][0])); p['events'][-1]['id'] = 'other-id'
        with self.assertRaises(ValueError): c.validate(p)
        p = self.payload(); p['events'][0]['year'] = 2024
        with self.assertRaises(ValueError): c.validate(p)
        p = self.payload(); p['as_of'] = '2099-01-01'
        with self.assertRaises(ValueError): c.validate(p)

    def test_incremental_expansion_and_changed_review_digest(self):
        p = self.payload(); e = p['events'][0]
        e.update(scope='incremental_phase', before_tpa=10000, after_tpa=22000)
        old = c.validate(p)[0][0]['dataset_id']
        e['note_en'] = 'Revised review'
        self.assertNotEqual(c.validate(p)[0][0]['dataset_id'], old)
        e['capacity_tpa'] = 22000
        with self.assertRaises(ValueError): c.validate(p)

    def test_failed_refresh_preserves_both_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder); path = data / 'manual/copper-capacity-events.json'; path.parent.mkdir()
            payload = self.payload(); path.write_text(json.dumps(payload))
            c.run(data, refresh=True)
            paths = [data / 'out/capacity-events.csv', data / 'out/capacity-annual.csv']
            old = [p.read_bytes() for p in paths]
            payload['events'][0]['milestone'] = 'forecast'
            path.write_text(json.dumps(payload))
            with self.assertRaises(ValueError): c.run(data, refresh=True)
            self.assertEqual([p.read_bytes() for p in paths], old)

    def test_complete_calendar_year_and_stale_review(self):
        p = self.payload(); p['as_of'] = '2024-12-31'
        rows = c.aggregate(*c.validate(p, today=date(2026, 1, 1)))
        self.assertEqual(rows[-1]['partial_year'], 0)
        self.assertEqual(rows[-1]['year'], 2024)  # Never extend an old review with made-up zeros.
