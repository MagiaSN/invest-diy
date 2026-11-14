"""Synthetic institutional forecast fixtures; no market observations."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from investdiy.global_track_copper import forecasts as f


class ForecastTests(unittest.TestCase):
    def payload(self):
        return dict(source=f.SOURCE, publication=f.EDITION, scenario=f.SCENARIO,
                    unit='MMt Cu', source_table='Appendix B, Figures 83 and 84',
                    scope='Total copper demand; baseline primary plus secondary supply',
                    reviewed_at='2026-01-10', observations=[dict(year=y, supply_mmt=25.1,
                    demand_mmt=26.2, primary_mmt=20, secondary_mmt=5.1) for y in range(2024, 2041)])

    def test_units_sign_and_forecast_years_only(self):
        rows = f.validate(self.payload())
        self.assertEqual([r['year'] for r in rows], list(range(2026, 2041)))
        self.assertEqual(rows[0]['forecast_supply_t'], 25_100_000)
        self.assertEqual(rows[0]['forecast_demand_t'], 26_200_000)
        self.assertEqual(rows[0]['forecast_balance_t'], -1_100_000)
        self.assertEqual(rows[-1]['precision_t'], 100_000)

    def test_reject_mixed_editions_units_and_years(self):
        for key, value in [('source', 'https://example.org/other.pdf'), ('publication', '2025-01'),
                           ('scenario', 'unconstrained'), ('unit', 'kt Cu'), ('scope', 'Mine only'),
                           ('source_table', 'Figure 85'), ('reviewed_at', '2099-01-01')]:
            payload = self.payload(); payload[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): f.validate(payload)
        for mutate in [lambda r: r.pop(), lambda r: r.reverse(),
                       lambda r: r[1].update(year=2024)]:
            payload = self.payload(); mutate(payload['observations'])
            with self.assertRaises(ValueError): f.validate(payload)

    def test_nonfinite_missing_precision_and_composition(self):
        for value in ['NaN', 'Infinity', '', None, -1, 0, 200, 25.123, True]:
            payload = self.payload(); payload['observations'][2]['supply_mmt'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): f.validate(payload)
        payload = self.payload(); payload['observations'][2]['secondary_mmt'] = 6
        with self.assertRaises(ValueError): f.validate(payload)
        payload['observations'][2]['secondary_mmt'] = 5.2
        self.assertEqual(len(f.validate(payload)), 15)  # Published component rounding.
        del payload['observations'][2]['demand_mmt']
        with self.assertRaises(KeyError): f.validate(payload)

    def test_failed_review_preserves_output_and_refresh_uses_review(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder); manual = data / 'manual/copper-forecast-spglobal-2026.json'
            manual.parent.mkdir(); payload = self.payload(); manual.write_text(json.dumps(payload))
            self.assertEqual(len(f.run(data, refresh=True)), 15)
            out = data / 'out/forecasts.csv'; previous = out.read_bytes()
            invalid = deepcopy(payload); invalid['unit'] = 'kt'
            manual.write_text(json.dumps(invalid))
            with self.assertRaises(ValueError): f.run(data, refresh=True)
            self.assertEqual(out.read_bytes(), previous)
            manual.unlink()
            with self.assertRaises(FileNotFoundError): f.run(data)
            self.assertEqual(out.read_bytes(), previous)
