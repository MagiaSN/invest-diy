"""Annual demand source contracts, net flows, rounding and revision precedence."""

from copy import deepcopy
from datetime import date
import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from requests import HTTPError, Response

from investdiy.global_track_gold import demand as d


class DemandTests(unittest.TestCase):
    def history(self):
        values = {'Jewellery fabrication ': 2000, 'Technology': 300, 'Total bar and coin': 1000,
                  'ETFs and similar products': -200, 'Central banks and other inst.': 500, 'Gold demand': 3600}
        return {'yAxis': [{'title': {'text': '<i>Tonnes</i>'}}], 'xAxis': {'categories': list(range(2010, 2023))},
                'series': [{'name': k, 'data': [v]*13} for k, v in values.items()]}

    def encode(self, options):
        return ('_self._opt = ' + json.dumps(options) + '; throw new Error("never execute");').encode()

    def report(self, edition=2023):
        values = {'Jewellery Fabrication': 2000, 'Jewellery Consumption': 1900, 'Jewellery Inventory': 100,
                  'Technology': 300, 'Electronics': 250, 'Other Industrial': 40, 'Dentistry': 10,
                  'Investment': 800, 'Total Bar and Coin': 1000, 'ETFs & Similar Products': -200,
                  'Central Banks & Other inst.': 500, 'Gold Demand': 3600, 'OTC and Other': -100, 'Total Demand': 3500}
        return ('<h2>Gold supply and demand by sector, tonnes</h2><table>'
                f'<tr><th></th><th>{edition-1}</th><th>{edition}</th><th>Annual change</th><th>Q4</th></tr>' +
                ''.join(f'<tr><td>{k}</td><td>{v}</td><td>{v}</td><td>0</td><td>999</td></tr>' for k,v in values.items()) + '</table>').encode()

    def test_history_signed_values_and_missing_otc(self):
        rows=d.parse_history(self.encode(self.history()))
        self.assertEqual(len(rows),13)
        self.assertEqual(rows[0]['etf_t'],-200)
        self.assertEqual(rows[0]['investment_t'],800)
        self.assertIsNone(rows[0]['otc_t'])
        self.assertIsNone(rows[0]['total_demand_t'])
        self.assertEqual(rows[0]['precision_t'],1)

    def test_history_unit_alignment_duplicates_and_categories(self):
        for mutate in [lambda o:o['yAxis'][0]['title'].update(text='USD'),
                       lambda o:o['series'][0]['data'].pop(),
                       lambda o:o['series'].append(o['series'][0]),
                       lambda o:o['series'][0].update(name='Jewellery consumption'),
                       lambda o:o['xAxis']['categories'].__setitem__(0,2020)]:
            options=self.history();mutate(options)
            with self.assertRaises(ValueError):d.parse_history(self.encode(options))

    def test_table_parent_categories_are_not_double_counted(self):
        rows=d.parse_report(self.report(),2023)
        self.assertEqual([r['year'] for r in rows],[2022,2023])
        self.assertEqual(rows[0]['jewellery_t'],2000)
        self.assertEqual(rows[0]['technology_t'],300)
        self.assertEqual(sum(rows[0][k] for k in d.CATEGORIES),3600)
        self.assertEqual(rows[0]['total_demand_t'],3500)
        self.assertEqual(rows[0]['otc_t'],-100)
        self.assertEqual(rows[0]['precision_t'],0.1)

    def test_2023_chart_units_title(self):
        source=self.report().replace(b'Gold supply and demand by sector, tonnes',
                                    b'Gold supply and demand</h2><h3>Annual gold demand by sector, tonnes')
        self.assertEqual(len(d.parse_report(source,2023)),2)

    def test_reject_missing_fields_bad_units_nonfinite_and_future(self):
        for source in [self.report().replace(b'Jewellery Fabrication',b'Unknown'),
                       self.report().replace(b'tonnes',b'US dollars'),
                       self.report().replace(b'<td>-200</td>',b'<td>NaN</td>'),
                       self.report().replace(b'<td>-100</td>',b'<td></td>'),
                       self.report().replace(b'<td>3600</td>',b'<td>9999</td>')]:
            with self.assertRaises(ValueError):d.parse_report(source,2023)
        with self.assertRaises(ValueError):d.parse_report(self.report(date.today().year),date.today().year)

    def test_rounding_tolerance_depends_on_source_precision(self):
        row=d.parse_history(self.encode(self.history()))[0]
        row['gold_demand_t']+=2
        d.validate(row)
        row['precision_t']=0.1
        with self.assertRaises(ValueError):d.validate(row)
        row=d.parse_report(self.report(),2023)[0];row['total_demand_t']=None
        with self.assertRaises(ValueError):d.validate(row)

    def test_latest_edition_replaces_whole_year_and_preserves_older_history(self):
        history=d.parse_history(self.encode(self.history()))
        newer=d.parse_report(self.report(),2023)
        merged=d.merge_editions([newer,history])
        self.assertEqual(len(merged),14)
        self.assertEqual(merged[-2]['edition'],2023)
        self.assertEqual(merged[-2]['otc_t'],-100)
        self.assertIsNone(merged[0]['otc_t'])
        conflict=deepcopy(newer);conflict[0]['source']='different source'
        with self.assertRaises(ValueError):d.merge_editions([history,newer,conflict])
        with self.assertRaises(ValueError):d.merge_editions([history[:-1],newer[1:]])

    def test_unpublished_latest_report_can_fall_back_but_existing_report_failure_cannot(self):
        history=d.parse_history(self.encode(self.history()))
        response=Response();response.status_code=404
        error=HTTPError('not published',response=response)
        with tempfile.TemporaryDirectory() as folder:
            data=Path(folder)
            with patch.object(d,'date') as clock:
                clock.today.return_value=date(2024,1,5)
                with patch.object(d,'cached',side_effect=[history,error]):
                    self.assertEqual(d.fetch_demand(data)[-1]['year'],2022)
                (data/'raw').mkdir();(data/'raw/demand-2023.html').write_bytes(b'old report')
                with patch.object(d,'cached',side_effect=[history,error]),self.assertRaises(HTTPError):
                    d.fetch_demand(data)
                response.status_code=503
                with patch.object(d,'cached',side_effect=[history,error]),self.assertRaises(HTTPError):
                    d.fetch_demand(data)


if __name__=='__main__':unittest.main()
