/* Copper dashboard. CSVs retain missing values and each series' own dates. */
(() => {
  const $ = (id) => document.getElementById(id);
  const t = (key, vars) => i18n.t(key, vars);
  const el = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text != null) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  };
  const markets = ['cme', 'lme', 'shfe'];
  const pairs = ['cme_lme', 'shfe_lme', 'shfe_cme'];
  const series = ['cme_price', 'lme_price', 'shfe_price', 'cme_stock', 'lme_stock', 'shfe_stock', 'usdcny'];
  const colors = ['var(--s2)', 'var(--s1)', 'var(--s3)'];
  const asDate = (s) => new Date(`${s}T00:00:00Z`);
  const fmt = (v, decimals = 2) => Number.isFinite(v) ? d3.format(`,.${decimals}f`)(v) : '—';
  const age = (day) => Math.max(0, Math.floor((d3.utcDay.floor(new Date()) - asDate(day)) / 86400000));
  const stale = (s, day) => !day || age(day) > (s === 'shfe_stock' ? 14 : 7);
  let D = null;
  const ranges = {}, hidden = { prices: new Set(), premiums: new Set(), stocks: new Set() };
  const basis = () => $('basis').value;
  const metric = () => $('metric').value;
  const priceKey = (market) => market === 'shfe' ? `shfe_${basis()}_usd_t` : `${market}_usd_t`;
  const priceUnit = () => $('price-unit').value;
  const priceUnitLabel = () => t({ usd_t: 'usdT', usd_lb: 'usdLb', cny_t: 'cnyT' }[priceUnit()]);
  const priceDecimals = () => priceUnit() === 'usd_lb' ? 4 : 2;
  function chartPrice(row, market) {
    // Domestic CNY quotes need no FX round trip; retain their own observation dates.
    if (priceUnit() === 'cny_t' && market === 'shfe') {
      if (!Number.isFinite(row.shfe_price)) return NaN;
      if (basis() === 'gross') return row.shfe_price;
      return Number.isFinite(row.vat_rate) && row.vat_rate >= 0 ? row.shfe_price / (1 + row.vat_rate) : NaN;
    }
    const usd = row[priceKey(market)];
    if (!Number.isFinite(usd)) return NaN;
    if (priceUnit() === 'usd_lb') return usd / (1000 / 0.45359237);
    if (priceUnit() === 'cny_t') return Number.isFinite(row.usdcny) && row.usdcny > 0 ? usd * row.usdcny : NaN;
    return usd;
  }
  const latest = (key) => D.daily.findLast((r) => Number.isFinite(r[key]));

  function drawSnapshot() {
    $('snapshot').replaceChildren(...markets.map((market, i) => {
      const card = el('article', null, 'kpi');
      card.style.setProperty('--market-color', colors[i]);
      const price = D.bySeries[`${market}_price`].at(-1);
      const stock = D.bySeries[`${market}_stock`].at(-1);
      const key = priceKey(market), normalized = latest(key);
      card.append(el('h2', t(market)), el('span', t(`${market}_price`), 'kpi-label'),
        el('span', normalized ? `${fmt(normalized[key])} ${t('usdT')}` : '—', 'kpi-value'));
      if (normalized) card.append(el('span', t('convertedDate', { date: normalized.date }), `kpi-sub ${stale(`${market}_price`, normalized.date) ? 'status-warn' : ''}`));
      if (price) card.append(el('span', t('native', { value: fmt(+price.value, market === 'cme' ? 4 : 0), unit: price.unit }), 'kpi-sub'),
        el('span', t('priceDate', { date: price.date }), 'kpi-sub'));
      const tonnes = stock ? +stock.value * (market === 'cme' ? 0.90718474 : 1) : NaN;
      card.append(el('span', t('stockValue', { value: fmt(tonnes / 1e4, 2) }), 'stock-value'));
      card.append(el('span', stock ? t('stockDate', { date: stock.date }) : t('missing'), 'kpi-sub'));
      if (!stock || stale(`${market}_stock`, stock.date)) card.append(el('span', stock ? t('stale', { days: age(stock.date) }) : t('missing'), 'kpi-sub status-warn'));
      return card;
    }));
  }

  function drawFreshness() {
    const issues = series.filter((s) => stale(s, D.bySeries[s].at(-1)?.date)).length;
    $('message').textContent = issues ? t('issue', { n: issues }) : t('healthy');
  }

  function definitions(kind) {
    if (kind === 'premiums') return pairs.map((pair, i) => ({ id: pair, key: `${pair}_${basis()}_${metric()}`, label: t(pair), color: colors[i], maxGap: 7 }));
    const defs = markets.map((market, i) => ({ id: market, key: kind === 'stocks' ? `${market}_stock_t` : priceKey(market),
      label: t(market), color: colors[i], maxGap: kind === 'stocks' && market === 'shfe' ? 14 : 7 }));
    if (kind === 'stocks') defs.push({ id: 'total', key: 'total_stock_t', label: t('stocks.total'), color: 'var(--s4)', maxGap: 14, width: 2.6 });
    return defs;
  }

  function drawChart(kind) {
    if (kind === 'prices') $('price-unit-label').textContent = priceUnitLabel();
    const box = $(`${kind}-chart`), card = $(kind), defs = definitions(kind);
    const [start, end] = ranges[kind].get();
    const rows = D.daily.filter((r) => r.d >= start && r.d <= end);
    const selected = defs.filter((def) => !hidden[kind].has(def.id));
    $(`${kind}-legend`).replaceChildren(...defs.map((def) => {
      const button = el('button'); button.type = 'button';
      button.setAttribute('aria-pressed', String(!hidden[kind].has(def.id)));
      const swatch = el('i', null, 'line'); swatch.style.background = def.color;
      button.append(swatch, def.label);
      button.addEventListener('click', () => {
        if (hidden[kind].has(def.id)) hidden[kind].delete(def.id); else hidden[kind].add(def.id);
        drawChart(kind);
      });
      return button;
    }));
    kit.ready(box);
    if (!selected.length) { kit.fail(box, t('hidden')); return; }
    const displayValue = (row, def) => kind === 'prices' ? chartPrice(row, def.id)
      : Number.isFinite(row[def.key]) ? row[def.key] / (kind === 'stocks' ? 1e4 : 1) : NaN;
    const values = rows.flatMap((r) => selected.map((def) => displayValue(r, def)).filter(Number.isFinite));
    if (!values.length) { kit.fail(box, t('empty')); return; }
    const W = Math.max(260, box.clientWidth), H = 300, m = { l: 61, r: 12, t: 12, b: 30 };
    let domain = d3.extent(values);
    if (kind !== 'prices') domain = [Math.min(0, domain[0]), Math.max(0, domain[1])];
    const pad = (domain[1] - domain[0]) * .08 || Math.abs(domain[0]) * .05 || 1;
    const y = d3.scaleLinear([domain[0] - (kind === 'stocks' ? 0 : pad), domain[1] + pad], [H - m.b, m.t]).nice();
    const x = d3.scaleUtc([start, +end === +start ? d3.utcDay.offset(end, 1) : end], [m.l, W - m.r]);
    const svg = d3.select(box).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('width', '100%').attr('role', 'img').attr('aria-label', t(`${kind}.title`));
    svg.append('title').text(t(`${kind}.title`));
    const ax = svg.append('g').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(Math.max(2, Math.floor(W / 120))).tickFormat(d3.utcFormat('%Y-%m')).tickSizeOuter(0));
    const tickFormat = kind === 'prices' && priceUnit() === 'usd_lb' ? ',.4~f' : kind === 'stocks' ? ',.2~f' : '~s';
    const ay = svg.append('g').attr('transform', `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5).tickFormat(d3.format(tickFormat)).tickSize(-(W - m.l - m.r)));
    ay.select('.domain').remove(); kit.axisStyle(ax, ay);
    if (kind === 'premiums') svg.append('line').attr('x1', m.l).attr('x2', W - m.r).attr('y1', y(0)).attr('y2', y(0)).attr('stroke', 'var(--axis)').attr('stroke-dasharray', '4 4');
    for (const def of selected) {
      const valid = rows.filter((r) => Number.isFinite(displayValue(r, def)));
      const segments = [];
      for (const row of valid) {
        const prev = segments.at(-1);
        // Inventory observations keep their weekly/daily cadence. Price gaps break
        // when another market has a dated row with this series missing.
        const missing = prev && kind !== 'stocks' && rows.some((r) => r.d > prev.d && r.d < row.d && !Number.isFinite(displayValue(r, def)));
        if (prev && (row.d - prev.d > def.maxGap * 86400000 || missing)) segments.push(null);
        segments.push(row);
      }
      svg.append('path').datum(segments).attr('data-series', def.id).attr('d', d3.line().defined((r) => r !== null).x((r) => x(r.d)).y((r) => y(displayValue(r, def))))
        .attr('fill', 'none').attr('stroke', def.color).attr('stroke-width', def.width || 1.8);
      svg.append('g').selectAll('circle').data(valid).join('circle').attr('cx', (r) => x(r.d)).attr('cy', (r) => y(displayValue(r, def))).attr('r', valid.length > 150 ? 1.6 : 2.4).attr('fill', def.color);
    }
    const hoverRows = rows.filter((r) => selected.some((def) => Number.isFinite(displayValue(r, def))));
    const tooltip = kit.tip(card);
    tooltip.hide();
    const line = svg.append('line').attr('y1', m.t).attr('y2', H - m.b).attr('stroke', 'var(--axis)').style('opacity', 0);
    svg.append('rect').attr('x', m.l).attr('y', m.t).attr('width', W - m.l - m.r).attr('height', H - m.t - m.b).attr('fill', 'transparent')
      .on('pointermove', (event) => {
        const index = d3.bisector((r) => r.d).center(hoverRows, x.invert(d3.pointer(event)[0]));
        const row = hoverRows[index];
        line.attr('x1', x(row.d)).attr('x2', x(row.d)).style('opacity', 1);
        const unit = kind === 'prices' ? priceUnitLabel() : kind === 'stocks' ? t('tenThousandT') : metric() === 'pct' ? '%' : t('usdT');
        tooltip.show(event, [{ text: row.date }, ...selected.map((def) => ({ color: def.color,
          text: `${def.label}: ${fmt(displayValue(row, def), kind === 'prices' ? priceDecimals() : 2)} ${Number.isFinite(displayValue(row, def)) ? unit : ''}` }))]);
      }).on('pointerleave', () => { tooltip.hide(); line.style('opacity', 0); });
  }

  function drawAll() {
    if (!D) return;
    drawSnapshot(); drawFreshness();
    $('premium-note').textContent = t('premium.note', { basis: t(basis()) });
    $('premium-unit').textContent = metric() === 'pct' ? '%' : t('usdT');
    $('pair-latest').replaceChildren(...definitions('premiums').map((def) => {
      const row = latest(def.key), span = el('span');
      span.append(el('strong', `${def.label}: ${fmt(row?.[def.key])}${metric() === 'pct' ? '%' : ` ${t('usdT')}`}`), ` · ${row?.date || t('missing')}`);
      return span;
    }));
    for (const kind of ['prices', 'premiums', 'stocks']) drawChart(kind);
  }

  kit.sectionNav($('secnav'));
  $('basis').addEventListener('change', drawAll);
  $('metric').addEventListener('change', drawAll);
  $('price-unit').addEventListener('change', () => { if (D) drawChart('prices'); });
  Promise.all([kit.csv('data/daily.csv'), kit.csv('data/observations.csv')]).then(([daily, observations]) => {
    D = { daily: daily.map((r) => Object.fromEntries(Object.entries(r).map(([k, v]) => [k, k === 'date' ? v : kit.num(v)]))).map((r) => ({ ...r, d: asDate(r.date) })),
      bySeries: Object.fromEntries(series.map((s) => [s, observations.filter((r) => r.series === s).sort((a, b) => a.date.localeCompare(b.date))])) };
    D.daily.sort((a, b) => a.d - b.d);
    for (const kind of ['prices', 'premiums', 'stocks']) {
      const relevant = D.daily.filter((r) => kind === 'prices'
        ? ['cme_usd_t', 'lme_usd_t', 'shfe_price'].some((key) => Number.isFinite(r[key]))
        : definitions(kind).some((def) => Number.isFinite(r[def.key])));
      const today = d3.utcDay.floor(new Date());
      const min = relevant[0]?.d || d3.utcYear.offset(today, -1), max = relevant.at(-1)?.d || today;
      ranges[kind] = kit.rangePicker($(`${kind}-range`), { min, max, initial: '1y', onChange: () => drawChart(kind) });
    }
    drawAll(); kit.onRedraw(drawAll);
  }).catch((err) => {
    console.error(err);
    const show = () => {
      $('message').textContent = t('loadError');
      ['prices', 'premiums', 'stocks'].forEach((kind) => kit.fail($(`${kind}-chart`), t('empty')));
    };
    show(); i18n.onChange(show);
  });
})();
