/* Monthly observations are aligned by calendar month; missing values remain gaps. */
(function () {
  const $ = (id) => document.getElementById(id);
  const t = (key, vars) => i18n.t(key, vars);
  const node = (tag, cls, text) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  };
  const translated = (tag, key, cls) => {
    const e = node(tag, cls, t(key)); e.dataset.i18n = key; return e;
  };
  const configs = [
    { id: 'cpi', color: '--s1', fields: { yoy: 'cpi_yoy', mom: 'cpi_mom', index: 'cpi_sa' }, primary: 'cpi_yoy' },
    { id: 'ppi', color: '--s2', fields: { yoy: 'ppi_yoy', mom: 'ppi_mom', index: 'ppi_sa' }, primary: 'ppi_yoy' },
    { id: 'pce', color: '--s3', fields: { yoy: 'pce_yoy', mom: 'pce_mom', index: 'pce' }, primary: 'pce_yoy' },
    { id: 'unemployment', color: '--s4', fields: { rate: 'unemployment' }, primary: 'unemployment' },
    { id: 'payrolls', color: '--s1', fields: { level: 'payrolls_k', change: 'payrolls_change_k' }, primary: 'payrolls_k' },
    { id: 'fed', color: '--s5', fields: { rate: 'fed_funds' }, primary: 'fed_funds' },
  ];
  const sources = [
    ['CPIAUCSL', 'cpi_sa', 'BLS'], ['CPIAUCNS', 'cpi_nsa', 'BLS'],
    ['PPIFIS', 'ppi_sa', 'BLS'], ['PPIFID', 'ppi_nsa', 'BLS'],
    ['PCEPI', 'pce', 'BEA'], ['UNRATE', 'unemployment', 'BLS'],
    ['PAYEMS', 'payrolls_k', 'BLS'], ['FEDFUNDS', 'fed_funds', 'Federal Reserve'],
  ];
  const columns = ['month', 'cpi_yoy', 'cpi_mom', 'ppi_yoy', 'ppi_mom', 'pce_yoy', 'pce_mom',
    'unemployment', 'payrolls_k', 'payrolls_change_k', 'fed_funds'];
  const numericFields = [...new Set([...sources.map((s) => s[1]), ...columns.slice(1),
    'unemployment_change_pp', 'fed_funds_change_pp'])];
  let rows = [], failed = false;
  const activeFields = (c) => c.variant && c.variant !== 'all' ? c.variants[c.variant].fields : c.fields;
  const variantLabel = (c) => t(`variant.${c.variant}`);
  const chartLabel = (c) => [t(c.id), c.variant && variantLabel(c), t(`mode.${c.mode}`)].filter(Boolean).join(' · ');
  const beaWorkbook = 'https://apps.bea.gov/national/Release/XLS/Underlying/Section2All_xls.xlsx';
  const latest = (field) => rows.findLast((r) => Number.isFinite(r[field]));
  const number = (v, digits = 2, signed = false) => Number.isFinite(v)
    ? d3.format(`${signed ? '+' : ''},.${digits}f`)(v) : '—';
  const unit = (mode) => ['yoy', 'mom', 'rate'].includes(mode) ? 'percent' : mode;
  const scaleValue = (v, mode) => mode === 'level' ? v / (i18n.lang === 'zh' ? 10 : 1000)
    : mode === 'change' ? v / (i18n.lang === 'zh' ? 10 : 1) : v;
  const format = (v, mode, signed = false) => {
    if (!Number.isFinite(v)) return '—';
    const digits = mode === 'level' ? (i18n.lang === 'zh' ? 1 : 3)
      : mode === 'change' ? (i18n.lang === 'zh' ? 1 : 0) : 2;
    const value = number(scaleValue(v, mode), digits, signed);
    return mode === 'index' ? value : t(`value.${unit(mode)}`, { v: value });
  };

  configs.forEach((c) => {
    c.mode = Object.keys(c.fields)[0];
    const kpi = node('article', 'kpi');
    kpi.style.setProperty('--series-color', `var(${c.color})`);
    kpi.append(translated('span', c.id, 'kpi-label'));
    c.value = node('span', 'kpi-value', '—');
    c.sub = node('span', 'kpi-sub', '—');
    c.period = node('span', 'kpi-period', '—');
    kpi.append(c.value, c.sub, c.period); $('summary').append(kpi);

    const card = node('section', 'card'); card.id = c.id; card.dataset.nav = c.id;
    const head = node('div', 'card-head'); head.append(translated('h2', c.id));
    const controls = node('div', 'chart-controls');
    if (c.fields.yoy) {
      c.variant = 'all';
      c.variants = {};
      const label = node('label', 'mode-label');
      c.selector = node('select'); c.selector.id = `${c.id}-variant`;
      const all = translated('option', 'variant.all'); all.value = 'all';
      c.selector.append(all); c.selector.disabled = true;
      label.append(translated('span', 'variant.label'), c.selector); controls.append(label);
      c.selector.addEventListener('change', () => {
        c.variant = c.selector.value;
        const fields = activeFields(c);
        for (const option of c.measure.options) option.disabled = !fields[option.value];
        if (!fields[c.mode]) { c.mode = 'yoy'; c.measure.value = c.mode; }
        drawChart(c); drawTable(); drawSources();
      });
    }
    if (Object.keys(c.fields).length > 1) {
      const label = node('label', 'mode-label');
      label.append(translated('span', 'mode.label'));
      const select = node('select'); c.measure = select; select.id = `${c.id}-mode`;
      Object.keys(c.fields).forEach((mode) => {
        const option = translated('option', `mode.${mode}`); option.value = mode; select.append(option);
      });
      select.addEventListener('change', () => { c.mode = select.value; drawChart(c); });
      label.append(select); controls.append(label);
    }
    head.append(controls);
    c.rangeHost = node('div'); c.rangeHost.id = `${c.id}-range`;
    const meta = node('div', 'chart-meta'); c.unit = node('span'); c.coverage = node('span');
    meta.append(c.unit, c.coverage);
    c.box = node('div', 'chart loading'); c.box.id = `${c.id}-chart`;
    c.note = node('p', 'note');
    card.append(head, c.note, c.rangeHost, meta, c.box);
    c.card = card; $('charts').append(card);
  });
  kit.sectionNav($('secnav'));
  kit.downloadLinks();

  function drawSummary() {
    const stale = [];
    configs.forEach((c) => {
      // Keep the latest observation month even when its YoY base is missing.
      const row = latest(c.fields.index || c.primary);
      if (!row) {
        c.value.textContent = '—'; c.sub.textContent = t('state.unavailable'); c.period.textContent = '—'; return;
      }
      c.value.textContent = format(row[c.primary], c.id === 'payrolls' ? 'level' : 'rate');
      c.period.textContent = t('period', { m: row.month });
      c.sub.textContent = c.fields.yoy ? t(Number.isFinite(row[c.primary]) ? 'summary.inflation' : 'summary.inflationGap', { v: format(row[`${c.id}_mom`], 'mom', true) })
        : c.id === 'payrolls' ? t('summary.jobs', { v: format(row.payrolls_change_k, 'change', true) })
          : t('summary.rate', { v: number(row[c.id === 'fed' ? 'fed_funds_change_pp' : 'unemployment_change_pp'], 2, true) });
      const monthEnd = d3.utcDay.offset(d3.utcMonth.offset(row.d, 1), -1);
      if (Date.now() - monthEnd.getTime() > 75 * 86400000) stale.push(`${t(c.id)} (${row.month})`);
    });
    $('stale').hidden = stale.length === 0;
    $('stale').textContent = t('state.stale', { names: stale.join(' · ') });
    $('asof').textContent = t('state.fetched', { d: rows[0].fetched_at.replace('T', ' ').replace('+00:00', '') });
  }

  function drawChart(c) {
    const selected = c.variants?.[c.variant];
    const notes = [selected ? t(selected.nsa ? 'note.paired' : 'note.adjusted') : t(`${c.id}.note`)];
    if (selected && i18n.has(`note.${c.variant}`)) notes.push(t(`note.${c.variant}`));
    c.note.textContent = notes.join(' ');
    if (!c.range) return;
    const field = activeFields(c)[c.mode], [start, end] = c.range.get();
    const visible = rows.filter((r) => r.d >= start && r.d <= end);
    const valid = visible.filter((r) => Number.isFinite(r[field]));
    const tip = kit.tip(c.card); tip.hide();
    kit.ready(c.box);
    c.unit.textContent = t(`unit.${unit(c.mode)}`);
    c.coverage.textContent = valid.length ? t('period.range', { a: valid[0].month, b: valid.at(-1).month }) : '';
    if (!valid.length) { c.box.append(node('p', 'error', t('state.empty'))); return; }
    const W = Math.max(260, c.box.clientWidth), H = 260, m = { l: 58, r: 14, t: 12, b: 30 };
    const x = d3.scaleUtc([d3.utcDay.offset(start, -15), d3.utcDay.offset(end, 15)], [m.l, W - m.r]);
    const values = valid.map((r) => scaleValue(r[field], c.mode));
    let [lo, hi] = d3.extent(values);
    if (c.mode !== 'index' && c.mode !== 'level') { lo = Math.min(0, lo); hi = Math.max(0, hi); }
    const pad = (hi - lo || Math.abs(hi) || 1) * 0.08;
    const y = d3.scaleLinear([lo - pad, hi + pad], [H - m.b, m.t]).nice();
    const svg = d3.select(c.box).append('svg').attr('viewBox', `0 0 ${W} ${H}`)
      .attr('role', 'img').attr('aria-label', chartLabel(c));
    svg.append('title').text(chartLabel(c));
    const years = (end - start) / 31557600000;
    const ticks = Math.max(2, Math.floor(W / 105));
    const ax = svg.append('g').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x)
      .ticks(years > 3 ? d3.utcYear.every(Math.ceil(years / ticks)) : d3.utcMonth.every(Math.max(1, Math.ceil(years * 12 / ticks))))
      .tickFormat(d3.utcFormat(years > 3 ? '%Y' : '%Y-%m')).tickSizeOuter(0));
    const ay = svg.append('g').attr('transform', `translate(${m.l},0)`).call(d3.axisLeft(y)
      .ticks(5).tickFormat(y.tickFormat(5, ',~f')).tickSize(-(W - m.l - m.r)));
    ay.select('.domain').remove(); kit.axisStyle(ax, ay);
    if (lo <= 0 && hi >= 0) svg.append('line').attr('x1', m.l).attr('x2', W - m.r)
      .attr('y1', y(0)).attr('y2', y(0)).attr('stroke', 'var(--axis)');
    if (c.mode === 'change') {
      const bw = Math.max(1, Math.min(22, (x(d3.utcMonth.offset(start, 1)) - x(start)) * 0.7));
      svg.append('g').selectAll('rect').data(valid).join('rect')
        .attr('x', (r) => x(r.d) - bw / 2).attr('width', bw)
        .attr('y', (r) => y(Math.max(0, scaleValue(r[field], c.mode))))
        .attr('height', (r) => Math.abs(y(scaleValue(r[field], c.mode)) - y(0)))
        .attr('fill', (r) => r[field] >= 0 ? 'var(--up)' : 'var(--down)');
    } else {
      svg.append('path').datum(visible).attr('fill', 'none').attr('stroke', `var(${c.color})`).attr('stroke-width', 2)
        .attr('d', d3.line().defined((r) => Number.isFinite(r[field])).x((r) => x(r.d)).y((r) => y(scaleValue(r[field], c.mode))));
      svg.append('g').selectAll('circle').data(valid).join('circle')
        .attr('cx', (r) => x(r.d)).attr('cy', (r) => y(scaleValue(r[field], c.mode)))
        .attr('r', valid.length < 80 ? 2.5 : 1).attr('fill', `var(${c.color})`);
    }
    const rule = svg.append('line').attr('y1', m.t).attr('y2', H - m.b).attr('stroke', 'var(--axis)').attr('opacity', 0);
    const nearest = d3.bisector((r) => r.d).center;
    svg.append('rect').attr('x', m.l).attr('y', m.t).attr('width', W - m.l - m.r).attr('height', H - m.t - m.b)
      .attr('fill', 'transparent').on('pointermove', (event) => {
        const row = visible[nearest(visible, x.invert(d3.pointer(event)[0]))];
        rule.attr('x1', x(row.d)).attr('x2', x(row.d)).attr('opacity', 1);
        tip.show(event, [{ text: row.month }, { text: `${chartLabel(c)} · ${format(row[field], c.mode)}`, color: `var(${c.color})` }]);
      }).on('pointerleave', () => { tip.hide(); rule.attr('opacity', 0); });
  }

  function drawTable() {
    const tr = node('tr');
    const tableFields = columns.map((field) => {
      const [family, mode] = field.split('_');
      const chart = configs.find((c) => c.id === family && c.variant && c.variant !== 'all');
      const label = t(`column.${field}`);
      tr.append(node('th', '', chart ? `${label} · ${variantLabel(chart)}` : label));
      return chart ? activeFields(chart)[mode] : field;
    });
    $('history-table').querySelector('thead').replaceChildren(tr);
    const year = $('year').value;
    const fragment = document.createDocumentFragment();
    rows.slice().reverse().filter((r) => year === 'all' || r.month.startsWith(year)).forEach((r) => {
      const row = node('tr');
      tableFields.forEach((field) => {
        const v = r[field];
        const value = field === 'month' ? r.month : field === 'payrolls_k'
          ? number(scaleValue(v, 'level'), i18n.lang === 'zh' ? 1 : 3)
          : field === 'payrolls_change_k' ? number(scaleValue(v, 'change'), i18n.lang === 'zh' ? 1 : 0, true) : number(v);
        row.append(node('td', '', value));
      });
      fragment.append(row);
    });
    $('history-table').querySelector('tbody').replaceChildren(fragment);
    $('year').querySelector('option[value="all"]').textContent = t('history.all');
  }

  function drawSources() {
    const body = $('sources-table').querySelector('tbody'); body.replaceChildren();
    const entries = sources.map(([sid, field, agency]) => ({ sid, field, agency, label: t(`source.${sid}`) }));
    for (const c of configs) {
      const spec = c.variants?.[c.variant];
      if (!spec) continue;
      for (const mode of ['index', 'nsa', 'yoy', 'annualized_mom']) {
        if (!spec[mode]) continue;
        entries.push({ sid: spec[mode], field: `${c.id}_${c.variant}_${mode}`, provider: spec.provider,
          agency: spec.agency || (c.id === 'pce' ? 'BEA' : 'BLS'),
          label: `${c.id.toUpperCase()} · ${variantLabel(c)} · ${t(`sourceMode.${mode}`)}` });
      }
    }
    entries.forEach(({ sid, field, agency, label, provider }) => {
      const tr = node('tr'), td = node('td'), a = node('a', '', sid);
      a.href = provider === 'bea' ? beaWorkbook : provider === 'bls' ? `https://data.bls.gov/timeseries/${sid}` : `https://fred.stlouisfed.org/series/${sid}`;
      a.target = '_blank'; a.rel = 'noopener noreferrer'; td.append(a);
      tr.append(node('td', '', label), td, node('td', '', agency), node('td', '', latest(field)?.month || '—'));
      body.append(tr);
    });
  }

  function render() {
    if (failed) {
      $('asof').textContent = t('state.unavailable');
      configs.forEach((c) => { kit.ready(c.box); c.box.append(node('p', 'error', t('state.unavailable'))); });
      return;
    }
    if (!rows.length) return;
    drawSummary(); configs.forEach(drawChart); drawTable(); drawSources();
  }
  $('year').addEventListener('change', drawTable);
  kit.onRedraw(render);
  Promise.all([kit.csv('data/monthly.csv'), d3.json('variants.json')]).then(([data, catalog]) => {
    if (!data.length || !['month', 'fetched_at', ...numericFields].every((key) => data.columns.includes(key))) throw new Error('Invalid monthly CSV');
    const fields = data.columns.filter((name) => !['month', 'as_of', 'fetched_at'].includes(name));
    for (const c of configs.filter((chart) => chart.selector)) {
      for (const [key, spec] of Object.entries(catalog[c.id])) {
        const prefix = `${c.id}_${key}_`;
        const modes = spec.index ? ['yoy', 'mom', 'index'] : ['yoy', 'mom'];
        if (!modes.every((mode) => fields.includes(prefix + mode))) continue;
        c.variants[key] = { ...spec, fields: Object.fromEntries(modes.map((mode) => [mode, prefix + mode])) };
        const option = translated('option', `variant.${key}`); option.value = key; c.selector.append(option);
      }
      c.selector.disabled = !Object.keys(c.variants).length;
    }
    rows = data.map((r) => ({ ...r, d: new Date(`${r.month}-01T00:00:00Z`),
      ...Object.fromEntries(fields.map((field) => [field, kit.num(r[field])])) })).sort((a, b) => a.d - b.d);
    if (rows.some((r) => !Number.isFinite(r.d.getTime()))) throw new Error('Invalid observation month');
    configs.forEach((c) => {
      const chartFields = [...Object.values(c.fields), ...Object.values(c.variants || {}).flatMap((v) => Object.values(v.fields))];
      const valid = rows.filter((r) => chartFields.some((field) => Number.isFinite(r[field])));
      if (!valid.length) { kit.ready(c.box); c.box.append(node('p', 'error', t('state.unavailable'))); return; }
      c.range = kit.rangePicker(c.rangeHost, { min: valid[0].d, max: valid.at(-1).d, initial: '5y', onChange: () => drawChart(c) });
    });
    const years = [...new Set(rows.slice().reverse().map((r) => r.month.slice(0, 4)))];
    years.forEach((year) => { const option = node('option', '', year); option.value = year; $('year').append(option); });
    const all = node('option', '', t('history.all')); all.value = 'all'; $('year').append(all); $('year').disabled = false;
    render();
  }).catch((error) => {
    console.error(error); failed = true; $('load-error').hidden = false; render();
  });
})();
