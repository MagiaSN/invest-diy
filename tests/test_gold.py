"""Synthetic source contracts, unit conversions, period alignment and failure safety."""

import csv
from datetime import date
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from investdiy.global_track_gold import fetch as f, model as m
from investdiy.global_track_gold import __main__ as cli
from investdiy import registry


class CalculationTests(unittest.TestCase):
    def test_price_ratios_missing_values_and_zero_denominators(self):
        row = m.price_ratios([dict(date='2024-01-31', gold=2000, silver=25, brent=80, wti=0)])[0]
        self.assertEqual(row['gold_silver'], 80)
        self.assertEqual(row['gold_brent'], 25)
        self.assertIsNone(row['gold_wti'])
        self.assertIsNone(m.ratio(None, 1))
        self.assertIsNone(m.ratio(1, None))
        self.assertEqual(m.ratio(0, 5), 0)
        for v in ['NaN', 'inf', '-1']:
            with self.assertRaises(ValueError): m.number(v)

    def test_stocks_backcast_mine_production_and_stop_at_anchor(self):
        rows = m.stock_history('2024-06-30', 210000, {2023:3000,2022:3000}, {(2024,1):800,(2024,2):900})
        values = {r['date']:r['stock_t'] for r in rows}
        self.assertEqual(values['2023-12-31'], 208300)
        self.assertEqual(values['2022-12-31'], 205300)
        self.assertEqual(rows[-1]['method'], 'published_anchor')
        with self.assertRaises(KeyError): m.stock_history('2024-06-30', 210000, {2023:3000}, {})
        with self.assertRaises(ValueError): m.stock_history('2024-05-31', 210000, {}, {})

    def test_monthly_interpolation_no_extrapolation_or_debt_fill(self):
        stocks = [dict(date='2023-12-31',stock_t=200000,method='mine_backcast'),dict(date='2024-12-31',stock_t=212000,method='published_anchor')]
        prices = [dict(date=d,gold=2000) for d in ['2023-11-30','2024-06-30','2024-07-31','2025-01-31']]
        debt = [dict(date='2024-06-30',debt_date='2024-06-28',total=20e12,public=15e12)]
        rows = m.compare_market(prices,debt,stocks)
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]['stock_t'],206000)
        self.assertAlmostEqual(rows[0]['gold_usd'],206000*m.OZ_PER_TONNE*2000)
        self.assertIsNone(rows[1]['gold_debt_ratio'])
        self.assertEqual(rows[0]['debt_date'],'2024-06-28')

    def test_reserve_units_market_valuation_denominators_and_gaps(self):
        rows = [dict(country='USA',date='2023-01-31',gold_oz=10*m.OZ_PER_TONNE),
                dict(country='USA',date='2024-01-31',gold_oz=12*m.OZ_PER_TONNE,total_usd=300,exgold_usd=100,fx_usd=50),
                dict(country='USA',date='2024-03-31',gold_oz=13*m.OZ_PER_TONNE,total_usd=300)]
        r=m.reserves(rows)
        self.assertAlmostEqual(r[1]['gold_t'],12)
        self.assertAlmostEqual(r[1]['yoy_t'],2)
        self.assertIsNone(r[1]['change_t'])
        self.assertAlmostEqual(r[1]['gold_total_pct'],200/3)
        self.assertEqual(r[1]['gold_fx_pct'],400)
        self.assertIsNone(r[2]['change_t'])
        self.assertIsNone(r[2]['gold_usd'])
        with self.assertRaises(ValueError):
            m.reserves([dict(country='USA',date='2024-01-31',gold_oz=10,total_usd=1,exgold_usd=3)])

    def test_monthly_change_and_zero_holdings(self):
        rows = [dict(country='CAN',date='2024-01-31',gold_oz=m.OZ_PER_TONNE,total_usd=10,exgold_usd=10,fx_usd=5),
                dict(country='CAN',date='2024-02-29',gold_oz=0,total_usd=10,exgold_usd=10,fx_usd=5)]
        r=m.reserves(rows)[-1]
        self.assertEqual(r['change_t'],-1)
        self.assertEqual(r['gold_total_pct'],0)

    def test_positive_holdings_with_unavailable_gold_valuation_are_not_zero_share(self):
        row = m.reserves([dict(country='JPN',date='2024-01-31',gold_oz=100,
                               total_usd=1000,exgold_usd=1000,fx_usd=800)])[0]
        self.assertGreater(row['gold_t'],0)
        self.assertIsNone(row['gold_usd'])
        self.assertIsNone(row['gold_total_pct'])
        self.assertIsNone(row['gold_fx_pct'])


class SourceTests(unittest.TestCase):
    def test_anchor_and_production_headers_ignore_recycling(self):
        self.assertEqual(f.parse_anchor(b'<p>Total above-ground stock (end-Q3 2024):<br>210,000 tonnes</p>'),('2024-09-30',210000))
        source=b'<table><tr><th>Tonnes</th><th>2023</th><th>2024</th></tr><tr><td>Mine production</td><td>3,000.1</td><td>3,100.2</td></tr><tr><td>Recycled gold</td><td>900</td><td>950</td></tr></table>'
        self.assertEqual(f.parse_mine(source),{2023:3000.1,2024:3100.2})
        with self.assertRaises(ValueError): f.parse_mine(source.replace(b'Mine production',b'Total supply'))
        with self.assertRaises(ValueError): f.parse_anchor(b'Total above-ground stock: 210000 tonnes')

    def price_sheet(self):
        rows=[{'B':'Gold','C':'Silver','D':'Crude oil, Brent','E':'Crude oil, WTI'},
              {'B':'($/troy oz)','C':'($/troy oz)','D':'($/bbl)','E':'($/bbl)'}]
        rows += [dict(A=f'{1970+i//12}M{i%12+1:02d}',B='1000',C='20',D='50',E='…') for i in range(600)]
        return rows

    def test_prices_column_mapping_missing_cells_and_unit_guard(self):
        sheet=self.price_sheet()
        with patch.object(f,'worksheets',return_value=[sheet]):
            rows=f.parse_prices(b'')
        self.assertEqual(rows[0]['gold'],1000)
        self.assertIsNone(rows[0]['wti'])
        sheet[1]['B']='($/kg)'
        with patch.object(f,'worksheets',return_value=[sheet]),self.assertRaises(ValueError):f.parse_prices(b'')

    def test_prices_duplicates_rejected(self):
        sheet=self.price_sheet();sheet.append(sheet[-1])
        with patch.object(f,'worksheets',return_value=[sheet]),self.assertRaises(ValueError):f.parse_prices(b'')

    def test_imf_observation_units_not_display_scale(self):
        output=io.StringIO();w=csv.writer(output)
        w.writerow(['COUNTRY','INDICATOR','UNIT','FREQUENCY','TIME_PERIOD','OBS_VALUE','SCALE'])
        for c in m.COUNTRIES:
            for indicator,unit,value in [('RGV_REVS','FTO',32150.7465686),('TRGMV_REVS','USD',100),('RXF11_REVS','USD',90)]:
                w.writerow([c,indicator,unit,'M','2024-M01',value,6])
        rows=f.parse_imf(output.getvalue().encode())
        self.assertAlmostEqual(rows[0]['gold_oz'],32150.7465686)
        with self.assertRaises(ValueError):f.parse_imf(output.getvalue().replace(',FTO,',',TONNES,').encode())

    def debt_payload(self):
        rows=[]
        for i in range(120):
            d=m.month_end(f'{2010+i//12}-{i%12+1:02d}')
            rows.append(dict(record_date=d,tot_pub_debt_out_amt='100',debt_held_public_amt='80',intragov_hold_amt='20'))
        return dict(data=rows,meta={'total-count':len(rows)})

    def test_debt_pagination_month_end_and_reconciliation(self):
        p=self.debt_payload()
        self.assertEqual(len(f.parse_debt(json.dumps(p).encode())),120)
        p['data'][-1]['record_date']='2019-12-20'
        self.assertEqual(len(f.parse_debt(json.dumps(p).encode())),119)
        p['meta']['total-count']=121
        with self.assertRaises(ValueError):f.parse_debt(json.dumps(p).encode())
        p=self.debt_payload();p['data'][-1]['intragov_hold_amt']='10'
        with self.assertRaises(ValueError):f.parse_debt(json.dumps(p).encode())

    def test_cache_replaced_only_after_parse_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=Path(tmp);(data/'raw').mkdir();path=data/'raw/test';path.write_bytes(b'old')
            with patch.object(f,'get') as get:
                get.return_value.content=b'new'
                def reject(_):raise ValueError('bad source')
                with self.assertRaises(ValueError):f.cached(data,'test','https://example.org',reject)
            self.assertEqual(path.read_bytes(),b'old')

    def test_failed_update_keeps_outputs_and_reports_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=Path(tmp);out=data/'out';out.mkdir()
            (out/'prices.csv').write_text('date,gold\n2024-01-31,2000\n')
            (out/'market.csv').write_text('date,gold_usd\n2024-01-31,100\n')
            (out/'demand.csv').write_text('previous demand output')
            def fail(*args):raise ValueError('source unavailable')
            with patch.object(cli,'SOURCES',{k:(fail,'https://example.org') for k in cli.SOURCES}):
                self.assertFalse(cli.run(data))
            self.assertEqual((out/'market.csv').read_text(),'date,gold_usd\n2024-01-31,100\n')
            self.assertEqual((out/'prices.csv').read_text(),'date,gold\n2024-01-31,2000\n')
            self.assertIn('error', (out/'sources.csv').read_text())
            self.assertEqual((out/'demand.csv').read_text(),'previous demand output')

    def test_tool_discovery_is_local(self):
        tool,_=registry.discover()['global-track-gold']
        self.assertEqual(tool.visibility,'local')
        self.assertNotIn(tool.slug,registry.discover(public_only=True))


if __name__=='__main__':unittest.main()
