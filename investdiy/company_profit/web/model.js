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
    potash: {symbol: 'KCl', volumeUnit: '10kt', salesScale: 10000},
    lithium: {symbol: 'Li₂CO₃', volumeUnit: 'tonne', salesScale: 1},
    phosphate: {symbol: 'HA+LA', volumeUnit: '10kt', salesScale: 10000},
  };
  // Early CMOC reports publish revenue and costs for these three product groups.
  const cmocGroups = ['copperCobalt', 'molyTungsten', 'niobiumPhosphate'];
  for (const id of cmocGroups) products[id] = {volumeUnit: '10kt', salesScale: 10000};
  const companyProducts = {zijin: ids, zangge: ['potash', 'lithium'], cmoc: ['copper', 'cobalt', 'molybdenum', 'tungsten', 'niobium', 'gold', 'phosphate']};
  function number(value, min, max) {
    if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) throw new Error('invalid');
    return value;
  }
  function reportedSalesInput(m) {
    return {id: m.id, production: m.sales / products[m.id].salesScale, price: m.price, cost: m.cost};
  }
  function defaults(base, annualize = true, history = [], basis = 'reported') {
    const scale = annualize ? 12 / base.months : 1;
    const input = {
      metals: base.metals.map(reportedSalesInput),
      tax: base.tax * 100, adjustment: 0, months: annualize ? 12 : base.months,
    };
    if (annualize) input.metals.forEach(m => { m.production *= scale; });
    if (base.operatingTax !== undefined) {
      input.tax = base.operatingTax * 100;
      input.otherMonthly = base.other / base.months;
      input.nciMonthly = base.nci / base.months;
      if (base.potashResourceTaxPct !== undefined) {
        const potash = base.metals.find(m => m.id === 'potash');
        input.potashResourceTaxPct = base.potashResourceTaxPct;
        input.baseMonthlyPotashRevenue = potash.sales * potash.price / 1e8 / base.months;
      }
      if (base.julongSales !== undefined) {
        input.julongSales = base.julongSales * scale;
        input.julongStake = base.julongStake;
        input.julongPrice = base.julongPrice;
        input.julongCost = base.julongCost;
        input.julongOtherPerTonne = base.julongOtherPerTonne;
        input.julongTaxPct = base.julongTaxPct;
      } else {
        let earnings = base.associate;
        if (basis === 'forecast' && base.months === 12 && base.julongStake > 0) {
          const previous = history.find(r => r.year === String(Number(base.year) - 1) && r.months === 12);
          if (previous?.julongStake === base.julongStake) earnings += base.associate - previous.associate;
        }
        input.julongMonthly = earnings / base.months;
      }
      return input;
    }
    input.share = base.share * 100;
    if (base.grouped || base.metals.some(m => m.id === 'cobalt')) {
      input.associateMonthly = base.associate / base.months;
      if (basis === 'forecast' && base.taxWindow?.pretax > 0) {
        const rate = 100 * base.taxWindow.expense / base.taxWindow.pretax;
        if (rate >= 0 && rate <= 60) input.tax = rate;
      }
      const revenue = base.metals.reduce((sum, m) => sum + m.sales * m.price * m.factor / 1e8, 0);
      input.other = base.other / revenue * 100;
      input.baseMonthlyNet = base.net / base.months;
      input.marginalShare = input.share;
      const lastYear = Number(base.year.slice(0, 4)) - (base.months === 12 ? 0 : 1);
      const last = base.months === 12 ? base : history.find(r => r.year === String(lastYear));
      const previous = history.find(r => r.year === String(lastYear - 1));
      if (last && previous && last.net !== previous.net) {
        const slope = (last.actual - previous.actual) / (last.net - previous.net);
        if (slope >= 0 && slope <= 1) input.marginalShare = slope * 100;
      }
    } else {
      input.otherMonthly = base.other / base.months;
      input.associate = base.associate / base.metals.find(m => m.id === 'copper').gp * 100;
    }
    return input;
  }
  function julongIncome(input, months) {
    if (input.julongSales === undefined) return months * number(input.julongMonthly, -10000, 10000);
    const tonnes = number(input.julongSales, 0, 1e6) * 10000;
    const stake = number(input.julongStake, 0, 100) / 100;
    // Version 1 scenario exports stored the adjusted after-tax margin directly.
    if (input.julongPrice === undefined && input.julongUnitNet !== undefined) {
      return tonnes * number(input.julongUnitNet, -1e7, 1e7) * stake / 1e8;
    }
    const margin = number(input.julongPrice, 0, 1e7) - number(input.julongCost, 0, 1e7);
    const pretax = tonnes * (margin + number(input.julongOtherPerTonne, -1e7, 1e7));
    const tax = Math.max(0, pretax) * number(input.julongTaxPct, 0, 60) / 100;
    return (pretax - tax) * stake / 1e8;
  }
  function estimate(input, company = 'zijin') {
    const grouped = company === 'cmoc' && input?.metals?.[0]?.id === 'copperCobalt';
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
    // Older exported scenarios encode both lines as percentages.
    const months = input.months === undefined ? 12 : number(input.months, 1, 12);
    let associate;
    if (company === 'zangge') {
      associate = julongIncome(input, months);
    } else if (company === 'cmoc' && input.associateMonthly !== undefined) {
      associate = months * number(input.associateMonthly, -10000, 10000);
    } else {
      let driver = grouped ? metals[0].gp : metals.find(m => m.id === 'copper').gp;
      if (company === 'cmoc' && input.groupedCopperDriver && !grouped) driver += metals.find(m => m.id === 'cobalt').gp;
      associate = driver * number(input.associate, -100, 200) / 100;
    }
    const cmocBridge = company === 'cmoc' && input.baseMonthlyNet !== undefined;
    let other;
    if (company === 'zangge' || (company === 'zijin' && input.otherMonthly !== undefined)) {
      other = months * number(input.otherMonthly, -10000, 10000);
    } else {
      const driver = cmocBridge ? metals.reduce((sum, m) => sum + m.revenue, 0) : gp;
      other = driver * number(input.other, -200, 200) / 100;
    }
    if (company === 'zangge' && input.potashResourceTaxPct !== undefined) {
      // The monthly residual already includes tax on the baseline sales.
      const baselineRevenue = months * number(input.baseMonthlyPotashRevenue, 0, Infinity);
      const delta = metals.find(m => m.id === 'potash').revenue - baselineRevenue;
      other -= delta * number(input.potashResourceTaxPct, 0, 100) / 100;
    }
    const pretax = gp + associate + other;
    // No automatic recognition of a tax asset in a loss scenario.
    const taxable = company === 'zangge' ? gp + other : pretax;
    const tax = Math.max(0, taxable) * number(input.tax, 0, 60) / 100;
    const net = pretax - tax;
    let coreParent;
    if (company === 'zangge') {
      coreParent = net - months * number(input.nciMonthly, -10000, 10000);
    } else {
      const share = number(input.share, 0, 100) / 100;
      coreParent = net * share;
      if (cmocBridge) {
        const baseNet = number(input.baseMonthlyNet, 0, Infinity) * months;
        const marginal = number(input.marginalShare, 0, 100) / 100;
        coreParent += Math.max(net - baseNet, 0) * (marginal - share);
      }
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
    const input = defaults(base, false, history, 'forecast');
    // These three user inputs come from the target annual report.
    input.metals = target.metals.map(reportedSalesInput);
    if (input.julongSales !== undefined && target.julongSales !== undefined) input.julongSales = target.julongSales;
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
