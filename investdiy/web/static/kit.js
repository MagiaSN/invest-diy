/* Front-end helpers shared by the tool pages: data loading, formatting, colours, tooltips, redraw
   scheduling and page components. Depends on the globals d3 (/static/vendor/d3.v7.9.0.min.js) and i18n
   (/static/i18n.js); exposed as window.kit.

   Amounts and unit counts are passed in "yi" (100 millions, as in the data files) and formatted for the
   current language:
     Chinese  460 亿元 / 352.4 亿份
     English  ¥46.0bn  / 35.24bn units   (1 yi = 0.1 bn) */
(function () {
  const num = (x) => (x === '' || x == null ? NaN : Number(x));
  const sign = (v) => (v > 0 ? '+' : v < 0 ? '−' : '');
  const zh = () => i18n.lang === 'zh';
  const fmt = (v, digits) => d3.format(`,.${digits}f`)(v);

  const kit = {
    num,
    /** Fetch a CSV and return an array of row objects (all fields are strings) */
    csv: (url) => fetch(url, { cache: 'no-cache' }).then((r) => {
      if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
      return r.text();
    }).then((t) => d3.csvParse(t)),

    /** Amount (input in yi). opts.sign defaults to true; opts.digits overrides the precision */
    amt(v, { sign: withSign = true, digits } = {}) {
      const s = withSign ? sign(v) : (v < 0 ? '−' : '');
      return zh() ? `${s}${fmt(Math.abs(v), digits ?? 0)} 亿元` : `${s}¥${fmt(Math.abs(v) / 10, digits ?? 1)}bn`;
    },
    /** Unit count (input in yi) */
    shares(v, digits) {
      return zh() ? `${fmt(v, digits ?? 1)} 亿份` : `${fmt(v / 10, (digits ?? 1) + 1)}bn units`;
    },
    /** Amount / unit count without a unit (table columns, axes; the unit goes in the header or caption) */
    yi(v, digits = 0, withSign = false) {
      const s = withSign ? sign(v) : (v < 0 ? '−' : '');
      return zh() ? s + fmt(Math.abs(v), digits) : s + fmt(Math.abs(v) / 10, digits + 1);
    },
    axisYi: (v) => (zh() ? d3.format(',')(v) : d3.format(',~f')(v / 10)),
    fmtPct: (v) => sign(v) + d3.format('.2f')(Math.abs(v)) + '%',
    fmtNum: (v, digits = 0) => fmt(v, digits),
    signCls: (v) => (v > 0 ? 'up' : v < 0 ? 'down' : ''),
    monthLabel: (d) => (zh() ? `${d.getUTCMonth() + 1}月` : d3.utcFormat('%b')(d)),

    /** Resolved colour of a CSS variable (rgb string), for d3 interpolation */
    color(name) {
      const el = document.createElement('span');
      el.style.color = `var(${name})`;
      el.hidden = true;
      document.body.appendChild(el);
      const c = getComputedStyle(el).color;
      el.remove();
      return c;
    },
    series: () => ['--s1', '--s2', '--s3', '--s4', '--s5', '--s6', '--s7', '--s8'].map((n) => `var(${n})`),

    /** Tooltip inside a card: tip(card).show(event, [{text, color?}, ...]) */
    tip(card) {
      let el = card.querySelector(':scope > .tip');
      if (!el) { el = document.createElement('div'); el.className = 'tip'; el.hidden = true; card.appendChild(el); }
      return {
        show(event, lines) {
          el.replaceChildren(...lines.map((ln, i) => {
            const div = document.createElement('div');
            if (i === 0) div.className = 'tip-h';
            if (ln.color) { const sw = document.createElement('i'); sw.style.background = ln.color; div.appendChild(sw); }
            div.append(ln.text);
            return div;
          }));
          el.hidden = false;
          const [px, py] = d3.pointer(event, card);
          const w = el.offsetWidth, h = el.offsetHeight, cw = card.clientWidth;
          let x = px + 14; if (x + w > cw - 4) x = px - w - 14; if (x < 4) x = 4;
          let y = py - h - 10; if (y < 4) y = py + 16;
          el.style.left = `${x}px`; el.style.top = `${y}px`;
        },
        hide() { el.hidden = true; },
      };
    },

    /** Put a chart container into its loading / error state */
    loading(box) { box.replaceChildren(); box.classList.add('loading'); },
    fail(box, msg) {
      box.classList.remove('loading');
      const d = document.createElement('div'); d.className = 'error'; d.textContent = msg || i18n.t('common.failed');
      box.replaceChildren(d);
    },
    ready(box) { box.classList.remove('loading'); box.replaceChildren(); },

    /** Redraw when the window size, colour scheme or language changes */
    onRedraw(fn) {
      let t;
      const run = () => { clearTimeout(t); t = setTimeout(fn, 120); };
      window.addEventListener('resize', run);
      matchMedia('(prefers-color-scheme: dark)').addEventListener('change', run);
      i18n.onChange(fn);
    },

    /** Strip d3's axis font attributes and leave styling to CSS */
    axisStyle: (...gs) => gs.forEach((g) => g.attr('font-size', null).attr('font-family', null)),

    /** Range picker (one per chart): 1Y / 3Y / 5Y / All / custom start and end dates.
        min / max are the first and last data dates (UTC Date); returns {get()} -> [start, end] and calls
        onChange when the range changes */
    rangePicker(host, { min, max, initial = '1y', onChange }) {
      const iso = d3.utcFormat('%Y-%m-%d');
      const keys = ['1y', '3y', '5y', 'all', 'custom'];
      let mode = initial;
      let custom = null;
      const range = () => {
        if (mode === 'all') return [min, max];
        if (mode === 'custom' && custom) return custom;
        const s = d3.utcYear.offset(max, -Number(mode[0]));
        return [s < min ? min : s, max];
      };
      const seg = document.createElement('div');
      seg.className = 'seg';
      seg.setAttribute('role', 'group');
      const buttons = keys.map((k) => {
        const b = document.createElement('button');
        b.type = 'button';
        b.addEventListener('click', () => {
          if (k === 'custom' && !custom) custom = range();  // a custom range starts from the current one
          mode = k;
          render();
          onChange(range());
        });
        seg.appendChild(b);
        return b;
      });
      const from = document.createElement('input');
      const to = document.createElement('input');
      const dash = document.createElement('span');
      [from, to].forEach((inp) => {
        inp.type = 'date';
        inp.min = iso(min); inp.max = iso(max);
        inp.addEventListener('change', () => {
          if (!from.value || !to.value || !from.validity.valid || !to.validity.valid || from.value > to.value) return;
          custom = [new Date(from.value), new Date(to.value)];
          onChange(range());
        });
      });
      host.classList.add('range');
      host.replaceChildren(seg, from, dash, to);
      function render() {
        seg.setAttribute('aria-label', i18n.t('range.label'));
        buttons.forEach((b, i) => {
          b.textContent = i18n.t(`range.${keys[i]}`);
          b.setAttribute('aria-pressed', String(keys[i] === mode));
        });
        const show = mode === 'custom';
        [from, dash, to].forEach((n) => { n.hidden = !show; });
        dash.textContent = i18n.t('range.to');
        from.setAttribute('aria-label', i18n.t('range.from'));
        to.setAttribute('aria-label', i18n.t('range.to'));
        if (show && custom) { from.value = iso(custom[0]); to.value = iso(custom[1]); }
      }
      i18n.onChange(render);
      render();
      return { get: range };
    },

    /** Section navigation: links every section with an id and data-nav="<dictionary key>", highlighting the current one on scroll */
    sectionNav(container) {
      const secs = [...document.querySelectorAll('[data-nav][id]')];
      const links = secs.map((sec) => {
        const a = document.createElement('a');
        a.href = `#${sec.id}`;
        container.appendChild(a);
        return a;
      });
      const label = () => links.forEach((a, i) => { a.textContent = i18n.t(secs[i].dataset.nav); });
      label();
      i18n.onChange(label);
      // current section = the last one whose top has passed the sticky bar (steadier than IntersectionObserver when several sections are visible)
      let ticking = false;
      const update = () => {
        ticking = false;
        const offset = (document.querySelector('.topbar')?.offsetHeight || 0) + 24;
        let cur = 0;
        secs.forEach((sec, i) => { if (sec.getBoundingClientRect().top <= offset) cur = i; });
        links.forEach((a, i) => a.classList.toggle('active', i === cur));
        const act = links[cur];
        const box = container.getBoundingClientRect(), r = act.getBoundingClientRect();
        if (r.left < box.left || r.right > box.right) container.scrollLeft += r.left - box.left - 16;
      };
      window.addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
      update();
    },

    /** Download links: <span class="dl" data-files="daily monthly"> renders as "Download CSV: <label> · <label>"
        (with one file the whole label is the link). A page names each file with an i18n key file.<name>
        (falls back to the file name); the file name shows on hover. base is the relative path of the data folder */
    downloadLinks(base = 'data/') {
      const render = () => document.querySelectorAll('.dl[data-files]').forEach((host) => {
        const files = host.dataset.files.split(/\s+/).filter(Boolean);
        const link = (f, text) => {
          const a = document.createElement('a');
          a.className = 'dl'; a.href = `${base}${f}.csv`; a.download = `${f}.csv`; a.title = `${f}.csv`; a.textContent = text;
          return a;
        };
        if (files.length === 1) { host.replaceChildren(link(files[0], `${i18n.t('common.download')} ↓`)); return; }
        const parts = [i18n.t('common.downloadPrefix')];
        files.forEach((f, i) => { if (i) parts.push(' · '); parts.push(link(f, i18n.has(`file.${f}`) ? i18n.t(`file.${f}`) : f)); });
        host.replaceChildren(...parts);
      });
      render();
      i18n.onChange(render);
    },

    /** Stale-data notice: shown when minDays or more weekdays separate the data date from today (holidays are not excluded,
        hence "about"). Daily data uses the default of 3; tools with monthly data pass a longer threshold */
    markStale(el, asof, minDays = 3) {
      const show = () => {
        const d0 = new Date(`${asof}T00:00:00Z`);
        const today = new Date();
        let n = 0;
        for (let d = d3.utcDay.offset(d0, 1); d < d3.utcDay.floor(today); d = d3.utcDay.offset(d, 1)) {
          if (d.getUTCDay() % 6 !== 0) n += 1;
        }
        el.hidden = n < minDays;
        el.textContent = i18n.t('common.stale', { d: asof, n });
      };
      show();
      i18n.onChange(show);
    },
  };
  window.kit = kit;
})();
