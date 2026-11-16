"""Public-source adapters with validation before replacing the local raw cache."""

import csv
from datetime import date
from html.parser import HTMLParser
import io
import json
import re
from urllib.parse import urljoin

from ..common.net import get
from ..common.xlsx import worksheets
from .model import COUNTRIES, month_end, number, stock_history

WB_PAGE = 'https://www.worldbank.org/en/research/commodity-markets'
STOCK_PAGE = 'https://www.gold.org/goldhub/data/how-much-gold'
WGC_REPORT = 'https://www.gold.org/goldhub/research/gold-demand-trends/gold-demand-trends-'
DEBT_URL = 'https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny'
IMF_URL = ('https://api.imf.org/external/sdmx/2.1/data/IMF.STA,IL/' + '+'.join(COUNTRIES)
           + '.RGV_REVS+RXF11FX_REVS+RXF11_REVS+TRGMV_REVS.FTO+USD.M')
IMF_FIELDS = {'RGV_REVS': ('gold_oz', 'FTO'), 'RXF11FX_REVS': ('fx_usd', 'USD'),
              'RXF11_REVS': ('exgold_usd', 'USD'), 'TRGMV_REVS': ('total_usd', 'USD')}


class Tables(HTMLParser):
    """Preserve table boundaries so unrelated headers cannot be paired with values."""
    def __init__(self):
        super().__init__()
        self.tables, self.table, self.row, self.cell = [], None, None, None
        self.links = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.append(dict(attrs).get('href', ''))
        if tag == 'table':
            self.table = []
        elif tag == 'tr' and self.table is not None:
            self.row = []
        elif tag in ('td', 'th') and self.row is not None:
            self.cell = []

    def handle_data(self, text):
        self.text.append(text)
        if self.cell is not None:
            self.cell.append(text)

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split()))
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == 'table' and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def html(content):
    parser = Tables()
    parser.feed(content.decode('utf-8'))
    return parser


def parse_prices(content):
    labels = {'Gold': ('gold', '($/troy oz)'), 'Silver': ('silver', '($/troy oz)'),
              'Crude oil, Brent': ('brent', '($/bbl)'), 'Crude oil, WTI': ('wti', '($/bbl)')}
    for sheet in worksheets(content):
        for index, row in enumerate(sheet[:-1]):
            columns = {c: labels[v] for c, v in row.items() if v in labels}
            if len(columns) != len(labels):
                continue
            if any(sheet[index + 1].get(c) != unit for c, (_, unit) in columns.items()):
                raise ValueError('Pink Sheet price units changed')
            result = {}
            for row in sheet[index + 2:]:
                m = re.fullmatch(r'(\d{4})M(\d{2})', row.get('A', ''))
                if not m:
                    continue
                day = month_end(f'{m[1]}-{m[2]}')
                if day >= date.today().isoformat():
                    continue
                if day in result:
                    raise ValueError(f'Duplicate price month: {day}')
                values = {key: number(row.get(c)) for c, (key, _) in columns.items()}
                if any(v == 0 for v in values.values()):
                    raise ValueError('Zero commodity price')
                result[day] = dict(date=day, **values)
            if len(result) < 600:
                raise ValueError('Pink Sheet monthly history unexpectedly short')
            return [result[d] for d in sorted(result)]
    raise ValueError('Missing monthly Gold / Silver / Brent / WTI price table')


def parse_imf(content):
    result = {}
    for row in csv.DictReader(io.StringIO(content.decode('utf-8-sig'))):
        indicator = row['INDICATOR']
        if indicator not in IMF_FIELDS or row['COUNTRY'] not in COUNTRIES:
            continue
        field, unit = IMF_FIELDS[indicator]
        if row['UNIT'] != unit or row['FREQUENCY'] != 'M':
            raise ValueError('IMF units or frequency changed')
        m = re.fullmatch(r'(\d{4})-M(\d{2})', row['TIME_PERIOD'])
        if not m:
            raise ValueError('Invalid IMF monthly period')
        day = month_end(f'{m[1]}-{m[2]}')
        if day >= date.today().isoformat():
            continue
        value = number(row['OBS_VALUE'])
        if value is None:
            continue
        target = result.setdefault((row['COUNTRY'], day), dict(country=row['COUNTRY'], date=day))
        if field in target and target[field] != value:
            raise ValueError('Conflicting IMF observation')
        # OBS_VALUE is in full USD / fine troy ounces. SCALE is display metadata.
        target[field] = value
    countries = {r['country'] for r in result.values() if 'gold_oz' in r}
    if countries != set(COUNTRIES):
        raise ValueError(f'Missing IMF gold holdings: {set(COUNTRIES) - countries}')
    if not any('exgold_usd' in r and 'total_usd' in r for r in result.values()):
        raise ValueError('Missing IMF market-valued total reserves')
    return sorted(result.values(), key=lambda r: (r['country'], r['date']))


def parse_debt(content):
    payload = json.loads(content)
    if int(payload['meta']['total-count']) != len(payload['data']):
        raise ValueError('Incomplete Treasury pagination')
    by_month = {}
    for row in sorted(payload['data'], key=lambda r: r['record_date']):
        day = date.fromisoformat(row['record_date']).isoformat()
        end = month_end(day[:7])
        if end >= date.today().isoformat():
            continue
        total, public, internal = (number(row[k]) for k in ('tot_pub_debt_out_amt', 'debt_held_public_amt', 'intragov_hold_amt'))
        if total is None or public is None or internal is None or total <= 0:
            raise ValueError('Missing Treasury debt components')
        by_month[end] = dict(date=end, debt_date=day, total=total, public=public, internal=internal)
    # Do not treat an interrupted month as a month-end observation.
    result = [r for r in by_month.values()
              if (date.fromisoformat(r['date']) - date.fromisoformat(r['debt_date'])).days <= 4]
    if any(abs(r['total'] - r['public'] - r['internal']) > 1 for r in result):
        raise ValueError('Treasury month-end debt components do not reconcile')
    if len(result) < 100:
        raise ValueError('Treasury history unexpectedly short')
    return sorted(result, key=lambda r: r['date'])


def parse_anchor(content):
    text = ' '.join(html(content).text)
    m = re.search(r'Total above-ground stock\s*\(end-(?:Q([1-4])\s+)?(20\d{2})\)\s*:\s*([\d,]+)\s*tonnes', text)
    if not m:
        raise ValueError('WGC dated stock anchor not found')
    day = month_end(f'{m[2]}-{int(m[1] or 4) * 3:02d}')
    value = number(m[3])
    if day > date.today().isoformat() or not 100_000 < value < 500_000:
        raise ValueError('Invalid stock anchor')
    return day, value


def parse_mine(content):
    result = {}
    for table in html(content).tables:
        mine = next((r for r in table if r and r[0].lower() == 'mine production'), None)
        if not mine:
            continue
        for header in table[:3]:
            for i, period in enumerate(header):
                annual = re.fullmatch(r'20\d{2}', period)
                quarterly = re.fullmatch(r"Q([1-4])['’](\d{2})", period)
                if not annual and not quarterly:
                    continue
                key = int(period) if annual else (2000 + int(quarterly[2]), int(quarterly[1]))
                value = number(mine[i])
                if value is None or not (2000 < value < 5000 if annual else 400 < value < 1600):
                    raise ValueError(f'Invalid mine production: {period}')
                result[key] = value
    if not result:
        raise ValueError('Missing mine production table')
    return result


def cached(data, name, url, parser, *, offline=False, headers=None, params=None):
    path = data / 'raw' / name
    if offline:
        return parser(path.read_bytes())
    response = get(url, headers=headers, params=params, timeout=60, retries=2)
    result = parser(response.content)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_bytes(response.content)
    tmp.replace(path)
    return result


def fetch_prices(data, offline=False):
    def link(content):
        links = [urljoin(WB_PAGE, u) for u in html(content).links if 'CMO-Historical-Data-Monthly.xlsx' in u]
        if not links:
            raise ValueError('World Bank monthly workbook link not found')
        return links[0]
    url = cached(data, 'worldbank.html', WB_PAGE, link, offline=offline)
    return cached(data, 'prices.xlsx', url, parse_prices, offline=offline)


def fetch_imf(data, offline=False):
    return cached(data, 'imf.csv', IMF_URL, parse_imf, offline=offline,
                  params={'startPeriod': '2000'}, headers={'Accept': 'application/vnd.sdmx.data+csv;version=1.0.0'})


def fetch_debt(data, offline=False):
    # 10,000 rows covers this window until the 2050s; reject truncated results.
    return cached(data, 'debt.json', DEBT_URL, parse_debt, offline=offline,
                  params={'filter': 'record_date:gte:2014-01-01', 'sort': 'record_date', 'page[size]': 10000})


def fetch_stocks(data, offline=False):
    anchor_day, anchor = cached(data, 'stock.html', STOCK_PAGE, parse_anchor, offline=offline)
    year, mon = int(anchor_day[:4]), int(anchor_day[5:7])
    annual, quarters = {}, {}
    last_full = year if mon == 12 else year - 1
    for y in range(2016, last_full + 1):
        url = f'{WGC_REPORT}full-year-{y}/supply'
        values = cached(data, f'supply-{y}.html', url, parse_mine, offline=offline)
        if y not in values or y - 1 not in values:
            raise ValueError(f'Annual report does not cover {y}')
        annual.update({k: v for k, v in values.items() if isinstance(k, int)})
    if mon != 12:
        # The latest report's rolling five quarters incorporates recent revisions.
        url = f'{WGC_REPORT}q{mon // 3}-{year}'
        values = cached(data, f'supply-{year}-q{mon // 3}.html', url, parse_mine, offline=offline)
        quarters.update({k: v for k, v in values.items() if isinstance(k, tuple)})
    return stock_history(anchor_day, anchor, annual, quarters)
