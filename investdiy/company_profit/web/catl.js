(function () {
  'use strict';
  const $ = id => document.getElementById('catl-' + id);
  const t = (key, vars) => i18n.t('catl.' + key, vars);
  const data = window.CatlProfitData, model = window.CatlProfitModel;
  const products = ['ev', 'storage'];
  const advanced = ['materialsGross', 'otherGrossPerWh', 'payroll', 'spendingRate', 'finance', 'investment',
    'otherIncome', 'impairment', 'remaining', 'taxRate', 'parentShare'];
  const errorItems = ['otherGross', 'expenses', 'ancillary', 'tax', 'minority'];
  const shocks = [-20, -10, 0, 10, 20];
  let helpers, annual, period, marginYear, input, result;
  const isQuarter = () => period === 'q4';
  const year = () => isQuarter() ? 2026 : period;
  const report = y => data.history.find(r => r.year === Number(y));
  const reportedParent = () => isQuarter() ? data.forecast.nineMonths.parent : 0;
  const fmt = (n, digits = 2) => helpers.fmt(n, digits);
  const percent = n => (n > 0 ? '+' : '') + n + '%';
  function field(name, label, min, max) {
    const wrap = document.createElement('label'), span = document.createElement('span');
    span.dataset.i18n = 'catl.' + label;
    const el = document.createElement('input');
    el.id = 'catl-' + name;
    el.name = name;
    el.type = 'number';
    el.step = 'any';
    el.required = true;
    if (min !== undefined) el.min = min;
    if (max !== undefined) el.max = max;
    wrap.append(span, el);
    return wrap;
  }
  function setValue(name, value) {
    const el = $(name);
    el.value = Number(value.toFixed(6));
    el.dataset.display = el.value;
    el.dataset.exact = value;
  }
  function setScenario() {
    period = $('period').value;
    marginYear = isQuarter() ? data.history.at(-1).year : Number(period);
    $('margin-year').value = marginYear;
    const values = isQuarter() ? model.quarterInputs(data) : model.annualInputs(report(period));
    Object.entries(values).forEach(([k, v]) => setValue(k, v));
    refresh();
  }
  function read() {
    const values = {};
    let valid = true;
    for (const el of $('inputs').querySelectorAll('input')) {
      const bad = !el.validity.valid || !Number.isFinite(el.valueAsNumber);
      el.setAttribute('aria-invalid', String(bad));
      valid &&= !bad;
      values[el.name] = el.value === el.dataset.display ? Number(el.dataset.exact) : el.valueAsNumber;
    }
    return valid ? values : null;
  }
  function kpi(label, value) {
    const div = document.createElement('div'), span = document.createElement('span'), strong = document.createElement('strong');
    span.textContent = label; strong.textContent = value; div.append(span, strong);
    return div;
  }
  function headers(id, labels) {
    const tr = document.createElement('tr');
    for (const label of labels) {
      const th = document.createElement('th'); th.scope = 'col'; th.textContent = label; tr.append(th);
    }
    $(id).replaceChildren(tr);
  }
  function link(url, label) {
    const a = document.createElement('a');
    a.href = url; a.target = '_blank'; a.rel = 'noopener noreferrer'; a.textContent = label;
    return a;
  }
  function notes() {
    const y = year();
    $('input-title').textContent = t(isQuarter() ? 'q4Inputs' : 'annualInputs', {year: y});
    $('result-title').textContent = t('annualParent', {year: y});
    $('basis').textContent = isQuarter() ? t('q4Basis', {year: marginYear}) : t('annualBasis', {year: y, marginYear});
    if ((marginYear < 2024) !== (Number(y) < 2024)) $('basis').textContent += ' ' + t('warrantyMix');
    const links = [];
    for (const sourceYear of new Set([isQuarter() ? data.history.at(-1).year : Number(period), marginYear])) {
      const r = report(sourceYear);
      links.push(link(r.url, t('annualReport', {year: sourceYear})));
      if (r.costUrl) links.push(link(r.costUrl, t('costSource')));
    }
    if (isQuarter()) {
      for (const [key, label] of [['halfUrl', 'halfReport'], ['quarterUrl', 'quarterReport'], ['callUrl', 'call']]) {
        links.push(link(data.forecast[key], t(label)));
      }
    }
    $('sources').replaceChildren(...links.flatMap((a, i) => i ? [' · ', a] : [a]));
    $('sensitivity-note').textContent = t('sensitivityNote', {year: y});
  }
  function sensitivity() {
    headers('heat-head', ['Δ', ...shocks.map(percent)]);
    $('heat').replaceChildren();
    for (const ev of shocks) {
      const tr = document.createElement('tr'), th = document.createElement('th');
      th.scope = 'row'; th.textContent = percent(ev); tr.append(th);
      for (const storage of shocks) {
        const trial = {...input, evMarginPerWh: input.evMarginPerWh * (1 + ev / 100), storageMarginPerWh: input.storageMarginPerWh * (1 + storage / 100)};
        const td = document.createElement('td'), btn = document.createElement('button');
        btn.type = 'button';
        try {
          btn.textContent = fmt(model.estimate(trial, reportedParent()).annual, 1);
          btn.setAttribute('aria-label', t('cell', {ev: percent(ev), storage: percent(storage), profit: btn.textContent}));
          if (!ev && !storage) btn.className = 'current';
          btn.addEventListener('click', () => {
            setValue('evMarginPerWh', trial.evMarginPerWh); setValue('storageMarginPerWh', trial.storageMarginPerWh); render();
          });
        } catch (error) {
          btn.textContent = '—'; btn.disabled = true;
        }
        td.append(btn); tr.append(td);
      }
      $('heat').append(tr);
    }
  }
  function render() {
    input = read(); result = null;
    if (input) {
      try { result = model.estimate(input, reportedParent()); } catch (error) { /* Out-of-range arithmetic. */ }
    }
    $('error').hidden = Boolean(result);
    $('results').hidden = !result; $('download').disabled = !result;
    $('parent').textContent = result ? fmt(result.annual) : '—';
    const amount = key => result ? fmt(result[key]) : '—';
    $('kpis').replaceChildren(...(isQuarter()
      ? [kpi(t('ytd'), fmt(reportedParent())), kpi(t('quarterParent'), amount('parent'))]
      : [kpi(t('groupGross'), amount('gp')), kpi(t('net'), amount('net'))]));
    if (!result) return;
    const lines = [
      [t('ev'), result.ev], [t('storage'), result.storage], [t('materialsGross'), result.materialsGross],
      [t('otherBusiness'), result.otherBusiness],
      [t('groupGross'), result.gp], [t('expenses'), result.expenses],
      ...['finance', 'investment', 'otherIncome', 'impairment', 'remaining'].map(k => [t(k), input[k]]),
      [i18n.t('bridge.pretax'), result.pretax], [i18n.t('bridge.tax'), result.tax],
      [t('net'), result.net], [t('minority'), result.minority],
    ];
    if (isQuarter()) lines.push([t('quarterParent'), result.parent], [t('ytd'), reportedParent()]);
    lines.push([t('annualParent', {year: year()}), result.annual]);
    $('bridge').replaceChildren(...lines.map(([label, n], i) =>
      helpers.row([label, fmt(n)], i === lines.length - 1 ? 'bridge-total' : '')));
    sensitivity();
  }
  function history() {
    const common = i18n.t, stats = window.CompanyProfitModel.metrics(annual);
    $('metrics').replaceChildren(kpi(common('backtest.mape'), fmt(stats.mape) + '%'),
      kpi(common('backtest.max'), fmt(stats.maxError) + '%'),
      kpi(common('backtest.gate'), common(stats.mape <= 10 && stats.maxError <= 10 ? 'backtest.pass' : 'backtest.fail')));
    $('history').replaceChildren(); $('audit').replaceChildren(); $('errors').replaceChildren();
    headers('audit-head', [common('backtest.period'), common('cnooc.audit.metal'), t('volume'), t('margin')]);
    headers('errors-head', [common('backtest.period'), ...errorItems.map(k => t(k))]);
    for (const r of annual) {
      const tr = helpers.row([r.year, r.base, fmt(r.predicted), fmt(r.actual), (r.error > 0 ? '+' : '') + fmt(r.error) + '%']);
      tr.cells[0].replaceChildren(link(report(r.year).url, r.year));
      $('history').append(tr);
      for (const id of products) $('audit').append(helpers.row([r.year, t(id), fmt(r.input[id + 'Volume']), fmt(r.input[id + 'MarginPerWh'], 6)]));
      $('errors').append(helpers.row([r.year, ...errorItems.map(k => fmt(r.errors[k]))]));
    }
  }
  function refresh() {
    i18n.apply($('panel'));
    notes(); render(); history();
  }
  function option(select, value, key) {
    const el = document.createElement('option');
    el.value = value; el.dataset.i18n = key; select.append(el);
  }
  function show(shared) {
    if (helpers) { refresh(); return; }
    helpers = shared;
    annual = model.backtests(data.history);
    option($('period'), 'q4', 'catl.q4');
    for (const r of [...data.history].reverse()) {
      for (const id of ['period', 'margin-year']) option($(id), r.year, 'period.' + r.year);
    }
    for (const id of products) {
      const line = document.createElement('div'), name = document.createElement('div');
      line.className = 'metal-row catl-product'; name.className = 'metal-name'; name.dataset.i18n = 'catl.' + id;
      line.append(name, field(id + 'Volume', 'volume', 0), field(id + 'MarginPerWh', 'margin')); $('products').append(line);
    }
    for (const k of advanced) {
      const rate = k === 'taxRate' || k === 'parentShare';
      $('advanced').append(field(k, k, rate || k === 'payroll' || k === 'spendingRate' ? 0 : undefined, rate ? 100 : undefined));
    }
    $('inputs').addEventListener('submit', e => e.preventDefault());
    $('inputs').addEventListener('input', render);
    $('load').addEventListener('click', setScenario);
    $('apply-margin').addEventListener('click', () => {
      marginYear = Number($('margin-year').value);
      const values = model.annualInputs(report(marginYear));
      for (const id of products) setValue(id + 'MarginPerWh', values[id + 'MarginPerWh']);
      notes(); render();
    });
    $('download').addEventListener('click', () => {
      if (!result) return;
      const basis = isQuarter() ? data.forecast : report(period);
      const scenario = {company: 'catl', modelVersion: 3, period: isQuarter() ? '2026Q4' : period,
        quantityBasis: 'sales', units: {volume: 'GWh', unitGrossProfit: 'CNY/Wh', profit: 'CNY 100m'},
        sourceSha256: data.source_sha256, basis,
        annualFinancialSource: (isQuarter() ? data.history.at(-1) : basis).url, marginSource: report(marginYear).url,
        reportedParent: reportedParent(), inputs: input, outputs: result};
      helpers.download('catl-profit-scenario.json', JSON.stringify(scenario, null, 2), 'application/json');
    });
    $('csv').addEventListener('click', () => {
      const columns = ['year', 'base', 'estimated_parent_CNY_100m', 'actual_parent_CNY_100m', 'error_pct',
        'ev_GWh', 'ev_gross_profit_CNY_per_Wh', 'storage_GWh', 'storage_gross_profit_CNY_per_Wh',
        ...errorItems.map(k => k + '_error_CNY_100m'), 'target_report', 'baseline_report', 'tax_attribution_comparative_year'];
      const rows = annual.map(r => [r.year, r.base, r.predicted, r.actual, r.error, r.input.evVolume,
        r.input.evMarginPerWh, r.input.storageVolume, r.input.storageMarginPerWh, ...errorItems.map(k => r.errors[k]),
        report(r.year).url, report(r.base).url, r.base - 1]);
      helpers.download('catl-profit-backtest.csv', '\uFEFF' + [columns, ...rows].map(r => r.join(',')).join('\r\n'), 'text/csv;charset=utf-8');
    });
    setScenario();
  }
  window.CatlProfitPage = {show, refresh};
})();
