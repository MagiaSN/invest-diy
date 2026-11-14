"""Validated observations and same-date comparisons; no implicit forward filling."""

from __future__ import annotations

from datetime import date
import math
from pathlib import Path

from ..common.csvio import read_rows, write_rows

ROOT = Path(__file__).resolve().parent
POUNDS_PER_TONNE = 1000 / 0.45359237
SHORT_TON_TO_TONNE = 0.90718474
SERIES = {
    "cme_price": ("USD/lb", 7),
    "lme_price": ("USD/t", 7),
    "shfe_price": ("CNY/t", 7),
    "cme_stock": ("short ton", 7),
    "lme_stock": ("t", 7),
    "shfe_stock": ("t", 14),
    "usdcny": ("CNY/USD", 7),
}
FIELDS = ["series", "date", "value", "unit", "source"]


def observation(series, day, value, source, unit=None):
    if series not in SERIES:
        raise ValueError(f"Unknown series: {series}")
    day = date.fromisoformat(str(day)).isoformat()
    if day > date.today().isoformat():
        raise ValueError(f"Future observation: {day}")
    value = float(value)
    if not math.isfinite(value) or value < 0 or (value == 0 and not series.endswith('_stock')):
        raise ValueError(f"Invalid {series} value: {value}")
    expected = SERIES[series][0]
    if unit is not None and unit != expected:
        raise ValueError(f"{series}: expected {expected}, got {unit}")
    if not str(source).strip():
        raise ValueError("Source is required")
    return dict(series=series, date=day, value=value, unit=expected, source=str(source))


def validate(rows):
    result = {}
    for row in rows:
        r = observation(row['series'], row['date'], row['value'], row['source'], row['unit'])
        key = (r['series'], r['date'])
        if key in result and result[key] != r:
            raise ValueError(f"Conflicting duplicate: {key}")
        result[key] = r
    return list(result.values())


def merge(old, new):
    """New observations revise matching dates without deleting earlier history."""
    result = {(r['series'], r['date']): r for r in validate(old)}
    result.update({(r['series'], r['date']): r for r in validate(new)})
    return sorted(result.values(), key=lambda r: (r['series'], r['date']))


def atomic_csv(path, rows, fields):
    tmp = path.with_suffix('.tmp')
    write_rows(tmp, rows, fields)
    tmp.replace(path)


def vat_rate(day):
    if day >= '2019-04-01':
        return 0.13
    if day >= '2018-05-01':
        return 0.16
    return 0.17


def compute(rows):
    """Keep the union of dates, leaving unavailable cells blank."""
    days = {}
    for r in validate(rows):
        days.setdefault(r['date'], {})[r['series']] = r['value']
    result = []
    for day, values in sorted(days.items()):
        out = {'date': day, 'vat_rate': vat_rate(day), **values}
        if 'cme_price' in values:
            out['cme_usd_t'] = values['cme_price'] * POUNDS_PER_TONNE
        if 'lme_price' in values:
            out['lme_usd_t'] = values['lme_price']
        if 'shfe_price' in values and 'usdcny' in values:
            out['shfe_gross_usd_t'] = values['shfe_price'] / values['usdcny']
            out['shfe_net_usd_t'] = out['shfe_gross_usd_t'] / (1 + out['vat_rate'])
        for exchange in ('cme', 'lme', 'shfe'):
            if f'{exchange}_stock' in values:
                out[f'{exchange}_stock_t'] = values[f'{exchange}_stock'] * (SHORT_TON_TO_TONNE if exchange == 'cme' else 1)
        stock_keys = ('cme_stock_t', 'lme_stock_t', 'shfe_stock_t')
        if all(key in out for key in stock_keys):
            out['total_stock_t'] = sum(out[key] for key in stock_keys)
        for basis in ('net', 'gross'):
            prices = {'cme': out.get('cme_usd_t'), 'lme': out.get('lme_usd_t'), 'shfe': out.get(f'shfe_{basis}_usd_t')}
            for left, right in (('cme', 'lme'), ('shfe', 'lme'), ('shfe', 'cme')):
                a, b = prices[left], prices[right]
                if a is not None and b is not None:
                    stem = f'{left}_{right}_{basis}'
                    out[f'{stem}_spread'] = a - b
                    out[f'{stem}_pct'] = (a / b - 1) * 100
        result.append(out)
    return result


DAILY_FIELDS = ['date', 'vat_rate', *SERIES, 'cme_usd_t', 'lme_usd_t', 'shfe_gross_usd_t', 'shfe_net_usd_t',
                'cme_stock_t', 'lme_stock_t', 'shfe_stock_t', 'total_stock_t'] + [
    f'{pair}_{basis}_{metric}' for basis in ('net', 'gross')
    for pair in ('cme_lme', 'shfe_lme', 'shfe_cme') for metric in ('spread', 'pct')]


def export(data_dir=ROOT / 'data'):
    rows = validate(read_rows(data_dir / 'history.csv'))
    daily = compute(rows)
    out = data_dir / 'out'
    atomic_csv(out / 'observations.csv', rows, FIELDS)
    atomic_csv(out / 'daily.csv', daily, DAILY_FIELDS)
    latest = {s: max((r['date'] for r in rows if r['series'] == s), default='') for s in SERIES}
    # Do not advertise the newest price as the freshness of the whole dashboard.
    as_of = min(latest.values()) if all(latest.values()) else ''
    atomic_csv(out / 'summary.csv', [{'as_of': as_of, 'latest_date': max(latest.values(), default='')}], ['as_of', 'latest_date'])
    return daily
