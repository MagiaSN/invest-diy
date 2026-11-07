/* Reusable single-series freight chart. Each instance owns its selection, date
   picker and DOM; the page owns the list and enforces the minimum chart count. */
(function () {
  const t = (key, values) => i18n.t(key, values);
  const name = (row) => i18n.lang === 'zh' ? row.name : row.name_en || row.name;
  const unitName = (unit) => unit === 'points' ? t('unit.points') : unit === 'pp' ? t('unit.pp') : unit;
  const valueText = (value) => value === '' || value == null ? '—' : kit.fmtNum(kit.num(value), 3);
  const isHistorical = (row) => {
    if (!row?.date) return false;
    // Compare calendar dates in Beijing time, including leap-year anniversaries.
    const today = new Date(Date.now() + 8 * 3600e3);
    const year = today.getUTCFullYear() - 1, month = today.getUTCMonth();
    const day = Math.min(today.getUTCDate(), new Date(Date.UTC(year, month + 1, 0)).getUTCDate());
    const cutoff = new Date(Date.UTC(year, month, day)).toISOString().slice(0, 10);
    return row.date <= cutoff;
  };
  const GAP_DAYS = 17;
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
  };
  let nextId = 0;
  // ---------------- line chart for weekly series with gaps ----------------
  /** lines: [{key, label, color, rows: [{d, date, v, src}]}] */
  function drawLines(box, card, lines, [s0, e0], H) {
    const tt = kit.tip(card);
    tt.hide();
    kit.ready(box);
    const shown = lines.map((ln) => ({ ...ln, rows: ln.rows.filter((r) => r.d >= s0 && r.d <= e0) })).filter((ln) => ln.rows.length);
    const all = shown.flatMap((ln) => ln.rows);
    if (!all.length) { box.appendChild(el('div', 'chart-empty', t('chart.empty'))); return; }
    const W = Math.max(280, box.clientWidth), m = { t: 10, r: 16, b: 26, l: 52 };
    const x = d3.scaleUtc([s0, e0], [m.l, W - m.r]);
    const y = d3.scaleLinear(d3.extent(all, (r) => r.v), [H - m.b, m.t]).nice();
    const svg = d3.select(box).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${H}`);
    const ax = svg.append('g').attr('transform', `translate(0,${H - m.b})`)
      .call(d3.axisBottom(x).ticks(Math.max(3, Math.floor(W / 110))).tickSizeOuter(0));
    const ay = svg.append('g').attr('transform', `translate(${m.l},0)`)
      .call(d3.axisLeft(y).ticks(6).tickFormat(d3.format(',')).tickSize(-(W - m.l - m.r)));
    ay.select('.domain').remove();
    kit.axisStyle(ax, ay);

    const near = (a, b) => Math.abs(b.d - a.d) <= GAP_DAYS * 864e5;
    shown.forEach((ln) => {
      const rs = ln.rows;
      // break the line where two periods are more than GAP_DAYS apart
      const segs = [];
      rs.forEach((r, i) => { if (i === 0 || !near(rs[i - 1], r)) segs.push([]); segs[segs.length - 1].push(r); });
      svg.append('g').selectAll('path').data(segs.filter((s) => s.length > 1)).join('path')
        .attr('d', d3.line((r) => x(r.d), (r) => y(r.v)))
        .style('fill', 'none').style('stroke', ln.color).style('stroke-width', 1.8).style('stroke-linejoin', 'round');
      const dots = segs.filter((s) => s.length <= 4 || rs.length <= 80).flat();  // dots on short runs (archive pairs), or everywhere when few
      svg.append('g').selectAll('circle').data(dots).join('circle')
        .attr('cx', (r) => x(r.d)).attr('cy', (r) => y(r.v)).attr('r', 2.6).style('fill', ln.color);
    });

    // tooltip: nearest period across the lines shown, with each line's value on that date
    const dates = [...new Set(all.map((r) => r.date))].sort().map((s) => ({ date: s, d: new Date(s) }));
    const byDate = shown.map((ln) => new Map(ln.rows.map((r) => [r.date, r])));
    const rule = svg.append('line').attr('y1', m.t).attr('y2', H - m.b).style('stroke', 'var(--axis)').style('opacity', 0);
    const bis = d3.bisector((r) => r.d).center;
    svg.append('rect').attr('x', m.l).attr('y', m.t).attr('width', W - m.l - m.r).attr('height', H - m.t - m.b)
      .style('fill', 'transparent')
      .on('mousemove', (event) => {
        const p = dates[bis(dates, x.invert(d3.pointer(event)[0]))];
        rule.attr('x1', x(p.d)).attr('x2', x(p.d)).style('opacity', 1);
        const rows = shown.map((ln, i) => [ln, byDate[i].get(p.date)]).filter(([, r]) => r);
        const archived = rows.some(([, r]) => r.src === 'archive');
        tt.show(event, [
          { text: p.date + (archived ? t('tip.archive') : '') },
          ...rows.map(([ln, r]) => ({ text: `${ln.label} ${valueText(r.v)} ${unitName(ln.unit || 'points')}`, color: ln.color })),
        ]);
      })
      .on('mouseleave', () => { tt.hide(); rule.style('opacity', 0); });
  }

  class FreightChart {
    constructor({ host, data, index = 'ccfi', series = 'composite', initialRange = '1y', onRemove }) {
      this.data = data;
      this.index = index;
      this.series = series;
      this.initialRange = initialRange;
      this.root = document.getElementById('freight-chart-template').content.firstElementChild.cloneNode(true);
      this.root.id = `freight-chart-${++nextId}`;
      this.q = (selector) => this.root.querySelector(selector);
      this.q('.chart-title').id = `${this.root.id}-title`;
      this.root.setAttribute('aria-labelledby', this.q('.chart-title').id);
      host.appendChild(this.root);
      this.q('.chart-index').addEventListener('change', (event) => {
        this.index = event.target.value;
        const rows = this.components();
        this.series = (rows.find((row) => row.series === 'composite' && !isHistorical(row)) || rows[0])?.series || '';
        this.resetRange();
        this.render();
      });
      this.q('.chart-series').addEventListener('change', (event) => {
        this.series = event.target.value;
        this.resetRange();
        this.render();
      });
      this.q('.chart-remove').addEventListener('click', () => onRemove(this));
      this.resetRange();
      this.setPosition(1, false);
      this.render();
    }

    components() {
      // Only entries with no observation for at least a year are moved to the end.
      return this.data.allLatest.filter((row) => row.index === this.index)
        .sort((a, b) => Number(isHistorical(a)) - Number(isHistorical(b)));
    }
    points() { return this.data.series.get(`${this.index}/${this.series}`) || []; }

    resetRange() {
      this.range?.destroy();
      let [min, max] = d3.extent(this.points(), (row) => row.d);
      min ||= new Date(); max ||= min;
      if (+min === +max) { min = d3.utcDay.offset(min, -7); max = d3.utcDay.offset(max, 1); }
      this.range = kit.rangePicker(this.q('.chart-range'), {
        min, max, initial: this.initialRange, onChange: () => this.draw(),
      });
    }

    setPosition(position, canRemove) {
      this.position = position;
      this.canRemove = canRemove;
      this.q('.chart-number').textContent = String(position).padStart(2, '0');
      this.q('.chart-remove').disabled = !canRemove;
    }

    render() {
      const meta = this.data.latest.get(`${this.index}/${this.series}`);
      const status = this.data.status.find((row) => row.index === this.index);
      const title = meta ? `${this.index.toUpperCase()} · ${name(meta)}` : this.index.toUpperCase();
      this.q('.chart-title').textContent = title;
      this.q('.chart-index-label').textContent = t('charts.index');
      this.q('.chart-series-label').textContent = t('charts.series');
      const remove = this.q('.chart-remove');
      remove.textContent = t('charts.remove');
      remove.title = this.canRemove ? t('charts.remove') : t('charts.minimum');
      remove.setAttribute('aria-label', t('charts.removeLabel', { n: this.position, title }));
      const option = (value, label, selected) => {
        const node = el('option', '', label); node.value = value; node.selected = selected; return node;
      };
      this.q('.chart-index').replaceChildren(...this.data.status.map((row) =>
        option(row.index, `${row.index.toUpperCase()} · ${name(row)}`, row.index === this.index)));
      const components = this.components();
      this.q('.chart-series').replaceChildren(...components.map((row) => {
        const suffix = isHistorical(row) ? t('t.historical') : '';
        return option(row.series, `${name(row)}${row.unit ? ` · ${unitName(row.unit)}` : ''}${suffix ? ` (${suffix})` : ''}`, row.series === this.series);
      }));
      this.q('.chart-series').disabled = !components.length;
      this.q('.chart-caption').textContent = meta ? t('charts.caption', { unit: unitName(meta.unit) || '—', n: meta.n }) : '';
      this.q('.chart-state').textContent = !meta ? t('status.not_fetched')
        : isHistorical(meta) ? t('charts.historical', { date: meta.date }) : '';
      this.q('.chart-details summary').textContent = t('charts.details');
      const values = meta ? [
        ['t.period', meta.period || meta.reported_date || '—'], ['t.current', valueText(meta.current)],
        ['t.unit', unitName(meta.unit) || '—'], ['t.weight', meta.weight || '—'],
        ['t.publishedChange', meta.change === '' ? '—' : `${valueText(meta.change)} ${unitName(meta.change_unit)}`],
        ['t.lastDate', meta.date || '—'], ['t.lastValue', valueText(meta.value)],
        ...['1w', '4w', '52w'].map((key) => [`t.${key}`, Number.isFinite(kit.num(meta[`chg_${key}`])) ? kit.fmtPct(kit.num(meta[`chg_${key}`])) : '—']),
      ] : [];
      this.q('.chart-facts').replaceChildren(...values.map(([key, value]) => {
        const pair = el('div'); pair.append(el('dt', '', t(key)), el('dd', '', value)); return pair;
      }));
      const link = this.q('.chart-source-link');
      link.href = status?.url || `https://www.sse.net.cn/index/singleIndex?indexType=${this.index}`;
      link.textContent = t('source.link');
      const age = status?.date ? (Date.now() - new Date(status.date)) / 864e5 : Infinity;
      this.q('.chart-source').textContent = status ? t('source.status', {
        date: status.date || '—', frequency: t(`frequency.${status.frequency}`), checked: status.checked_at || '—',
        success: status.last_success || '—', state: t(`status.${status.status}`), available: status.available, total: status.total,
      }) + (age > (status.frequency === 'monthly' ? 100 : 17) ? '\n' + t('source.stale') : '') : t('status.not_fetched');
      this.draw();
    }

    draw() {
      const meta = this.data.latest.get(`${this.index}/${this.series}`);
      drawLines(this.q('.chart-plot'), this.root, meta ? [{
        key: this.series, label: name(meta), unit: meta.unit, color: kit.series()[0], rows: this.points(),
      }] : [], this.range.get(), 300);
      this.q('.chart-plot svg')?.setAttribute('role', 'img');
      this.q('.chart-plot svg')?.setAttribute('aria-label', this.q('.chart-title').textContent);
    }

    destroy() { this.range.destroy(); this.root.remove(); }
  }

  window.FreightChart = FreightChart;
})();
