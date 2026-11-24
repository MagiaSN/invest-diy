// Battery unit gross profit is CNY/Wh. All income statement amounts are CNY 100m.
(function (root) {
  'use strict';
  const products = ['ev', 'storage'];
  const periodItems = ['finance', 'investment', 'otherIncome', 'impairment', 'remaining'];
  const volumeKey = id => id + 'Volume';
  // GWh sold × CNY/Wh × (Wh/GWh) / (CNY per 100m).
  const grossProfitFactor = 1e9 / 1e8;
  function operatingInputs(report) {
    const input = {};
    for (const id of products) {
      const p = report.products[id];
      input[volumeKey(id)] = p.volume;
      input[id + 'MarginPerWh'] = (p.revenue - p.cost) / (p.volume * grossProfitFactor);
    }
    return input;
  }
  function incomeRates(report, previous) {
    const tax = report.tax + (previous?.tax ?? 0);
    const pretax = report.pretax + (previous?.pretax ?? 0);
    const parent = report.parent + (previous?.parent ?? 0);
    const net = report.net + (previous?.net ?? 0);
    return {taxRate: 100 * tax / pretax, parentShare: 100 * parent / net};
  }
  function forecastFinance(report, fees) {
    const averageCash = (report.openingCash + report.closingCash) / 2;
    const interest = report.interestIncome * report.closingCash / averageCash;
    return interest - report.interestExpense - fees;
  }
  function spendingInputs(report, batteryGross, periodScale, warranty = 0) {
    // Match the cost and gross-profit bases when warranty moves to cost of sales.
    const nonPayroll = report.expenses - report.payroll - warranty;
    return {payroll: report.payroll * periodScale,
      spendingRate: 100 * nonPayroll / (batteryGross - warranty)};
  }
  function annualInputs(report, historical = true, previous = report.priorIncome) {
    const op = operatingInputs(report);
    const batteryGross = products.reduce((sum, id) => {
      const p = report.products[id];
      return sum + (p.revenue - p.cost);
    }, 0);
    const materialsGross = report.groupGross - batteryGross - report.ancillaryBusinessGross;
    const remaining = report.pretax - report.groupGross + report.expenses - report.finance
      - report.associates - report.otherIncome - report.impairment;
    return {...op, materialsGross,
      otherGrossPerWh: report.ancillaryBusinessGross / ((op.evVolume + op.storageVolume) * grossProfitFactor),
      ...spendingInputs(report, batteryGross, 1, historical ? 0 : report.warrantyInSellingExpenses ?? 0),
      ...incomeRates(report, historical ? null : previous),
      finance: historical ? report.finance : forecastFinance(report, report.financeFees),
      investment: report.associates, otherIncome: report.otherIncome, impairment: report.impairment,
      remaining: historical ? remaining : 0};
  }
  function quarterInputs(data) {
    const f = data.forecast, half = f.half, nine = f.nineMonths;
    const latest = data.history.at(-1);
    const op = operatingInputs(latest);
    const annualVolume = op.evVolume + op.storageVolume;
    return {...op, evVolume: f.volume.ev, storageVolume: f.volume.storage,
      otherGrossPerWh: latest.ancillaryBusinessGross / (annualVolume * grossProfitFactor),
      materialsGross: half.materialsGross / 2, ...spendingInputs(half, half.batteryGross, 1 / 2),
      ...incomeRates(nine, f.priorNineMonths),
      // The interim fee disclosure covers six months. Express it on the same
      // nine-month basis as the interest flows before converting to one quarter.
      finance: forecastFinance(nine, half.financeFees * 1.5) / 3,
      investment: nine.associates / 3, otherIncome: nine.otherIncome / 3,
      impairment: nine.impairment / 3, remaining: 0};
  }
  function estimate(input, reportedParent = 0) {
    function productGross(id) {
      const volume = input[volumeKey(id)];
      let margin = input[id + 'MarginPerWh'];
      // Version 1 scenario exports stored product margins in CNY/GWh.
      if (margin === undefined && Number.isFinite(input[id + 'Margin'])) margin = input[id + 'Margin'] / 1e9;
      if (!Number.isFinite(volume) || volume < 0 || !Number.isFinite(margin)) throw new RangeError('Invalid CATL product');
      return volume * margin * grossProfitFactor;
    }
    if (input.expensePerGWh < 0
        || [input.taxRate, input.parentShare].some(rate => !Number.isFinite(rate) || rate < 0 || rate > 100)) {
      throw new RangeError('Invalid CATL assumptions');
    }
    const ev = productGross('ev');
    const storage = productGross('storage');
    const volume = input.evVolume + input.storageVolume;
    // Versions 1 and 2 exported one expense rate in CNY/GWh.
    const legacy = input.expensePerGWh !== undefined && input.payroll === undefined;
    if (!legacy && (!(input.payroll >= 0) || !(input.spendingRate >= 0))) throw new RangeError('Invalid expense budget');
    const expenses = legacy ? -volume * input.expensePerGWh / 1e8
      : -input.payroll - Math.max(0, ev + storage) * input.spendingRate / 100;
    const materialsGross = legacy ? 0 : input.materialsGross;
    const otherMargin = input.otherGrossPerWh ?? input.otherGrossPerGWh / 1e9;
    const otherBusiness = volume * otherMargin * grossProfitFactor;
    const otherGross = materialsGross + otherBusiness;
    const gp = ev + storage + otherGross;
    const ancillary = periodItems.reduce((sum, k) => sum + input[k], input.nonRecurring ?? 0);
    const pretax = gp + expenses + ancillary;
    const tax = -Math.max(0, pretax) * input.taxRate / 100;
    const net = pretax + tax;
    const parent = net * input.parentShare / 100;
    const minority = parent - net;
    const annual = reportedParent + parent;
    const result = {ev, storage, materialsGross, otherBusiness, otherGross, gp, expenses, ancillary, pretax, tax, net, minority, parent, annual};
    if (!Object.values(result).every(Number.isFinite)) throw new RangeError('Invalid CATL input');
    return result;
  }
  function backtests(history) {
    return history.slice(1).slice(-5).map(target => {
      const base = history.find(r => r.year === target.year - 1);
      const previous = history.find(r => r.year === base.year - 1) ?? base.priorIncome;
      const input = {...annualInputs(base, false, previous), ...operatingInputs(target)};
      const result = estimate(input);
      const reported = estimate(annualInputs(target));
      const errors = {};
      for (const k of ['otherGross', 'expenses', 'ancillary', 'tax', 'minority']) {
        errors[k] = result[k] - reported[k];
      }
      return {year: target.year, base: base.year, input, predicted: result.parent,
        actual: target.parent, error: 100 * (result.parent / target.parent - 1), errors};
    });
  }
  const model = {annualInputs, quarterInputs, estimate, backtests};
  if (typeof module !== 'undefined' && module.exports) module.exports = model;
  else root.CatlProfitModel = model;
})(typeof globalThis !== 'undefined' ? globalThis : this);
