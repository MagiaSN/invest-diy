"""Public copper mine register with dated status and conservative production joins.

The register defines the mapped facilities. Production is matched by reviewed
identifiers, never proximity or fuzzy names. Missing data remains missing.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from urllib.parse import urlparse
import calendar
import json
import math
import re
import sqlite3

from ..common.net import get
from .fundamentals import YEARBOOK, worksheets
from .model import ROOT, atomic_csv

REGISTER = 'https://criticalmineralsmap.com/data/sites.json'
DATABASE = 'https://raw.githubusercontent.com/kadoa-org/world-mining-monitor/main/public/data/mining.db'
FIELDS = ['id', 'name', 'country', 'country_en', 'country_zh', 'latitude', 'longitude',
          'status', 'status_asof', 'owners', 'operator', 'production_t', 'production_period',
          'production_basis', 'production_form', 'production_scope', 'reporter', 'status_sources', 'production_source',
          'production_evidence', 'register_source']
FIELDS += ['name_zh', 'owners_zh', 'operator_zh', 'production_scope_zh', 'note_en', 'note_zh',
           'details_sources', 'details_reviewed', 'details_evidence']
# Explicit identity matches; separate shareholders are not separate mines.
PRODUCTION_IDS = {
    'cu-escondida': ['bhp-escondida'], 'cu-collahuasi': ['collahuasi-anglo'],
    'cu-grasberg': ['fcx-grasberg'], 'cu-cobre-panama': ['cobre-panama'],
    'cu-kamoa-kakula': ['kamoa-kakula'], 'cu-buenavista': ['buenavista'],
    'cu-antamina': ['antamina-glencore', 'antamina-teck'], 'cu-cerro-verde': ['fcx-cerro-verde'],
    'cu-morenci': ['fcx-morenci'], 'cu-oyu-tolgoi': ['oyu-tolgoi'],
    'cu-kansanshi': ['kansanshi'], 'cu-olympic-dam': ['bhp-olympic-dam'],
    'cu-kghm-copper-belt': ['kghm-poland'], 'cu-aitik': ['aitik'],
    'cu-neves-corvo': ['somincor'], 'ni-norilsk': ['norilsk'],
    'ni-kevitsa': ['kevitsa'], 'cu-mutanda': ['mutanda'], 'cu-kamoto': ['katanga-kcc'],
    'cu-tenke-fungurume': ['tfm'],
}
STATUSES = {'prod', 'care', 'cons', 'proj', 'ramp', 'stockpile', 'closed', 'suspended'}
FORMS = {None: 'reported', 'concentrate': 'concentrate', 'cathode': 'cathode',
         'metal': 'metal', 'mine-produced': 'metal', 'mined': 'metal'}
UNIT_FACTORS = {'kt': 1000, 'Kt': 1000, '1,000 t': 1000, 'thousand tonnes': 1000,
                'tonnes': 1, 'Tonnes': 1, 't': 1, 'tonne': 1, 'metric tons': 1,
                'Mlbs': 453.59237, 'million pounds': 453.59237,
                'million recoverable pounds': 453.59237, 'millions of recoverable pounds': 453.59237}


def period_end(value, today=None):
    """Accept completed calendar quarters/halves/years; reject ambiguous fiscal years."""
    today = today or date.today()
    match = re.fullmatch(r'(Q[1-4]|H[12]|9M) (20\d{2})', value or '')
    if match:
        label, year = match.groups()
        month = int(label[1]) * (3 if label[0] == 'Q' else 6) if label != '9M' else 9
    else:
        match = re.fullmatch(r'(?:FY)?(20\d{2})', value or '')
        if not match:
            return None
        year, month = match[1], 12
    end = date(int(year), month, calendar.monthrange(int(year), month)[1])
    return end if end < today else None


def production_candidate(row):
    """Require copper output, units, evidence and an elapsed reporting period."""
    if row['commodity'] != 'copper' or row['metric'] != 'production':
        return None
    if row['product_form'] not in FORMS or row['basis'] in {'guidance', 'unknown', 'provisional'}:
        return None
    if not row['source_excerpt'] or not row['source_url'] or (row['confidence'] or 0) < .9:
        return None
    if re.search(r'guidance|forecast|target|capacity', row['source_excerpt'], re.I):
        return None
    # Fiscal quarter labels require an explicit calendar mapping for June-year reporters.
    if row['company'] in {'BHP', 'South32'} and not row['calendar_period']:
        return None
    period = row['calendar_period'] or row['time_period']
    end = period_end(period)
    if end is None or row['unit'] not in UNIT_FACTORS:
        return None
    value = row['value'] * UNIT_FACTORS[row['unit']]
    if not math.isfinite(value) or not 0 <= value <= 2_000_000:
        return None
    # Cross-check provider normalization; original units determine stored precision.
    if row['unit_normalized'] != 'kt' or row['value_normalized'] is None:
        return None
    if abs(row['value_normalized'] * 1000 - value) > max(2, value * .001):
        return None
    basis = 'equity' if row['basis'] in {'attributable', 'equity', 'proportionate'} else 'reported'
    return dict(production_t=round(value, 3), production_period=period,
                production_basis=basis, production_form=FORMS[row['product_form']],
                production_scope=row['operation'], reporter=row['company'], production_source=row['source_url'],
                production_evidence=row['source_excerpt'], end=end)


def select_production(rows):
    candidates = [c for r in rows if (c := production_candidate(r))]
    if not candidates:
        return {}
    # Prefer the latest period, then a whole-operation observation. Do not sum
    # products or shareholders, or silently resolve conflicting duplicate reports.
    latest = max(c['end'] for c in candidates)
    candidates = [c for c in candidates if c['end'] == latest]
    rank = lambda c: (c['production_form'] == 'reported', c['production_basis'] != 'equity',
                      c['production_period'].startswith('Q'))
    best = max(map(rank, candidates))
    candidates = [c for c in candidates if rank(c) == best]
    groups = {(c['production_period'], c['production_basis'], c['production_form'], c['reporter']) for c in candidates}
    if len(groups) != 1:
        return {}
    values = [c['production_t'] for c in candidates]
    if max(values) - min(values) > max(2, max(values) * .001):
        return {}
    chosen = dict(candidates[0]); chosen.pop('end')
    return chosen


def chile_production(content):
    """Official whole-operation annual output overrides shareholder-only observations."""
    wanted = {'Escondida': 'cu-escondida', 'Collahuasi': 'cu-collahuasi',
              'División Chuquicamata': 'cu-chuquicamata', 'División El Teniente': 'cu-el-teniente'}
    result = {}
    for rows in worksheets(content):
        header = ' '.join(r.get('A', '') for r in rows[:6])
        if 'Chilean Copper Production by Mining Operation' not in header:
            continue
        if 'kMT copper content' not in header:
            raise ValueError('Unexpected Chile mine production units')
        years = next(({k: int(v) for k, v in r.items() if re.fullmatch(r'20\d{2}', v)}
                      for r in rows[:10] if sum(bool(re.fullmatch(r'20\d{2}', v)) for v in r.values()) > 10), {})
        column = max(years, key=years.get)
        if years[column] >= date.today().year:
            raise ValueError('Incomplete Chile annual mine data')
        for row in rows:
            name = re.sub(r'\s*\(\d+\)', '', row.get('A', '')).strip()
            if name not in wanted:
                continue
            value = float(row[column]) * 1000
            if not math.isfinite(value) or not 0 <= value <= 2_000_000:
                raise ValueError('Invalid Chile mine production')
            result[wanted[name]] = dict(production_t=round(value, 1), production_period=str(years[column]),
                production_basis='100%', production_form='metal', production_scope=name, reporter='COCHILCO',
                production_source=YEARBOOK, production_evidence=f'Table 2.3: {name}, {years[column]}')
    return result


def build(register, production, countries, chile=None):
    if not isinstance(register.get('curated'), list) or not register.get('generated'):
        raise ValueError('Invalid mine register')
    result, seen = [], set()
    for mine in register['curated']:
        if 'Cu' not in mine['m'] or mine['stage'] != 'mine':
            continue
        ident = mine['id']
        if ident in seen:
            raise ValueError(f'Duplicate mine: {ident}')
        seen.add(ident)
        longitude, latitude = mine['at']
        if not (math.isfinite(latitude) and math.isfinite(longitude) and -90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError(f'Invalid coordinates: {ident}')
        asof = mine['asof']
        if not re.fullmatch(r'\d{4}-\d{2}', asof) or date.fromisoformat(asof + '-01') > date.today():
            raise ValueError(f'Invalid status date: {ident}')
        if mine['status'] not in STATUSES or not mine['src']:
            raise ValueError(f'Invalid status/source: {ident}')
        cc = countries.get(mine['cc'])
        if not cc:
            raise ValueError(f'Unknown country: {mine["cc"]}')
        row = dict(id=ident, name=mine['name'], country=mine['cc'], country_en=cc['NAME_EN'],
                   country_zh=cc['NAME_ZH'], latitude=latitude, longitude=longitude,
                   status=mine['status'], status_asof=asof, owners=mine.get('owners') or '',
                   operator=mine.get('op') or '', register_source=REGISTER,
                   status_sources=json.dumps(mine['src'], ensure_ascii=False))
        ids = PRODUCTION_IDS.get(ident, [])
        row.update(select_production([r for r in production if r['mine_id'] in ids]))
        if chile and ident in chile:
            row.update(chile[ident])
        result.append(row)
    if not result:
        raise ValueError('No copper mines found')
    return sorted(result, key=lambda r: r['name'])


def apply_reviews(rows, reviews):
    """Apply locally reviewed primary evidence without losing it on source refresh.

    Every review is validated before any row is modified. Production observations
    are indivisible bundles, and an older report never overwrites newer output.
    Market observations live in ignored data, not in the application source.
    """
    if not isinstance(reviews, list):
        raise ValueError('Mine reviews must be a list')
    known = {r['id'] for r in rows}
    production = {'production_t', 'production_period', 'production_basis', 'production_form',
                  'production_scope', 'reporter', 'production_source', 'production_evidence'}
    allowed = production | {'name', 'name_zh', 'owners', 'owners_zh', 'operator', 'operator_zh',
                           'production_scope_zh', 'note_en', 'note_zh', 'status', 'status_asof'}
    def url(value):
        parsed = urlparse(value)
        return parsed.scheme in {'http', 'https'} and bool(parsed.netloc)
    seen = set()
    for review in reviews:
        ident = review['id']
        if ident not in known or ident in seen:
            raise ValueError(f'Unknown or duplicate reviewed mine: {ident}')
        seen.add(ident)
        if date.fromisoformat(review['reviewed_on']) > date.today():
            raise ValueError(f'Future mine review: {ident}')
        if (not isinstance(review['sources'], list) or not review['sources']
                or not all(isinstance(s, str) and url(s) for s in review['sources'])
                or not isinstance(review['evidence'], str) or not review['evidence'].strip()):
            raise ValueError(f'Missing review evidence: {ident}')
        update = review['updates']
        if not isinstance(update, dict) or not update or set(update) - allowed:
            raise ValueError(f'Unsupported reviewed fields: {ident}')
        if any(not isinstance(v, str) or not v.strip() for k, v in update.items() if k != 'production_t'):
            raise ValueError(f'Empty reviewed field: {ident}')
        if (set(update) & (production | {'production_scope_zh'})):
            if not production <= set(update):
                raise ValueError(f'Incomplete reviewed production: {ident}')
            value = update['production_t']
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or not 0 <= value <= 2_000_000
                    or period_end(update['production_period']) is None
                    or update['production_basis'] not in {'100%', 'equity', 'reported'}
                    or update['production_form'] not in set(FORMS.values())
                    or update['production_source'] not in review['sources']):
                raise ValueError(f'Invalid reviewed production: {ident}')
        if set(update) & {'status', 'status_asof'}:
            if (update.get('status') not in STATUSES
                    or not re.fullmatch(r'\d{4}-\d{2}', update.get('status_asof', ''))
                    or date.fromisoformat(update['status_asof'] + '-01') > date.today()):
                raise ValueError(f'Invalid reviewed status: {ident}')
    result = {r['id']: dict(r) for r in rows}
    for review in reviews:
        row = result[review['id']]
        update = dict(review['updates'])
        old_end = period_end(row.get('production_period'))
        if 'production_t' in update and old_end and old_end > period_end(update['production_period']):
            update = {k: v for k, v in update.items() if k not in production | {'production_scope_zh'}}
        if 'status' in update and row.get('status_asof', '') > update['status_asof']:
            update.pop('status'); update.pop('status_asof')
        row.update(update)
        row.update(details_sources=json.dumps(review['sources'], ensure_ascii=False),
                   details_reviewed=review['reviewed_on'], details_evidence=review['evidence'])
    return sorted(result.values(), key=lambda r: r['name'])


def download_database(url=DATABASE):
    """Bounded HTTP range requests avoid truncated large-file transfers.

    The ETag and Content-Range checks prevent stitching different upstream versions.
    """
    first = get(url, headers={'Range': 'bytes=0-262143'}, retries=2, timeout=30)
    if first.status_code == 200:
        return first.content
    match = re.fullmatch(r'bytes 0-(\d+)/(\d+)', first.headers.get('Content-Range', ''))
    if first.status_code != 206 or not match:
        raise ValueError('Invalid database range response')
    step, total = int(match[1]) + 1, int(match[2])
    etag = first.headers.get('ETag')
    if len(first.content) != step or not etag or not 0 < total < 100_000_000:
        raise ValueError('Invalid database size or version')
    def part(start):
        end = min(start + step, total) - 1
        response = get(url, headers={'Range': f'bytes={start}-{end}'}, retries=2, timeout=30)
        if (response.status_code != 206 or response.headers.get('ETag') != etag
                or response.headers.get('Content-Range') != f'bytes {start}-{end}/{total}'
                or len(response.content) != end - start + 1):
            raise ValueError('Database changed or download was truncated; retry later')
        return response.content
    with ThreadPoolExecutor(max_workers=4) as pool:
        parts = list(pool.map(part, range(step, total, step)))
    return first.content + b''.join(parts)


def run(data, *, refresh=False):
    raw = data / 'raw' / 'fundamentals'; raw.mkdir(parents=True, exist_ok=True)
    register_path, database_path = raw / 'mine-register.json', raw / 'mining.db'
    register = get(REGISTER, retries=2).json() if refresh or not register_path.exists() else json.loads(register_path.read_text())
    # Deserialize into an in-memory read-only query connection. Never run upstream SQL.
    database = download_database() if refresh or not database_path.exists() else database_path.read_bytes()
    connection = sqlite3.connect(':memory:')
    try:
        connection.deserialize(database)
        connection.execute('PRAGMA query_only=ON')
        connection.row_factory = sqlite3.Row
        if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Invalid production database')
        production = [dict(r) for r in connection.execute("SELECT * FROM production WHERE commodity='copper' AND metric='production'")]
    finally:
        connection.close()
    world = json.loads((ROOT.parent / 'web/static/vendor/world-countries-110m.json').read_text())
    countries = {f['properties']['ADM0_A3']: f['properties'] for f in world['features']}
    book = raw / 'cochilco-2000-2025.xlsx'
    chile = chile_production(book.read_bytes()) if book.exists() else {}
    rows = build(register, production, countries, chile)
    reviews = data / 'manual' / 'mine-details.json'
    if reviews.exists():
        rows = apply_reviews(rows, json.loads(reviews.read_text(encoding='utf-8')))
    if len(rows) < 20:
        raise ValueError('Mine register unexpectedly short')
    # Validate everything before replacing the last good output or its inputs.
    register_path.write_text(json.dumps(register, ensure_ascii=False))
    database_path.write_bytes(database)
    atomic_csv(data / 'out' / 'mines.csv', rows, FIELDS)
    return rows
