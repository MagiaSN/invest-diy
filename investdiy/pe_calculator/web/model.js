/* Pure valuation functions. All input rates are percentages, not fractions. */
(function (root) {
  'use strict';
  const limits = { stages: 20, years: 100, scenarios: 20 };
  const finite = (v) => typeof v === 'number' && Number.isFinite(v);
  function fail(code) { throw new RangeError(code); }

  function parseRates(text) {
    const tokens = String(text).trim().split(/[\s,，;；、]+/).filter(Boolean);
    if (!tokens.length || tokens.length > limits.scenarios) fail('rates');
    const rates = tokens.map((token) => {
      if (!/^(?:\d+(?:\.\d*)?|\.\d+)[%％]?$/.test(token)) fail('rates');
      const rate = Number(token.replace(/[%％]$/, ''));
      if (!finite(rate) || rate <= 0 || rate > 100) fail('rates');
      return rate;
    });
    return [...new Set(rates)].sort((a, b) => a - b);
  }

  function calculate({ stages, premium, terminalRatio, rates }) {
    if (!Array.isArray(stages) || !stages.length || stages.length > limits.stages) fail('stages');
    let years = 0;
    for (const stage of stages) {
      if (!Number.isInteger(stage.years) || stage.years < 1 || stage.years > limits.years) fail('years');
      if (!finite(stage.growth) || stage.growth < -100 || stage.growth > 1000) fail('growth');
      if (!finite(stage.fcfeRatio) || stage.fcfeRatio < 0) fail('stageRatio');
      years += stage.years;
    }
    if (years > limits.years) fail('horizon');
    if (!finite(premium) || premium < 0 || premium > 100) fail('premium');
    if (!finite(terminalRatio) || terminalRatio < 0) fail('terminalRatio');
    if (!Array.isArray(rates) || !rates.length || rates.length > limits.scenarios ||
        rates.some((rate) => !finite(rate) || rate <= 0 || rate > 100)) fail('rates');

    // Normalize positive current earnings to 1. Each stage converts earnings
    // to distributable cash; the terminal ratio applies only after the forecast.
    let earnings = 1;
    const annual = [];
    stages.forEach((stage, index) => {
      for (let j = 0; j < stage.years; j++) {
        const year = annual.length + 1;
        earnings *= 1 + stage.growth / 100;
        annual.push({ year, stage: index + 1, growth: stage.growth, fcfeRatio: stage.fcfeRatio,
          earnings, fcfe: earnings * (stage.fcfeRatio / 100) });
      }
    });
    const scenarios = [...new Set(rates)].sort((a, b) => a - b).map((rate) => {
      const discount = rate + premium;
      let forecastPV = 0;
      const discountedAnnual = annual.map((entry) => {
        const factor = (1 + discount / 100) ** -entry.year;
        const pv = entry.fcfe * factor;
        forecastPV += pv;
        return { ...entry, factor, pv, cumulative: forecastPV };
      });
      // Keep the simplified risk-free exit capitalization assumption. Discount
      // forecast cash flows and the exit value at risk-free rate plus equity premium.
      const terminalPE = (terminalRatio / 100) / (rate / 100);
      const terminalValue = earnings * terminalPE;
      const terminalPV = terminalValue * (1 + discount / 100) ** -years;
      const pe = forecastPV + terminalPV;
      return { rate, discount, annual: discountedAnnual, terminalPE, terminalValue, terminalPV, forecastPV, pe,
        terminalShare: pe === 0 ? 0 : terminalPV / pe };
    });
    if (annual.some((a) => !Number.isFinite(a.fcfe)) || scenarios.some((s) => !Number.isFinite(s.pe))) fail('overflow');
    return { years, earnings, annual, scenarios };
  }

  const api = { calculate, parseRates, limits };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.peModel = api;
})(typeof window !== 'undefined' ? window : globalThis);
