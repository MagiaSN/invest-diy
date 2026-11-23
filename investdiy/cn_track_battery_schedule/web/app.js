(async function () {
  const t = i18n.t;
  const series = ['mainland', 'catl'];
  const parseMonth = d3.utcParse('%Y-%m');
  const monthKey = d3.utcFormat('%Y-%m');
  const monthLabel = (date) => date.toLocaleDateString(i18n.lang, {
    year: 'numeric', month: 'short', timeZone: 'UTC',
  });
  const valueLabel = (r) => ({ above: '>', at_least: '≥', estimate: '≈', revised_approx: '≈' }[r.qualifier] || '') + r.gwh;
  const isInferred = r => r.attribution === 'survey_a' || r.attribution === 'citi_a';
  const provenanceLabel = r => t('attribution.' + (r.attribution || 'named'));
  const latestLabel = (r) => t('latest', { month: monthLabel(r.date), qualifier: isInferred(r) ? provenanceLabel(r) : t(r.qualifier) });

  function followupLabel(row) {
    return t('followup.' + row.followup_kind, { pct: row.followup_mom_pct });
  }

  function draw(card, id, data, range) {
    const box = card.querySelector('.chart');
    kit.ready(box);
    const [start, end] = range;
    const dates = d3.utcMonth.range(d3.utcMonth.ceil(start), d3.utcMonth.offset(d3.utcMonth.floor(end), 1));
    const visible = data.filter(r => r.date >= start && r.date <= end);
    if (!visible.length) {
      box.textContent = t('noRange');
      return;
    }
    const width = box.clientWidth, height = box.clientHeight, left = 36, base = height - 32;
    const x = d3.scaleBand().domain(dates.map(monthKey)).range([left, width - 24]).padding(0.24);
    const y = d3.scaleLinear().domain([0, d3.max(visible, r => +r.gwh)]).nice(4).range([base, 20]);
    const svg = d3.select(box).append('svg').attr('width', width).attr('height', height)
      .attr('role', 'img').attr('aria-label', t('chartLabel', { series: t(id) }));
    const axis = svg.append('g').attr('transform', `translate(${left},0)`)
      .call(d3.axisLeft(y).ticks(4).tickSize(left - width + 24).tickPadding(5));
    axis.select('.domain').remove();
    const stride = Math.max(1, Math.ceil(dates.length / Math.max(1, (width - left) / 66)));
    const ticks = dates.filter((_, i) => i % stride === 0).map(monthKey);
    const bottom = svg.append('g').attr('transform', `translate(0,${base})`)
      .call(d3.axisBottom(x).tickValues(ticks).tickFormat(key => monthLabel(parseMonth(key))).tickSizeOuter(0));
    kit.axisStyle(axis, bottom);
    const barWidth = Math.min(x.bandwidth(), 45);
    const center = r => x(r.month) + x.bandwidth() / 2;
    const tip = kit.tip(card);
    tip.hide();
    const bars = svg.selectAll('rect').data(visible).join('rect')
      .attr('x', r => center(r) - barWidth / 2).attr('width', barWidth)
      .attr('y', r => y(+r.gwh)).attr('height', r => base - y(+r.gwh))
      .attr('fill', r => ['above', 'at_least'].includes(r.qualifier) ? 'var(--panel)' : 'var(--series)')
      .attr('stroke', 'var(--series)').attr('rx', 2)
      .attr('class', r => isInferred(r) ? 'inferred' : null);
    bars.on('pointermove', (event, r) => tip.show(event, [
      { text: latestLabel(r) }, { text: valueLabel(r) + ' GWh' },
      { text: t('source.' + r.source) + ' · ' + r.as_of },
      ...(r.followup_kind ? [{ text: r.followup_as_of + ' · ' + followupLabel(r) }] : []),
    ])).on('pointerleave', tip.hide);
    if (x.step() > 27) {
      svg.selectAll('.value').data(visible).join('text').attr('class', 'value')
        .attr('text-anchor', 'middle').attr('x', center).attr('y', r => y(+r.gwh) - 5)
        .text(r => valueLabel(r));
    }
  }

  function appendRecord(cell, r) {
    cell.append(valueLabel(r) + ' GWh');
    if (r.series === 'catl') {
      const attribution = document.createElement('small');
      attribution.className = 'attribution';
      attribution.textContent = provenanceLabel(r);
      cell.append(attribution);
    }
    if (r.previous_plan_gwh) {
      const prior = document.createElement('span');
      prior.className = 'previous';
      prior.textContent = t('earlier', { value: r.previous_plan_gwh });
      cell.append(prior);
    }
    const link = document.createElement('a');
    link.href = r.url;
    link.className = 'source';
    link.textContent = t('source.' + r.source) + ' · ' + r.as_of;
    cell.append(link);
    if (r.lfp_gwh) {
      const split = document.createElement('span');
      split.className = 'previous';
      split.textContent = t(r.prior_lfp_gwh ? 'chemistry' : 'chemistrySplit', { prior: r.prior_lfp_gwh, lfp: r.lfp_gwh, ncm: r.ncm_gwh });
      cell.append(split);
    }
    if (r.followup_kind) {
      const update = document.createElement('a');
      update.className = 'followup';
      update.href = r.followup_url;
      update.textContent = r.followup_as_of + ' · ' + followupLabel(r);
      cell.append(update);
    }
  }

  function fillHistory(months, byMonth) {
    const body = document.querySelector('#rows');
    body.replaceChildren();
    for (const month of months.slice().reverse()) {
      const tr = body.insertRow();
      tr.insertCell().textContent = month;
      for (const id of series) {
        const cell = tr.insertCell();
        const records = byMonth.get(month)?.get(id) || [];
        if (!records.length) { cell.textContent = '—'; continue; }
        for (const row of records) {
          const record = document.createElement('div');
          record.className = 'record';
          appendRecord(record, row);
          cell.append(record);
        }
      }
    }
  }

  const status = document.querySelector('#status');
  try {
    const rows = await kit.csv('data/monthly.csv');
    rows.forEach(r => { r.date = parseMonth(r.month); });
    const priority = { named: 0, survey_a: 1, citi_a: 2 };
    rows.sort((a, b) => a.date - b.date || (priority[a.attribution] || 0) - (priority[b.attribution] || 0));
    const min = parseMonth('2025-01');
    const today = new Date();
    const shanghaiMonth = new Intl.DateTimeFormat('sv-SE', {
      year: 'numeric', month: '2-digit', timeZone: 'Asia/Shanghai',
    }).format(today);
    const max = d3.max([parseMonth(shanghaiMonth), d3.max(rows, r => r.date)]);
    const months = d3.utcMonth.range(min, d3.utcMonth.offset(max, 1)).map(monthKey);
    const byMonth = d3.group(rows, r => r.month, r => r.series);
    const asof = d3.max(rows, r => r.as_of);
    for (const id of series) {
      const combined = months.map(month => byMonth.get(month)?.get(id)?.[0]).filter(Boolean);
      const card = document.querySelector('#series-card').content.firstElementChild.cloneNode(true);
      card.classList.add(id);
      const control = card.querySelector('.series-view');
      const select = control.querySelector('select');
      if (id === 'catl') {
        for (const option of Array.from(select.options)) {
          if (option.value && !rows.some(r => r.attribution === option.value)) option.remove();
        }
        for (const item of control.querySelectorAll('[data-i18n]')) item.textContent = t(item.dataset.i18n);
        select.addEventListener('change', render);
      } else {
        control.remove();
      }
      document.querySelector('#charts').append(card);
      function render() {
        const data = select.value ? rows.filter(r => r.series === id && r.attribution === select.value) : combined;
        const inferredCount = data.filter(isInferred).length;
        const latest = data[data.length - 1];
        card.querySelector('h2').textContent = t(id);
        card.querySelector('strong').textContent = valueLabel(latest);
        card.querySelector('.latest').textContent = latestLabel(latest);
        card.querySelector('.coverage').textContent = t(id === 'catl' ? 'catlCoverage' : 'coverage', {
          first: monthKey(min), last: monthKey(max), count: data.length, total: months.length, named: data.length - inferredCount, inferred: inferredCount,
        });
        card.querySelector('.scope').textContent = t('scope.' + id);
        draw(card, id, data, picker.get());
      }
      const picker = kit.rangePicker(card.querySelector('.picker'), { min, max, initial: 'all', onChange: render });
      kit.onRedraw(render);
      render();
    }
    function renderHistory() {
      document.querySelector('#asof').textContent = t('sourceDate', { date: asof });
      fillHistory(months, byMonth);
    }
    renderHistory();
    i18n.onChange(renderHistory);
    kit.downloadLinks();
    status.hidden = true;
  } catch (error) {
    console.error(error);
    status.dataset.i18n = 'failed';
    status.textContent = t('failed');
  }
})();
