/* Same-period comparisons, independent chart ranges and explicit missing observations. */
(function () {
  const $ = id => document.getElementById(id), t = (k, v) => i18n.t(k, v);
  const numeric = kit.num, fmt = (v, digits = 2) => Number.isFinite(v) ? d3.format(`,.${digits}f`)(Math.abs(v) < 0.5 * 10 ** -digits ? 0 : v) : '—';
  const date = s => new Date(`${s}T00:00:00Z`), day = d3.utcFormat('%Y-%m-%d');
  const colors = ['#b48923', '#367cc3', '#bf5761', '#2d987d', '#8568b4', '#c87535', '#548e9b', '#c45d99', '#858e3d', '#7c7c7c', '#457445', '#bb903c', '#537093', '#9d6b52', '#797dc1', '#a14776', '#569588', '#ac6c6c'];
  const defaults = ['USA', 'DEU', 'CHN', 'RUS', 'IND', 'JPN'];
  let selected = new Set(defaults), D = {}, R = {}, missing = false;
  const element = (tag, text, cls) => { const e = document.createElement(tag); if (text != null) e.textContent = text; if (cls) e.className = cls; return e; };
  const list = name => D[name] || [];
  const countryName = r => i18n.lang === 'zh' ? r.name : r.name_en;
  const economies = () => [...new Map(list('reserves').map(r => [r.country, r])).values()];
  const color = code => colors[economies().findIndex(r => r.country === code) % colors.length];
  const stale = (s, days = 120) => s && Date.now() - +date(s) > days * 86400000;
  const dated = (s, days) => s ? `${s}${stale(s, days) ? ` · ${t('stale')}` : ''}` : '—';

  function legend(id, series) {
    $(id).replaceChildren(...series.map(s => {
      const e = element('span'), dot = element('i'); dot.style.background = s.color;
      e.append(dot, s.label); return e;
    }));
  }

  function chart(id, series, unit, annual = false, observedDates = false) {
    const box = $(`${id}-chart`);
    legend(`${id}-legend`, series);
    kit.ready(box);
    const all = series.flatMap(s => s.rows).filter(r => Number.isFinite(r.value));
    const range = R[id]?.get();
    const visible = all.filter(r => !range || (r.d >= range[0] && r.d <= range[1]));
    if (!visible.length) { kit.fail(box, t(series.length ? 'empty' : 'choose')); return; }
    const width = Math.max(260, box.clientWidth), height = 300;
    const m = {top: 28, right: 16, bottom: 30, left: 64};
    let [x0, x1] = range || d3.extent(visible, r => r.d);
    if (+x0 === +x1) { x0 = d3.utcMonth.offset(x0, -1); x1 = d3.utcMonth.offset(x1, 1); }
    const x = d3.scaleUtc([x0, x1], [m.left, width - m.right]);
    const extent = d3.extent(visible, r => r.value);
    let low = Math.min(0, extent[0]), high = Math.max(0, extent[1]);
    if (low === high) high = low + 1;
    const y = d3.scaleLinear().domain([low, high]).nice().range([height - m.bottom, m.top]);
    const svg = d3.select(box).append('svg').attr('viewBox', `0 0 ${width} ${height}`).attr('role', 'img').attr('aria-label', `${t(`${id}.title`)} · ${unit}`);
    svg.append('text').attr('x', m.left).attr('y', 15).attr('fill', 'var(--fg-muted)').attr('font-size', 11).text(unit);
    const gx = svg.append('g').attr('transform', `translate(0,${height-m.bottom})`).call(d3.axisBottom(x).ticks(width < 500 ? 4 : 7).tickFormat(d3.utcFormat(x1-x0 > 730*86400000 ? '%Y' : '%y-%m')));
    const gy = svg.append('g').attr('transform', `translate(${m.left},0)`).call(d3.axisLeft(y).ticks(5).tickFormat(d3.format(',~f')));
    kit.axisStyle(gx, gy);
    const interval = annual ? d3.utcYear : d3.utcMonth;
    const dates = observedDates ? [...new Set(all.map(r => +r.d))].sort((a,b) => a-b).map(d => new Date(d)).filter(d => d >= x0 && d <= x1) : interval.range(interval.floor(x0), interval.offset(interval.ceil(x1), 1)).map(d => {
      const end = annual ? new Date(Date.UTC(d.getUTCFullYear(), 11, 31)) : new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0));
      return end;
    }).filter(d => d >= x0 && d <= x1);
    const prepared = series.map(s => {
      const byDate = new Map(s.rows.map(r => [day(r.d), r]));
      return {...s, rows: dates.map(d => byDate.get(day(d)) || {d, value:NaN})};
    });
    const line = d3.line().defined(r => Number.isFinite(r.value)).x(r => x(r.d)).y(r => y(r.value));
    svg.append('defs').append('clipPath').attr('id',`${id}-clip`).append('rect')
      .attr('x',m.left-4).attr('y',m.top-4).attr('width',width-m.left-m.right+8).attr('height',height-m.top-m.bottom+8);
    const plot = svg.append('g').attr('clip-path',`url(#${id}-clip)`);
    prepared.forEach(s => {
      plot.append('path').datum(s.rows).attr('fill', 'none').attr('stroke', s.color).attr('stroke-width', 2).attr('stroke-dasharray', s.dash || null).attr('d', line);
      plot.append('g').selectAll('circle').data(s.rows.filter(r => Number.isFinite(r.value))).join('circle')
        .attr('cx', r => x(r.d)).attr('cy', r => y(r.value)).attr('r', r => r.radius || (annual ? 3 : 1.4)).attr('fill', r => r.color || s.color);
    });
    const tip = kit.tip(box.closest('.card')); tip.hide();
    const cursor = svg.append('line').attr('y1', m.top).attr('y2', height-m.bottom).attr('stroke', 'var(--fg-muted)').attr('stroke-dasharray', '3 3').style('display','none');
    svg.append('rect').attr('x',m.left).attr('y',m.top).attr('width',width-m.left-m.right).attr('height',height-m.top-m.bottom).attr('fill','transparent')
      .on('pointermove', event => {
        if (!dates.length) return;
        const target = x.invert(d3.pointer(event, svg.node())[0]);
        const index = d3.bisector(d => d).center(dates, target), current = dates[index];
        cursor.style('display',null).attr('x1',x(current)).attr('x2',x(current));
        tip.show(event, [{text:day(current)}, ...prepared.map(s => {
          const row = s.rows[index];
          return {text:`${s.label}: ${fmt(row?.value)} ${unit}${row?.note ? ` · ${row.note}` : ''}`,color:row?.color || s.color};
        })]);
      }).on('pointerleave', () => { tip.hide(); cursor.style('display','none'); });
  }

  const series = (rows, field, label, col, scale = 1) => ({label, color:col, rows:rows.map(r => ({d:r.d, value:numeric(r[field])/scale}))});
  function drawStocks() {
    const rows = list('stocks');
    chart('stocks', [{label:t('stocks.total'), color:colors[0], rows:rows.map(r => {
      const published = r.method === 'published_anchor';
      return {d:r.d, value:numeric(r.stock_t), color:colors[published ? 1 : 0], radius:published ? 4 : 3,
        note:t(published ? 'stocks.published' : 'stocks.backcast')};
    })}], t('tonnes'), false, true);
    legend('stocks-legend', [{label:t('stocks.backcast'),color:colors[0]}, {label:t('stocks.published'),color:colors[1]}]);
    const latest = rows.at(-1);
    $('stocks-latest').textContent = latest ? t('stocks.latest',{date:latest.date,value:fmt(numeric(latest.stock_t),0)}) : t('empty');
    const range = R.stocks?.get();
    const visible = rows.filter(r => numeric(r.stock_t) > 0 && Number.isFinite(numeric(r.stock_t)) &&
      (!range || (r.d >= range[0] && r.d <= range[1]))).sort((a,b) => a.d-b.d);
    const first = visible[0], last = visible.at(-1);
    const years = visible.length >= 2 ? (last.d-first.d)/(365.25*86400000) : 0;
    const growth = years > 0 ? Math.expm1(Math.log(numeric(last.stock_t)/numeric(first.stock_t))/years)*100 : NaN;
    $('stocks-growth').textContent = Number.isFinite(growth)
      ? t('stocks.growth',{value:fmt(growth),start:first.date,end:last.date,years:fmt(years)})
      : t('stocks.growth.empty');
  }
  function drawMarket() {
    const annual = $('frequency').value === 'annual', rows = list(annual ? 'annual' : 'market');
    const ratio = $('market-metric').value === 'ratio';
    const debtReference = {label:t('market.debt40'), color:colors[3], dash:'6 4',
      rows:rows.map(r => ({d:r.d, value:numeric(r.debt_usd)*0.4/1e12}))};
    chart('market', ratio ? [series(rows, 'gold_debt_ratio', t('market.ratio'), colors[0])]
      : [series(rows, 'gold_usd', t('market.gold'), colors[0], 1e12), series(rows, 'debt_usd', t('market.debt'), colors[1], 1e12), series(rows, 'public_debt_usd', t('market.public'), colors[2], 1e12), debtReference], t(ratio ? 'unit.ratio' : 'unit.trillion'), annual);
    const range = R.market?.get();
    const last = rows.filter(r => !range || r.d >= range[0] && r.d <= range[1]).at(-1);
    $('market-period').textContent = last ? t('market.period', {date:last.date, debt:last.debt_date || '—'}) : t('empty');
  }
  function drawOil() { chart('oil', [series(list('prices'),'gold_brent',t('oil.brent'),colors[0]), series(list('prices'),'gold_wti',t('oil.wti'),colors[1])],t('oil.unit')); }
  function drawSilver() { chart('silver', [series(list('prices'),'gold_silver',t('silver.ratio'),colors[0])],t('unit.ratio')); }
  function drawDemand() {
    const total = $('demand-scope').value === 'total', range = R.demand?.get();
    const definitions = [
      ['jewellery_t',colors[0]], ['technology_t',colors[1]], ['bars_coins_t',colors[3]],
      ['etf_t',colors[2]], ['central_banks_t',colors[4]], ...(total ? [['otc_t',colors[9]]] : [])
    ];
    const keys = definitions.map(([key]) => key), totalKey = total ? 'total_demand_t' : 'gold_demand_t';
    const rows = list('demand').filter(r => (!range || r.d >= range[0] && r.d <= range[1]) &&
      keys.every(key => Number.isFinite(numeric(r[key]))) && Number.isFinite(numeric(r[totalKey])));
    const netLabel = t(total ? 'demand.net.total' : 'demand.net.core');
    legend('demand-legend', [...definitions.map(([key,color]) => ({label:t(`demand.${key}`),color})),
      {label:netLabel,color:'var(--fg)'}]);
    $('demand-scope-note').textContent = t(total ? 'demand.total.note' : 'demand.core.note');
    const box = $('demand-chart'); kit.ready(box);
    const tip = kit.tip(box.closest('.card')); tip.hide();
    const latest = rows.at(-1);
    $('demand-summary').textContent = latest ? t('demand.summary', {
      start:rows[0].year, end:latest.year, value:fmt(numeric(latest[totalKey]),1), scope:netLabel
    }) : t('empty');
    if (!rows.length) { kit.fail(box,t('empty')); return; }
    const width = Math.max(260,box.clientWidth), height = 340, m = {top:28,right:12,bottom:30,left:60};
    const x = d3.scaleBand(rows.map(r => r.year),[m.left,width-m.right]).padding(0.24);
    const layers = d3.stack().keys(keys).value((r,key) => numeric(r[key])).offset(d3.stackOffsetDiverging)(rows);
    const bounds = layers.flatMap(layer => layer.flatMap(segment => [segment[0],segment[1]]));
    const y = d3.scaleLinear().domain([Math.min(0,...bounds),Math.max(0,...bounds)]).nice().range([height-m.bottom,m.top]);
    const svg = d3.select(box).append('svg').attr('viewBox',`0 0 ${width} ${height}`).attr('role','img').attr('aria-label',t('demand.title'));
    svg.append('text').attr('x',m.left).attr('y',15).text(t('tonnes'));
    const every = Math.max(1,Math.ceil(rows.length/(width < 500 ? 5 : 12)));
    const gx = svg.append('g').attr('transform',`translate(0,${height-m.bottom})`)
      .call(d3.axisBottom(x).tickValues(rows.filter((r,i) => i%every===0 || i===rows.length-1).map(r=>r.year)));
    const gy = svg.append('g').attr('transform',`translate(${m.left},0)`).call(d3.axisLeft(y).ticks(6).tickFormat(d3.format(',~f')));
    kit.axisStyle(gx,gy);
    svg.append('line').attr('x1',m.left).attr('x2',width-m.right).attr('y1',y(0)).attr('y2',y(0)).attr('stroke','var(--axis)');
    function show(event,row) {
      let point = event;
      if (!Number.isFinite(event.clientX)) {
        const rect = event.currentTarget.getBoundingClientRect();
        point = {clientX:rect.x+rect.width/2,clientY:rect.y+rect.height/2};
      }
      tip.show(point,[{text:row.year}, ...definitions.map(([key,color])=>({text:`${t(`demand.${key}`)}: ${fmt(numeric(row[key]),1)} ${t('tonnes')}`,color})),
        {text:`${netLabel}: ${fmt(numeric(row[totalKey]),1)} ${t('tonnes')}`}, {text:t('demand.edition',{year:row.edition})}]);
    }
    layers.forEach((layer,i) => {
      svg.append('g').attr('data-category',layer.key).attr('fill',definitions[i][1]).selectAll('rect').data(layer).join('rect')
        .attr('x',s=>x(s.data.year)).attr('width',x.bandwidth()).attr('y',s=>y(s[1])).attr('height',s=>Math.max(0,y(s[0])-y(s[1])))
        .attr('tabindex',0).attr('aria-label',s=>`${s.data.year} · ${t(`demand.${layer.key}`)}: ${fmt(numeric(s.data[layer.key]),1)} ${t('tonnes')}`)
        .on('pointermove',(event,s)=>show(event,s.data)).on('pointerleave',()=>tip.hide())
        .on('focus',(event,s)=>show(event,s.data)).on('blur',()=>tip.hide());
    });
    const net = svg.append('g').attr('class','demand-net');
    net.append('path').datum(rows)
      .attr('d',d3.line().x(r=>x(r.year)+x.bandwidth()/2).y(r=>y(numeric(r[totalKey]))))
      .attr('fill','none').attr('stroke','var(--fg)').attr('stroke-width',2).attr('pointer-events','none');
    net.selectAll('circle').data(rows).join('circle')
      .attr('cx',r=>x(r.year)+x.bandwidth()/2).attr('cy',r=>y(numeric(r[totalKey]))).attr('r',3.5)
      .attr('fill','var(--fg)').attr('stroke','var(--panel)').attr('stroke-width',1.5)
      .attr('tabindex',0).attr('aria-label',r=>`${r.year} · ${netLabel}: ${fmt(numeric(r[totalKey]),1)} ${t('tonnes')}`)
      .on('pointermove',(event,r)=>show(event,r)).on('pointerleave',()=>tip.hide())
      .on('focus',(event,r)=>show(event,r)).on('blur',()=>tip.hide());
  }
  function reserveSeries(field) {
    return economies().filter(r => selected.has(r.country)).map(r => series(list('reserves').filter(x => x.country === r.country),field,countryName(r),color(r.country)));
  }
  function drawHoldings() { chart('holdings',reserveSeries($('holdings-metric').value),t('tonnes')); }
  function drawShare() {
    const fx = $('share-metric').value === 'gold_fx_pct';
    $('share-note').textContent = t(fx ? 'share.fx.note' : 'share.total.note');
    chart('share',reserveSeries($('share-metric').value),'%');
  }
  function drawCountries() {
    $('countries').replaceChildren(...economies().map(r => {
      const b = element('button'), dot = element('i'); dot.style.background = color(r.country);
      b.type = 'button'; b.dataset.country = r.country; b.setAttribute('aria-pressed',String(selected.has(r.country))); b.append(dot,countryName(r));
      b.addEventListener('click', () => { selected.has(r.country) ? selected.delete(r.country) : selected.add(r.country); drawCountries(); drawHoldings(); drawShare(); });
      return b;
    }));
  }
  function drawSnapshot() {
    const rows = economies().sort((a,b) => numeric(b.gold_t)-numeric(a.gold_t));
    $('snapshot-body').replaceChildren(...rows.map(r => {
      const history = list('reserves').filter(x => x.country === r.country);
      const share = history.filter(x => Number.isFinite(numeric(x.gold_total_pct)) && Number.isFinite(numeric(x.gold_fx_pct))).at(-1);
      const tr = element('tr');
      [countryName(r),dated(r.date),fmt(numeric(r.gold_t),1),fmt(numeric(r.change_t),1),fmt(numeric(r.yoy_t),1), dated(share?.date),fmt(numeric(share?.gold_total_pct)),fmt(numeric(share?.gold_fx_pct))].forEach(v => tr.append(element('td',v)));
      return tr;
    }));
  }
  function drawHeader() {
    const p = list('prices').at(-1), m = list('market').at(-1);
    const specs = [
      [t('market.gold'),`${fmt(numeric(m?.gold_usd)/1e12)} ${t('unit.trillion')}`,m ? t('market.kpi',{date:m.date}):'—'],
      [t('market.ratio'),`${fmt(numeric(m?.gold_debt_ratio))} ${t('unit.ratio')}`,m?.date || '—'],
      [t('oil.brent'),`${fmt(numeric(p?.gold_brent))}`,`${p?.date || '—'} · ${t('oil.unit')}`],
      [t('silver.title'),`${fmt(numeric(p?.gold_silver))}`,p?.date || '—']
    ];
    $('kpis').replaceChildren(...specs.map(([label,value,sub]) => { const k=element('div',null,'kpi'); k.append(element('span',label,'kpi-label'),element('span',value,'kpi-value'),element('span',sub,'kpi-sub')); return k; }));
    $('asof').textContent = p ? t('common.asof',{d:p.date}):'';
    $('message').textContent = missing ? t('load.error') : list('sources').some(s=>s.status==='error') ? t('load.partial') : t('loaded',{price:p?.date || '—',market:m?.date || '—'});
    $('source-body').replaceChildren(...list('sources').map(s => {
      const tr=element('tr'), td=element('td'), a=element('a',t(`source.${s.source}`)); a.href=s.url; a.target='_blank'; a.rel='noopener'; td.append(a); tr.append(td);
      [dated(s.latest,s.source==='demand'?450:120),t(`status.${s.status}`),s.fetched_at ? s.fetched_at.replace('T',' ').replace('+00:00',''):'—'].forEach(v=>tr.append(element('td',v))); return tr;
    }));
  }
  const draws={stocks:drawStocks,market:drawMarket,oil:drawOil,silver:drawSilver,demand:drawDemand,holdings:drawHoldings,share:drawShare};
  function drawAll() { drawHeader(); drawCountries(); drawSnapshot(); Object.values(draws).forEach(fn=>fn()); }
  $('frequency').addEventListener('change',drawMarket); $('market-metric').addEventListener('change',drawMarket);
  $('holdings-metric').addEventListener('change',drawHoldings); $('share-metric').addEventListener('change',drawShare);
  $('demand-scope').addEventListener('change',drawDemand);
  for (const [id,values] of [['all',()=>economies().map(r=>r.country)],['default',()=>defaults],['none',()=>[]]]) {
    $(`select-${id}`).addEventListener('click',()=>{selected=new Set(values());drawCountries();drawHoldings();drawShare();});
  }
  kit.sectionNav($('secnav')); kit.downloadLinks('data/');
  const files=['prices','market','annual','reserves','sources','stocks','demand'];
  Promise.allSettled(files.map(f=>kit.csv(`data/${f}.csv`))).then(results=>{
    results.forEach((r,i)=>{ if(r.status==='fulfilled') D[files[i]]=r.value.map(x=>({...x,d:x.date?date(x.date):null})); else {missing=true;D[files[i]]=[];} });
    for (const [id,file] of Object.entries({stocks:'stocks',market:'market',oil:'prices',silver:'prices',demand:'demand',holdings:'reserves',share:'reserves'})) {
      const rows=list(file); if(!rows.length) continue;
      const [min,max]=d3.extent(rows,r=>r.d);
      R[id]=kit.rangePicker($(`${id}-range`),{min,max,initial:['market','stocks','demand'].includes(id)?'all':'5y',onChange:draws[id]});
    }
    drawAll(); kit.onRedraw(drawAll);
  });
})();
