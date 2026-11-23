/* Shared, deterministic financial model for the browser and Node tests. */
(function (root) {
  'use strict';
  const ids = ['gold', 'copper', 'zinc', 'silver'];
  const products = {
    gold: {symbol: 'Au', volumeUnit: 'tonne', salesScale: 1000, priceScale: 1000},
    silver: {symbol: 'Ag', volumeUnit: 'tonne', salesScale: 1000, priceScale: 1000},
    copper: {symbol: 'Cu', volumeUnit: '10kt', salesScale: 10000},
    zinc: {symbol: 'Zn', volumeUnit: '10kt', salesScale: 10000},
    cobalt: {symbol: 'Co', volumeUnit: '10kt', salesScale: 10000},
    molybdenum: {symbol: 'Mo', volumeUnit: 'tonne', salesScale: 1},
    tungsten: {symbol: 'W', volumeUnit: 'tonne', salesScale: 1},
    niobium: {symbol: 'Nb', volumeUnit: 'tonne', salesScale: 1},
    phosphate: {symbol: 'HA+LA', volumeUnit: '10kt', salesScale: 10000},
  };
  // Early CMOC reports publish revenue and costs for these three product groups.
  const cmocGroups = ['copperCobalt', 'molyTungsten', 'niobiumPhosphate'];
  for (const id of cmocGroups) products[id] = {volumeUnit: '10kt', salesScale: 10000};
  const companyProducts = {zijin: ids, cmoc: ['copper', 'cobalt', 'molybdenum', 'tungsten', 'niobium', 'gold', 'phosphate']};
  function number(value, min, max) {
    if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) throw new Error('invalid');
    return value;
  }
  function reportedSalesInput(m) {
    return {id: m.id, production: m.sales / products[m.id].salesScale, price: m.price, cost: m.cost};
  }
  function defaults(base, annualize = true, history = []) {
    const scale = annualize ? 12 / base.months : 1;
    const input = {
      metals: base.metals.map(reportedSalesInput),
      tax: base.tax * 100, share: base.share * 100, other: base.other / base.gp * 100,
      associate: base.associate / base.metals.find(m => m.id === (base.grouped ? 'copperCobalt' : 'copper')).gp * 100, adjustment: 0,
    };
    if (annualize) input.metals.forEach(m => { m.production *= scale; });
    if (base.grouped || base.metals.some(m => m.id === 'cobalt')) {
      if (base.grouped) input.groupedCopperDriver = true;
      const revenue = base.metals.reduce((sum, m) => sum + m.sales * m.price * m.factor / 1e8, 0);
      input.other = base.other / revenue * 100;
      input.months = annualize ? 12 : base.months;
      input.baseMonthlyNet = base.net / base.months;
      input.marginalShare = input.share;
      const lastYear = Number(base.year.slice(0, 4)) - (base.months === 12 ? 0 : 1);
      const last = base.months === 12 ? base : history.find(r => r.year === String(lastYear));
      const previous = history.find(r => r.year === String(lastYear - 1));
      if (last && previous && last.net !== previous.net) {
        const slope = (last.actual - previous.actual) / (last.net - previous.net);
        if (slope >= 0 && slope <= 1) input.marginalShare = slope * 100;
      }
    }
    return input;
  }
  function estimate(input, company = 'zijin') {
    const grouped = company === 'cmoc' && input?.groupedCopperDriver && input.metals?.[0]?.id === 'copperCobalt';
    const expected = grouped ? cmocGroups : companyProducts[company];
    if (!input || !Array.isArray(input.metals) || input.metals.length !== expected.length) throw new Error('invalid');
    const metals = input.metals.map((m, i) => {
      if (m.id !== expected[i]) throw new Error('invalid');
      const q = number(m.production, 0, 1e6), p = number(m.price, 0, 1e7), c = number(m.cost, 0, 1e7);
      const sales = q * products[m.id].salesScale;
      const factor = products[m.id].priceScale || 1;
      const revenue = sales * p * factor / 1e8, cost = sales * c * factor / 1e8;
      return {...m, sales, revenue, totalCost: cost, gp: revenue - cost};
    });
    const gp = metals.reduce((s, m) => s + m.gp, 0);
    const copperGP = grouped ? metals[0].gp : metals.find(m => m.id === 'copper').gp;
    // At the disclosure transition, apply the prior copper/cobalt ratio to both metals.
    const associateDriver = company === 'cmoc' && input.groupedCopperDriver && !grouped
      ? copperGP + metals.find(m => m.id === 'cobalt').gp : copperGP;
    const associate = associateDriver * number(input.associate, -100, 200) / 100;
    // Archived CMOC scenarios used gross profit as the residual's driver.
    const cmocBridge = company === 'cmoc' && input.baseMonthlyNet !== undefined;
    const otherDriver = cmocBridge ? metals.reduce((sum, m) => sum + m.revenue, 0) : gp;
    const other = otherDriver * number(input.other, -200, 200) / 100;
    const pretax = gp + associate + other;
    // No automatic recognition of a tax asset in a loss scenario.
    const tax = Math.max(0, pretax) * number(input.tax, 0, 60) / 100;
    const net = pretax - tax;
    const share = number(input.share, 0, 100) / 100;
    let coreParent = net * share;
    if (cmocBridge) {
      const baseNet = number(input.baseMonthlyNet, 0, Infinity) * number(input.months, 1, 12);
      const marginal = number(input.marginalShare, 0, 100) / 100;
      coreParent += Math.max(net - baseNet, 0) * (marginal - share);
    }
    const adjustment = number(input.adjustment, -10000, 10000);
    const parent = coreParent + adjustment;
    const nci = net - coreParent;
    const result = {metals, gp, associate, other, pretax, tax, net, coreParent, adjustment, parent, nci};
    for (const v of [gp, associate, other, pretax, tax, net, parent, nci]) if (!Number.isFinite(v)) throw new Error('invalid');
    return result;
  }
  function backtest(history, targetId, company = 'zijin') {
    const target = history.find(r => r.year === targetId);
    if (!target || target.months !== 12 || !/^\d{4}$/.test(target.year)) throw new Error('annual target');
    const baseId = String(Number(target.year.slice(0, 4)) - 1);
    const base = history.find(r => r.year === baseId);
    if (!base || base.months !== 12) throw new Error('base');
    const input = defaults(base, false, history);
    // These three user inputs come from the target annual report.
    input.metals = target.metals.map(reportedSalesInput);
    const predicted = estimate(input, company).parent;
    const error = target.actual === 0 ? null : 100 * (predicted / target.actual - 1);
    return {year: targetId, base: baseId, predicted, actual: target.actual, error, input};
  }
  function annualBacktests(history, company) {
    const years = history.filter(r => r.months === 12 && /^\d{4}$/.test(r.year))
      .map(r => Number(r.year)).sort((a, b) => a - b);
    const latest = years.at(-1);
    return years.filter(year => year > latest - 5 && years.includes(year - 1))
      .map(year => backtest(history, String(year), company));
  }
  function metrics(rows) {
    const errors = rows.map(r => r.error).filter(Number.isFinite).map(Math.abs);
    return {mape: errors.length ? errors.reduce((a, b) => a + b, 0) / errors.length : null,
      maxError: errors.length ? Math.max(...errors) : null};
  }
  const api = {ids, products, companyProducts, defaults, estimate, backtest, annualBacktests, metrics};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.CompanyProfitModel = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
