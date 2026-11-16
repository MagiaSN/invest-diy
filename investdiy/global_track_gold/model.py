"""Period-aligned calculations; missing observations are never forward filled."""

from bisect import bisect_left
from calendar import monthrange
from datetime import date
import math

OZ_PER_TONNE = 1_000_000 / 31.1034768
COUNTRIES = {
    'USA': ('美国', 'United States'), 'DEU': ('德国', 'Germany'),
    'ITA': ('意大利', 'Italy'), 'FRA': ('法国', 'France'),
    'CHN': ('中国', 'China'), 'RUS': ('俄罗斯', 'Russia'),
    'CHE': ('瑞士', 'Switzerland'), 'IND': ('印度', 'India'),
    'JPN': ('日本', 'Japan'), 'TUR': ('土耳其', 'Türkiye'),
    'NLD': ('荷兰', 'Netherlands'), 'POL': ('波兰', 'Poland'),
    'GBR': ('英国', 'United Kingdom'), 'SAU': ('沙特阿拉伯', 'Saudi Arabia'),
    'ESP': ('西班牙', 'Spain'), 'BRA': ('巴西', 'Brazil'),
    'KOR': ('韩国', 'South Korea'), 'CAN': ('加拿大', 'Canada'),
}


def number(value):
    if value in (None, '', '…', '...', '—', 'NA'):
        return None
    result = float(str(value).replace(',', ''))
    if not math.isfinite(result) or result < 0:
        raise ValueError(f'Invalid nonnegative observation: {value}')
    return result


def month_end(month):
    year, mon = map(int, month.split('-'))
    return date(year, mon, monthrange(year, mon)[1]).isoformat()


def month_index(month):
    year, mon = map(int, month[:7].split('-'))
    return year * 12 + mon - 1


def ratio(a, b):
    return a / b if a is not None and b is not None and b > 0 else None


def price_ratios(rows):
    return [dict(r, gold_brent=ratio(r.get('gold'), r.get('brent')),
                 gold_wti=ratio(r.get('gold'), r.get('wti')),
                 gold_silver=ratio(r.get('gold'), r.get('silver'))) for r in rows]


def stock_history(anchor_date, anchor_tonnes, annual, quarterly):
    """Backcast the public WGC stock anchor using mine production only.

    Annual stocks are estimates, not the gated WGC historical stock dataset.
    Recycled gold and producer hedging do not create additional physical gold.
    """
    year, month = map(int, anchor_date[:7].split('-'))
    if month not in (3, 6, 9, 12) or anchor_date != month_end(anchor_date[:7]):
        raise ValueError('Stock anchor must be a quarter end')
    result = {anchor_date: anchor_tonnes}
    stock = anchor_tonnes
    if month != 12:
        for q in range(month // 3, 0, -1):
            stock -= quarterly[(year, q)]
            end = month_end(f'{year}-{(q - 1) * 3:02d}') if q > 1 else f'{year - 1}-12-31'
            result[end] = stock
        year -= 1
    while year in annual:
        stock -= annual[year]
        year -= 1
        result[f'{year}-12-31'] = stock
    if len(result) < 3 or min(result.values()) <= 0:
        raise ValueError('Insufficient or invalid stock reconstruction')
    return [dict(date=d, stock_t=v, method='published_anchor' if d == anchor_date else 'mine_backcast',
                 anchor_date=anchor_date) for d, v in sorted(result.items())]


def compare_market(prices, debts, stocks):
    points = {month_index(r['date']): r for r in stocks}
    indices = sorted(points)
    by_month = {r['date'][:7]: r for r in debts}
    rows = []
    for price in prices:
        month = price['date'][:7]
        index = month_index(month)
        if index < indices[0] or index > indices[-1] or price.get('gold') is None:
            continue
        j = bisect_left(indices, index)
        right = indices[j]
        left = right if right == index else indices[j - 1]
        fraction = (index - left) / (right - left) if left != right else 0
        stock = points[left]['stock_t'] + fraction * (points[right]['stock_t'] - points[left]['stock_t'])
        debt = by_month.get(month, {})
        value = stock * OZ_PER_TONNE * price['gold']
        rows.append(dict(date=price['date'], stock_t=stock, gold_price=price['gold'],
                         gold_usd=value, debt_usd=debt.get('total'), public_debt_usd=debt.get('public'),
                         gold_debt_ratio=ratio(value, debt.get('total')), debt_date=debt.get('debt_date', ''),
                         stock_method=points[left]['method'] if left == right else 'interpolated',
                         stock_left=points[left]['date'], stock_right=points[right]['date']))
    return rows


def reserves(rows):
    result = []
    for country in COUNTRIES:
        history = {r['date']: r for r in rows if r['country'] == country}
        for day, row in sorted(history.items()):
            oz = row.get('gold_oz')
            if oz is None:
                continue
            total, exgold, fx = (row.get(k) for k in ('total_usd', 'exgold_usd', 'fx_usd'))
            gold = total - exgold if total is not None and exgold is not None else None
            if gold is not None and gold < -max(1, total * 1e-8):
                raise ValueError(f'Negative market gold value: {country} {day}')
            gold = max(0, gold) if gold is not None else None
            # Some latest IMF totals omit a gold valuation while volumes exist.
            # A zero residual must not imply zero-valued positive gold holdings.
            if oz > 0 and gold == 0:
                gold = None
            index = month_index(day)
            prev_month = f'{(index-1)//12}-{(index-1)%12+1:02d}'
            previous = history.get(month_end(prev_month), {}).get('gold_oz')
            yoy_day = month_end(f'{int(day[:4])-1}-{day[5:7]}')
            yoy = history.get(yoy_day, {}).get('gold_oz')
            result.append(dict(date=day, country=country, name=COUNTRIES[country][0], name_en=COUNTRIES[country][1],
                               gold_t=oz / OZ_PER_TONNE, gold_usd=gold, total_usd=total, fx_usd=fx,
                               gold_total_pct=None if ratio(gold, total) is None else ratio(gold, total)*100,
                               gold_fx_pct=None if ratio(gold, fx) is None else ratio(gold, fx)*100,
                               change_t=None if previous is None else (oz-previous)/OZ_PER_TONNE,
                               yoy_t=None if yoy is None else (oz-yoy)/OZ_PER_TONNE))
    return sorted(result, key=lambda r: (r['country'], r['date']))
