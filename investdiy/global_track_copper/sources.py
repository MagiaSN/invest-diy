"""Validated stock reports and daily FX; keep native dates and provenance."""

from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
import io
import json
import math
import re

import requests

from ..common import net
from .model import atomic_csv, observation, validate

WEST = 'https://www.westmetall.com/en/markdaten.php?action=table&field=LME_Cu_stock'
SHFE = 'https://www.shfe.com.cn/data/tradedata/future/stockdata/weeklystock_{day}/ZH/all.html'
ECB = 'https://data-api.ecb.europa.eu/service/data/EXR/D.CNY+USD.EUR.SP00.A'
METALCHARTS = 'https://metalcharts.org/comex/copper'
MC_API = 'https://metalcharts.org/api/comex/inventory?symbol=HG&range=1Y'
# Earlier chart rows have inconsistent dates/totals, even with components.
# The interval from this date was corroborated against the 99qh history.
MC_VERIFIED_FROM = '2026-06-12'


class TableRows(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.rows, self.row, self.cell = [], None, None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.row = []
        elif tag in ('td', 'th') and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split()))
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def number(value):
    value = float(str(value).replace(',', '').strip())
    if not math.isfinite(value) or value < 0:
        raise ValueError('Invalid nonnegative report value')
    return value


def parse_west(text, year):
    table = TableRows(text).rows
    if not any(r[:2] == ['date', 'LME Copper stock'] for r in table):
        raise ValueError('Westmetall copper stock column missing')
    rows = []
    for r in table:
        if len(r) != 4 or not re.fullmatch(r'\d{1,2}\. [A-Za-z]+ \d{4}', r[0]):
            continue
        day = datetime.strptime(r[0], '%d. %B %Y').date()
        if day.year != year:
            raise ValueError('Westmetall year mismatch')
        rows.append(observation('lme_stock', day, number(r[1]), f'{WEST}&year={year}'))
    return validate(rows)


def parse_shfe(text, day):
    table = TableRows(text).rows
    if not table or not table[0] or not table[0][0].startswith(day + ' '):
        raise ValueError('SHFE report date mismatch')
    if '本周库存' not in text or '小计' not in text or '期货' not in text:
        raise ValueError('SHFE weekly inventory columns missing')
    copper, totals = False, {}
    for r in table:
        if any('单位：' in c for c in r):
            if copper:
                break
            copper = r == ['铜', '单位：吨']
        elif copper and r and r[0] in ('保税商品总计', '完税商品总计', '总计'):
            if len(r) != 10 or r[0] in totals:
                raise ValueError('SHFE stock total layout changed')
            # Current subtotal (index 3) includes warranted and unwarranted stock.
            # Index 4 is warranted stock, not total inventory.
            total, warranted = number(r[3]), number(r[4])
            if warranted > total:
                raise ValueError('SHFE warrants exceed total stock')
            if abs(number(r[1]) + float(r[5].replace(',', '')) - total) > .01:
                raise ValueError('SHFE weekly stock change does not reconcile')
            totals[r[0]] = total
    if set(totals) != {'保税商品总计', '完税商品总计', '总计'}:
        raise ValueError('SHFE copper grand total or components missing')
    if abs(totals['总计'] - totals['完税商品总计'] - totals['保税商品总计']) > .01:
        raise ValueError('SHFE bonded/duty-paid stocks do not reconcile')
    return observation('shfe_stock', day, totals['总计'], SHFE.format(day=day.replace('-', '')))


def parse_ecb(text):
    rates = {}
    for row in csv.DictReader(io.StringIO(text)):
        currency = row['CURRENCY']
        if (currency not in ('CNY', 'USD') or row['CURRENCY_DENOM'] != 'EUR'
                or row['FREQ'] != 'D' or row['EXR_TYPE'] != 'SP00' or row['EXR_SUFFIX'] != 'A'):
            raise ValueError('Unexpected ECB exchange rate series')
        if row['OBS_VALUE'] in ('', 'NaN'):
            continue
        value = number(row['OBS_VALUE'])
        if value == 0:
            raise ValueError('Zero ECB reference rate')
        key = (row['TIME_PERIOD'], currency)
        if key in rates and rates[key] != value:
            raise ValueError('Conflicting ECB observation')
        rates[key] = value
    return [observation('usdcny', day, rates[day, 'CNY'] / rates[day, 'USD'], ECB)
            for day in sorted({key[0] for key in rates})
            if (day, 'CNY') in rates and (day, 'USD') in rates]


def parse_metalcharts(text):
    data = json.loads(text)
    if data.get('success') is not True or data.get('symbol') != 'HG' or data.get('count') != len(data['data']):
        raise ValueError('Unexpected MetalCharts copper payload')
    rows, rejected = [], []
    for r in data['data']:
        reason = ''
        try:
            day = date.fromisoformat(r['date'])
            if day.isoformat() < MC_VERIFIED_FROM:
                raise ValueError('Unverified historical date alignment')
            if day.weekday() > 4:
                raise ValueError('Weekend report date')
            total, registered, eligible = (number(r[k]) for k in ('total', 'registered', 'eligible'))
            if total == 0 or abs(total - registered - eligible) > 1:
                raise ValueError('Registered plus eligible does not reconcile')
            rows.append(observation('cme_stock', day, total, METALCHARTS))
        except (ValueError, TypeError, KeyError) as exc:
            reason = str(exc)
        if reason:
            rejected.append(dict(date=r.get('date', ''), value=r.get('total', ''), reason=reason))
    return validate(rows), rejected


def save_raw(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(text, encoding='utf-8')
    tmp.replace(path)


def fetch_west(start, data_dir):
    rows = []
    for year in range(date.fromisoformat(start).year, date.today().year + 1):
        path = data_dir / 'raw' / f'lme-stock-{year}.html'
        text = path.read_text() if path.exists() and year < date.today().year else net.get(f'{WEST}&year={year}').text
        parsed = parse_west(text, year)
        if not parsed:
            raise ValueError(f'Empty Westmetall stock table: {year}')
        rows.extend(parsed)
        save_raw(path, text)
    return [r for r in rows if r['date'] >= start], ''


def fetch_ecb(start, data_dir):
    text = net.get(ECB, params={'startPeriod': start, 'endPeriod': date.today().isoformat(), 'format': 'csvdata'}, timeout=45).text
    rows = parse_ecb(text)
    if not rows:
        raise ValueError('Empty ECB paired reference rates')
    save_raw(data_dir / 'raw' / 'usdcny.csv', text)
    return rows, ''


def fetch_shfe(start, data_dir, trading_dates):
    # A shortened trading week may end on Monday, Wednesday or Thursday.
    # Also try Fridays so an outage in the price source cannot suppress reports.
    last_by_week = {}
    today = date.today()
    for value in trading_dates:
        day = date.fromisoformat(value)
        if start <= value <= today.isoformat():
            week = day.isocalendar()[:2]
            last_by_week[week] = max(value, last_by_week.get(week, value))
    candidates = set(last_by_week.values())
    day = date.fromisoformat(start)
    while day <= today:
        if day.weekday() == 4:
            candidates.add(day.isoformat())
        day += timedelta(days=1)
    missing_path = data_dir / 'raw' / 'shfe-missing.json'
    missing = json.loads(missing_path.read_text()) if missing_path.exists() else {}

    def get_report(day):
        path = data_dir / 'raw' / 'shfe' / f'{day}.html'
        # Retry unavailable archives weekly; recent reports may appear later today.
        if day in missing and (today - date.fromisoformat(missing[day])).days < 7 and day < (today - timedelta(days=7)).isoformat():
            return day, None, ''
        try:
            text = path.read_text() if path.exists() and day < (today - timedelta(days=14)).isoformat() else None
            if text is None:
                url = SHFE.format(day=day.replace('-', ''))
                try:
                    response = net.get(url, retries=1, timeout=20)
                except (requests.Timeout, requests.ConnectionError):
                    response = net.get(url, retries=1, timeout=20)
                response.encoding = 'utf-8'
                text = response.text
            row = parse_shfe(text, day)
            save_raw(path, text)
            return day, row, ''
        except requests.HTTPError as exc:
            if exc.response.status_code == 404:
                return day, None, ''
            return day, None, str(exc)
        except Exception as exc:
            return day, None, str(exc)

    rows, errors = [], []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for index, (day, row, error) in enumerate(pool.map(get_report, sorted(candidates)), 1):
            if row:
                rows.append(row)
                missing.pop(day, None)
            elif error:
                errors.append(f'{day}: {error}')
            else:
                missing.setdefault(day, today.isoformat())
                # Refresh the negative-cache timestamp after a weekly retry.
                if (today - date.fromisoformat(missing[day])).days >= 7:
                    missing[day] = today.isoformat()
            if index % 50 == 0:
                print(f'SHFE archive: checked {index}/{len(candidates)} reports through {day}; {len(rows)} valid', flush=True)
    save_raw(missing_path, json.dumps(missing, indent=2))
    if not rows:
        raise ValueError('No valid official SHFE weekly reports; ' + '; '.join(errors[:3]))
    return rows, f'{len(errors)} failed SHFE reports: ' + '; '.join(errors[:3]) if errors else ''


def metalcharts_browser():
    """Observe the public chart's normal request, without login or private APIs."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError('COMEX extension needs optional Playwright: pip install playwright; python -m playwright install chromium') from exc
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            with page.expect_response(lambda r: r.url == MC_API and r.status == 200, timeout=45000) as pending:
                page.goto(METALCHARTS, wait_until='domcontentloaded', timeout=45000)
            return pending.value.text()
        finally:
            browser.close()


def extend_comex(primary, text, data_dir):
    candidates, rejected = parse_metalcharts(text)
    known = {r['date']: r for r in primary}
    for row in candidates:
        old = known.get(row['date'])
        if old:
            if abs(float(old['value']) - row['value']) > 1:
                rejected.append(dict(date=row['date'], value=row['value'], reason='Conflicts with primary inventory'))
        else:
            known[row['date']] = row
    atomic_csv(data_dir / 'raw' / 'comex-rejected.csv', rejected, ['date', 'value', 'reason'])
    save_raw(data_dir / 'raw' / 'comex-metalcharts.json', text)
    return validate(list(known.values()))
