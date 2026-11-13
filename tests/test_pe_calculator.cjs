const { test } = require('node:test');
const assert = require('node:assert/strict');
const { calculate, parseRates } = require('../investdiy/pe_calculator/web/model.js');

const stage = (years, growth, fcfeRatio = 100) => ({ years, growth, fcfeRatio });
const base = { stages: [stage(1, 0)], premium: 6, terminalRatio: 100, rates: [2, 4, 6] };
const close = (actual, expected) => assert.ok(Math.abs(actual - expected) <= 1e-10 * Math.max(1, Math.abs(expected)), `${actual} != ${expected}`);

test('one-year hand calculation uses risk-free rate plus equity premium in each scenario', () => {
  const result = calculate(base);
  assert.deepEqual(result.scenarios.map((s) => s.discount), [8, 10, 12]);
  for (const scenario of result.scenarios) {
    const divisor = 1 + (scenario.rate + base.premium) / 100;
    close(scenario.forecastPV, 1 / divisor);
    close(scenario.terminalPE, 100 / scenario.rate);
    close(scenario.terminalPV, 100 / scenario.rate / divisor);
    close(scenario.pe, (1 + 100 / scenario.rate) / divisor);
  }
});

test('flat earnings with identical capitalization and discount rates equal a perpetuity at every horizon', () => {
  for (const years of [1, 3, 15, 100]) {
    const result = calculate({ ...base, premium: 0, stages: [stage(years, 0)], rates: [10] });
    close(result.scenarios[0].pe, 10);
  }
});

test('stage boundaries compound from the previous year without resets or extra years', () => {
  const result = calculate({ ...base, stages: [
    stage(5, 20), stage(5, 3),
  ] });
  assert.equal(result.annual.length, 10);
  close(result.annual[4].earnings, 1.2 ** 5);
  close(result.annual[5].earnings, 1.2 ** 5 * 1.03);
  close(result.earnings, 1.2 ** 5 * 1.03 ** 5);
  for (const s of result.scenarios) {
    const divisor = 1 + (s.rate + base.premium) / 100;
    const expected = Array.from({ length: 10 }, (_, index) => {
      const year = index + 1;
      return 1.2 ** Math.min(year, 5) * 1.03 ** Math.max(0, year - 5) / divisor ** year;
    });
    s.annual.forEach((a, index) => close(a.pv, expected[index]));
    close(s.forecastPV, expected.reduce((sum, value) => sum + value, 0));
    close(s.annual.at(-1).cumulative, s.forecastPV);
    close(s.terminalPV, 1.2 ** 5 * 1.03 ** 5 * (100 / s.rate) / divisor ** 10);
  }
});

test('FCFE ratio scales annual cash flows and valuation, including zero and above 100%', () => {
  const full = calculate(base);
  for (const fcfeRatio of [0, 30, 60, 150]) {
    const partial = calculate({ ...base, stages: [stage(1, 0, fcfeRatio)], terminalRatio: fcfeRatio });
    partial.annual.forEach((a) => close(a.fcfe, a.earnings * fcfeRatio / 100));
    partial.scenarios.forEach((s, index) => {
      close(s.pe, full.scenarios[index].pe * fcfeRatio / 100);
      close(s.terminalPE, full.scenarios[index].terminalPE * fcfeRatio / 100);
      assert.ok(Number.isFinite(s.terminalShare));
    });
  }
});

test('negative growth and a complete earnings loss remain finite', () => {
  const result = calculate({ ...base, stages: [stage(2, -50), stage(1, -100), stage(2, 20)] });
  assert.deepEqual(result.annual.map((a) => a.earnings), [0.5, 0.25, 0, 0, 0]);
  result.scenarios.forEach((s) => {
    const divisor = 1 + (s.rate + base.premium) / 100;
    close(s.terminalPV, 0);
    close(s.pe, 0.5 / divisor + 0.25 / divisor ** 2);
  });
});

test('higher risk-free rates reduce both forecast and terminal present values', () => {
  const scenarios = calculate(base).scenarios;
  assert.ok(scenarios[0].pe > scenarios[1].pe && scenarios[1].pe > scenarios[2].pe);
  assert.ok(scenarios[0].forecastPV > scenarios[1].forecastPV && scenarios[1].forecastPV > scenarios[2].forecastPV);
  assert.ok(scenarios[0].terminalPV > scenarios[1].terminalPV && scenarios[1].terminalPV > scenarios[2].terminalPV);
  for (const s of scenarios) close(s.pe, s.forecastPV + s.terminalPV);
});

test('higher equity premium reduces both present values while preserving the exit multiple', () => {
  const a = calculate(base).scenarios[0];
  const b = calculate({ ...base, premium: 10 }).scenarios[0];
  assert.ok(b.forecastPV < a.forecastPV && b.terminalPV < a.terminalPV);
  assert.equal(a.terminalPE, b.terminalPE);
});

test('scenario parsing accepts common separators, percentages and duplicates', () => {
  assert.deepEqual(parseRates('6%, 2％，4; 2；.5、3.25'), [0.5, 2, 3.25, 4, 6]);
  for (const text of ['', '0', '-2', '101', '2foo', 'Infinity', 'NaN', '2%%', '1e2', Array(21).fill('2').join(',')]) {
    assert.throws(() => parseRates(text), /rates/);
  }
});

test('invalid assumptions are rejected instead of silently coerced', () => {
  for (const [override, code] of [
    [{ stages: [] }, 'stages'], [{ stages: Array(21).fill({ years: 1, growth: 0 }) }, 'stages'],
    [{ stages: [{ years: 1.5, growth: 0 }] }, 'years'], [{ stages: [{ years: NaN, growth: 0 }] }, 'years'],
    [{ stages: [{ years: 0, growth: 0 }] }, 'years'],
    [{ stages: [stage(60, 0), stage(41, 0)] }, 'horizon'],
    [{ stages: [{ years: 1, growth: -101 }] }, 'growth'], [{ stages: [{ years: 1, growth: NaN }] }, 'growth'],
    [{ premium: NaN }, 'premium'], [{ premium: -1 }, 'premium'], [{ premium: 101 }, 'premium'],
    [{ premium: undefined }, 'premium'], [{ premium: Infinity }, 'premium'],
    [{ stages: [stage(1, 0, NaN)] }, 'stageRatio'], [{ stages: [stage(1, 0, Infinity)] }, 'stageRatio'],
    [{ stages: [stage(1, 0, -1)] }, 'stageRatio'], [{ stages: [{ years: 1, growth: 0 }] }, 'stageRatio'],
    [{ terminalRatio: NaN }, 'terminalRatio'], [{ terminalRatio: Infinity }, 'terminalRatio'],
    [{ terminalRatio: -1 }, 'terminalRatio'], [{ terminalRatio: undefined }, 'terminalRatio'],
    [{ rates: [0] }, 'rates'], [{ rates: [] }, 'rates'], [{ rates: [NaN] }, 'rates'],
  ]) assert.throws(() => calculate({ ...base, ...override }), new RegExp(code));
});

test('extremely small capitalization rates never display Infinity', () => {
  assert.throws(() => calculate({ ...base, rates: [Number.MIN_VALUE] }), /overflow/);
});

test('30% FCFE ratio reproduces the 17.44 PE example without changing earnings growth', () => {
  const result = calculate({ stages: [stage(5, 20, 30), stage(5, 3, 30)],
    premium: 10, terminalRatio: 30, rates: [2] });
  close(result.scenarios[0].forecastPV, 3.5125814535270306);
  close(result.scenarios[0].terminalPV, 13.931676651867203);
  close(result.scenarios[0].pe, 17.444258105394233);
  close(result.earnings, 1.2 ** 5 * 1.03 ** 5);
});

test('extreme FCFE ratios fail safely on overflow', () => {
  assert.throws(() => calculate({ ...base, terminalRatio: Number.MAX_VALUE, rates: [0.000001] }), /overflow/);
  assert.throws(() => calculate({ ...base, stages: [stage(2, 1000, Number.MAX_VALUE)] }), /overflow/);
});

test('each year uses its stage ratio, including the boundary year', () => {
  const result = calculate({ ...base, stages: [stage(2, 20, 30), stage(2, 3, 80)], terminalRatio: 60 });
  assert.deepEqual(result.annual.map((a) => a.fcfeRatio), [30, 30, 80, 80]);
  for (const s of result.scenarios) {
    const earnings = [1.2, 1.2 ** 2, 1.2 ** 2 * 1.03, 1.2 ** 2 * 1.03 ** 2];
    const cash = earnings.map((e, index) => e * (index < 2 ? 0.3 : 0.8));
    s.annual.forEach((a, index) => close(a.fcfe, cash[index]));
    close(s.forecastPV, cash.reduce((sum, c, index) => sum + c / (1 + s.discount / 100) ** (index + 1), 0));
    close(s.terminalPV, earnings[3] * 0.6 / (s.rate / 100) / (1 + s.discount / 100) ** 4);
  }
});

test('changing a stage ratio only changes its forecast cash, not earnings or exit value', () => {
  const original = calculate({ ...base, stages: [stage(2, 20, 30), stage(2, 3, 80)] });
  const changed = calculate({ ...base, stages: [stage(2, 20, 70), stage(2, 3, 80)] });
  assert.equal(changed.earnings, original.earnings);
  assert.deepEqual(changed.annual.slice(2), original.annual.slice(2));
  changed.scenarios.forEach((s, index) => {
    assert.ok(s.forecastPV > original.scenarios[index].forecastPV);
    assert.equal(s.terminalPV, original.scenarios[index].terminalPV);
  });
});

test('long-run ratio changes terminal value without rewriting the final forecast cash flow', () => {
  const a = calculate({ ...base, stages: [stage(5, 20, 30), stage(5, 3, 70)], terminalRatio: 100 });
  const b = calculate({ ...base, stages: [stage(5, 20, 30), stage(5, 3, 70)], terminalRatio: 40 });
  assert.deepEqual(a.annual, b.annual);
  b.scenarios.forEach((s, index) => {
    assert.equal(s.forecastPV, a.scenarios[index].forecastPV);
    close(s.terminalPV, a.scenarios[index].terminalPV * 0.4);
  });
});

test('zero forecast and zero terminal ratios are independent', () => {
  const noForecast = calculate({ ...base, stages: [stage(1, 0, 0)], terminalRatio: 100 });
  const noTerminal = calculate({ ...base, terminalRatio: 0 });
  noForecast.scenarios.forEach((s) => { close(s.forecastPV, 0); assert.ok(s.pe > 0); });
  noTerminal.scenarios.forEach((s) => { close(s.terminalPV, 0); close(s.pe, s.forecastPV); });
});
