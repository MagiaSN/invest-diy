(function () {
  'use strict';
  const M = window.CompanyProfitModel, D = window.CompanyProfitData, P = window.CompanyProfitPresets, $ = id => document.getElementById(id), t = (k, v) => i18n.t(k, v);
  if (!D) { $('error').hidden = false; $('error').textContent = t('common.failed'); $('results').hidden = true; $('download').disabled = true; return; }
  const fmt = (v, digits = 2) => new Intl.NumberFormat(i18n.lang === 'zh' ? 'zh-CN' : 'en', {maximumFractionDigits: digits, minimumFractionDigits: digits}).format(v);
  const annual = ['2023', '2024', '2025'].map(y => M.backtest(D.history, y));
  const extension = ['2026H1', '20269M'].map(y => M.backtest(D.history, y));
  const stats = M.metrics(annual);
  const period = y => i18n.has('period.' + y) ? t('period.' + y) : y;
  const fields = [ ['tax', 0, 60], ['share', 0, 100], ['associate', -100, 200], ['other', -200, 200], ['adjustment', -10000, 10000] ];
  let base, input, current, valid = false, productionApplied = null;
  const snapshot = D.market, fx = snapshot?.fx?.cny_per_usd;
  const units = Object.fromEntries(M.ids.map(id => [id, P.priceUnits[id][0]]));
  const priceValues = {};
  let marketApplied = null, latest = null;
  try { latest = P.snapshotPrices(snapshot); } catch (_) { /* Historical/manual inputs remain available. */ }
  const priceDigits = id => units[id] === 'USD/lb' ? 6 : 4;
  function priceLimit(id) {
    const scale = 10 ** priceDigits(id);
    return Math.ceil(P.fromBasePrice(id, 1e7, units[id], fx) * scale) / scale;
  }
  function setPrice(id, value) {
    const el = $(id + '-price');
    el.value = Number(P.fromBasePrice(id, value, units[id], fx).toFixed(priceDigits(id)));
    priceValues[id] = {display: el.value, value};
  }
  function readPrice(id) {
    const el = $(id + '-price');
    // Keep the canonical price when only its display unit or language changes.
    if (priceValues[id]?.display === el.value) return priceValues[id].value;
    try { return P.toBasePrice(id, el.valueAsNumber, units[id], fx); }
    catch (error) { el.setAttribute('aria-invalid', 'true'); throw error; }
  }
  function priceField(m) {
    const wrapper = document.createElement('div'); wrapper.className = 'price-field';
    const max = priceLimit(m.id);
    wrapper.append(field(m.id + '-price', `${t('price')} (${t('unit.' + units[m.id])})`, P.fromBasePrice(m.id, m.price, units[m.id], fx), 0, max));
    if (P.priceUnits[m.id].length > 1) {
      const select = document.createElement('select'); select.id = m.id + '-price-unit';
      select.setAttribute('aria-label', t('price.unit', {metal:t(m.id)}));
      P.priceUnits[m.id].forEach(unit => {
        const option = document.createElement('option'); option.value = unit; option.textContent = t('unit.' + unit);
        option.disabled = unit.startsWith('USD/') && !(Number.isFinite(fx) && fx > 0);
        select.append(option);
      });
      select.value = units[m.id];
      select.addEventListener('change', () => {
        try {
          const value = readPrice(m.id);
          units[m.id] = select.value; setPrice(m.id, value);
          $(m.id + '-price').max = priceLimit(m.id);
          wrapper.querySelector('label span').textContent = `${t('price')} (${t('unit.' + units[m.id])})`;
          renderResult(); renderSnapshot();
        } catch (_) { select.value = units[m.id]; renderResult(); }
      });
      wrapper.append(select);
    }
    return wrapper;
  }
  function field(id, label, value, min, max) {
    const wrapper = document.createElement('label'); wrapper.htmlFor = id;
    const span = document.createElement('span'); span.textContent = label;
    const el = document.createElement('input'); el.id = id; el.type = 'number'; el.step = 'any'; el.required = true;
    el.min = min; el.max = max; el.value = Number(value.toFixed(4));
    wrapper.append(span, el); return wrapper;
  }
  function buildInputs() {
    $('metal-inputs').replaceChildren(); $('advanced-inputs').replaceChildren();
    input.metals.forEach((m, i) => {
      const el = document.createElement('div'); el.className = 'metal-row';
      const name = document.createElement('div'); name.className = 'metal-name';
      const symbol = document.createElement('b'); symbol.textContent = ['Au', 'Cu', 'Zn', 'Ag'][i];
      const label = document.createElement('span'); label.textContent = t(m.id); name.append(symbol, label); el.append(name);
      const qu = t(i === 0 || i === 3 ? 'unit.tonne' : 'unit.10kt');
      const pu = t(i === 0 || i === 3 ? 'unit.gram' : 'unit.priceT');
      el.append(field(m.id + '-production', `${t('production')} (${qu})`, m.production, 0, 1e6), priceField(m), field(m.id + '-cost', `${t('cost')} (${pu})`, m.cost, 0, 1e7));
      $('metal-inputs').append(el); setPrice(m.id, m.price);
      $('advanced-inputs').append(field(m.id + '-conversion', `${t(m.id)} · ${t('conversion')} (%)`, m.conversion * 100, 0, 500));
    });
    fields.forEach(([key, min, max]) => $('advanced-inputs').append(field(key, t(key), input[key], min, max)));
  }
  function read() {
    let ok = true;
    $('inputs').querySelectorAll('input').forEach(el => { const bad = el.value.trim() === '' || !el.validity.valid || !Number.isFinite(el.valueAsNumber); el.setAttribute('aria-invalid', String(bad)); if (bad) ok = false; });
    if (!ok) throw new Error('invalid');
    const result = {metals: M.ids.map(id => ({id, production: $(id + '-production').valueAsNumber, price: readPrice(id), cost: $(id + '-cost').valueAsNumber, conversion: $(id + '-conversion').valueAsNumber / 100}))};
    fields.forEach(([k]) => { result[k] = $(k).valueAsNumber; }); return result;
  }
  function row(values, cls) {
    const tr = document.createElement('tr'); if (cls) tr.className = cls;
    values.forEach(value => { const td = document.createElement('td'); td.textContent = value; tr.append(td); }); return tr;
  }
  function renderResult() {
    try { input = read(); current = M.estimate(input); valid = true; } catch (_) { valid = false; }
    $('error').hidden = valid; $('error').textContent = t('error'); $('results').hidden = !valid; $('download').disabled = !valid;
    for (const id of ['parent', 'net', 'gross']) $(id).textContent = valid ? fmt(current[id === 'gross' ? 'gp' : id]) : '—';
    $('apply-price-preset').disabled = !latest;
    $('price-preset').disabled = !latest;
    $('bull').disabled = !valid || input.metals.some(m => m.price * 1.1 > 1e7);
    $('bear').disabled = !valid;
    if (!valid) { $('band').textContent = ''; $('scenario-warning').textContent = ''; return; }
    const reference = M.defaults(base, false);
    const extreme = input.metals.some((m, i) => m.production < reference.metals[i].production * .7 || m.production > reference.metals[i].production * 1.3 || m.price < reference.metals[i].price * .5 || m.price > reference.metals[i].price * 1.5 || m.cost < reference.metals[i].cost * .8 || m.cost > reference.metals[i].cost * 1.2 || m.conversion < reference.metals[i].conversion * .8 || m.conversion > reference.metals[i].conversion * 1.2) || current.gp <= base.gp * .2 || input.adjustment !== 0 || fields.slice(0, 4).some(([k]) => Math.abs(input[k] - reference[k]) > 5);
    $('scenario-warning').textContent = t(extreme ? 'scenario.extreme' : 'scenario.normal');
    const span = Math.abs(current.parent) * stats.maxError / 100;
    $('band').textContent = extreme ? '' : t('band', {lo: fmt(current.parent - span), hi: fmt(current.parent + span), error: fmt(stats.maxError, 1)});
    const bridge = $('bridge'); bridge.replaceChildren();
    current.metals.forEach(m => bridge.append(row([t(m.id), fmt(m.gp)])));
    [['bridge.associate', current.associate], ['bridge.other', current.other], ['bridge.pretax', current.pretax], ['bridge.tax', -current.tax], ['result.net', current.net], ['bridge.nci', -current.nci], ['bridge.core', current.coreParent], ['adjustment', current.adjustment], ['result.parent', current.parent]].forEach(([label, val], i) => bridge.append(row([t(label), fmt(val)], i === 8 ? 'bridge-total' : '')));
    renderSensitivity();
  }
  function renderPresetNotes() {
    $('baseline-note').textContent = t('baseline.selected', {period:period(base.year)});
    $('production-preview').textContent = t('production.preview', P.production($('production-preset').value));
    $('production-applied').hidden = !productionApplied;
    $('production-applied').textContent = productionApplied ? t('production.applied', {plan:t('plan.' + productionApplied)}) : '';
  }
  function applyProduction() {
    productionApplied = $('production-preset').value;
    for (const [id, value] of Object.entries(P.production(productionApplied))) $(id + '-production').value = value;
    renderPresetNotes(); renderResult();
  }
  function renderSnapshot() {
    $('snapshot-status').textContent = latest ? t('prices.snapshot', {date:snapshot.fetched_at.slice(0, 10)}) : t('prices.missing');
    $('fx-note').textContent = Number.isFinite(fx) && fx > 0 ? t('prices.fx', {rate:fmt(fx, 6), date:snapshot.fx.as_of}) : t('prices.fxMissing');
    $('snapshot-rows').replaceChildren();
    $('snapshot-details').hidden = !latest;
    if (!latest) return;
    snapshot.quotes.forEach((q, i) => {
      const value = P.fromBasePrice(q.id, latest[i].price, units[q.id], fx);
      const tr = row([t(q.id), '', q.quoted_at.replace('T', ' ').slice(0, 19), fmt(value, 4) + ' ' + t('unit.' + units[q.id])]);
      const link = document.createElement('a'); link.href = q.source_url; link.target = '_blank'; link.rel = 'noopener noreferrer';
      link.textContent = `${q.contract} · ${fmt(q.price, 4)} ${t('unit.' + q.unit)}`;
      tr.children[1].append(link); $('snapshot-rows').append(tr);
    });
    $('fx-source').href = snapshot.fx.source_url;
    $('fx-source').textContent = t('prices.fxSource', {date:snapshot.fx.as_of});
  }
  function applyLatest() {
    if (!latest) return;
    latest.forEach(v => setPrice(v.id, v.price));
    marketApplied = {snapshot, conversion:latest}; renderResult();
  }
  function renderSensitivity() {
    const shocks = [-20, -10, 0, 10, 20]; $('heat-head').replaceChildren(); $('heat').replaceChildren();
    const heading = document.createElement('tr');
    ['Au / Cu', ...shocks.map(n => (n > 0 ? '+' : '') + n + '%')].forEach(s => { const th = document.createElement('th'); th.textContent = s; th.scope = 'col'; heading.append(th); }); $('heat-head').append(heading);
    for (const gold of shocks) {
      const tr = document.createElement('tr'), th = document.createElement('th'); th.scope = 'row'; th.textContent = (gold > 0 ? '+' : '') + gold + '%'; tr.append(th);
      for (const copper of shocks) {
        const trial = JSON.parse(JSON.stringify(input)); trial.metals[0].price *= 1 + gold / 100; trial.metals[1].price *= 1 + copper / 100;
        const td = document.createElement('td'), button = document.createElement('button');
        let value;
        try { value = M.estimate(trial).parent; } catch (_) { button.textContent = '—'; button.disabled = true; td.append(button); tr.append(td); continue; }
        button.type = 'button'; button.textContent = fmt(value, 1); button.setAttribute('aria-label', t('sensitivity.cell', {g:gold,c:copper,v:fmt(value)}));
        if (!gold && !copper) button.className = 'current';
        button.style.background = `rgba(8,127,120,${.04 + (gold + copper + 40) / 400})`;
        button.addEventListener('click', () => { setPrice('gold', trial.metals[0].price); setPrice('copper', trial.metals[1].price); renderResult(); }); td.append(button); tr.append(td);
      }
      $('heat').append(tr);
    }
    const values = [0, 1].map(i => { const trial = JSON.parse(JSON.stringify(input)); trial.metals[i].price *= 1.1; try { return fmt(M.estimate(trial).parent); } catch (_) { return '—'; } });
    $('elasticity').textContent = t('elasticity', {g:values[0], c:values[1]});
  }
  function renderHistory() {
    $('mape').textContent = fmt(stats.mape) + '%'; $('max-error').textContent = fmt(stats.maxError) + '%';
    $('gate').textContent = t(stats.mape <= D.thresholds.mape && stats.maxError <= D.thresholds.maxError ? 'backtest.pass' : 'backtest.fail');
    $('backtests').replaceChildren(); $('audit').replaceChildren();
    [...annual, ...extension].forEach(r => {
      $('backtests').append(row([period(r.year), r.base, fmt(r.predicted), fmt(r.actual), (r.error >= 0 ? '+' : '') + fmt(r.error) + '%', t(r.year.length === 4 ? 'backtest.annual' : 'backtest.extension')]));
      r.input.metals.forEach(m => $('audit').append(row([period(r.year), t(m.id), fmt(m.production, 4), fmt(m.price), fmt(m.cost), fmt(m.conversion * 100) + '%'])));
    });
    $('sources').replaceChildren();
    D.history.forEach(r => { const li = document.createElement('li'), a = document.createElement('a'); a.href = r.url; a.target = '_blank'; a.rel = 'noopener noreferrer'; a.textContent = t('source.' + r.year); li.append(a); $('sources').append(li); });
    $('version').textContent = t('version', {date:D.verified, hash:D.source_sha256.slice(0, 16)});
  }
  function reset() {
    base = D.history.find(r => r.year === $('base').value);
    productionApplied = null; marketApplied = null;
    input = M.defaults(base, false); buildInputs(); renderResult(); renderPresetNotes();
  }
  function download(name, contents, mime) {
    const blob = new Blob([contents], {type:mime}), url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  $('inputs').addEventListener('submit', e => e.preventDefault()); $('inputs').addEventListener('input', event => {
    if (event.target.matches('input[id$="-price"]')) delete priceValues[event.target.id.slice(0, -6)];
    renderResult();
  });
  $('reset').addEventListener('click', reset);
  $('production-preset').addEventListener('change', renderPresetNotes);
  $('apply-production').addEventListener('click', applyProduction);
  $('production-source').href = P.source;
  $('price-preset').addEventListener('change', () => {
    if ($('price-preset').value === 'latest') applyLatest();
    renderResult();
  });
  $('apply-price-preset').addEventListener('click', applyLatest);
  [['bull', 1.1], ['bear', .9]].forEach(([id, factor]) => $(id).addEventListener('click', () => {
    if (!valid) return;
    const prices = M.ids.map(id => [id, readPrice(id) * factor]);
    if (prices.some(([, value]) => value > 1e7)) return;
    prices.forEach(([id, value]) => setPrice(id, value));
    renderResult();
  }));
  $('download').addEventListener('click', () => { if (!valid) return; download('company-profit-scenario.json', JSON.stringify({modelVersion:D.version, sourceSha256:D.source_sha256, baseline:base, fullPreset:base.year, lastProductionPreset:productionApplied, productionSource:productionApplied ? P.source : null, lastMarketApplication:marketApplied, units:D.unit, displayPriceUnits:{...units}, exchangeRate:snapshot?.fx || null, input, result:current, historicalAnnualMetrics:stats}, null, 2), 'application/json'); });
  $('download-backtest').addEventListener('click', () => {
    const header = ['period','baseline','estimated_parent_CNY_100m','actual_parent_CNY_100m','signed_error_pct','role','inputs_json'];
    const escape = value => '"' + String(value).replaceAll('"', '""') + '"';
    const rows = [...annual, ...extension].map(r => [r.year,r.base,r.predicted,r.actual,r.error,r.year.length === 4 ? 'annual' : 'overlapping_interim',JSON.stringify(r.input)]);
    download('company-profit-backtest.csv', '\uFEFF' + [header,...rows].map(r => r.map(escape).join(',')).join('\r\n'), 'text/csv;charset=utf-8');
  });
  i18n.onChange(() => {
    // Preserve even invalid drafts across a language switch.
    const drafts = Object.fromEntries([...$('inputs').querySelectorAll('input')].map(el => [el.id, el.value]));
    const savedPrices = {...priceValues};
    buildInputs(); for (const [id, value] of Object.entries(drafts)) $(id).value = value;
    Object.assign(priceValues, savedPrices);
    renderPresetNotes(); renderResult(); renderHistory(); renderSnapshot();
  });
  reset(); applyProduction(); applyLatest(); renderHistory(); renderSnapshot(); i18n.apply();
})();
