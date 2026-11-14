/* Reviewed mine capacity events; never infer gross flows from net output changes. */
(() => {
  const $ = (id) => document.getElementById(id), t = (key, vars) => i18n.t(key, vars);
  const node = (tag, text) => { const n = document.createElement(tag); if (text != null) n.textContent = text; return n; };
  const defs = [
    { key: 'retired', color: 'var(--s2)' },
    { key: 'commissioned', color: 'var(--s1)' },
    { key: 'started', color: 'var(--s4)' },
  ];
  const hidden = new Set(), fmt = (v) => Number.isFinite(v) ? d3.format(',.2f')(v / 1e4) : '—';
  const nullable = (v) => v === '' || v == null ? null : kit.num(v);
  const local = (r, key) => r[`${key}_${i18n.lang === 'zh' ? 'zh' : 'en'}`];
  let annual = [], events = [], range, selected;
  function details() {
    const rows = events.filter((r) => r.year === selected && !hidden.has(r.kind));
    $('capacity-events').replaceChildren(...rows.map((r) => {
      const tr = node('tr'), name = node('td', local(r, 'project'));
      name.append(node('small', local(r, 'note')));
      const amount = node('td', r.capacity_tpa == null ? t('capacity.unknown') : `${fmt(r.capacity_tpa)} ${t('capacity.unit')}`);
      if (r.basis !== 'unquantified') amount.append(node('small', t(`capacity.${r.basis}`)));
      tr.append(node('td', t(`capacity.${r.kind}`)), name, node('td', local(r, 'country')), amount); return tr;
    }));
    $('capacity-detail-note').textContent = t(rows.length ? 'capacity.detail' : 'capacity.noEvents');
  }
  function draw() {
    const box = $('capacity-chart'), [from, to] = range.get();
    const rows = annual.filter((r) => r.d >= from && r.d <= to), visible = defs.filter((d) => !hidden.has(d.key));
    if (!rows.some((r) => r.year === selected)) selected = rows.at(-1)?.year;
    $('capacity-year').replaceChildren(...rows.map((r) => {
      const o = node('option', String(r.year) + (r.partial_year ? t('capacity.partial', { date: r.as_of }) : ''));
      o.value = r.year; return o;
    }));
    $('capacity-year').value = String(selected); $('capacity-year').disabled = !rows.length;
    $('capacity-legend').replaceChildren(...defs.map((d) => {
      const b = node('button'), sw = node('i'); sw.className = 'line'; sw.style.background = d.color;
      b.type = 'button'; b.setAttribute('aria-pressed', String(!hidden.has(d.key))); b.append(sw, t(`capacity.${d.key}`));
      b.onclick = () => { hidden.has(d.key) ? hidden.delete(d.key) : hidden.add(d.key); draw(); }; return b;
    }));
    const latest = annual.at(-1);
    $('capacity-asof').textContent = t(latest.partial_year ? 'capacity.asof' : 'capacity.closedYear', { date: latest.as_of, year: latest.year });
    details(); kit.ready(box);
    const tip = kit.tip($('capacity')); tip.hide();
    if (!rows.length || !visible.length) { kit.fail(box, t(!rows.length ? 'empty' : 'hidden')); return; }
    const W = Math.max(260, box.clientWidth), H = 300, m = { l: 48, r: 24, t: 18, b: 34 };
    const y = d3.scaleLinear([0, Math.max(1, (d3.max(rows, (r) => d3.max(visible, (d) => r[`${d.key}_tpa`])) || 0) / 1e4 * 1.12)], [H - m.b, m.t]).nice();
    const x = d3.scaleUtc([d3.utcMonth.offset(from, -5), d3.utcMonth.offset(to, 5)], [m.l, W - m.r]);
    const svg = d3.select(box).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${H}`).attr('role', 'img').attr('aria-label', t('capacity.title'));
    const ticks = rows.filter((_, i) => i % Math.max(1, Math.ceil(rows.length / (W / 65))) === 0).map((r) => r.d);
    const ax = svg.append('g').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickValues(ticks).tickFormat(d3.utcFormat('%Y')).tickSizeOuter(0));
    const ay = svg.append('g').attr('transform', `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5).tickSize(-(W - m.l - m.r)));
    ay.select('.domain').remove(); kit.axisStyle(ax, ay);
    for (const d of visible) {
      const value = (r) => r[`${d.key}_tpa`];
      svg.append('path').datum(rows).attr('class', 'capacity-line').attr('data-series', d.key)
        .attr('fill', 'none').attr('stroke', d.color).attr('stroke-width', 2)
        .attr('d', d3.line().defined((r) => Number.isFinite(value(r))).x((r) => x(r.d)).y((r) => y(value(r) / 1e4)));
      svg.append('g').selectAll('circle').data(rows.filter((r) => Number.isFinite(value(r)))).join('circle')
        .attr('cx', (r) => x(r.d)).attr('cy', (r) => y(value(r) / 1e4)).attr('r', 3.5)
        .attr('fill', (r) => r.partial_year || r[`${d.key}_unknown`] ? 'var(--panel)' : d.color).attr('stroke', d.color).attr('stroke-width', 1.5);
      svg.append('g').selectAll('text').data(rows.filter((r) => value(r) == null)).join('text')
        .text('?').attr('class', 'capacity-unknown').attr('x', (r) => x(r.d)).attr('y', H - m.b - 8 - defs.indexOf(d) * 17)
        .attr('text-anchor', 'middle').attr('fill', d.color);
    }
    const cursor = svg.append('line').attr('class', 'capacity-selection').attr('stroke', 'var(--fg-muted)').attr('stroke-dasharray', '3 4').attr('y1', m.t).attr('y2', H - m.b);
    const mark = () => { const r = rows.find((r) => r.year === selected); cursor.attr('x1', x(r.d)).attr('x2', x(r.d)); };
    mark();
    const nearest = (event) => rows[d3.bisector((r) => r.d).center(rows, x.invert(d3.pointer(event)[0]))];
    svg.append('rect').attr('x', m.l).attr('y', m.t).attr('width', W - m.l - m.r).attr('height', H - m.t - m.b).attr('fill', 'transparent')
      .on('pointermove', (event) => {
        const r = nearest(event), lines = [{ text: `${r.year}${r.partial_year ? t('capacity.partial', { date: r.as_of }) : ''}` }];
        for (const d of visible) {
          lines.push({ color: d.color, text: `${t(`capacity.${d.key}`)}: ${t('capacity.value', { value: fmt(r[`${d.key}_tpa`]), count: r[`${d.key}_count`] - r[`${d.key}_unknown`] })}` });
          if (r[`${d.key}_unknown`]) lines.push({ text: t('capacity.unquantified', { n: r[`${d.key}_unknown`] }) });
          else if (!r[`${d.key}_count`]) lines.push({ text: t('capacity.none') });
        }
        tip.show(event, lines);
      }).on('pointerleave', () => tip.hide())
      .on('click', (event) => { selected = nearest(event).year; $('capacity-year').value = String(selected); mark(); details(); });
    $('capacity-year').onchange = () => { selected = +$('capacity-year').value; mark(); details(); tip.hide(); };
  }
  Promise.all([kit.csv('data/capacity-annual.csv'), kit.csv('data/capacity-events.csv')]).then(([rows, entries]) => {
    if (!rows.length || !entries.length) throw new Error('Empty capacity register');
    const id = rows[0].dataset_id;
    if (!id || [...rows, ...entries].some((r) => r.dataset_id !== id)) throw new Error('Mismatched capacity data generations');
    annual = rows.map((r) => ({ ...r, year: +r.year, partial_year: +r.partial_year, d: new Date(`${r.year}-12-31T00:00:00Z`),
      ...Object.fromEntries(defs.flatMap((d) => ['tpa', 'count', 'unknown'].map((s) => [`${d.key}_${s}`, s === 'tpa' ? nullable(r[`${d.key}_${s}`]) : kit.num(r[`${d.key}_${s}`])]))),
    }));
    events = entries.map((r) => ({ ...r, year: +r.year, capacity_tpa: nullable(r.capacity_tpa) }));
    if (annual.some((r, i) => !Number.isInteger(r.year) || !Number.isFinite(+r.d) || (i && r.year !== annual[i - 1].year + 1))
      || events.some((r) => !defs.some((d) => d.key === r.kind) || !annual.some((a) => a.year === r.year))) throw new Error('Invalid capacity years or event kinds');
    // Reconcile the exported chart with its contributors; blank capacities are never zero.
    for (const r of annual) for (const d of defs) {
      const matching = events.filter((e) => e.year === r.year && e.kind === d.key), known = matching.filter((e) => e.capacity_tpa != null);
      const expected = !known.length && matching.length ? null : d3.sum(known, (e) => e.capacity_tpa);
      if (known.some((e) => !Number.isFinite(e.capacity_tpa) || e.capacity_tpa <= 0)
        || r[`${d.key}_count`] !== matching.length || r[`${d.key}_unknown`] !== matching.length - known.length
        || r[`${d.key}_tpa`] !== expected) throw new Error('Capacity totals do not match contributors');
    }
    range = kit.rangePicker($('capacity-range'), { min: annual[0].d, max: annual.at(-1).d, initial: 'all', onChange: draw });
    selected = annual.at(-1).year; draw(); kit.onRedraw(draw);
  }).catch((err) => {
    console.error(err); const fail = () => { kit.fail($('capacity-chart'), t('capacity.error')); $('capacity-year').disabled = true; };
    fail(); i18n.onChange(fail);
  });
})();
