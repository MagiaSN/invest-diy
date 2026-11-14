"""Annual copper fundamentals from the COCHILCO statistical yearbook.

Read published XLSX values with the standard library. Never evaluate formulas or
mix mine output with refined consumption when calculating the market balance.
"""

from datetime import date
from io import BytesIO
import math
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from ..common.net import get
from .model import atomic_csv

YEARBOOK = ('https://www.cochilco.cl/web/download/1036/2026/16850/'
            'base-de-datos-anuario-de-estadisticas-cochilco-2000-2025.xlsx')
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
TITLES = {
    'World Copper Mine Production': 'mine_production_t',
    'World Refined Copper Production': 'refined_production_t',
    'World Refined Copper Consumption': 'refined_usage_t',
}
FIELDS = ['year', *TITLES.values(), 'balance_t', 'source', 'edition']


def worksheets(content):
    """Yield sparse rows keyed by Excel column letters, preserving empty cells."""
    with ZipFile(BytesIO(content)) as archive:
        shared = [''.join(n.itertext()) for n in ET.fromstring(archive.read('xl/sharedStrings.xml'))]
        for name in archive.namelist():
            if not re.fullmatch(r'xl/worksheets/sheet\d+\.xml', name):
                continue
            rows = []
            for row in ET.fromstring(archive.read(name)).findall('.//s:row', NS):
                values = {}
                for cell in row.findall('s:c', NS):
                    value = cell.find('s:v', NS)
                    if value is not None:
                        value = shared[int(value.text)] if cell.get('t') == 's' else value.text
                    elif cell.get('t') == 'inlineStr':
                        value = ''.join(cell.find('s:is', NS).itertext())
                    else:
                        continue
                    values[re.sub(r'\d', '', cell.get('r'))] = value.strip()
                if values:
                    rows.append(values)
            yield rows


def annual_table(rows):
    """Validate a world-total table and return its annual values in tonnes."""
    header = ' '.join(str(v) for r in rows[:6] for v in r.values())
    title = next((t for t in TITLES if t in header), None)
    if title is None:
        return None
    if 'kMT copper content' not in header:
        raise ValueError(f'Unexpected unit: {title}')
    years = next(({c: int(v) for c, v in r.items() if re.fullmatch(r'(19|20)\d{2}', v)}
                  for r in rows[:10] if sum(bool(re.fullmatch(r'(19|20)\d{2}', v)) for v in r.values()) >= 2), {})
    totals = [r for r in rows if r.get('A') == 'TOTAL MUNDIAL / WORLD TOTAL']
    if not years or len(totals) != 1:
        raise ValueError(f'Missing years or unique world total: {title}')
    result = {}
    for column, year in years.items():
        if year >= date.today().year:
            raise ValueError(f'Incomplete/future annual observation: {year}')
        value = float(totals[0][column]) * 1000
        if not math.isfinite(value) or not 1_000_000 <= value <= 100_000_000:
            raise ValueError(f'Invalid world total: {year} {value}')
        if year in result:
            raise ValueError(f'Duplicate annual column: {year}')
        result[year] = round(value, 1)
    return TITLES[title], result


def parse_yearbook(content):
    series = {}
    for rows in worksheets(content):
        table = annual_table(rows)
        if table:
            key, values = table
            if key in series:
                raise ValueError(f'Duplicate world table: {key}')
            series[key] = values
    if set(series) != set(TITLES.values()):
        raise ValueError('Incomplete supply/demand tables')
    years = sorted(series['refined_usage_t'])
    if any(set(v) != set(years) for v in series.values()):
        raise ValueError('Supply/demand years do not align')
    if years != list(range(years[0], years[-1] + 1)):
        raise ValueError('Missing annual observations')
    return [dict(year=y, **{k: v[y] for k, v in series.items()},
                 balance_t=round(series['refined_production_t'][y] - series['refined_usage_t'][y], 1),
                 source=YEARBOOK, edition='COCHILCO 2000–2025') for y in years]


def run(data, *, refresh=False):
    cache = data / 'raw' / 'fundamentals' / 'cochilco-2000-2025.xlsx'
    content = get(YEARBOOK, retries=1, timeout=60).content if refresh or not cache.exists() else cache.read_bytes()
    rows = parse_yearbook(content)
    if len(rows) < 20:
        raise ValueError('Yearbook history unexpectedly short')
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(content)
    atomic_csv(data / 'out' / 'annual.csv', rows, FIELDS)
    return rows
