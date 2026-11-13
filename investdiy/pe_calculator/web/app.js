(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const t = (key, vars) => i18n.t(key, vars);
  const number = (value, digits = 2) => new Intl.NumberFormat(i18n.lang === 'zh' ? 'zh-CN' : 'en-US',
    { maximumFractionDigits: digits, notation: Math.abs(value) >= 1e9 ? 'scientific' : 'standard' }).format(value);
  const multiple = (value) => t('result.multiple', { n: number(value) });
  const multipleRange = (values) => {
    const low = Math.min(...values), high = Math.max(...values);
    return low === high ? multiple(low) : t('result.multiple', { n: `${number(low)}–${number(high)}` });
  };
  const percentage = (value) => `${number(value, 4)}%`;
  const readNumber = (input) => input.value.trim() === '' ? NaN : Number(input.value);
  let latest = null;
  let nextId = 0;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function addStage(years, growth, fcfeRatio = 100) {
    const row = element('div', 'stage-row');
    const name = element('div', 'stage-name');
    name.append(element('span'), element('small'));
    row.append(name);
    const id = nextId++;
    for (const [field, value, min, max, step] of [
      ['years', years, 1, 100, '1'], ['growth', growth, -100, 1000, 'any'],
      ['fcfeRatio', fcfeRatio, 0, '', 'any'],
    ]) {
      const label = element('label');
      const span = element('span');
      span.dataset.i18n = `stage.${field}`;
      const input = element('input');
      Object.assign(input, { type: 'number', value, min, max, step, required: true, id: `stage-${id}-${field}` });
      input.dataset.field = field;
      if (field === 'fcfeRatio') input.setAttribute('aria-describedby', 'stage-ratio-note');
      label.htmlFor = input.id;
      label.append(span, input);
      row.append(label);
    }
    const remove = element('button', 'remove-stage');
    remove.type = 'button';
    remove.dataset.i18n = 'stage.remove';
    remove.addEventListener('click', () => {
      if ($('stages').children.length === 1) return;
      const focusRow = row.nextElementSibling || row.previousElementSibling;
      row.remove();
      refresh();
      focusRow.querySelector('input').focus();
    });
    row.append(remove);
    $('stages').append(row);
    i18n.apply(row);
    return row;
  }

  function updateStages() {
    let start = 1;
    const rows = [...$('stages').children];
    rows.forEach((row, index) => {
      const n = index + 1;
      const years = readNumber(row.querySelector('[data-field="years"]'));
      const valid = Number.isInteger(years) && years >= 1 && Number.isFinite(start);
      row.querySelector('.stage-name span').textContent = t('stage.name', { n });
      row.querySelector('.stage-name small').textContent = valid ? t('stage.span', { start, end: start + years - 1 }) : '—';
      start = valid ? start + years : NaN;
      for (const field of ['years', 'growth', 'fcfeRatio']) {
        row.querySelector(`[data-field="${field}"]`).setAttribute('aria-label', t(`stage.${field}Label`, { n }));
      }
      row.querySelector('button').setAttribute('aria-label', t('stage.removeLabel', { n }));
      row.querySelector('button').disabled = rows.length === 1;
    });
    $('horizon').textContent = t('stage.horizon', { stages: rows.length, years: Number.isFinite(start) ? start - 1 : '—' });
    $('add-stage').disabled = rows.length >= peModel.limits.stages;
  }

  function fillTable(id, rows) {
    $(id).querySelector('tbody').replaceChildren(...rows.map((values) => {
      const row = element('tr');
      row.append(...values.map((value) => element('td', '', value)));
      return row;
    }));
  }

  function refresh() {
    updateStages();
    const inputs = [...$('assumptions').querySelectorAll('input')];
    inputs.forEach((input) => input.removeAttribute('aria-invalid'));
    try {
      const config = {
        stages: [...$('stages').children].map((row) => ({
          years: readNumber(row.querySelector('[data-field="years"]')),
          growth: readNumber(row.querySelector('[data-field="growth"]')),
          fcfeRatio: readNumber(row.querySelector('[data-field="fcfeRatio"]')),
        })),
        premium: readNumber($('premium')), terminalRatio: readNumber($('terminal-ratio')),
        rates: peModel.parseRates($('rates').value),
      };
      const result = peModel.calculate(config);
      latest = { config, result };
      $('error').hidden = true;
      $('results').hidden = false;
      $('download').disabled = false;
      const values = result.scenarios.map((s) => s.pe);
      const high = Math.max(...values);
      $('pe-range').textContent = multipleRange(values);
      $('forecast-pe').textContent = multipleRange(result.scenarios.map((s) => s.forecastPV));
      $('end-earnings').textContent = multiple(result.earnings);
      $('end-year').textContent = t('result.endYear', { n: result.years });
      $('comparison-note').textContent = t('compare.note', { premium: number(config.premium, 4),
        ratio: number(config.terminalRatio, 4), start: result.years + 1 });
      $('comparison-bars').replaceChildren(...result.scenarios.map((scenario) => {
        const row = element('div', 'bar-row');
        const track = element('div', 'bar-track');
        track.setAttribute('aria-hidden', 'true');
        for (const [className, value] of [['bar-forecast', scenario.forecastPV], ['bar-terminal', scenario.terminalPV]]) {
          const bar = element('span', className);
          bar.style.width = `${high === 0 ? 0 : value / high * 100}%`;
          track.append(bar);
        }
        row.append(element('span', '', percentage(scenario.rate)), track, element('span', 'bar-value', multiple(scenario.pe)));
        return row;
      }));
      fillTable('scenario-table', result.scenarios.map((s) => [percentage(s.rate), percentage(s.discount),
        multiple(s.terminalPE), multiple(s.forecastPV), multiple(s.terminalPV), multiple(s.pe), percentage(s.terminalShare * 100)]));
      const previousRate = $('annual-scenario').value;
      $('annual-scenario').replaceChildren(...result.scenarios.map((s) => {
        const option = element('option', '', t('annual.option', { rate: number(s.rate, 4), discount: number(s.discount, 4) }));
        option.value = String(s.rate);
        return option;
      }));
      if (result.scenarios.some((s) => String(s.rate) === previousRate)) $('annual-scenario').value = previousRate;
      renderAnnual();
    } catch (error) {
      latest = null;
      $('results').hidden = true;
      $('download').disabled = true;
      $('error').hidden = false;
      $('error').textContent = t(`error.${error.message}`);
      const selector = { rates: '#rates', premium: '#premium', terminalRatio: '#terminal-ratio', stageRatio: '[data-field="fcfeRatio"]',
        years: '[data-field="years"]', growth: '[data-field="growth"]', horizon: '[data-field="years"]' }[error.message];
      if (selector) document.querySelectorAll(selector).forEach((input) => input.setAttribute('aria-invalid', 'true'));
    }
  }

  function renderAnnual() {
    if (!latest) return;
    const scenario = latest.result.scenarios.find((s) => String(s.rate) === $('annual-scenario').value);
    if (!scenario) return;
    fillTable('annual-table', scenario.annual.map((a) => [a.year, a.stage, percentage(a.growth), percentage(a.fcfeRatio),
      number(a.earnings, 4), number(a.fcfe, 4), number(a.factor, 6), number(a.pv, 4)]));
  }

  function reset() {
    $('premium').value = '10';
    $('terminal-ratio').value = '100';
    $('rates').value = '2, 4, 6';
    $('stages').replaceChildren();
    $('annual-scenario').replaceChildren();
    for (const [years, growth] of [[5, 20], [5, 3]]) addStage(years, growth);
    refresh();
  }

  $('assumptions').addEventListener('submit', (event) => event.preventDefault());
  $('assumptions').addEventListener('input', refresh);
  $('add-stage').addEventListener('click', () => {
    if ($('stages').children.length >= peModel.limits.stages) return;
    const row = addStage(5, 0);
    refresh();
    row.querySelector('input').focus();
  });
  $('reset').addEventListener('click', reset);
  $('annual-scenario').addEventListener('change', renderAnnual);
  $('download').addEventListener('click', () => {
    if (!latest) return;
    const { config, result } = latest;
    // Stable English column names and full precision keep exported scenarios reproducible.
    const rows = [['risk_free_rate_pct', 'equity_risk_premium_pct', 'discount_pct', 'terminal_distributable_ratio_pct', 'forecast_years',
      'stages_years_growth_pct_distributable_pct', 'terminal_earnings', 'terminal_pe', 'forecast_pv', 'terminal_pv', 'current_pe', 'terminal_share_pct'],
    ...result.scenarios.map((s) => [s.rate, config.premium, s.discount, config.terminalRatio, result.years,
      config.stages.map((stage) => `${stage.years}@${stage.growth}@${stage.fcfeRatio}`).join(';'), result.earnings,
      s.terminalPE, s.forecastPV, s.terminalPV, s.pe, s.terminalShare * 100])];
    const csv = rows.map((row) => row.map((value) => `"${String(value).replace(/"/g, '""')}"`).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob(['\uFEFF', csv, '\r\n'], { type: 'text/csv;charset=utf-8' }));
    const link = element('a');
    link.href = url;
    link.download = 'pe-scenarios.csv';
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  i18n.onChange(refresh);
  reset();
})();
