"""Directly reported primary/secondary refined copper, kept on ICSG's basis."""

from datetime import date
from io import BytesIO
import calendar
import re

import pdfplumber

from ..common.net import get, ensure_resolvable
from .model import atomic_csv

TABLE = 'https://icsg.org/wp-content/uploads/Table1.pdf'
SOURCES = [
    ('2023-01', 'https://icsg.org/download/2023-01-20-monthly-press-release/'
     '?wpdmdl=7398&ind=63cabc463a349&filename=2023-01-20-Monthly-Press-Release.pdf', '2023-01'),
    ('current', TABLE, None),
]
FIELDS = ['year', 'primary_refined_t', 'secondary_refined_t', 'total_refined_t',
          'secondary_share_pct', 'publication', 'source']


def parse_table(text, source, publication=None):
    """Read only the four annual columns, never year-to-date/monthly figures."""
    if (not any(title in text for title in ['WORLD REFINED COPPER PRODUCTION AND USAGE TRENDS',
                                          'World Refined Copper Usage and Supply Trends'])
            or not re.search(r'Thousand metric tonnes,\s*copper', text)):
        raise ValueError('Unexpected ICSG table or units')
    header = text.split('World Copper Mine Production')[0]
    match = re.search(r'(?m)^((?:20\d{2}\s+(?:p/\s*)?){4})', header)
    if not match:
        raise ValueError('Missing four annual ICSG columns')
    years = list(map(int, re.findall(r'20\d{2}', match[1])))
    if years != list(range(years[0], years[0] + 4)) or years[-1] >= date.today().year:
        raise ValueError('Noncontiguous or incomplete ICSG annual years')
    if publication is None:
        issue = re.search(r'ICSG Copper Bulletin\s*-\s*([A-Za-z]+)\s+(20\d{2})', text)
        if not issue or issue[1] not in calendar.month_name:
            raise ValueError('Missing ICSG publication date')
        publication = f'{issue[2]}-{list(calendar.month_name).index(issue[1]):02d}'
    if (date.fromisoformat(publication + '-01') > date.today()
            or int(publication[:4]) <= years[-1]):
        raise ValueError('Invalid ICSG publication date')
    def values(label):
        # Some PDF producers put the product qualifier on a separate line.
        pattern = re.escape(label) + r'\s*(?:\(Primary\s*&\s*Secondary\)\s*)?((?:\d[\d,]*\s+){3}\d[\d,]*)(?=\s|$)'
        matches = re.findall(pattern, text)
        if len(matches) != 1:
            raise ValueError(f'Missing or ambiguous ICSG row: {label}')
        return [int(v.replace(',', '')) * 1000 for v in matches[0].split()]
    primary = values('Primary Refined Copper Production')
    secondary = values('Secondary Refined Copper Production')
    total = values('World Refined Copper Production')
    rows = []
    for year, p, s, t in zip(years, primary, secondary, total):
        if not (1_000_000 <= p <= 50_000_000 and 0 < s < t <= 60_000_000
                and abs(p + s - t) <= 2000):
            raise ValueError(f'Invalid ICSG refining components: {year}')
        rows.append(dict(year=year, primary_refined_t=p, secondary_refined_t=s, total_refined_t=t,
                         secondary_share_pct=round(s / t * 100, 3), publication=publication, source=source))
    return rows


def parse_pdf(content, source, publication=None):
    with pdfplumber.open(BytesIO(content)) as pdf:
        tables = [text for page in pdf.pages if 'Secondary Refined Copper Production' in (text := page.extract_text() or '')]
    if len(tables) != 1:
        raise ValueError('Expected one ICSG refining table')
    return parse_table(tables[0], source, publication)


def merge_editions(editions):
    """Keep the latest publication for each full-year observation as a bundle."""
    result = {}
    for rows in editions:
        for row in rows:
            old = result.get(row['year'])
            if old and old['publication'] == row['publication'] and old != row:
                raise ValueError('Conflicting ICSG observations in the same edition')
            if not old or row['publication'] > old['publication']:
                result[row['year']] = row
    return sorted(result.values(), key=lambda r: r['year'])


def run(data, *, refresh=False):
    raw = data / 'raw' / 'fundamentals' / 'icsg'
    editions, pending = [], []
    for name, url, publication in SOURCES:
        path = raw / f'{name}.pdf'
        if refresh or not path.exists():
            ensure_resolvable('icsg.org')
            content = get(url, retries=1, timeout=30).content
        else:
            content = path.read_bytes()
        editions.append(parse_pdf(content, url, publication))
        pending.append((path, content))
    current_publication = editions[-1][0]['publication']
    # The rolling table drops old annual columns. Retain every accepted edition
    # so later refreshes cannot erase years that leave that rolling window.
    for path in sorted(raw.glob('table-*.pdf')):
        if path.name != f'table-{current_publication}.pdf':
            editions.append(parse_pdf(path.read_bytes(), TABLE))
    rows = merge_editions(editions)
    raw.mkdir(parents=True, exist_ok=True)
    # Validate every edition before replacing the output or any good source cache.
    for path, content in pending:
        path.write_bytes(content)
    (raw / f'table-{current_publication}.pdf').write_bytes(pending[-1][1])
    atomic_csv(data / 'out' / 'refining.csv', rows, FIELDS)
    return rows
