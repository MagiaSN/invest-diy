/* English / Chinese support shared by every page. Load before kit.js and the page scripts.
   Language priority: the user's choice (localStorage) > browser language (zh* means Chinese) > English.
   Usage:
     i18n.add({zh: {key: '中文'}, en: {key: 'English'}})   // a page registers its dictionary
     <span data-i18n="key">                                // static text (textContent)
     <p data-i18n-html="key">                              // static text with markup such as <b> (dictionaries are first-party, trusted)
     data-i18n-title / data-i18n-aria-label                 // attributes
     i18n.t('key', {n: 3})                                  // dynamic text, {n} is a placeholder
     i18n.onChange(fn)                                      // redraw dynamic content after a language switch
   A switch button is inserted into the top bar (.topbar-in). */
(function () {
  const KEY = 'tools.lang';
  const dicts = { zh: {}, en: {} };

  function detect() {
    try {
      const saved = localStorage.getItem(KEY);
      if (saved === 'zh' || saved === 'en') return saved;
    } catch (e) { /* fall back to the browser language when storage is unavailable (e.g. private mode) */ }
    const first = (navigator.languages && navigator.languages[0]) || navigator.language || '';
    return /^zh\b/i.test(first) ? 'zh' : 'en';
  }

  let lang = detect();

  const i18n = {
    get lang() { return lang; },
    add(d) { for (const l of ['zh', 'en']) Object.assign(dicts[l], d[l] || {}); },
    has: (key) => key in dicts[lang] || key in dicts.zh,
    t(key, vars) {
      let s = dicts[lang][key] ?? dicts.zh[key] ?? key;
      if (vars) s = s.replace(/\{(\w+)\}/g, (_, k) => (vars[k] ?? ''));
      return s;
    },
    /** Split a template into text and nodes: placeholder values are wrapped in <b> (or are caller-supplied nodes), for summary sentences */
    rich(key, vars) {
      const parts = [];
      const s = dicts[lang][key] ?? dicts.zh[key] ?? key;
      let last = 0;
      s.replace(/\{(\w+)\}/g, (m, k, idx) => {
        parts.push(s.slice(last, idx));
        const v = vars[k];
        if (v instanceof Node) parts.push(v);
        else { const b = document.createElement('b'); b.textContent = v ?? ''; parts.push(b); }
        last = idx + m.length;
        return m;
      });
      parts.push(s.slice(last));
      return parts;
    },
    apply(root = document) {
      document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
      root.querySelectorAll('[data-i18n]').forEach((el) => { el.textContent = i18n.t(el.dataset.i18n); });
      root.querySelectorAll('[data-i18n-html]').forEach((el) => { el.innerHTML = i18n.t(el.dataset.i18nHtml); });
      root.querySelectorAll('[data-i18n-title]').forEach((el) => { el.title = i18n.t(el.dataset.i18nTitle); });
      root.querySelectorAll('[data-i18n-aria-label]').forEach((el) => { el.setAttribute('aria-label', i18n.t(el.dataset.i18nAriaLabel)); });
      syncButton();
    },
    set(l) {
      if (l === lang) return;
      lang = l;
      try { localStorage.setItem(KEY, l); } catch (e) { /* if it cannot be stored, it applies to this visit only */ }
      i18n.apply();
      document.dispatchEvent(new CustomEvent('langchange', { detail: l }));
    },
    onChange(fn) { document.addEventListener('langchange', fn); },
  };

  function syncButton() {
    const b = document.querySelector('.lang-toggle');
    if (!b) return;
    b.textContent = lang === 'zh' ? 'EN' : '中文';
    b.lang = lang === 'zh' ? 'en' : 'zh-CN';
    b.setAttribute('aria-label', lang === 'zh' ? 'Switch to English' : '切换到中文');
  }

  function mount() {
    const bar = document.querySelector('.topbar-in');
    if (bar && !bar.querySelector('.lang-toggle')) {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'lang-toggle';
      b.addEventListener('click', () => i18n.set(lang === 'zh' ? 'en' : 'zh'));
      bar.appendChild(b);
    }
    i18n.apply();
  }

  // entries shared by every page
  i18n.add({
    zh: {
      'common.home': '投研工具箱',
      'common.asof': '数据截至 {d}',
      'common.loading': '加载中…',
      'common.failed': '加载失败',
      'common.download': '下载 CSV',
      'common.downloadPrefix': '下载 CSV：',
      'common.stale': '数据截至 {d}，已约 {n} 个工作日没有更新，以下内容可能已过时。',
      'common.disclaimer': '<b>免责声明</b>：本站内容仅为对交易所、基金定期报告等公开信息的整理与计算，可能存在错误、遗漏或延迟；其中的归因与判断（如"国家队"进出场）均为基于公开数据的推断，并非官方确认。本站不代表任何机构的观点，不构成任何投资建议，据此操作风险自负。',
      'range.1y': '近1年', 'range.3y': '近3年', 'range.5y': '近5年', 'range.all': '全部', 'range.custom': '自定义',
      'range.from': '从', 'range.to': '至', 'range.label': '时间段',
    },
    en: {
      'common.home': 'Research Toolkit',
      'common.asof': 'Data as of {d}',
      'common.loading': 'Loading…',
      'common.failed': 'Failed to load',
      'common.download': 'Download CSV',
      'common.downloadPrefix': 'Download CSV: ',
      'common.stale': 'Data is as of {d}, about {n} business days old; what follows may be out of date.',
      'common.disclaimer': '<b>Disclaimer</b>: this site only organises and computes publicly available information such as exchange disclosures and fund periodic reports, and may contain errors, omissions or delays. Attributions and judgements (such as national-team entries and exits) are inferences from public data, not official confirmation. Nothing here represents the views of any institution or constitutes investment advice; any action taken on it is at your own risk.',
      'range.1y': '1Y', 'range.3y': '3Y', 'range.5y': '5Y', 'range.all': 'All', 'range.custom': 'Custom',
      'range.from': 'From', 'range.to': 'to', 'range.label': 'Time range',
    },
  });

  window.i18n = i18n;
  // DOMContentLoaded fires after the page scripts at the end of body have run, so page dictionaries are registered by then
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
})();
