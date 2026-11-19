/* Shared, deterministic financial model for the browser and Node tests. */
(function (root) {
  'use strict';
  const ids = ['gold', 'copper', 'zinc', 'silver'];
  function number(value, min, max) {
    if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) throw new Error('invalid');
    return value;
  }
  function defaults(base, annualize = true) {
    const scale = annualize ? 12 / base.months : 1;
    return {
      metals: base.metals.map(m => ({id: m.id, production: m.production * scale, price: m.price, cost: m.cost, conversion: m.conversion})),
      tax: base.tax * 100, share: base.share * 100, other: base.other / base.gp * 100,
      associate: base.associate / base.metals[1].gp * 100, adjustment: 0,
    };
  }
  function estimate(input) {
    if (!input || !Array.isArray(input.metals) || input.metals.length !== 4) throw new Error('invalid');
    const metals = input.metals.map((m, i) => {
      if (m.id !== ids[i]) throw new Error('invalid');
      const q = number(m.production, 0, 1e6), p = number(m.price, 0, 1e7), c = number(m.cost, 0, 1e7);
      const conversion = number(m.conversion, 0, 5);
      const sales = q * conversion * (i === 0 || i === 3 ? 1000 : 10000);
      const factor = i === 0 || i === 3 ? 1000 : 1;
      const revenue = sales * p * factor / 1e8, cost = sales * c * factor / 1e8;
      return {...m, sales, revenue, totalCost: cost, gp: revenue - cost};
    });
    const gp = metals.reduce((s, m) => s + m.gp, 0);
    const associate = metals[1].gp * number(input.associate, -100, 200) / 100;
    const other = gp * number(input.other, -200, 200) / 100;
    const pretax = gp + associate + other;
    // No automatic recognition of a tax asset in a loss scenario.
    const tax = Math.max(0, pretax) * number(input.tax, 0, 60) / 100;
    const net = pretax - tax;
    const coreParent = net * number(input.share, 0, 100) / 100;
    const adjustment = number(input.adjustment, -10000, 10000);
    const parent = coreParent + adjustment;
    const nci = net - coreParent;
    const result = {metals, gp, associate, other, pretax, tax, net, coreParent, adjustment, parent, nci};
    for (const v of [gp, associate, other, pretax, tax, net, parent, nci]) if (!Number.isFinite(v)) throw new Error('invalid');
    return result;
  }
  function backtest(history, targetId) {
    const target = history.find(r => r.year === targetId);
    if (!target) throw new Error('target');
    const baseId = String(Number(target.year.slice(0, 4)) - 1);
    const base = history.find(r => r.year === baseId);
    if (!base) throw new Error('base');
    const input = defaults(base, false);
    // Only target production and realized prices enter the estimator.
    input.metals.forEach((m, i) => { m.production = target.metals[i].production; m.price = target.metals[i].price; });
    const predicted = estimate(input).parent;
    const error = target.actual === 0 ? null : 100 * (predicted / target.actual - 1);
    return {year: targetId, base: baseId, predicted, actual: target.actual, error, input};
  }
  function metrics(rows) {
    const errors = rows.map(r => Math.abs(r.error)).filter(Number.isFinite);
    return {mape: errors.length ? errors.reduce((a, b) => a + b, 0) / errors.length : null,
      maxError: errors.length ? Math.max(...errors) : null};
  }
  const api = {ids, defaults, estimate, backtest, metrics};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.CompanyProfitModel = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
