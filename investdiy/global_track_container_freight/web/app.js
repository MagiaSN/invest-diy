/* Dashboard headlines and a user-managed list of independent freight charts. */
(function () {
  const { num, fmtPct } = kit;
  const t = (key, values) => i18n.t(key, values);
  const $ = (id) => document.getElementById(id);
  const pct = (v) => (isFinite(v) ? fmtPct(v) : t('t.none'));
  const UPDATE_CMD = 'python -m investdiy.global_track_container_freight --latest-only';
  let D = null;
  const charts = [];

  // ---------------- header ----------------
  function drawHeader() {
    const k = D.kpi;
    const set = (id, r) => {
      if (!r) return;
      const c = num(r.chg_1w);
      $(id).textContent = kit.fmtNum(num(r.value), 2);
      $(`${id}-sub`).textContent = isFinite(c) ? t('k.sub', { d: r.date, c: fmtPct(c) }) : t('k.subNone', { d: r.date });
      $(`${id}-sub`).className = 'kpi-sub';
    };
    const scfi = D.latest.get('scfi/composite'), ccfi = D.latest.get('ccfi/composite');
    const eu = D.latest.get('scfis/europe'), us = D.latest.get('scfis/uswc');
    set('k-scfi', scfi); set('k-ccfi', ccfi); set('k-scfis-eu', eu); set('k-scfis-us', us);
    $('asof').textContent = t('weekly.asof', { d: k.as_of || '—' });

    const parts = [];
    if (scfi && ccfi) {
      parts.push(...i18n.rich('take.now', {
        d: scfi.date, d2: ccfi.date, scfi: kit.fmtNum(num(scfi.value), 2), c1: pct(num(scfi.chg_1w)),
        ccfi: kit.fmtNum(num(ccfi.value), 2), c2: pct(num(ccfi.chg_1w)),
      }));
    }
    if (eu && us) {
      parts.push(' ', ...i18n.rich('take.scfis', {
        d: eu.date, eu: kit.fmtNum(num(eu.value), 2), c3: pct(num(eu.chg_1w)), us: kit.fmtNum(num(us.value), 2), c4: pct(num(us.chg_1w)),
      }));
    }
    $('take-now').replaceChildren(...parts);
  }


  function updateChartControls() {
    charts.forEach((chart, index) => { chart.setPosition(index + 1, charts.length > 1); chart.render(); });
  }

  function removeChart(chart) {
    if (charts.length <= 1) return;
    const position = charts.indexOf(chart);
    if (position < 0) return;
    charts.splice(position, 1);
    chart.destroy();
    updateChartControls();
    charts[Math.min(position, charts.length - 1)].q('.chart-index').focus();
    $('chart-message').textContent = t('charts.count', { n: charts.length });
  }

  function addChart(focus = false) {
    if (!D) return;
    const chart = new FreightChart({ host: $('chart-list'), data: D, onRemove: removeChart });
    charts.push(chart);
    updateChartControls();
    if (focus) chart.q('.chart-index').focus();
    $('chart-message').textContent = t('charts.count', { n: charts.length });
  }

  function drawAll() {
    if (!D) return;
    drawHeader();
    updateChartControls();
    $('chart-message').textContent = t('charts.count', { n: charts.length });
  }

  $('add-chart').addEventListener('click', () => addChart(true));
  $('take-now').textContent = t('common.loading');
  kit.sectionNav($('secnav'));
  kit.downloadLinks('data/');
  Promise.all(['kpi', 'latest', 'history', 'status'].map((file) => kit.csv(`data/${file}.csv`))).then(([kpi, latest, history, status]) => {
    const rows = history.map((row) => ({ key: `${row.index}/${row.series}`, date: row.date, d: new Date(row.date), v: num(row.value), src: row.source }));
    D = {
      kpi: kpi[0], latest: new Map(latest.map((row) => [`${row.index}/${row.series}`, row])),
      allLatest: latest, status,
      series: d3.group(rows.sort((a, b) => d3.ascending(a.date, b.date)), (row) => row.key),
    };
    addChart();
    $('add-chart').disabled = false;
    kit.markStale($('stale'), D.kpi.as_of, 8);
    drawHeader();
    kit.onRedraw(drawAll);
  }).catch((error) => {
    console.error(error);
    charts.splice(0).forEach((chart) => chart.destroy());
    $('add-chart').disabled = true;
    const show = () => {
      $('take-now').textContent = t('loadError', { cmd: UPDATE_CMD });
      $('chart-message').textContent = t('common.failed');
    };
    show(); i18n.onChange(show);
  });
})();
