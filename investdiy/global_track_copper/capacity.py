"""Annual copper mine capacity events from an explicitly incomplete reviewed register.

Disabled in the dashboard and normal updates: a complete global source for all
three annual event series has not been verified. Retained for offline review only.
Capacity is whole-project annual copper metal capacity, not ore throughput,
Cu-equivalent output, actual production, or shareholder-attributable capacity.
"""

from datetime import date
import hashlib
import json
import math
from urllib.parse import urlparse

from .model import atomic_csv

KINDS = {'retired': 'permanent_closure', 'commissioned': 'first_production',
         'started': 'physical_construction_start'}
EVENT_FIELDS = ['id', 'project_id', 'year', 'kind', 'milestone', 'project_en', 'project_zh',
                'country_en', 'country_zh', 'capacity_tpa', 'basis', 'scope',
                'note_en', 'note_zh', 'event_source', 'capacity_source',
                'event_evidence', 'capacity_evidence', 'as_of', 'dataset_id']
ANNUAL_FIELDS = ['year', 'as_of', 'partial_year', 'dataset_id'] + [
    f'{kind}_{suffix}' for kind in KINDS for suffix in ['tpa', 'count', 'unknown']]


def validate(payload, today=None):
    today = today or date.today()
    if (payload.get('schema') != 1 or payload.get('unit') != 't Cu/year'
            or payload.get('coverage') != 'reviewed-projects-not-global-total'):
        raise ValueError('Unexpected capacity event schema, units or coverage')
    as_of = date.fromisoformat(payload['as_of'])
    start = payload['start_year']
    if as_of > today or type(start) is not int or not 2000 <= start <= as_of.year:
        raise ValueError('Invalid capacity event review period')
    dataset_id = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
    seen, milestones, rows = set(), {}, []
    for event in payload['events']:
        r = dict(event)
        key = (r['project_id'], r['kind'])
        if r['id'] in seen or key in milestones:
            raise ValueError('Duplicate project-phase event')
        seen.add(r['id']); milestones[key] = r['year']
        if (r['kind'] not in KINDS or r['milestone'] != KINDS[r['kind']]
                or type(r['year']) is not int or not start <= r['year'] <= as_of.year):
            raise ValueError('Not a confirmed, elapsed capacity event')
        if r['scope'] not in {'whole_project', 'incremental_phase'} or r.get('ownership_basis') != '100%':
            raise ValueError('Capacity must be whole-project or incremental phase, on a 100% basis')
        for field in ['id', 'project_id', 'project_en', 'project_zh', 'country_en', 'country_zh',
                      'event_evidence', 'capacity_evidence', 'note_en', 'note_zh']:
            if not isinstance(r.get(field), str) or not r[field].strip():
                raise ValueError(f'Missing capacity event field: {field}')
        for field in ['event_source', 'capacity_source']:
            u = urlparse(r[field])
            if u.scheme not in {'https', 'http'} or not u.netloc:
                raise ValueError(f'Invalid source URL: {field}')
        value = r['capacity_tpa']
        if value is None:
            if r['basis'] != 'unquantified':
                raise ValueError('Missing capacity needs an explicit unquantified basis')
        elif (type(value) not in {float, int} or not math.isfinite(value)
              or not 0 < value <= 2_000_000 or r['basis'] not in {'design', 'official_estimate'}):
            raise ValueError('Invalid copper capacity or basis')
        before, after = r.get('before_tpa'), r.get('after_tpa')
        if before is not None or after is not None:
            if (r['scope'] != 'incremental_phase' or value is None
                    or any(type(v) not in {float, int} or not math.isfinite(v) or v < 0 for v in [before, after])
                    or abs(after - before - value) > .01):
                raise ValueError('Expansion must be the incremental difference, not total site capacity')
        r.update(as_of=as_of.isoformat(), dataset_id=dataset_id)
        rows.append({k: r[k] for k in EVENT_FIELDS})
    if not rows:
        raise ValueError('Empty capacity event register')
    for project, kind in milestones:
        if kind == 'started' and (project, 'commissioned') in milestones:
            if milestones[(project, kind)] > milestones[(project, 'commissioned')]:
                raise ValueError('Construction cannot follow first production of the same phase')
    return sorted(rows, key=lambda r: (r['year'], r['kind'], r['id'])), start, as_of


def aggregate(events, start, as_of):
    """Zero means no event in this sample; unquantified events never become zero."""
    rows = []
    for year in range(start, as_of.year + 1):
        r = dict(year=year, as_of=as_of.isoformat(), partial_year=int(date(year, 12, 31) > as_of),
                 dataset_id=events[0]['dataset_id'])
        for kind in KINDS:
            selected = [e for e in events if e['year'] == year and e['kind'] == kind]
            known = [e['capacity_tpa'] for e in selected if e['capacity_tpa'] is not None]
            unknown = len(selected) - len(known)
            r.update({f'{kind}_tpa': sum(known) if known or not selected else None,
                      f'{kind}_count': len(selected), f'{kind}_unknown': unknown})
        rows.append(r)
    return rows


def run(data, *, refresh=False):
    # Reviews are manual; a refresh revalidates evidence without claiming new coverage.
    path = data / 'manual' / 'copper-capacity-events.json'
    events, start, as_of = validate(json.loads(path.read_text(encoding='utf-8')))
    rows = aggregate(events, start, as_of)
    # Both outputs carry the same content digest; readers reject mismatched generations.
    atomic_csv(data / 'out' / 'capacity-events.csv', events, EVENT_FIELDS)
    atomic_csv(data / 'out' / 'capacity-annual.csv', rows, ANNUAL_FIELDS)
    return rows
