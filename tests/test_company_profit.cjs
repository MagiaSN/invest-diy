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
  const input = {metals: M.ids.map(id => ({id,production:1,conversion:1,price:0,cost:0})), tax:25,share:80,other:0,associate:0,adjustment:0};
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
  const input = M.defaults(base); close(input.metals[0].production, 70.13 * 4 / 3);
  close(input.metals[0].price, base.metals[0].price);
  close(M.estimate(input).parent, base.actual * 4 / 3);
});

test('walk-forward predictions do not consume target costs, sales, profits, tax, NCI or bridge parameters', () => {
  const before = M.backtest(D.history, '2025');
  const history = clone(D.history), target = history.find(r => r.year === '2025');
  Object.assign(target, {actual:1,net:1,nci:0,pretax:1,tax:.9,share:.1,associate:9000,other:9000,gp:1});
  target.metals.forEach(m => { m.cost = 1e6; m.sales = 1; m.conversion = .01; m.gp = 1; });
  close(before.predicted, M.backtest(history, '2025').predicted);
});

test('annual validation meets preset gates; original 2022 output is preserved', () => {
  const first = D.history[0];
  assert.equal(first.year, '2022'); close(first.metals[1].production,87.7317); close(first.metals[3].production,387.458);
  const rows = ['2023','2024','2025'].map(y => M.backtest(D.history,y));
  const stats = M.metrics(rows);
  assert.ok(stats.mape <= D.thresholds.mape); assert.ok(stats.maxError <= D.thresholds.maxError);
  assert.ok(rows[0].error > 17 && rows[0].error < 18);
  assert.ok(rows[1].error < 0 && rows[2].error < 0);
  // Positive price sensitivity is economically necessary in the calibrated regime.
  const input = M.defaults(D.history[3]); const initial = M.estimate(input).parent;
  for (let i = 0; i < 4; i++) { const changed = clone(input); changed.metals[i].price *= 1.1; assert.ok(M.estimate(changed).parent > initial); }
});

test('no automatic tax asset on losses; incremental attributable adjustments are separate', () => {
  const input = M.defaults(D.history[3]); input.metals.forEach(m => { m.price = 0; });
  const loss = M.estimate(input); assert.ok(loss.parent < 0); close(loss.tax,0);
  input.adjustment = 10; const adjusted = M.estimate(input); close(adjusted.parent,loss.parent+10); close(adjusted.net,loss.net);
});

test('empty strings, non-finite values, negative quantities and invalid ownership fail closed', () => {
  const base = M.defaults(D.history[3]);
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
  const input = M.defaults(D.history[3], false), before = clone(input);
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
