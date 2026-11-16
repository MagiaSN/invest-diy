"""Annual WGC demand: public chart history plus later full-year table revisions."""

from datetime import date
import json
import math
import re
from requests import HTTPError

from .fetch import WGC_REPORT, cached, html

PAGE = 'https://www.gold.org/goldhub/research/gold-demand-trends'
HISTORY_PAGE = WGC_REPORT + 'full-year-2022'
HISTORY_CHART = 'https://fsapi.gold.org/api/v12/charts/js/gdt-fy-2022-x02sq/1482'
CATEGORIES = ['jewellery_t', 'technology_t', 'bars_coins_t', 'etf_t', 'central_banks_t']
FIELDS = ['date', 'year', *CATEGORIES, 'investment_t', 'gold_demand_t', 'otc_t', 'total_demand_t',
          'precision_t', 'edition', 'source', 'data_source']
LABELS = {
    'jewellery fabrication': 'jewellery_t', 'technology': 'technology_t',
    'total bar and coin': 'bars_coins_t', 'etfs and similar products': 'etf_t',
    'central banks and other inst.': 'central_banks_t', 'investment': 'investment_t',
    'gold demand': 'gold_demand_t', 'otc and other': 'otc_t', 'total demand': 'total_demand_t',
}


def label(value):
    return ' '.join(value.lower().replace('&', 'and').split())


def value(cell):
    # Negative net investment and OTC values are meaningful, not missing data.
    text = str(cell).strip().replace(',', '').replace('−', '-')
    if not re.fullmatch(r'-?\d+(?:\.\d+)?', text):
        raise ValueError(f'Invalid demand observation: {cell!r}')
    result = float(text)
    if not math.isfinite(result):
        raise ValueError('Nonfinite demand observation')
    return result


def validate(row):
    year = row['year']
    if year >= date.today().year or year < 2010:
        raise ValueError(f'Incomplete or unsupported demand year: {year}')
    if any(k not in row or not math.isfinite(row[k]) for k in [*CATEGORIES, 'gold_demand_t', 'investment_t']):
        raise ValueError('Incomplete demand categories')
    if row['jewellery_t'] < 0 or row['technology_t'] < 0 or row['gold_demand_t'] <= 0:
        raise ValueError('Invalid fabrication or total demand')
    tolerance = row['precision_t'] * 3 + 1e-6
    if abs(sum(row[k] for k in CATEGORIES) - row['gold_demand_t']) > tolerance:
        raise ValueError(f'{year}: demand categories do not reconcile')
    if abs(row['bars_coins_t'] + row['etf_t'] - row['investment_t']) > tolerance:
        raise ValueError(f'{year}: investment components do not reconcile')
    if (row.get('otc_t') is None) != (row.get('total_demand_t') is None):
        raise ValueError('OTC and total demand must be available together')
    if row.get('total_demand_t') is not None:
        if not all(math.isfinite(row[k]) for k in ('otc_t', 'total_demand_t')) or row['total_demand_t'] <= 0:
            raise ValueError('Invalid total demand including OTC')
        if abs(row['gold_demand_t'] + row['otc_t'] - row['total_demand_t']) > tolerance:
            raise ValueError(f'{year}: OTC and total demand do not reconcile')
    return row


def parse_history(content):
    """Decode only the JSON configuration; never execute downloaded JavaScript."""
    text = content.decode('utf-8')
    match = re.search(r'_self\._opt\s*=\s*', text)
    if not match:
        raise ValueError('Missing public chart configuration')
    options, _ = json.JSONDecoder().raw_decode(text[match.end():])
    units = re.sub('<[^>]*>', '', options['yAxis'][0]['title']['text']).strip().lower()
    if units != 'tonnes':
        raise ValueError('Unexpected demand chart units')
    years = options['xAxis']['categories']
    if years != list(range(2010, 2023)):
        raise ValueError('Unexpected annual chart coverage')
    series = {}
    for s in options['series']:
        key = LABELS.get(label(s['name']))
        if key:
            if key in series or len(s['data']) != len(years):
                raise ValueError('Duplicate or misaligned chart series')
            series[key] = [value(v) for v in s['data']]
    if set(series) != {*CATEGORIES, 'gold_demand_t'}:
        raise ValueError('Unexpected public chart categories')
    result = []
    for i, year in enumerate(years):
        row = dict(date=f'{year}-12-31', year=year, **{k: vs[i] for k, vs in series.items()},
                   otc_t=None, total_demand_t=None, precision_t=1, edition=2022,
                   source=HISTORY_PAGE, data_source=HISTORY_CHART)
        row['investment_t'] = row['bars_coins_t'] + row['etf_t']
        result.append(validate(row))
    return result


def parse_report(content, edition):
    page = html(content)
    text = ' '.join(' '.join(page.text).split())
    if ('Gold supply and demand' not in text or
            not re.search(r'(?:Gold supply and demand|Annual gold demand) by sector,\s*tonnes', text, re.I)):
        raise ValueError('Missing demand table title or tonne units')
    tables = [table for table in page.tables if any(r and label(r[0]) == 'gold demand' for r in table)]
    if len(tables) != 1:
        raise ValueError('Missing unique gold demand table')
    table = tables[0]
    years = {i: int(v) for i, v in enumerate(table[0]) if re.fullmatch(r'20\d{2}', v)}
    if sorted(years.values()) != [edition - 1, edition]:
        raise ValueError('Annual report year headers changed')
    series = {}
    for cells in table[1:]:
        key = LABELS.get(label(cells[0])) if cells else None
        if key:
            if key in series:
                raise ValueError(f'Duplicate demand row: {key}')
            series[key] = {year: value(cells[i]) for i, year in years.items()}
    if set(series) != {*CATEGORIES, 'investment_t', 'gold_demand_t', 'otc_t', 'total_demand_t'}:
        raise ValueError('Missing demand categories or totals')
    source = WGC_REPORT + f'full-year-{edition}'
    return [validate(dict(date=f'{year}-12-31', year=year, **{k: vs[year] for k, vs in series.items()},
                          precision_t=0.1, edition=edition, source=source, data_source=source))
            for year in sorted(years.values())]


def merge_editions(bundles):
    result = {}
    for bundle in bundles:
        for row in bundle:
            validate(row)
            old = result.get(row['year'])
            if old and old['edition'] == row['edition'] and old != row:
                raise ValueError('Conflicting demand rows from the same edition')
            if not old or row['edition'] > old['edition']:
                result[row['year']] = row
    years = sorted(result)
    if not years or years != list(range(2010, years[-1] + 1)):
        raise ValueError('Incomplete annual demand history')
    return [result[y] for y in years]


def fetch_demand(data, offline=False):
    latest = date.today().year - 1
    bundles = [cached(data, 'demand-history-2022.js', HISTORY_CHART, parse_history, offline=offline)]
    for edition in range(2023, latest + 1):
        name = f'demand-{edition}.html'
        # The just-completed calendar year may not yet have an annual release.
        if offline and edition == latest and not (data / 'raw' / name).exists():
            break
        try:
            bundles.append(cached(data, name, WGC_REPORT + f'full-year-{edition}',
                                  lambda content, y=edition: parse_report(content, y), offline=offline))
        except HTTPError as exc:
            if edition != latest or exc.response.status_code != 404 or (data / 'raw' / name).exists():
                raise
            break
    return merge_editions(bundles)
