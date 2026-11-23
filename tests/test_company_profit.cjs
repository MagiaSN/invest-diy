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
  for (const [company, data] of [['zijin', D], ['cmoc', D.cmoc]]) {
    const history = clone(data.history), target = history.find(r => r.year === '2025');
    const predict = () => M.backtest(history, target.year, company);
    const before = predict();
    before.input.metals.forEach((m, i) => {
      const actual = target.metals[i];
      close(m.production * M.products[m.id].salesScale, actual.sales);
      close(m.price, actual.price); close(m.cost, actual.cost);
      close(M.estimate(before.input, company).metals[i].gp, actual.gp);
    });
    Object.assign(target, {actual:1, net:1, nci:0, pretax:1, tax:.9, share:.1, associate:9000, other:9000, gp:1});
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
  close(stats.mape, 9.27, .005); close(stats.maxError, 24.24, .005);
  close(rows[0].error, -24.24, .005);
  assert.ok(rows[1].error < 0 && rows[2].error < 0);
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
  close(rows[0].predicted, 142.24, .005); close(rows[1].predicted, 186.89, .005);
  close(stats.mape, 6.61, .005); close(stats.maxError, 8.11, .005);
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
  for (const [company, data] of [['zijin', D], ['cmoc', D.cmoc]]) {
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
  close(M.metrics(rows).mape, 15.38, .005); close(M.metrics(rows).maxError, 33.64, .005);
  const first = M.estimate(rows[0].input, 'cmoc').metals[0];
  close(first.sales, 205081 + 17085);
  close(first.revenue, 13268256624.20 / 1e8);
  close(first.totalCost, 6241622321.72 / 1e8);
  const base = history.find(r => r.year === '2022');
  const result = M.estimate(rows[2].input, 'cmoc');
  close(result.associate, (result.metals[0].gp + result.metals[1].gp) * base.associate / base.metals[0].gp);
  assert.equal(rows[3].input.groupedCopperDriver, undefined);
});
