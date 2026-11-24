/* Company production guidance and market-price conversions. */
(function (root) {
  'use strict';
  const source = 'https://www.zijinmining.com/upload/file/2026/02/09/c08d3f959bdd4800a9c30c15e6afaab5.pdf';
  const plans = {
    '2026': {gold: 105, copper: 120, silver: 520},
    '2028-low': {gold: 130, copper: 150, silver: 600},
    '2028-mid': {gold: 135, copper: 155, silver: 650},
    '2028-high': {gold: 140, copper: 160, silver: 700},
  };
  const cmocPlans = {
    '2026-mid': {copper: 79, cobalt: 11, molybdenum: 13000, tungsten: 7000, niobium: 10500, gold: 7, phosphate: 115},
    '2026-low': {copper: 76, cobalt: 10, molybdenum: 11500, tungsten: 6500, niobium: 10000, gold: 6, phosphate: 105},
    '2026-high': {copper: 82, cobalt: 12, molybdenum: 14500, tungsten: 7500, niobium: 11000, gold: 8, phosphate: 125},
  };
  const guidance = {
    zijin: {plans, source},
    cmoc: {plans: cmocPlans, source: 'https://static.cninfo.com.cn/finalpage/2026-04-02/1225072765.PDF'},
  };
  function production(id, company = 'zijin') {
    const plans = guidance[company].plans;
    if (!Object.hasOwn(plans, id)) throw new Error('Unknown production preset');
    return {...plans[id]};
  }
  function realizedPrice(quote, vat, realization) {
    const units = {gold: 'CNY/g', copper: 'CNY/t', zinc: 'CNY/t', silver: 'CNY/kg'};
    if (!quote || !Object.hasOwn(units, quote.id) || quote.unit !== units[quote.id] ||
        !Number.isFinite(quote.price) || quote.price <= 0 ||
        !Number.isFinite(vat) || vat < 0 || vat > 30 ||
        !Number.isFinite(realization) || realization <= 0 || realization > 200) throw new Error('Invalid price conversion');
    const value = quote.price / (quote.id === 'silver' ? 1000 : 1) / (1 + vat / 100) * realization / 100;
    if (value > 1e7) throw new Error('Price out of range');
    return value;
  }
  const priceUnits = {gold: ['CNY/g', 'USD/oz'], copper: ['CNY/t', 'USD/t', 'USD/lb'], zinc: ['CNY/t'], silver: ['CNY/g'],
    cobalt: ['CNY/t'], molybdenum: ['CNY/t'], tungsten: ['CNY/t'], niobium: ['CNY/t'], phosphate: ['CNY/t']};
  function priceFactor(id, unit, fx) {
    if (!priceUnits[id]?.includes(unit)) throw new Error('Unknown price unit');
    if (unit.startsWith('CNY/')) return 1;
    if (!Number.isFinite(fx) || fx <= 0) throw new Error('Invalid FX rate');
    // One troy ounce = 31.1034768 grams; one avoirdupois pound = 0.45359237 kg.
    if (unit === 'USD/oz') return fx / 31.1034768;
    if (unit === 'USD/lb') return fx * 1000 / 0.45359237;
    return fx;
  }
  function toBasePrice(id, value, unit, fx) {
    if (!Number.isFinite(value) || value < 0) throw new Error('Invalid price');
    const price = value * priceFactor(id, unit, fx);
    if (!Number.isFinite(price) || price > 1e7) throw new Error('Price out of range');
    return price;
  }
  function fromBasePrice(id, value, unit, fx) {
    if (!Number.isFinite(value) || value < 0 || value > 1e7) throw new Error('Invalid price');
    return value / priceFactor(id, unit, fx);
  }
  function snapshotPrices(snapshot) {
    const ids = ['gold', 'copper', 'zinc', 'silver'];
    if (!snapshot || !Number.isFinite(Date.parse(snapshot.fetched_at)) ||
        !Number.isFinite(snapshot.fx?.cny_per_usd) || snapshot.fx.cny_per_usd <= 0 ||
        !Number.isFinite(Date.parse(snapshot.fx.as_of)) || !Array.isArray(snapshot.quotes) ||
        snapshot.quotes.length !== ids.length) throw new Error('Incomplete snapshot');
    return ids.map((id, i) => {
      const quote = snapshot.quotes[i];
      if (quote.id !== id || !Number.isFinite(Date.parse(quote.quoted_at))) throw new Error('Invalid quote');
      const vat = snapshot.conversion?.vat_pct?.[id], realization = snapshot.conversion?.realization_pct;
      return {id, vat, realization, price: realizedPrice(quote, vat, realization)};
    });
  }
  const api = {guidance, source, production, realizedPrice, priceUnits, toBasePrice, fromBasePrice, snapshotPrices};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.CompanyProfitPresets = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
