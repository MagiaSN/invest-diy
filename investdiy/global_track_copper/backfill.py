"""Fill historical stock gaps from COCHILCO without revising verified history."""

from calendar import month_name
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
import math
import re

from ..common import net
from ..common.csvio import read_rows
from .model import FIELDS, ROOT, SHORT_TON_TO_TONNE, atomic_csv, merge, observation, validate
from .sources import TableRows, save_raw

URL = 'https://boletin.cochilco.cl/productos/boletin.asp'
AUDIT_FIELDS = ['series', 'date', 'value_t', 'existing_t', 'decision', 'reason', 'source']


def report_url(year, month):
    return f'{URL}?anio={year}&mes={month:02}&tabla=tabla4_2'


def report_number(text):
    if text.strip().lower() in ('', '-', 'feriado'):
        return None
    # Spanish formatting: dots group thousands; commas separate decimals.
    if not re.fullmatch(r'(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?', text):
        raise ValueError(f'Unexpected COCHILCO number: {text!r}')
    value = float(text.replace('.', '').replace(',', '.'))
    if not math.isfinite(value):
        raise ValueError('Nonfinite COCHILCO number')
    return value


def parse_report(text, year, month):
    table = TableRows(text).rows
    if (not any(f'{month_name[month]} {year}' in r for r in table)
            or ['TABLA / TABLE 4.2'] not in table or ['(TM / MT)'] not in table
            or not any(r[1:4] == ['BML/LME', 'COMEX', 'SHFE'] for r in table)):
        raise ValueError('COCHILCO report month, stock columns or metric-tonne unit mismatch')
    rows = {}
    for r in table:
        if not r or not r[0].isdigit():
            continue
        if len(r) != 12:
            raise ValueError('COCHILCO daily stock layout changed')
        values = dict(zip(('lme', 'cme', 'shfe', 'total'), (report_number(r[i]) for i in (4, 6, 8, 10))))
        if all(v is None for v in values.values()):
            continue  # Includes unused day 31 cells in short months.
        day = date(year, month, int(r[0]))
        if day.weekday() > 4 or day > date.today():
            raise ValueError(f'Unexpected COCHILCO observation date: {day}')
        if all(v is not None for v in values.values()) and abs(values['total'] - sum(values[k] for k in ('lme', 'cme', 'shfe'))) > 2:
            raise ValueError(f'COCHILCO components do not reconcile: {day}')
        row = dict(date=day.isoformat(), **values, source=report_url(year, month))
        if row['date'] in rows and rows[row['date']] != row:
            raise ValueError(f'Conflicting COCHILCO daily rows: {day}')
        rows[row['date']] = row
    if not rows:
        raise ValueError('Empty COCHILCO stock report')
    return list(rows.values())


def weekly_dates(history):
    """Use the established SHFE trading calendar, including shortened weeks."""
    weeks = {}
    for r in history:
        if r['series'] != 'shfe_price':
            continue
        week = date.fromisoformat(r['date']).isocalendar()[:2]
        weeks[week] = max(weeks.get(week, ''), r['date'])
    return set(weeks.values())


def select_additions(history, reports, start, end):
    history = validate(history)
    known = {(r['series'], r['date']): r for r in history}
    weekly = weekly_dates(history)
    additions, audit = [], []
    for market in ('cme', 'shfe'):
        series = f'{market}_stock'
        factor = SHORT_TON_TO_TONNE if market == 'cme' else 1
        candidates = sorted((r for r in reports if r[market] is not None
                             and (market != 'shfe' or r['date'] in weekly)), key=lambda r: r['date'])
        for i, r in enumerate(candidates):
            if not start <= r['date'] <= end:
                continue
            value = r[market]
            old = known.get((series, r['date']))
            old_t = old['value'] * factor if old else None
            decision, reason = 'added', ''
            if old:
                decision = 'retained'
                reason = 'Agrees within source rounding' if abs(value - old_t) <= 1 else 'Conflicting source; existing history retained'
            elif value <= 0:
                decision, reason = 'quarantined', 'Unverified zero inventory'
            elif 0 < i < len(candidates) - 1:
                before, after = candidates[i - 1], candidates[i + 1]
                lo, hi = sorted((before[market], after[market]))
                span = (date.fromisoformat(after['date']) - date.fromisoformat(before['date'])).days
                # An isolated spike/drop needs independent verification. This
                # conservative screen never alters an existing observation.
                if lo > 0 and hi / lo < 1.15 and span <= (21 if market == 'shfe' else 7) and (value < lo * .7 or value > hi * 1.3):
                    decision, reason = 'quarantined', 'Isolated inventory jump; needs independent verification'
            if decision == 'added':
                additions.append(observation(series, r['date'], value / factor, r['source']))
            audit.append(dict(series=series, date=r['date'], value_t=value,
                              existing_t=old_t if old else '', decision=decision, reason=reason, source=r['source']))
    return validate(additions), audit


def run(start, data_dir=ROOT / 'data'):
    history = read_rows(data_dir / 'history.csv')
    if not weekly_dates(history):
        raise ValueError('Fetch SHFE prices first to establish weekly report dates')
    end = (date.today().replace(day=1) - timedelta(days=1)).isoformat()
    cursor = date.fromisoformat(start).replace(day=1)
    months = []
    while cursor.isoformat() <= end:
        months.append((cursor.year, cursor.month))
        cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
    if not months:
        raise ValueError('Backfill requires at least one completed month')

    def get_month(ym):
        year, month = ym
        path = data_dir / 'raw' / 'cochilco' / f'{year}-{month:02}.html'
        try:
            text = path.read_text() if path.exists() else net.get(report_url(year, month), timeout=25, retries=2).text
            rows = parse_report(text, year, month)
            save_raw(path, text)
            return rows, ''
        except Exception as exc:
            return [], f'{year}-{month:02}: {exc}'

    reports, errors = [], []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for i, (rows, error) in enumerate(pool.map(get_month, months), 1):
            reports.extend(rows)
            if error:
                errors.append(error)
            if i % 12 == 0:
                print(f'COCHILCO: {i}/{len(months)} monthly reports checked', flush=True)
    additions, audit = select_additions(history, reports, start, end)
    merged = merge(history, additions)
    if additions:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        atomic_csv(data_dir / 'backups' / f'history-before-backfill-{stamp}.csv', history, FIELDS)
        atomic_csv(data_dir / 'history.csv', merged, FIELDS)
    atomic_csv(data_dir / 'out' / 'backfill-audit.csv', audit, AUDIT_FIELDS)
    status = dict(start=start, end=end, attempted_at=datetime.now(timezone.utc).isoformat(timespec='seconds'),
                  months_requested=len(months), months_loaded=len(months) - len(errors), added=len(additions),
                  quarantined=sum(r['decision'] == 'quarantined' for r in audit),
                  conflicts=sum(r['reason'].startswith('Conflicting') for r in audit), errors='; '.join(errors))
    atomic_csv(data_dir / 'out' / 'backfill-status.csv', [status], list(status))
    for series in ('cme_stock', 'shfe_stock'):
        print(f"{series}: added {sum(r['series'] == series for r in additions)} historical observations", flush=True)
    if errors:
        print('COCHILCO incomplete: ' + '; '.join(errors), flush=True)
    return status
