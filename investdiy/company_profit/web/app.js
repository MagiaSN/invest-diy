(function () {
  'use strict';
  const M = window.CompanyProfitModel, P = window.CompanyProfitPresets, data = window.CompanyProfitData;
  const histories = {zijin: data, cmoc: window.CmocProfitData, cnooc: window.CnoocProfitData};
  const firstCompany = Object.keys(histories).find(id => histories[id]);
  const $ = id => document.getElementById(id);
  if (!firstCompany) { $('error').hidden = false; $('error').textContent = i18n.t('common.failed'); $('results').hidden = true; $('download').disabled = true; return; }
  const snapshot = data?.market, fx = snapshot?.fx?.cny_per_usd;
  const saved = {};
  const tabs = [...document.querySelectorAll('[role="tab"]')];
  const localized = [...$('company-panel').querySelectorAll('[data-i18n]')].map(el => [el, el.dataset.i18n]);
  let company, ids, D, guidance, annual, stats, units, priceValues, latest;
  let base, reference, input, current, valid, productionApplied, marketApplied;
  const keyFor = k => i18n.has(company + '.' + k) ? company + '.' + k : k;
  const t = (k, vars) => i18n.t(keyFor(k), vars);
  const fmt = (v, digits = 2) => new Intl.NumberFormat(i18n.lang === 'zh' ? 'zh-CN' : 'en', {maximumFractionDigits: digits, minimumFractionDigits: digits}).format(v);
  const period = y => i18n.has('period.' + y) ? t('period.' + y) : y;
  const commonFields = [['tax', 0, 60], ['share', 0, 100], ['months', 1, 12], ['adjustment', -10000, 10000]];
  const fields = {
    zijin: [...commonFields, ['associate', -100, 200], ['otherMonthly', -10000, 10000]],
    cmoc: [...commonFields, ['associateMonthly', -10000, 10000], ['other', -200, 200], ['marginalShare', 0, 100]],
    cnooc: [['tax', 0, 60], ['months', 1, 12], ['associateMonthly', -10000, 10000],
      ['other', -200, 200], ['nciMonthly', -10000, 10000], ['adjustment', -10000, 10000]],
  };
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
    input.metals.forEach(m => {
      const product = M.products[m.id];
      const el = document.createElement('div'); el.className = 'metal-row'; el.dataset.product = m.id;
      const name = document.createElement('div'); name.className = 'metal-name';
      const symbol = document.createElement('b'); symbol.textContent = product.symbol;
      const label = document.createElement('span'); label.textContent = t(m.id); name.append(symbol, label); el.append(name);
      const qu = t('unit.' + product.volumeUnit);
      const pu = t('unit.' + P.priceUnits[m.id][0]);
      el.append(field(m.id + '-production', `${t('production')} (${qu})`, m.production, 0, 1e6), priceField(m), field(m.id + '-cost', `${t('cost')} (${pu})`, m.cost, 0, 1e7));
      $('metal-inputs').append(el); setPrice(m.id, m.price);
    });
    fields[company].forEach(([key, min, max]) => $('advanced-inputs').append(field(key, t(key), input[key], min, max)));
  }
  function read() {
    let ok = true;
    $('inputs').querySelectorAll('input').forEach(el => { const bad = el.value.trim() === '' || !el.validity.valid || !Number.isFinite(el.valueAsNumber); el.setAttribute('aria-invalid', String(bad)); if (bad) ok = false; });
    if (!ok) throw new Error('invalid');
    const result = {metals: ids.map(id => ({id, production: $(id + '-production').valueAsNumber, price: readPrice(id), cost: $(id + '-cost').valueAsNumber}))};
    fields[company].forEach(([k]) => { result[k] = $(k).valueAsNumber; });
    if (company === 'cmoc') result.baseMonthlyNet = base.net / base.months;
    return result;
  }
  function row(values, cls) {
    const tr = document.createElement('tr'); if (cls) tr.className = cls;
    values.forEach(value => { const td = document.createElement('td'); td.textContent = value; tr.append(td); }); return tr;
  }
  function renderResult() {
    try { input = read(); current = M.estimate(input, company); valid = true; } catch (_) { valid = false; }
    $('error').hidden = valid; $('error').textContent = t('error'); $('results').hidden = !valid; $('download').disabled = !valid;
    for (const id of ['parent', 'net', 'gross']) $(id).textContent = valid ? fmt(current[id === 'gross' ? 'gp' : id]) : '—';
    $('apply-price-preset').disabled = !latest;
    $('price-preset').disabled = !latest;
    $('bull').disabled = !valid || input.metals.some(m => m.price * 1.1 > 1e7);
    $('bear').disabled = !valid;
    if (!valid) { $('band').textContent = ''; $('scenario-warning').textContent = ''; return; }
    const durationScale = company === 'cnooc' ? input.months / reference.months : 1;
    const extremeProduct = input.metals.some((m, i) => {
      const baseline = reference.metals[i];
      const volume = baseline.production * durationScale;
      return m.production < volume * .7 || m.production > volume * 1.3 ||
        m.price < baseline.price * .5 || m.price > baseline.price * 1.5 ||
        m.cost < baseline.cost * .8 || m.cost > baseline.cost * 1.2;
    });
    const extreme = extremeProduct || current.gp <= base.gp * durationScale * .2 || input.adjustment !== 0 || fields[company].some(([k]) => {
      if (k.endsWith('Monthly')) return Math.abs(input[k] - reference[k]) > Math.max(1, Math.abs(reference[k]) * .2);
      return k !== 'months' && Math.abs(input[k] - reference[k]) > 5;
    });
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
    const plan = $('production-preset').value;
    $('production-preview').textContent = t('production.preview', {total: guidance.plans[plan], ...P.production(plan, company, guidance)});
    $('cnooc-sources').hidden = company !== 'cnooc';
    if (company === 'cnooc') {
      $('report-source').href = base.url;
      $('cost-source').href = base.costUrl;
      $('cost-source').hidden = base.costUrl === base.url;
      $('guidance-source').href = guidance.source;
    }
    $('production-applied').hidden = !productionApplied;
    $('production-applied').textContent = productionApplied ? t('production.applied', {plan:t('plan.' + productionApplied)}) : '';
  }
  function applyProduction() {
    productionApplied = $('production-preset').value;
    for (const [id, value] of Object.entries(P.production(productionApplied, company, guidance))) $(id + '-production').value = value;
    $('months').value = 12;
    renderPresetNotes(); renderResult();
  }
  function renderSnapshot() {
    const pricePeriod = D.priceReport?.year || D.history.at(-1).year;
    $('snapshot-status').textContent = latest ? t('prices.snapshot', {date:snapshot.fetched_at?.slice(0, 10), period:period(pricePeriod)}) : t('prices.missing');
    $('fx-note').textContent = Number.isFinite(fx) && fx > 0 ? t('prices.fx', {rate:fmt(fx, 6), date:snapshot.fx.as_of}) : t('prices.fxMissing');
    $('snapshot-rows').replaceChildren();
    $('snapshot-details').hidden = !latest;
    if (!latest) return;
    latest.forEach(entry => {
      const {id, quote, report, price} = entry;
      const date = quote ? quote.quoted_at.replace('T', ' ').slice(0, 19) : period(report.year);
      const value = P.fromBasePrice(id, price, units[id], fx);
      const tr = row([t(id), '', date, fmt(value, 4) + ' ' + t('unit.' + units[id])]);
      const link = document.createElement('a'); link.target = '_blank'; link.rel = 'noopener noreferrer';
      link.href = quote ? quote.source_url : report.url;
      if (company === 'cnooc') link.textContent = fmt(report[id]) + ' ' + t('unit.' + P.priceUnits[id][1]);
      else link.textContent = quote ? `${quote.contract} · ${fmt(quote.price, 4)} ${t('unit.' + quote.unit)}` : t('cmoc.realized');
      tr.children[1].append(link); $('snapshot-rows').append(tr);
    });
    $('fx-source').href = snapshot.fx.source_url;
    $('fx-source').textContent = t('prices.fxSource', {date:snapshot.fx.as_of});
  }
  function applyLatest() {
    if (!latest) return;
    latest.forEach(v => setPrice(v.id, v.price));
    if (company === 'cnooc') {
      marketApplied = {report: D.priceReport, fx: snapshot.fx};
      renderResult();
      return;
    }
    const quoted = latest.filter(entry => entry.quote);
    const quotes = quoted.map(entry => entry.quote);
    const vat = Object.fromEntries(quoted.map(entry => [entry.id, entry.vat]));
    marketApplied = {
      snapshot: {...snapshot, quotes, conversion: {...snapshot.conversion, vat_pct: vat}},
      conversion: latest,
    };
    renderResult();
  }
  function renderSensitivity() {
    const shocks = [-20, -10, 0, 10, 20]; $('heat-head').replaceChildren(); $('heat').replaceChildren();
    const heading = document.createElement('tr');
    [ids.slice(0, 2).map(id => M.products[id].symbol).join(' / '), ...shocks.map(n => (n > 0 ? '+' : '') + n + '%')].forEach(s => { const th = document.createElement('th'); th.textContent = s; th.scope = 'col'; heading.append(th); }); $('heat-head').append(heading);
    for (const rowShock of shocks) {
      const tr = document.createElement('tr'), th = document.createElement('th'); th.scope = 'row'; th.textContent = (rowShock > 0 ? '+' : '') + rowShock + '%'; tr.append(th);
      for (const colShock of shocks) {
        const trial = JSON.parse(JSON.stringify(input)); trial.metals[0].price *= 1 + rowShock / 100; trial.metals[1].price *= 1 + colShock / 100;
        const td = document.createElement('td'), button = document.createElement('button');
        let value;
        try { value = M.estimate(trial, company).parent; } catch (_) { button.textContent = '—'; button.disabled = true; td.append(button); tr.append(td); continue; }
        button.type = 'button'; button.textContent = fmt(value, 1); button.setAttribute('aria-label', t('sensitivity.cell', {g:rowShock,c:colShock,v:fmt(value)}));
        if (!rowShock && !colShock) button.className = 'current';
        button.style.background = `rgba(8,127,120,${.04 + (rowShock + colShock + 40) / 400})`;
        button.addEventListener('click', () => { setPrice(ids[0], trial.metals[0].price); setPrice(ids[1], trial.metals[1].price); renderResult(); }); td.append(button); tr.append(td);
      }
      $('heat').append(tr);
    }
    const values = [0, 1].map(i => { const trial = JSON.parse(JSON.stringify(input)); trial.metals[i].price *= 1.1; try { return fmt(M.estimate(trial, company).parent); } catch (_) { return '—'; } });
    $('elasticity').textContent = t('elasticity', {g:values[0], c:values[1]});
  }
  function renderHistory() {
    $('mape').textContent = fmt(stats.mape) + '%'; $('max-error').textContent = fmt(stats.maxError) + '%';
    $('gate').textContent = t(stats.mape <= D.thresholds.mape && stats.maxError <= D.thresholds.maxError ? 'backtest.pass' : 'backtest.fail');
    const worst = annual.filter(r => Number.isFinite(r.error)).sort((a, b) => Math.abs(b.error) - Math.abs(a.error))[0];
    $('backtest-diagnosis').textContent = worst ? t('backtest.diagnosis', {
      start: annual[0].year, end: annual.at(-1).year, count: annual.length, worst: worst.year,
    }) : '';
    $('backtests').replaceChildren(); $('audit').replaceChildren();
    annual.forEach(r => {
      $('backtests').append(row([period(r.year), r.base, fmt(r.predicted), fmt(r.actual), (r.error >= 0 ? '+' : '') + fmt(r.error) + '%']));
      r.input.metals.forEach(m => $('audit').append(row([period(r.year), t(m.id), fmt(m.production, 4), fmt(m.price), fmt(m.cost)])));
    });
  }
  function reset(taxBasis = 'reported') {
    base = D.history.find(r => r.year === $('base').value);
    productionApplied = null; marketApplied = null;
    reference = M.defaults(base, false, D.history, taxBasis);
    input = reference; buildInputs(); renderResult(); renderPresetNotes();
  }
  function download(name, contents, mime) {
    const blob = new Blob([contents], {type:mime}), url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  $('inputs').addEventListener('submit', e => e.preventDefault()); $('inputs').addEventListener('input', event => {
    if (event.target.matches('input[id$="-price"]')) delete priceValues[event.target.id.slice(0, -6)];
    renderResult();
  });
  $('reset').addEventListener('click', () => reset());
  $('production-preset').addEventListener('change', renderPresetNotes);
  $('apply-production').addEventListener('click', applyProduction);
  $('price-preset').addEventListener('change', () => {
    if ($('price-preset').value === 'latest') applyLatest();
    renderResult();
  });
  $('apply-price-preset').addEventListener('click', applyLatest);
  [['bull', 1.1], ['bear', .9]].forEach(([id, factor]) => $(id).addEventListener('click', () => {
    if (!valid) return;
    const prices = ids.map(id => [id, readPrice(id) * factor]);
    if (prices.some(([, value]) => value > 1e7)) return;
    prices.forEach(([id, value]) => setPrice(id, value));
    renderResult();
  }));
  $('download').addEventListener('click', () => {
    if (!valid) return;
    const scenario = {
      company, modelVersion: {zijin: 3, cmoc: 4, cnooc: 1}[company], quantityBasis: 'sales', sourceSha256: D.source_sha256,
      baseline: base, fullPreset: base.year, lastProductionPreset: productionApplied,
      productionSource: productionApplied ? guidance.source : null,
      ...(company === 'cnooc' && productionApplied ? {productionAssumptions: guidance} : {}),
      lastMarketApplication: marketApplied, units: D.unit, displayPriceUnits: {...units},
      exchangeRate: snapshot?.fx || null, input, result: current, historicalAnnualMetrics: stats,
    };
    const name = (company === 'zijin' ? 'company' : company) + '-profit-scenario.json';
    download(name, JSON.stringify(scenario, null, 2), 'application/json');
  });
  $('download-backtest').addEventListener('click', () => {
    const header = ['period','baseline','estimated_parent_CNY_100m','actual_parent_CNY_100m','signed_error_pct','role','quantity_basis','inputs_json'];
    const escape = value => '"' + String(value).replaceAll('"', '""') + '"';
    const rows = annual.map(r => [r.year,r.base,r.predicted,r.actual,r.error,'annual','reported_sales',JSON.stringify(r.input)]);
    download((company === 'zijin' ? 'company' : company) + '-profit-backtest.csv', '\uFEFF' + [header,...rows].map(r => r.map(escape).join(',')).join('\r\n'), 'text/csv;charset=utf-8');
  });
  function capture() {
    const drafts = Object.fromEntries([...$('inputs').querySelectorAll('input')].map(el => [el.id, el.value]));
    return {drafts, priceValues: {...priceValues}, input, base, reference, units, marketApplied, productionApplied,
      selectedBase: $('base').value, selectedPlan: $('production-preset').value};
  }
  function restore(state) {
    ({input, base, reference, units, marketApplied, productionApplied} = state);
    $('base').value = state.selectedBase;
    $('production-preset').value = state.selectedPlan;
    buildInputs();
    for (const [id, value] of Object.entries(state.drafts)) $(id).value = value;
    priceValues = {...state.priceValues};
    renderPresetNotes(); renderResult();
  }
  function options(id, values, prefix) {
    $(id).replaceChildren(...values.map(value => {
      const option = document.createElement('option');
      option.value = value;
      if (i18n.has(prefix + value)) option.dataset.i18n = prefix + value;
      option.textContent = option.dataset.i18n ? t(prefix + value) : value; return option;
    }));
  }
  function latestPrices() {
    if (company === 'cnooc') {
      if (!(Number.isFinite(fx) && fx > 0)) return null;
      return ids.map(id => ({
        id, price: P.toBasePrice(id, D.priceReport[id], P.priceUnits[id][1], fx), report: D.priceReport,
      }));
    }
    try {
      const quotes = P.snapshotPrices(snapshot).map((entry, i) => ({...entry, quote: snapshot.quotes[i]}));
      const recent = D.history.at(-1);
      return ids.map(id => quotes.find(q => q.id === id) || {
        id, price: recent.metals.find(m => m.id === id).price, report: {year:recent.year, url:recent.url},
      });
    } catch (_) { return null; }
  }
  function selectCompany(next) {
    if (next === company) return;
    if (company) saved[company] = capture();
    company = next;
    D = histories[company];
    guidance = D.guidance || P.guidance[company];
    ids = M.companyProducts[company];
    annual = M.annualBacktests(D.history, company);
    stats = M.metrics(annual);
    units = Object.fromEntries(ids.map(id => [id, P.priceUnits[id][0]]));
    priceValues = {};
    latest = latestPrices();
    if (company === 'cnooc' && latest) {
      for (const id of ids) units[id] = P.priceUnits[id][1];
    }
    $('ticker').textContent = {zijin: '601899.SH · 02899.HK', cmoc: '603993.SH · 03993.HK', cnooc: '600938.SH · 00883.HK'}[company];
    $('company-panel').setAttribute('aria-labelledby', 'company-' + company);
    tabs.forEach(tab => {
      const active = tab.id === 'company-' + company;
      tab.setAttribute('aria-selected', String(active)); tab.tabIndex = active ? 0 : -1;
    });
    localized.forEach(([el, key]) => { el.dataset.i18n = keyFor(key); });
    options('base', D.history.filter(r => !r.grouped).map(r => r.year).reverse(), 'period.');
    options('production-preset', Object.keys(guidance.plans), 'plan.');
    if (saved[company]) restore(saved[company]);
    else { reset('forecast'); applyProduction(); applyLatest(); }
    renderHistory(); renderSnapshot(); i18n.apply();
  }
  tabs.forEach(tab => {
    const name = tab.id.slice('company-'.length);
    if (!histories[name]) { tab.disabled = true; return; }
    tab.addEventListener('click', () => selectCompany(name));
    tab.addEventListener('keydown', e => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) return;
      e.preventDefault();
      const enabled = tabs.filter(el => !el.disabled);
      const index = enabled.indexOf(tab) + (e.key === 'ArrowLeft' ? -1 : 1);
      const target = e.key === 'Home' ? enabled[0] : e.key === 'End' ? enabled.at(-1) : enabled[(index + enabled.length) % enabled.length];
      target.focus(); target.click();
    });
  });
  i18n.onChange(() => { restore(capture()); renderHistory(); renderSnapshot(); });
  selectCompany(firstCompany);
})();
