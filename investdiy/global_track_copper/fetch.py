"""Public price references, validated exchange stocks and daily ECB FX.

Sina labels its LME quote a CFD reference. Never describe it as an official
exchange settlement. Upstream snapshots remain local for inspection.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import re

from ..common import net
from ..common.csvio import read_rows
from .model import ROOT, FIELDS, SERIES, atomic_csv, merge, observation
from . import sources

SINA = 'https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_copper=/'
FED = 'https://www.federalreserve.gov/releases/h10/hist/dat00_ch.htm'
URLS = {
    'cme_price': 'https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=101.HG00Y&klt=101&fqt=0&lmt=10000&end=20500000&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56',
    'lme_price': SINA + 'GlobalFuturesService.getGlobalFuturesDailyKLine?symbol=CAD',
    'shfe_price': SINA + 'InnerFuturesNewService.getDailyKLine?symbol=CU0',
    'cme_stock': 'https://www.99qh.com/data/stockOut?productId=100',
    'lme_stock': sources.WEST,
    'shfe_stock': sources.SHFE,
    'usdcny': sources.ECB,
}
OLD_SHFE = 'https://www.99qh.com/data/stockIn?productId=1'
STATUS_FIELDS = ['series', 'attempted_at', 'status', 'rows', 'latest_date', 'source_url', 'detail']


def parse_cme(text):
    data = json.loads(text)['data']
    if data['code'] != 'HG00Y' or data['market'] != 101:
        raise ValueError('Unexpected COMEX contract')
    today = datetime.now(timezone.utc).date().isoformat()
    rows = []
    for bar in data['klines']:
        day, _open, close, *_rest = bar.split(',')
        if day < today:
            rows.append(observation('cme_price', day, close, URLS['cme_price']))
    return rows


def parse_sina(text, series):
    match = re.search(r'=\s*\((\[.*\])\)\s*;', text, re.S)
    if not match:
        raise ValueError('Missing Sina JSONP array')
    rows = json.loads(match[1])
    day_key, close_key = ('d', 'c') if series == 'shfe_price' else ('date', 'close')
    # Only completed prior calendar dates: an intraday bar is not a daily close.
    today = datetime.now(timezone.utc).date().isoformat()
    return [observation(series, r[day_key], r[close_key], URLS[series])
            for r in rows if r[day_key] < today]


def parse_inventory(text, series):
    if series != 'cme_stock':
        raise ValueError('The 99qh SHFE column is warrants, not total inventory')
    match = re.search(r'<script\b[^>]*\bid="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.S)
    if not match:
        raise ValueError('Missing 99qh data payload')
    data = json.loads(match[1])['props']['pageProps']['data']
    product, unit = 100, '短吨'
    if int(data['defaultVariety']) != product or data['defaultVarietyUnit'] != unit:
        raise ValueError('Inventory product or unit mismatch')
    rows, skipped = [], 0
    for day, _price, value in data['positionTrendChartListData']['list']:
        # This mirror has emitted runs of zero placeholders for COMEX totals.
        # Exclude unverified zeros, while explicit CSV imports may contain zero.
        if value is None or str(value).strip() in ('', '-', '--') or float(value) == 0:
            skipped += 1
            continue
        rows.append(observation(series, day, value, URLS[series]))
    return rows, skipped


def fetch_one(series, start, data_dir):
    if series == 'lme_stock':
        return sources.fetch_west(start, data_dir)
    if series == 'usdcny':
        return sources.fetch_ecb(start, data_dir)
    if series == 'shfe_stock':
        trading_dates = [r['date'] for r in read_rows(data_dir / 'history.csv') if r['series'] == 'shfe_price']
        try:
            text = net.get(URLS['shfe_price'], retries=2, timeout=25).text
            trading_dates.extend(r['date'] for r in parse_sina(text, 'shfe_price'))
        except Exception:
            if not trading_dates:
                raise
        return sources.fetch_shfe(start, data_dir, trading_dates)
    if series == 'cme_stock':
        rows = [r for r in read_rows(data_dir / 'history.csv')
                if r['series'] == series and r['source'] == URLS[series]]
        warnings = []
        try:
            text = net.get(URLS[series], retries=2, timeout=25).text
            fresh, skipped = parse_inventory(text, series)
            rows = merge(rows, fresh)
            sources.save_raw(data_dir / 'raw' / 'cme_stock.txt', text)
            if skipped:
                warnings.append(f'Excluded {skipped} zero/missing primary observations')
        except Exception as exc:
            warnings.append(f'Primary: {exc}')
        try:
            rows = sources.extend_comex(rows, sources.metalcharts_browser(), data_dir)
        except Exception as exc:
            warnings.append(f'Public chart: {exc}')
        rows = [r for r in rows if r['date'] >= start]
        if not rows:
            raise ValueError('; '.join(warnings) or 'No valid COMEX inventory')
        return rows, '; '.join(warnings)
    response = net.get(URLS[series], retries=2, timeout=25)
    text = response.text
    if series == 'cme_price':
        rows = parse_cme(text)
    else:
        rows = parse_sina(text, series)
    rows = [r for r in rows if r['date'] >= start]
    if not rows:
        raise ValueError('No valid observations in the requested interval')
    sources.save_raw(data_dir / 'raw' / f'{series}.txt', text)
    return rows, ''


def discard_mislabeled_stock(history):
    """Quarantine the known warrant source even when replacement fetching fails."""
    return [r for r in history if not (r['series'] == 'shfe_stock' and r['source'] == OLD_SHFE)]


def run(start='2020-01-01', data_dir=ROOT / 'data'):
    history = read_rows(data_dir / 'history.csv')
    old_fx_dates = [r['date'] for r in history if r['series'] == 'usdcny' and r['source'] == FED]
    repaired = discard_mislabeled_stock(history)
    if repaired != history or old_fx_dates:
        backup = data_dir / 'backups' / ('history-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.csv')
        atomic_csv(backup, history, FIELDS)
        print(f'Pre-repair history: {backup}', flush=True)
    history = repaired
    statuses = []
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    for host in ('stock2.finance.sina.com.cn', 'push2his.eastmoney.com'):
        try:
            net.ensure_resolvable(host)
        except Exception as exc:
            print(f'{host} DNS: {exc}', flush=True)
    with ThreadPoolExecutor(max_workers=7) as pool:
        jobs = {pool.submit(fetch_one, s, min([start, *old_fx_dates]) if s == 'usdcny' else start, data_dir): s for s in SERIES}
        for future in as_completed(jobs):
            series = jobs[future]
            status = dict(series=series, attempted_at=now, source_url=URLS[series], detail='')
            try:
                rows, detail = future.result()
                previous = history
                if series == 'usdcny':
                    # Replace the entire legacy FX convention, including Fed-only
                    # holidays. Never splice different fixing times by date.
                    previous = [r for r in history if not (r['series'] == 'usdcny' and r['source'] == FED)]
                history = merge(previous, rows)
                status.update(status='partial' if detail else 'ok', rows=len(rows), detail=detail)
            except Exception as exc:
                status.update(status='error', rows=0, detail=str(exc))
            status['latest_date'] = max((r['date'] for r in history if r['series'] == series), default='')
            statuses.append(status)
            print(f"{series}: {status['status']}, latest {status['latest_date'] or 'missing'} {status['detail']}", flush=True)
    atomic_csv(data_dir / 'history.csv', history, FIELDS)
    atomic_csv(data_dir / 'out' / 'sources.csv', sorted(statuses, key=lambda r: r['series']), STATUS_FIELDS)
    return statuses
