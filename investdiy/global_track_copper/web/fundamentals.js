/* Annual fundamentals and an offline SVG mine map. Values are never annualised. */
(() => {
  const $ = (id) => document.getElementById(id), t = (key, vars) => i18n.t(key, vars);
  const node = (tag, text, cls) => {
    const n = document.createElement(tag); if (text != null) n.textContent = text; if (cls) n.className = cls; return n;
  };
  const fmt = (v, digits = 1) => Number.isFinite(v) ? d3.format(`,.${digits}f`)(v) : '—';
  const defs = [
    { key: 'mine_production_t', label: 'annual.mine', color: 'var(--s3)' },
    { key: 'refined_production_t', label: 'annual.supply', color: 'var(--s1)' },
    { key: 'refined_usage_t', label: 'annual.demand', color: 'var(--s2)' },
    { key: 'secondary_refined_t', label: 'annual.secondary', color: 'var(--s4)' },
  ];
  const hidden = new Set(), ranges = {};
  const forecastDefs = [
    { key: 'forecast_supply_t', label: 'forecast.supply', color: 'var(--s1)', forecast: true },
    { key: 'forecast_demand_t', label: 'forecast.demand', color: 'var(--s2)', forecast: true },
  ];
  let annual = [], forecasts = [], mines = [], world = null, selected = null, page = 0;
  const showForecast = () => $('annual-forecast').checked && forecasts.length > 0;
  let mapSvg, zoom, zoomState = d3.zoomIdentity;
  const statusColors = { prod: 'var(--s4)', care: 'var(--s2)', cons: 'var(--s1)', ramp: 'var(--s5)', stockpile: 'var(--s7)', proj: 'var(--s3)', unknownStatus: 'var(--fg-muted)', closed: 'var(--fg-muted)', suspended: 'var(--s2)' };
  const statusName = (s) => t(`mines.${s}`);
  const country = (r) => (i18n.lang === 'zh' ? r.country_zh : r.country_en) || r.country_en || r.country;
  const local = (r, key) => (i18n.lang === 'zh' ? r[`${key}_zh`] : '') || r[key];
  const output = (r) => Number.isFinite(r.production_t) ? `${fmt(r.production_t, 0)} ${t('tonnes')}` : t('mines.noProduction');
  function drawAnnual(kind) {
    const projecting = kind === 'annual' && showForecast();
    const box = $(`${kind}-chart`), [start, end] = ranges[projecting ? 'forecast' : kind].get();
    const rows = (projecting ? [...annual, ...forecasts] : annual).filter((r) => r.d >= start && r.d <= end);
    const availableDefs = projecting ? [...defs, ...forecastDefs] : defs;
    const selectedDefs = kind !== 'balance' ? availableDefs.filter((d) => !hidden.has(d.key)) : [{ key: 'balance_t', label: 'balance.value', color: 'var(--s4)' }];
    if (kind !== 'balance') $(`${kind}-legend`).replaceChildren(...availableDefs.map((d) => {
      const b = node('button'), sw = node('i', null, 'line'); sw.style.background = d.color;
      if (d.forecast) { sw.classList.add('forecast-swatch'); sw.style.setProperty('--forecast-color', d.color); }
      b.type = 'button'; b.setAttribute('aria-pressed', String(!hidden.has(d.key))); b.append(sw, t(d.label));
      b.onclick = () => { hidden.has(d.key) ? hidden.delete(d.key) : hidden.add(d.key); drawAnnual(kind); }; return b;
    }));
    if (kind === 'annual') {
      $('annual-range').hidden = projecting;
      $('annual-forecast-range').hidden = !projecting;
      $('annual-forecast-detail').hidden = !projecting;
      $('annual-forecast-status').textContent = forecasts.length ? '' : t('forecast.unavailable');
      $('annual-forecast-status').hidden = forecasts.length > 0;
      $('annual-forecast-milestones').replaceChildren(...rows.filter((r) => projecting && [2030, 2035, 2040].includes(r.year)).map((r) => {
        const card = node('div');
        card.append(node('strong', String(r.year)), node('span', t('forecast.milestone', {
          supply: fmt(r.forecast_supply_t / 1e4, 0), demand: fmt(r.forecast_demand_t / 1e4, 0),
          gap: fmt(Math.abs(r.forecast_balance_t) / 1e4, 0), balance: t(r.forecast_balance_t < 0 ? 'forecast.deficit' : 'forecast.surplus'),
        }))); return card;
      }));
    }
    kit.ready(box);
    if (!rows.length || !selectedDefs.length) { kit.fail(box, t(!selectedDefs.length ? 'hidden' : 'empty')); return; }
    const W = Math.max(260, box.clientWidth), H = 300, m = { l: 54, r: 16, t: 16, b: 34 };
    const divisor = 1e4;
    const values = rows.flatMap((r) => selectedDefs.map((d) => Number.isFinite(r[d.key]) ? r[d.key] / divisor : NaN));
    if (!values.some(Number.isFinite)) { kit.fail(box, t('empty')); return; }
    let [lo, hi] = d3.extent(values); lo = Math.min(0, lo); hi = Math.max(0, hi);
    const pad = (hi - lo) * .08 || 1;
    const y = d3.scaleLinear([lo < 0 ? lo - pad : 0, hi + pad], [H - m.b, m.t]).nice();
    const x = d3.scaleUtc([d3.utcMonth.offset(start, -5), d3.utcMonth.offset(end, 5)], [m.l, W - m.r]);
    const svg = d3.select(box).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('width', '100%').attr('role', 'img').attr('aria-label', t(`${kind}.title`));
    const ticks = projecting ? rows.filter((r) => r.year % (W < 500 ? 10 : 5) === 0).map((r) => r.d)
      : rows.filter((_, i) => i % Math.max(1, Math.ceil(rows.length / (W / 80))) === 0).map((r) => r.d);
    const ax = svg.append('g').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickValues(ticks).tickFormat(d3.utcFormat('%Y')).tickSizeOuter(0));
    const ay = svg.append('g').attr('transform', `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5).tickSize(-(W - m.l - m.r)));
    ay.select('.domain').remove(); kit.axisStyle(ax, ay);
    const tooltip = kit.tip($(kind)); tooltip.hide();
    const show = (event, r) => {
      const projected = Number.isFinite(r.forecast_supply_t);
      const lines = selectedDefs.filter((d) => Boolean(d.forecast) === projected).map((d) => ({ color: d.color, text: `${t(d.label)}: ${fmt(Number.isFinite(r[d.key]) ? r[d.key] / divisor : NaN, projected ? 0 : 2)} ${t('tenThousandT')}` }));
      if (projected && forecastDefs.every((d) => !hidden.has(d.key))) lines.push({ text: `${t('forecast.balance')}: ${fmt(r.forecast_balance_t / divisor, 0)} ${t('tenThousandT')}` });
      tooltip.show(event, [{ text: `${r.year}${projected ? ` · ${t('forecast.edition')}` : ''}` }, ...lines]);
    };
    if (projecting) {
      const boundary = Math.max(m.l, Math.min(W - m.r, x(forecasts[0].d)));
      svg.append('line').attr('class', 'forecast-boundary').attr('x1', boundary).attr('x2', boundary)
        .attr('y1', m.t).attr('y2', H - m.b).attr('stroke', 'var(--fg-muted)').attr('stroke-dasharray', '3 4');
      if (forecastDefs.every((d) => !hidden.has(d.key))) svg.append('path').datum(rows)
        .attr('class', 'forecast-gap').attr('fill', 'var(--s2)').attr('fill-opacity', .12)
        .attr('d', d3.area().defined((r) => Number.isFinite(r.forecast_balance_t))
          .x((r) => x(r.d)).y0((r) => y(r.forecast_supply_t / divisor)).y1((r) => y(r.forecast_demand_t / divisor)));
    }
    if (kind === 'balance') {
      const bw = Math.min(42, (W - m.l - m.r) / rows.length * .65);
      svg.append('line').attr('x1', m.l).attr('x2', W - m.r).attr('y1', y(0)).attr('y2', y(0)).attr('stroke', 'var(--axis)');
      svg.selectAll('rect.balance-bar').data(rows).join('rect').attr('class', 'balance-bar')
        .attr('x', (r) => x(r.d) - bw / 2).attr('width', bw).attr('y', (r) => Math.min(y(0), y(r.balance_t / divisor)))
        .attr('height', (r) => Math.max(1, Math.abs(y(0) - y(r.balance_t / divisor))))
        .attr('fill', (r) => r.balance_t >= 0 ? 'var(--s4)' : 'var(--s2)');
    } else for (const d of selectedDefs) {
      svg.append('path').datum(rows).attr('class', 'annual-line').attr('data-series', d.key).attr('fill', 'none').attr('stroke', d.color).attr('stroke-width', 2)
        .attr('stroke-dasharray', d.forecast ? '6 4' : null)
        .attr('d', d3.line().defined((r) => Number.isFinite(r[d.key])).x((r) => x(r.d)).y((r) => y(r[d.key] / divisor)));
      svg.append('g').selectAll('circle').data(rows.filter((r) => Number.isFinite(r[d.key]))).join('circle').attr('cx', (r) => x(r.d)).attr('cy', (r) => y(r[d.key] / divisor)).attr('r', 3).attr('fill', d.color);
    }
    svg.append('rect').attr('x', m.l).attr('y', m.t).attr('width', W - m.l - m.r).attr('height', H - m.t - m.b).attr('fill', 'transparent')
      .on('pointermove', (event) => show(event, rows[d3.bisector((r) => r.d).center(rows, x.invert(d3.pointer(event)[0]))]))
      .on('pointerleave', () => tooltip.hide());
  }
  Promise.all([kit.csv('data/annual.csv'), kit.csv('data/refining.csv').catch((err) => {
    console.warn('Secondary refined copper data unavailable', err); return [];
  }), kit.csv('data/forecasts.csv').catch((err) => {
    console.warn('Copper forecasts unavailable', err); return [];
  })]).then(([rows, refining, projected]) => {
    const secondary = new Map(refining.map((r) => [r.year, kit.num(r.secondary_refined_t)]));
    annual = rows.map((r) => ({ ...r, year: +r.year, d: new Date(`${r.year}-12-31T00:00:00Z`),
      ...Object.fromEntries([...defs.map((d) => d.key), 'balance_t'].map((k) => [k, kit.num(r[k])])), secondary_refined_t: secondary.get(r.year) ?? null })).sort((a, b) => a.year - b.year);
    if (!annual.length) throw new Error('Empty annual data');
    // Only this reviewed scenario is supported; malformed/mixed files cannot look like history.
    const parsed = projected.map((r) => ({ ...r, year: +r.year, d: new Date(`${r.year}-12-31T00:00:00Z`),
      ...Object.fromEntries([...forecastDefs.map((d) => d.key), 'forecast_balance_t'].map((k) => [k, kit.num(r[k])])) }));
    if (parsed.length === 15 && parsed.every((r, i) => r.year === 2026 + i && r.scenario === 'spglobal-2026-baseline'
      && r.publication === '2026-01' && r.forecast_supply_t > 0 && r.forecast_demand_t > 0
      && Number.isFinite(r.forecast_supply_t) && Number.isFinite(r.forecast_demand_t) && Number.isFinite(r.forecast_balance_t)
      && Math.abs(r.forecast_supply_t - r.forecast_demand_t - r.forecast_balance_t) < 1)) {
      forecasts = parsed.filter((r) => r.year > annual.at(-1).year);
    }
    $('annual-forecast').disabled = !forecasts.length;
    $('annual-forecast').checked = forecasts.length > 0;
    for (const kind of ['annual', 'balance']) ranges[kind] = kit.rangePicker($(`${kind}-range`), { min: annual[0].d, max: annual.at(-1).d, initial: 'all', onChange: () => drawAnnual(kind) });
    if (forecasts.length) ranges.forecast = kit.rangePicker($('annual-forecast-range'), {
      min: annual[0].d, max: forecasts.at(-1).d, initial: 'all', onChange: () => drawAnnual('annual'),
    });
    $('annual-forecast').onchange = () => drawAnnual('annual');
    const draw = () => {
      drawAnnual('annual'); drawAnnual('balance'); const r = annual.at(-1);
      $('annual-latest').textContent = t('annual.latest', { year: r.year, mine: fmt(r.mine_production_t / 1e4, 2), supply: fmt(r.refined_production_t / 1e4, 2), demand: fmt(r.refined_usage_t / 1e4, 2) });
    }; draw(); kit.onRedraw(draw);
  }).catch((err) => {
    console.error(err); const fail = () => ['annual', 'balance'].forEach((k) => kit.fail($(`${k}-chart`), t('fundamentals.error'))); fail(); i18n.onChange(fail);
  });


  // Normalise only the marker's time denominator; preserve reported ownership/product basis.
  const monthlyOutput = (r) => {
    if (!Number.isFinite(r.production_t) || r.production_t < 0) return null;
    const p = r.production_period || '';
    const months = /^(FY)?20\d{2}$/.test(p) ? 12 : /^Q[1-4] 20\d{2}$/.test(p) ? 3 : /^H[12] 20\d{2}$/.test(p) ? 6 : /^9M 20\d{2}$/.test(p) ? 9 : null;
    return months ? r.production_t / months : null;
  };
  const monthlyText = (r) => Number.isFinite(monthlyOutput(r)) ? `${fmt(monthlyOutput(r), 0)} ${t('mines.tonnesMonth')}` : t('mines.unknown');

  function filtered() {
    const query = $('mine-search').value.toLocaleLowerCase().trim(), cc = $('mine-country').value, status = $('mine-status').value;
    return mines.filter((r) => (!cc || r.country === cc) && (!status || r.status === status) &&
      (!query || [r.name, r.name_zh, r.owners, r.owners_zh, r.operator, r.operator_zh, r.reporter, country(r), r.country_en].join(' ').toLocaleLowerCase().includes(query)));
  }
  function selectMine(r) { selected = r.id; drawDetail(); drawMap(); drawTable(); }
  function drawDetail() {
    const host = $('mine-detail'), r = mines.find((m) => m.id === selected); host.replaceChildren();
    if (!r) { host.append(node('p', t('mines.choose'), 'note')); return; }
    host.append(node('h3', local(r, 'name')), node('p', `${country(r)} · ${statusName(r.status)}`, 'mine-status-label'));
    const list = node('dl');
    const fields = [['mines.company', local(r, 'owners')], ['mines.operator', local(r, 'operator')], ['mines.asof', r.status_asof],
      ['mines.production', output(r)], ['mines.monthly', monthlyText(r)], ['mines.period', r.production_period], ['mines.form', r.production_form ? t(`form.${r.production_form}`) : ''], ['mines.scope', local(r, 'production_scope')], ['mines.basis', r.production_basis ? t(`basis.${r.production_basis}`) : ''], ['mines.reporter', r.reporter]];
    for (const [key, value] of fields) list.append(node('dt', t(key)), node('dd', value || t('mines.unknown')));
    host.append(list);
    const note = i18n.lang === 'zh' ? r.note_zh : r.note_en;
    if (note) host.append(node('p', note, 'note'));
    if (r.status_asof && new Date() - new Date(`${r.status_asof.slice(0, 7)}-01`) > 366 * 864e5) host.append(node('p', t('mines.stale'), 'note status-warn'));
    if (Number.isFinite(r.production_t)) host.append(node('p', t('mines.notAnnual'), 'note'));
  }
  function drawTable() {
    const rows = filtered(), pages = Math.max(1, Math.ceil(rows.length / 12)); page = Math.min(page, pages - 1);
    $('mine-count').textContent = t('mines.count', { n: rows.length });
    $('mine-rows').replaceChildren(...rows.slice(page * 12, page * 12 + 12).map((r) => {
      const tr = node('tr'); if (r.id === selected) tr.className = 'selected';
      const name = node('td'), b = node('button', local(r, 'name')); b.type = 'button'; b.onclick = () => selectMine(r); name.append(b);
      tr.append(name, node('td', country(r)), node('td', statusName(r.status)), node('td', local(r, 'owners') || t('mines.unknown')));
      const production = node('td', output(r)); if (r.production_period) production.append(node('small', `${r.production_period} · ${t(`basis.${r.production_basis}`)} · ${t(`form.${r.production_form}`)}`)); tr.append(production); return tr;
    }));
    if (!rows.length) { const row = node('tr'), cell = node('td', t('empty')); cell.colSpan = 5; row.append(cell); $('mine-rows').append(row); }
    $('mine-page').textContent = t('mines.page', { page: page + 1, pages }); $('mine-prev').disabled = page === 0; $('mine-next').disabled = page >= pages - 1;
  }
  function drawMap() {
    const box = $('mine-map'), W = Math.max(260, box.clientWidth), H = Math.max(260, Math.min(440, W * .58)); box.replaceChildren();
    const projection = d3.geoNaturalEarth1().fitExtent([[12, 12], [W - 12, H - 12]], { type: 'Sphere' });
    const path = d3.geoPath(projection);
    mapSvg = d3.select(box).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('width', '100%').attr('role', 'img').attr('aria-label', t('map.description'));
    const g = mapSvg.append('g');
    g.append('path').datum({ type: 'Sphere' }).attr('d', path).attr('class', 'map-ocean');
    g.selectAll('path.country').data(world.features).join('path').attr('class', 'country').attr('d', path);
    // A global scale stays fixed when filtering or selecting a mine. Small symbols
    // have a minimum radius for legibility; zero is an explicit hollow point.
    const size = d3.scaleSqrt([0, 125000], [0, 24]);
    const radius = (r) => Number.isFinite(monthlyOutput(r)) ? Math.max(2.5, size(monthlyOutput(r))) : 9;
    const rows = filtered().sort((a, b) => (monthlyOutput(b) || 0) - (monthlyOutput(a) || 0));
    const markers = g.selectAll('g.mine-point').data(rows).join('g').attr('class', 'mine-point')
      .attr('data-mine', (r) => r.id).attr('data-monthly-output', (r) => monthlyOutput(r))
      .attr('transform', (r) => `translate(${projection([r.longitude, r.latitude])})`)
      .on('click', (event, r) => { event.stopPropagation(); selectMine(r); });
    markers.append('circle').attr('class', 'mine-hit').attr('r', (r) => Math.max(10, radius(r)))
      .attr('fill', 'transparent');
    markers.filter((r) => Number.isFinite(monthlyOutput(r))).append('circle').attr('class', 'mine-bubble')
      .attr('r', radius).attr('fill', (r) => monthlyOutput(r) === 0 ? 'var(--panel)' : statusColors[r.status])
      .attr('fill-opacity', .7).attr('stroke', (r) => statusColors[r.status]).attr('stroke-width', 1.2);
    markers.filter((r) => !Number.isFinite(monthlyOutput(r))).append('text').text('?')
      .attr('class', 'mine-unknown').attr('text-anchor', 'middle').attr('dy', '.35em').attr('fill', (r) => statusColors[r.status]);
    markers.filter((r) => r.id === selected).append('circle').attr('class', 'mine-selection')
      .attr('r', (r) => radius(r) + 3).attr('fill', 'none').attr('stroke', 'var(--fg)').attr('stroke-width', 1.5);
    markers.append('title').text((r) => `${local(r, 'name')} · ${country(r)} · ${statusName(r.status)}\n${output(r)} · ${r.production_period || '—'}\n${t('mines.monthly')}: ${monthlyText(r)}\n${r.production_basis ? t(`basis.${r.production_basis}`) : ''}`);
    markers.append('text').attr('x', (r) => radius(r) + 5).attr('y', 3).text((r) => local(r, 'name')).attr('class', 'map-label').style('display', $('map-labels').checked ? null : 'none');
    const scaleHost = $('mine-size-legend'); scaleHost.replaceChildren(node('span', t('mines.sizeLegend')));
    for (const value of [5000, 25000, 100000]) {
      const item = node('span');
      const sample = d3.select(item).append('svg').attr('width', 54).attr('height', 54).attr('aria-hidden', 'true');
      sample.append('circle').attr('cx', 27).attr('cy', 27).attr('r', Math.max(2.5, size(value)))
        .attr('fill', 'var(--s4)').attr('fill-opacity', .7);
      item.append(node('span', fmt(value, 0))); scaleHost.append(item);
    }
    scaleHost.append(node('span', t('mines.unknownLegend')));
    zoom = d3.zoom().scaleExtent([1, 12]).translateExtent([[0, 0], [W, H]]).extent([[0, 0], [W, H]])
      .filter((event) => event.type !== 'wheel' || event.ctrlKey)
      .on('zoom', (event) => {
        zoomState = event.transform; g.attr('transform', zoomState);
        markers.attr('transform', (r) => `translate(${projection([r.longitude, r.latitude])}) scale(${1 / zoomState.k})`);
      });
    mapSvg.call(zoom).call(zoom.transform, zoomState);
    $('mine-legend').replaceChildren(...Object.entries(statusColors).filter(([s]) => mines.some((r) => r.status === s)).map(([s, color]) => {
      const item = node('span'), dot = node('i', null, 'line'); dot.style.background = color; item.append(dot, statusName(s)); return item;
    }));
  }
  function options() {
    const selectedCountry = $('mine-country').value, selectedStatus = $('mine-status').value;
    const option = (value, text) => { const n = node('option', text); n.value = value; return n; };
    const countries = [...new Map(mines.map((r) => [r.country, country(r)])).entries()].sort((a, b) => a[1].localeCompare(b[1]));
    $('mine-country').replaceChildren(option('', t('mines.all')), ...countries.map(([cc, name]) => option(cc, name)));
    $('mine-status').replaceChildren(option('', t('mines.all')), ...Object.keys(statusColors).filter((s) => mines.some((r) => r.status === s)).map((s) => option(s, statusName(s))));
    $('mine-country').value = selectedCountry; $('mine-status').value = selectedStatus;
  }
  function drawMines() { options(); drawMap(); drawTable(); drawDetail(); }
  function filterChange() { page = 0; if (!filtered().some((r) => r.id === selected)) selected = null; drawMap(); drawTable(); drawDetail(); }
  Promise.all([kit.csv('data/mines.csv'), fetch('/static/vendor/world-countries-110m.json').then((r) => { if (!r.ok) throw new Error('Map unavailable'); return r.json(); })]).then(([rows, geometry]) => {
    mines = rows.map((r) => ({ ...r, latitude: kit.num(r.latitude), longitude: kit.num(r.longitude), production_t: kit.num(r.production_t) })).sort((a, b) => a.name.localeCompare(b.name));
    if (!mines.length) throw new Error('Empty mines'); world = geometry;
    $('mine-search').addEventListener('input', filterChange); ['mine-country', 'mine-status'].forEach((id) => $(id).addEventListener('change', filterChange));
    $('map-labels').onchange = drawMap; $('map-in').onclick = () => mapSvg.call(zoom.scaleBy, 1.6); $('map-out').onclick = () => mapSvg.call(zoom.scaleBy, 1 / 1.6);
    $('map-reset').onclick = () => mapSvg.call(zoom.transform, d3.zoomIdentity);
    $('mine-prev').onclick = () => { page--; drawTable(); }; $('mine-next').onclick = () => { page++; drawTable(); };
    drawMines(); kit.onRedraw(drawMines);
  }).catch((err) => { console.error(err); const fail = () => kit.fail($('mine-map'), t('fundamentals.error')); fail(); i18n.onChange(fail); });
})();
