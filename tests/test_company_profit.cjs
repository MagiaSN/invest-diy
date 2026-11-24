const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const M = require('../investdiy/company_profit/web/model.js');
const P = require('../investdiy/company_profit/web/presets.js');
const D = JSON.parse(fs.readFileSync(path.join(__dirname, '../investdiy/company_profit/data/out/history.json')));
const close = (a, b, tolerance = 1e-7) => assert.ok(Math.abs(a - b) < tolerance, `${a} != ${b}`);
const clone = value => JSON.parse(JSON.stringify(value));

test('tonnes, 10,000 tonnes, grams and CNY 100m use independent hand calculations', () => {
  const input = {metals: M.ids.map(id => ({id,production:1,price:0,cost:0})), tax:25,share:80,other:0,associate:0,adjustment:0};
  input.metals[0].price = 500; input.metals[0].cost = 200; // 1 tonne * CNY 300/g = CNY 300m
  input.metals[1].price = 60000; input.metals[1].cost = 40000; // 10kt * CNY 20,000/t = CNY 200m
  const result = M.estimate(input);
  close(result.gp, 5); close(result.net, 3.75); close(result.parent, 3); close(result.nci, .75);
});

test('all historical baseline calibrations reconcile both income attribution and tax', () => {
  for (const base of D.history) {
    const result = M.estimate(M.defaults(base, false));
    close(result.parent, base.actual); close(result.net, base.net); close(result.nci, base.nci);
    close(result.net, result.coreParent + result.nci);
  }
});

test('interim annualization scales flows but leaves prices, costs, tax and attribution fixed', () => {
  const base = D.history.find(r => r.year === '20269M');
  const input = M.defaults(base); close(input.metals[0].production, 66.793 * 4 / 3);
  close(input.metals[0].price, base.metals[0].price);
  close(M.estimate(input).parent, base.actual * 4 / 3);
});

test('annual tests consume reported sales, price and cost and freeze the rest of the model', () => {
  for (const [company, data] of [['zijin', D], ['cmoc', D.cmoc], ['cnooc', D.cnooc]]) {
    const history = clone(data.history), target = history.find(r => r.year === '2025');
    const predict = () => M.backtest(history, target.year, company);
    const before = predict();
    before.input.metals.forEach((m, i) => {
      const actual = target.metals[i];
      close(m.production * M.products[m.id].salesScale, actual.sales);
      close(m.price, actual.price); close(m.cost, actual.cost);
      close(M.estimate(before.input, company).metals[i].gp, actual.gp);
    });
    Object.assign(target, {actual:1, net:1, nci:0, pretax:1, tax:.9, taxWindow:{pretax:100, expense:55}, share:.1, associate:9000, other:9000, gp:1});
    target.metals.forEach(m => { m.production = 1; m.conversion = .01; m.gp = 1; });
    close(before.predicted, predict().predicted);
    target.metals[0].sales *= .5;
    assert.ok(predict().predicted < before.predicted);
    target.metals[0].sales *= 2;
    target.metals[0].cost += 100;
    assert.ok(predict().predicted < before.predicted);
    for (const period of ['2026H1', '20269M']) assert.throws(() => M.backtest(history, period, company), /annual/);
  }
});

test('annual validation meets preset gates; original 2022 output is preserved', () => {
  const first = D.history.find(r => r.year === '2022');
  assert.equal(first.year, '2022'); close(first.metals[1].production,87.7317); close(first.metals[3].production,387.458);
  const rows = M.annualBacktests(D.history, 'zijin');
  const stats = M.metrics(rows);
  assert.ok(stats.mape <= D.thresholds.mape); assert.ok(stats.maxError <= D.thresholds.maxError);
  close(stats.mape, 2.49, .005); close(stats.maxError, 6.09, .005);
  rows.forEach((r, i) => close(r.error, [-6.09, -1.74, -2.45, 1.72, -.44][i], .005));
  // Positive price sensitivity is economically necessary in the calibrated regime.
  const input = M.defaults(D.history.find(r => r.year === '2025')); const initial = M.estimate(input).parent;
  for (let i = 0; i < 4; i++) { const changed = clone(input); changed.metals[i].price *= 1.1; assert.ok(M.estimate(changed).parent > initial); }
});

test('no automatic tax asset on losses; incremental attributable adjustments are separate', () => {
  const input = M.defaults(D.history.find(r => r.year === '2025')); input.metals.forEach(m => { m.price = 0; });
  const loss = M.estimate(input); assert.ok(loss.parent < 0); close(loss.tax,0);
  input.adjustment = 10; const adjusted = M.estimate(input); close(adjusted.parent,loss.parent+10); close(adjusted.net,loss.net);
});

test('empty strings, non-finite values, negative quantities and invalid ownership fail closed', () => {
  const base = M.defaults(D.history.find(r => r.year === '2025'));
  for (const value of ['', null, NaN, Infinity, -1]) { const input = clone(base); input.metals[0].production = value; assert.throws(() => M.estimate(input)); }
  for (const value of [101, -1, Infinity]) { const input = clone(base); input.share = value; assert.throws(() => M.estimate(input)); }
});

test('exported offline HTML is self-contained, with data and scripts embedded', () => {
  const html = fs.readFileSync(path.join(__dirname,'../investdiy/company_profit/data/out/company-profit.html'),'utf8');
  assert.ok(!/<script\s+src=/.test(html)); assert.ok(!/<link\s+rel="stylesheet"/.test(html)); assert.ok(html.includes('window.CompanyProfitData = '));
});

test('production guidance preserves the disclosed ranges and does not invent zinc-only or 2027 targets', () => {
  assert.deepEqual(P.production('2026'), {gold:105,copper:120,silver:520});
  assert.deepEqual(P.production('2028-low'), {gold:130,copper:150,silver:600});
  assert.deepEqual(P.production('2028-mid'), {gold:135,copper:155,silver:650});
  assert.deepEqual(P.production('2028-high'), {gold:140,copper:160,silver:700});
  assert.throws(() => P.production('2027'));
  const input = M.defaults(D.history.find(r => r.year === '2025'), false), before = clone(input);
  const plan = P.production('2026');
  input.metals.forEach(m => { if (Object.hasOwn(plan,m.id)) m.production = plan[m.id]; });
  close(input.metals[2].production,before.metals[2].production);
  input.metals.forEach((m,i) => { close(m.price,before.metals[i].price); close(m.cost,before.metals[i].cost); });
  close(input.tax,before.tax); close(input.share,before.share);
});

test('market price conversion handles silver kilograms, VAT and realization independently', () => {
  close(P.realizedPrice({id:'gold',price:1000,unit:'CNY/g'},0,95),950);
  close(P.realizedPrice({id:'copper',price:113000,unit:'CNY/t'},13,90),90000);
  close(P.realizedPrice({id:'silver',price:11300,unit:'CNY/kg'},13,90),9);
  close(P.realizedPrice({id:'zinc',price:22600,unit:'CNY/t'},13,100),20000);
  const quote={id:'silver',price:11300,unit:'CNY/kg'};
  for (const vat of [NaN,-1,31,Infinity]) assert.throws(() => P.realizedPrice(quote,vat,100));
  for (const ratio of [NaN,0,-1,201]) assert.throws(() => P.realizedPrice(quote,13,ratio));
  for (const price of [0,-1,NaN,Infinity]) assert.throws(() => P.realizedPrice({...quote,price},13,100));
  assert.throws(() => P.realizedPrice({...quote,unit:'CNY/g'},13,100));
});


test('gold uses troy ounces; copper uses metric tonnes and avoirdupois pounds', () => {
  close(P.toBasePrice('gold', 31.1034768, 'USD/oz', 7), 7);
  close(P.fromBasePrice('gold', 7, 'USD/oz', 7), 31.1034768);
  close(P.toBasePrice('copper', 10000, 'USD/t', 7), 70000);
  close(P.toBasePrice('copper', 4.5359237, 'USD/lb', 7), 70000);
  close(P.fromBasePrice('copper', 70000, 'USD/lb', 7), 4.5359237);
  for (const [id, units] of Object.entries(P.priceUnits)) {
    for (const unit of units) close(P.toBasePrice(id, P.fromBasePrice(id, 1234.56789, unit, 7.123456), unit, 7.123456), 1234.56789);
  }
  close(P.toBasePrice('gold', 900, 'CNY/g', undefined), 900);
  for (const fx of [0, -1, NaN, Infinity, undefined]) assert.throws(() => P.toBasePrice('gold', 1000, 'USD/oz', fx));
  assert.throws(() => P.toBasePrice('gold', 1, 'USD/lb', 7));
  assert.throws(() => P.toBasePrice('copper', -1, 'CNY/t', 7));
  assert.throws(() => P.toBasePrice('copper', 1e7, 'USD/t', 7));
});

test('latest snapshot applies a complete dated set with explicit tax conversion', () => {
  const snapshot = {fetched_at:'2026-11-19T16:00:00+08:00', fx:{cny_per_usd:7,as_of:'2026-11-18'},
    conversion:{vat_pct:{gold:0,copper:13,zinc:13,silver:13},realization_pct:100},
    quotes:[['gold',900,'CNY/g'],['copper',113000,'CNY/t'],['zinc',22600,'CNY/t'],['silver',11300,'CNY/kg']]
      .map(([id,price,unit]) => ({id,price,unit,quoted_at:'2026-11-19T15:00:00+08:00'}))};
  const values = P.snapshotPrices(snapshot);
  for (const [i, expected] of [900,100000,20000,10].entries()) close(values[i].price, expected);
  for (const bad of [null, {...snapshot,fx:null}, {...snapshot,quotes:snapshot.quotes.slice(1)}, {...snapshot,conversion:null}]) assert.throws(() => P.snapshotPrices(bad));
});

test('CMOC historical product economics reconcile to reported product and group results', () => {
  const history = D.cmoc.history;
  for (const base of history) {
    const result = M.estimate(M.defaults(base, false), 'cmoc');
    close(result.parent, base.actual); close(result.net, base.net); close(result.nci, base.nci);
    result.metals.forEach((m, i) => close(m.gp, base.metals[i].gp));
  }
  const recent = history.at(-1);
  const byId = Object.fromEntries(recent.metals.map(m => [m.id, m]));
  close(byId.gold.production, 160913 * 31.1034768 / 1e6);
  close(byId.gold.price, 4707290 * 1000 / (158064 * 31.1034768));
  close(byId.cobalt.conversion, 12661 / 99694);
  close(byId.phosphate.production, 83.102);
  close(byId.tungsten.production, 5034);
  close(recent.actual, 240.1951286956);
  assert.throws(() => M.estimate(M.defaults(recent), 'zijin'));
});

test('CMOC guidance uses the disclosed unit ranges', () => {
  const bounds = {
    copper: [76, 82], cobalt: [10, 12], molybdenum: [11500, 14500],
    tungsten: [6500, 7500], niobium: [10000, 11000], gold: [6, 8], phosphate: [105, 125],
  };
  for (const [id, [low, high]] of Object.entries(bounds)) {
    close(P.production('2026-low', 'cmoc')[id], low);
    close(P.production('2026-high', 'cmoc')[id], high);
    close(P.production('2026-mid', 'cmoc')[id], (low + high) / 2);
  }
});

test('CMOC separates mining revenue exposure from unit margins and allocates only incremental profit', () => {
  const history = D.cmoc.history;
  const rows = ['2024', '2025'].map(y => M.backtest(history, y, 'cmoc'));
  const stats = M.metrics(rows);
  close(rows[0].predicted, 144.48, .005); close(rows[1].predicted, 194.09, .005);
  close(stats.mape, 5.67, .005); close(stats.maxError, 6.77, .005);
  close(rows[0].input.share, rows[0].input.marginalShare);
  const input = rows[1].input, a = history.find(r => r.year === '2023'), b = history.find(r => r.year === '2024');
  close(input.marginalShare, 100 * (b.actual - a.actual) / (b.net - a.net));
  const r = M.estimate(input, 'cmoc');
  close(r.parent, b.actual + (r.net - b.net) * input.marginalShare / 100);
  const trial = clone(input); trial.metals[0].cost += 1000;
  const changed = M.estimate(trial, 'cmoc');
  close(changed.other, r.other); assert.ok(changed.gp < r.gp);
  trial.metals.forEach(m => { m.price = 0; });
  const loss = M.estimate(trial, 'cmoc');
  assert.ok(loss.net < 0); close(loss.parent, loss.net * input.share / 100);
  const interim = history.at(-1), annualized = M.defaults(interim, true, history);
  close(annualized.months, 12);
  close(M.estimate(annualized, 'cmoc').parent, interim.actual * 12 / interim.months);
  for (const previous of [{...a, net:b.net}, {...a, actual:b.actual + 1}]) {
    const fallback = M.defaults(b, false, [previous, b]);
    close(fallback.marginalShare, fallback.share);
  }
});

test('five-year windows roll on a new annual report and exclude interim reports', () => {
  for (const [company, data] of [['zijin', D], ['cmoc', D.cmoc], ['cnooc', D.cnooc]]) {
    const history = clone(data.history);
    const years = () => M.annualBacktests(history, company).map(r => r.year);
    assert.deepEqual(years(), ['2021', '2022', '2023', '2024', '2025']);
    history.unshift({...history.find(r => r.year === '2025'), year:'2026'});
    assert.deepEqual(years(), ['2022', '2023', '2024', '2025', '2026']);
  }
});

test('CMOC grouped annual disclosures reconcile across the 2023 reporting transition', () => {
  const history = D.cmoc.history;
  const rows = M.annualBacktests(history, 'cmoc');
  close(M.metrics(rows).mape, 8.67, .005); close(M.metrics(rows).maxError, 19.72, .005);
  rows.forEach((r, i) => close(r.error, [19.72, -10.48, 1.80, 6.77, -4.57][i], .005));
  const first = M.estimate(rows[0].input, 'cmoc').metals[0];
  close(first.sales, 205081 + 17085);
  close(first.revenue, 13268256624.20 / 1e8);
  close(first.totalCost, 6241622321.72 / 1e8);
  const base = history.find(r => r.year === '2022');
  const result = M.estimate(rows[2].input, 'cmoc');
  close(result.associate, base.associate);
});

test('monthly items follow scenario duration independently of metal margins', () => {
  for (const [company, history, line] of [['zijin', D.history, 'other'], ['cmoc', D.cmoc.history, 'associate']]) {
    const base = history.find(r => r.year === '20269M');
    const input = M.defaults(base, false, history);
    input.metals.find(m => m.id === 'copper').price *= 2;
    close(M.estimate(input, company)[line], base[line]);
    input.months = 12;
    close(M.estimate(input, company)[line], base[line] * 12 / 9);
  }
});

test('CMOC forecast tax pools only the last three completed fiscal years at the baseline', () => {
  const history = D.cmoc.history;
  const annual = new Map([[2018, [69.8985741563, 18.3981590939]], [2019, [23.5844846392, 5.9260008607]]]);
  for (const r of history.filter(r => r.months === 12)) annual.set(Number(r.year), [r.pretax, r.tax * r.pretax]);
  for (const base of history) {
    const last = Number(base.year.slice(0, 4)) - (base.months < 12 ? 1 : 0);
    const years = [last - 2, last - 1, last].map(y => annual.get(y));
    const pretax = years.reduce((sum, v) => sum + v[0], 0);
    const expense = years.reduce((sum, v) => sum + v[1], 0);
    assert.equal(base.taxWindow.firstYear, last - 2); assert.equal(base.taxWindow.lastYear, last);
    close(M.defaults(base, false, history, 'forecast').tax, 100 * expense / pretax);
    close(M.defaults(base, false, history).tax, base.tax * 100);
  }
  const base = history.at(-1);
  for (const taxWindow of [undefined, {pretax:0, expense:1}, {pretax:100, expense:70}]) {
    close(M.defaults({...base, taxWindow}, false, history, 'forecast').tax, base.tax * 100);
  }
});

test('CNOOC cost allocation, native sales units and signed minority earnings reconcile', () => {
  for (const base of D.cnooc.history) {
    const result = M.estimate(M.defaults(base, false), 'cnooc');
    close(result.parent, base.actual);
    close(result.gp, base.gp);
    close(result.nci, base.nci);
  }
  const fy = D.cnooc.history.find(r => r.year === '2025');
  const input = M.defaults(fy, false);
  const [oil, gas] = M.estimate(input, 'cnooc').metals;
  close(oil.production, 589.2); close(gas.production, 984);
  close(oil.revenue, 2797.86); close(gas.revenue, 558.66);
  close(oil.cost, 136138 / 757.6);
  close(oil.totalCost + gas.totalCost, 1361.38);
  for (const id of ['oil', 'gas']) {
    const shock = clone(input);
    shock.metals.find(m => m.id === id).price *= 1.1;
    assert.ok(M.estimate(shock, 'cnooc').parent > fy.actual);
  }
  const rows = M.annualBacktests(D.cnooc.history, 'cnooc');
  close(M.metrics(rows).mape, 5.20, .005);
  close(M.metrics(rows).maxError, 11.48, .005);
});

test('CNOOC net production guidance scales consolidated oil and gas sales separately', () => {
  const guidance = D.cnooc.guidance;
  for (const [id, total] of Object.entries({'2026-low':780, '2026-mid':790, '2026-high':800})) {
    const plan = P.production(id, 'cnooc', guidance);
    close(plan.oil, 303.6 / 398.7 * total, .00005);
    close(plan.gas, 492.3 / 398.7 * total, .00005);
  }
});

const CATL = require('../investdiy/company_profit/web/catl-model.js');

test('CATL reconciles original product gross profits, annual earnings and signed losses', () => {
  for (const r of D.catl.history) {
    const input = CATL.annualInputs(r);
    const value = CATL.estimate(input);
    close(value.ev, r.products.ev.revenue - r.products.ev.cost);
    close(value.storage, r.products.storage.revenue - r.products.storage.cost);
    close(input.otherGrossPerWh * (input.evVolume + input.storageVolume) * 10, r.ancillaryBusinessGross);
    close(value.otherBusiness, r.ancillaryBusinessGross);
    close(value.gp, r.groupGross);
    close(value.parent, r.parent);
  }
  const q4 = CATL.quarterInputs(D.catl);
  const nineMonths = D.catl.forecast.nineMonths.parent;
  const current = CATL.estimate(q4, nineMonths);
  close(current.annual, current.parent + 645.30063);
  close(current.annual, 936.1711133, 1e-6);
  const shock = CATL.estimate({...q4, evMarginPerWh: q4.evMarginPerWh - .001}, nineMonths);
  close(current.ev - shock.ev, 1.95);
  close(current.storage, shock.storage);
  const loss = CATL.estimate({...q4, evMarginPerWh: -.2});
  assert.ok(loss.parent < 0);
  close(loss.tax, 0);
  assert.throws(() => CATL.estimate({...q4, storageVolume: -1}));
});

test('CATL five-year errors reconcile and forecasts exclude target financial results', () => {
  const history = clone(D.catl.history);
  const rows = CATL.backtests(history);
  assert.deepEqual(rows.map(r => r.year), [2021, 2022, 2023, 2024, 2025]);
  for (const r of rows) {
    assert.equal(r.base, r.year - 1);
    close(Object.values(r.errors).reduce((a, b) => a + b), r.predicted - r.actual);
  }
  const stats = M.metrics(rows);
  assert.ok(stats.mape < 10 && stats.maxError < 10);
  const basis = history.find(r => r.year === 2023);
  const batteryGross = Object.values(basis.products).reduce((n, p) => n + p.revenue - p.cost, 0);
  close(rows[3].input.spendingRate, 100 * (basis.expenses - basis.payroll - 149.116964)
    / (batteryGross - 149.116964));
  // Mutate each held-out year separately, so later years can never leak into an earlier estimate.
  for (const [index, expected] of rows.entries()) {
    const changed = clone(history);
    const target = changed[index + 1];
    for (const key of ['groupGross', 'ancillaryBusinessGross', 'expenses', 'payroll', 'finance', 'associates',
      'interestIncome', 'interestExpense', 'financeFees', 'openingCash', 'closingCash', 'otherIncome',
      'impairment', 'tax', 'pretax', 'net', 'parent']) target[key] *= 1.1;
    // Gross profit and volume are unchanged by equal increments to revenue and cost.
    target.products.ev.revenue += 20;
    target.products.ev.cost += 20;
    close(CATL.backtests(changed.slice(0, index + 2)).at(-1).predicted, expected.predicted);
  }
});

test('CATL cash yields, pooled attribution and payroll floor use reported baselines', () => {
  const h = D.catl.history, fy20 = h[0], r = CATL.backtests(h)[0].input;
  close(r.finance, 14.9460095867 * 684.2411605367 / ((322.6963532707 + 684.2411605367) / 2)
    - 6.4043431654 - .236170414);
  close(r.investment, -.0402733209);
  close(r.taxRate, 100 * (fy20.tax + fy20.priorIncome.tax) / (fy20.pretax + fy20.priorIncome.pretax));
  close(r.parentShare, 100 * (fy20.parent + fy20.priorIncome.parent) / (fy20.net + fy20.priorIncome.net));
  const loss = CATL.estimate({...r, evMarginPerWh: -1, storageMarginPerWh: -1});
  close(loss.expenses, -r.payroll);
  close(loss.tax, 0);
});

test('CATL version 1 and 2 scenarios retain their original volume-based profit bridges', () => {
  const input = {evVolume: 20, storageVolume: 5, evMarginPerWh: .12, storageMarginPerWh: .08,
    expensePerGWh: 2e7, otherGrossPerGWh: 1e7, finance: 2, investment: 1, otherIncome: 3,
    impairment: -2, remaining: -1, nonRecurring: 2, taxRate: 20, parentShare: 90};
  const {evMarginPerWh, storageMarginPerWh, ...common} = input;
  for (const old of [input, {...common, evMargin: evMarginPerWh * 1e9, storageMargin: storageMarginPerWh * 1e9}]) {
    const result = CATL.estimate(old);
    close(result.expenses, -5);
    close(result.otherGross, 2.5);
    close(result.parent, (24 + 4 + 2.5 - 5 + 5) * .8 * .9);
  }
});
