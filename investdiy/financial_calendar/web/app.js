(() => {
  const groups = { empsit: 'macro', cpi: 'macro', ppi: 'macro', pce: 'macro', fomc: 'macro', nvidia: 'nvidia', earnings: 'earnings' };
  const eastern = 'America/New_York';
  const beijing = 'Asia/Shanghai';
  const agenda = document.querySelector('#agenda');
  const buttons = document.querySelectorAll('[data-group]');
  const dialog = document.querySelector('#event-dialog');
  const index = document.querySelector('#earnings-index');
  const search = document.querySelector('#earnings-search');
  const clock = { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' };
  const fullDate = { year: 'numeric', month: 'short', day: 'numeric' };
  let viewKey;
  let selected = 'all';
  let rows;
  let macroDate;
  let earnings;

  function format(date, options, timeZone = 'UTC') {
    return new Intl.DateTimeFormat(i18n.lang === 'zh' ? 'zh-CN' : 'en-US', { timeZone, ...options }).format(date);
  }

  function isoDay(date, timeZone) {
    return new Intl.DateTimeFormat('sv-SE', { timeZone }).format(date);
  }

  function dayDate(iso) {
    return new Date(iso + 'T00:00:00Z');
  }

  function element(tag, text, className) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text) el.textContent = text;
    return el;
  }

  function releaseTime(row) {
    if (row.series === 'earnings') return i18n.t('cal.' + row.status);
    if (!row.release_at && row.kind) return i18n.t('cal.kind.' + row.kind);
    if (!row.release_at) return i18n.t(row.series === 'fomc' ? 'cal.meeting' : 'cal.annual');
    const at = new Date(row.release_at);
    let bj = format(at, clock, beijing);
    if (isoDay(at, beijing) !== row.start) bj = i18n.t('cal.nextDay', { time: bj });
    return i18n.t('cal.time', { et: format(at, clock, eastern), bj });
  }

  function openEvent(row) {
    const dateLabel = format(dayDate(row.start), fullDate);
    document.querySelector('#event-date').textContent = row.start === row.end ? dateLabel
      : dateLabel + ' – ' + format(dayDate(row.end), fullDate);
    document.querySelector('#event-title').textContent = row['title_' + i18n.lang] || i18n.t('cal.' + row.series);
    const details = document.querySelector('#event-details');
    details.replaceChildren(element('p', releaseTime(row)));
    if (row.series === 'earnings') {
      details.append(element('p', row.symbols.join(' · ')),
        element('p', row.indices.map(id => i18n.t('cal.' + id)).join(' · ')));
      if (row.period_end) {
        const month = format(dayDate(row.period_end), { year: 'numeric', month: 'long' });
        details.append(element('p', i18n.t('cal.periodEnd', { month })));
      }
    }
    if (row.kind) details.append(element('p', row['detail_' + i18n.lang]));
    if (row.series === 'empsit') details.append(element('p', i18n.t('cal.jobsDetail')));
    if (row.period) {
      const month = format(dayDate(row.period + '-01'), { year: 'numeric', month: 'long' });
      details.append(element('p', i18n.t('cal.period', { month })));
    }
    const link = element('a', i18n.t('cal.' + row.agency));
    link.href = row.url;
    details.append(link);
    if (row.kind) {
      details.append(element('small', i18n.t('cal.reviewed', { day: row.checked_on })));
    } else if (row.checked_on && row.checked_on !== row.as_of) {
      details.append(element('small', i18n.t('cal.checked', { day: row.checked_on })));
    }
    dialog.showModal();
  }

  function eventButton(row, day, dateLabel) {
    const title = row['title_' + i18n.lang] || i18n.t('cal.' + row.series);
    const button = element('button', '', 'event ' + row.series);
    const short = row.series === 'earnings' ? row.symbols[0].split(':')[1]
      : i18n.t(row.kind ? 'cal.kind.' + row.kind : 'cal.short.' + row.series);
    button.append(element('span', title, 'full-name'), element('span', short, 'short-name'));
    button.type = 'button';
    button.title = title;
    button.setAttribute('aria-label', dateLabel + ' · ' + title + ' · ' + releaseTime(row));
    button.setAttribute('aria-haspopup', 'dialog');
    if (row.series === 'earnings') {
      button.title = title + ' · ' + releaseTime(row);
      button.append(element('small', releaseTime(row), 'report-status'));
    } else if (row.release_at) {
      const zone = i18n.lang === 'zh' ? beijing : eastern;
      const at = new Date(row.release_at);
      let time = format(at, clock, zone);
      if (isoDay(at, zone) !== day) time = i18n.t('cal.nextDay', { time });
      button.append(element('small', i18n.t('cal.localTime', { time })));
    }
    button.addEventListener('click', () => openEvent(row));
    return button;
  }

  function monthTable(month, today, events) {
    const table = element('table', '', 'month');
    table.createCaption().textContent = format(month, { year: 'numeric', month: 'long' });
    const stop = d3.utcMonth.offset(month, 1);
    const monday = d3.utcMonday.floor(month);
    const header = table.createTHead().insertRow();
    const body = table.createTBody();
    for (let i = 0; i < 7; i++) {
      const th = element('th', format(d3.utcDay.offset(monday, i), { weekday: 'short' }));
      th.scope = 'col';
      header.append(th);
    }
    for (const week of d3.utcMonday.range(monday, stop)) {
      const tr = body.insertRow();
      for (const date of d3.utcDays(week, d3.utcDay.offset(week, 7))) {
        const td = tr.insertCell();
        if (date < month || date >= stop) {
          td.className = 'outside';
          continue;
        }
        const day = date.toISOString().slice(0, 10);
        const number = element('time', String(date.getUTCDate()));
        number.dateTime = day;
        if (day < today) td.className = 'past';
        if (day === today) number.setAttribute('aria-current', 'date');
        td.append(number);
        const dayRows = events.filter(row => row.start <= day && day <= row.end);
        const reports = dayRows.filter(row => row.series === 'earnings');
        const dateLabel = format(date, fullDate);
        for (const row of dayRows.filter(row => row.series !== 'earnings').concat(reports.slice(0, 2))) {
          td.append(eventButton(row, day, dateLabel));
        }
        if (reports.length > 2) {
          const more = element('details', '', 'more-earnings');
          const count = reports.length - 2;
          const summary = element('summary', '+' + count);
          summary.title = i18n.t('cal.more', { count });
          summary.setAttribute('aria-label', summary.title);
          more.append(summary);
          for (const row of reports.slice(2)) more.append(eventButton(row, day, dateLabel));
          td.append(more);
        }
      }
    }
    return table;
  }

  function render() {
    const today = isoDay(new Date(), eastern);
    const start = d3.utcMonth.floor(dayDate(today));
    const until = d3.utcMonth.offset(start, 4);
    const lastMonth = d3.utcMonth.offset(until, -1);
    const yearMonth = { year: 'numeric', month: 'short' };
    document.querySelector('#window').textContent = format(start, yearMonth) + ' – ' + format(lastMonth, yearMonth);
    buttons.forEach(b => b.setAttribute('aria-pressed', String(selected === b.dataset.group)));
    const earningsView = selected === 'earnings';
    document.querySelector('#earnings-filters').hidden = !earningsView;
    if (!rows) {
      agenda.replaceChildren(element('p', i18n.t('common.loading')));
      return;
    }
    const dates = [];
    const errors = [];
    if (!earningsView) {
      if (macroDate) dates.push(i18n.t('cal.checked', { day: macroDate }));
      else errors.push(i18n.t('cal.macroFailed'));
    }
    if (selected === 'all' || earningsView) {
      if (earnings) dates.push(i18n.t('cal.earningsChecked', { day: earnings.as_of }));
      else errors.push(i18n.t('cal.earningsFailed'));
    }
    document.querySelector('#checked').textContent = dates.join(' · ');
    const error = document.querySelector('#load-error');
    error.hidden = !errors.length;
    error.textContent = errors.join(' ');
    const term = search.value.trim().toLowerCase();
    const key = JSON.stringify([today, selected, index.value, term, i18n.lang]);
    if (key === viewKey) return;
    viewKey = key;
    const firstDay = start.toISOString().slice(0, 10);
    const limit = until.toISOString().slice(0, 10);
    const events = rows.filter(row => {
      if (row.end < firstDay || row.start >= limit) return false;
      if (selected !== 'all' && groups[row.series] !== selected) return false;
      if (!earningsView) return true;
      if (index.value && !row.indices.includes(index.value)) return false;
      if (!term) return true;
      const hkCodes = row.symbols.filter(s => s.startsWith('HKEX:')).map(s => s.slice(5).padStart(5, '0'));
      return [row.title_en, row.title_zh, ...row.symbols, ...hkCodes].some(s => s.toLowerCase().includes(term));
    });
    if (earningsView && earnings) {
      const counts = Object.entries(earnings.counts).filter(([id]) => !index.value || id === index.value)
        .map(([id, n]) => i18n.t('cal.' + id) + ' (' + n + ')');
      document.querySelector('#coverage').textContent = i18n.t('cal.coverage', { indices: counts.join(' · '), n: events.length });
    }
    const content = document.createDocumentFragment();
    if (!events.length && !errors.length) content.append(element('p', i18n.t('cal.empty')));
    for (const month of d3.utcMonths(start, until)) {
      content.append(monthTable(month, today, events));
    }
    agenda.replaceChildren(content);
  }

  buttons.forEach(button => button.addEventListener('click', () => {
    selected = button.dataset.group;
    render();
  }));
  index.addEventListener('change', render);
  search.addEventListener('input', render);
  i18n.onChange(render);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) render(); });
  setInterval(render, 60_000);
  render();
  Promise.allSettled([kit.csv('data/events.csv'), d3.json('data/earnings.json')]).then(([macro, reports]) => {
    rows = [];
    if (macro.status === 'fulfilled' && macro.value.length) {
      rows = macro.value;
      macroDate = rows[0].as_of;
      kit.markStale(document.querySelector('#stale'), macroDate, 7);
    }
    if (reports.status === 'fulfilled' && Array.isArray(reports.value?.events)) {
      earnings = reports.value;
      rows = rows.concat(earnings.events);
      kit.markStale(document.querySelector('#earnings-stale'), earnings.as_of, 7);
    }
    render();
  });
})();
