/* Checks against press reports (done item by item on 2026-10-27; see docs/tools/ashare-track-national-team-etf.md).
   This is a manual record and is not recalculated when the data updates; to add a check, add a row to ROWS
   with both Chinese and English text.
   verdict: match / scope (different scope, same size) / date (dated one day apart) / blind (invisible to this method) */
(function () {
  const ROWS = [
    {
      date: '2015-06-29 ~ 07-01',
      event: { zh: '救市：四大蓝筹 ETF 净申购（逐日）', en: 'Market rescue: net creations in the four blue-chip ETFs (daily)' },
      media: { zh: '94.5 / 155.6 / 134.3 亿元', en: 'CNY 9.45 / 15.56 / 13.43bn' },
      ours: { zh: '93.4 / 163.6 / 4.5 亿元；07-02 为 134.2 亿元', en: 'CNY 9.34 / 16.36 / 0.45bn; 13.42bn on 07-02' },
      verdict: 'date',
      note: { zh: '前两天相符；第三天对应本页 07-02，疑为交易所份额初值 / 终值的日期归属差一天，不影响波段识别', en: 'The first two days match; the third matches 07-02 here, likely a one-day difference in how preliminary and final unit counts are dated. Wave detection is unaffected' },
      src: [['澎湃新闻', 'The Paper', 'https://www.thepaper.cn/newsDetail_forward_1348782']],
    },
    {
      date: '2023 H2',
      event: { zh: '汇金增持华泰柏瑞沪深300（年报持有人）', en: 'Huijin adds to Huatai-PB CSI 300 (annual-report holders)' },
      media: { zh: '24.24 → 62.47 亿份', en: '2.424 → 6.247bn units' },
      ours: { zh: '24.24 → 62.47 亿份', en: '2.424 → 6.247bn units' },
      verdict: 'match',
      note: { zh: '本页直接解析同一份定期报告', en: 'This page parses the same periodic reports' },
      src: [['基金定期报告', 'Fund reports', 'https://fundf10.eastmoney.com/jjgg_510300_3.html']],
    },
    {
      date: '2023-10-23',
      event: { zh: '汇金公告买入 ETF', en: 'Huijin announces ETF purchases' },
      media: { zh: '尾盘成交放大，华泰柏瑞沪深300 全天成交 95.92 亿元', en: 'Heavy trading near the close; Huatai-PB CSI 300 turnover CNY 9.59bn for the day' },
      ours: { zh: '池内份额仅 +24 亿元，无信号', en: 'Pool units up only CNY 2.4bn, no signal' },
      verdict: 'blind',
      note: { zh: '汇金当天主要在二级市场买入，份额基本不变——份额推算方法的固有盲区，只能等下一期报告补上', en: 'Huijin bought mainly on the secondary market, so units barely moved: a built-in blind spot of the unit-count method, filled in only by the next report' },
      src: [['同花顺', '10jqka', 'https://stock.10jqka.com.cn/20231024/c651512729.shtml']],
    },
    {
      date: '2024 Q1',
      event: { zh: '汇金买入 5 只 ETF（媒体按一季报估算）', en: 'Huijin buys 5 ETFs (press estimate from Q1 reports)' },
      media: { zh: '华泰 889 / 易方达 750 / 华夏300 582 / 嘉实 543 / 50ETF 375，合计 3,139 亿元', en: 'Huatai 88.9 / E Fund 75.0 / ChinaAMC 300 58.2 / Harvest 54.3 / 50ETF 37.5, total CNY 313.9bn' },
      ours: { zh: '同 5 只合计净申赎 2,813 亿元（588 / 810 / 554 / 586 / 276）', en: 'Same 5 ETFs net creation CNY 281.3bn (58.8 / 81.0 / 55.4 / 58.6 / 27.6)' },
      verdict: 'scope',
      note: { zh: '量级一致；差额是其他投资者同期的赎回（华泰柏瑞沪深300 尤其明显）', en: 'Same order of magnitude; the gap is redemptions by other holders in the same period (notably Huatai-PB CSI 300)' },
      src: [['中证网', 'cs.com.cn', 'https://cs.com.cn/tzjj/jjdt/202404/t20240423_6404260.html']],
    },
    {
      date: '2024-03-31',
      event: { zh: '华泰柏瑞沪深300 汇金持仓', en: 'Huijin holding in Huatai-PB CSI 300' },
      media: { zh: '约 1,150 亿元', en: 'About CNY 115bn' },
      ours: { zh: '326.03 亿份 × 净值 ≈ 1,150 亿元', en: '32.603bn units × NAV ≈ CNY 115bn' },
      verdict: 'match',
      note: { zh: '', en: '' },
      src: [['中证网', 'cs.com.cn', 'https://cs.com.cn/tzjj/jjdt/202404/t20240423_6404260.html']],
    },
    {
      date: '2024-09-24 ~ 10-14',
      event: { zh: '华泰柏瑞沪深300 净申购', en: 'Huatai-PB CSI 300 net creation' },
      media: { zh: '+465.25 亿元', en: '+CNY 46.53bn' },
      ours: { zh: '+471.1 亿元', en: '+CNY 47.11bn' },
      verdict: 'match',
      note: { zh: '差 1.3%', en: '1.3% apart' },
      src: [['财联社', 'CLS', 'https://www.cls.cn/detail/1782822']],
    },
    {
      date: '2025-04-08',
      event: { zh: '关税冲击护盘：沪深300 ETF 合计', en: 'Tariff-shock support: CSI 300 ETFs combined' },
      media: { zh: '+534.17 亿元（Wind）', en: '+CNY 53.42bn (Wind)' },
      ours: { zh: '沪深300 族 +537.3 亿元', en: 'CSI 300 family +CNY 53.73bn' },
      verdict: 'match',
      note: { zh: '差 0.6%', en: '0.6% apart' },
      src: [['同花顺', '10jqka', 'https://news.10jqka.com.cn/20250414/c667422862.shtml']],
    },
    {
      date: '2025-04-07 ~ 04-11',
      event: { zh: '关税冲击护盘：四大宽基 ETF', en: 'Tariff-shock support: four major broad-based ETFs' },
      media: { zh: '1,500 亿元以上', en: 'Over CNY 150bn' },
      ours: { zh: '监控池 +1,587 亿元', en: 'Pool +CNY 158.7bn' },
      verdict: 'match',
      note: { zh: '', en: '' },
      src: [['同花顺', '10jqka', 'https://news.10jqka.com.cn/20250414/c667422862.shtml']],
    },
    {
      date: '2026-01-01 ~ 01-26',
      event: { zh: '减持：宽基 ETF 年内净流出', en: 'Selling: year-to-date net outflow from broad-based ETFs' },
      media: { zh: '7,382 亿元（全部宽基 ETF）', en: 'CNY 738.2bn (all broad-based ETFs)' },
      ours: { zh: '监控池 −6,744 亿元', en: 'Pool −CNY 674.4bn' },
      verdict: 'scope',
      note: { zh: '媒体口径更宽，监控池占约九成，合理', en: 'The press figure covers more ETFs; the pool accounts for about 90%, as expected' },
      src: [['第一财经', 'Yicai', 'https://www.yicai.com/news/103026365.html']],
    },
    {
      date: '2026-01-22 / 23 / 26',
      event: { zh: '减持：单日净赎回', en: 'Selling: single-day net redemptions' },
      media: { zh: '770 / 871 / 1,165 亿元', en: 'CNY 77.0 / 87.1 / 116.5bn' },
      ours: { zh: '−710 / −875 / −1,138 亿元', en: '−CNY 71.0 / 87.5 / 113.8bn' },
      verdict: 'match',
      note: { zh: '媒体口径为全部宽基 ETF，略大', en: 'The press figure covers all broad-based ETFs and runs slightly higher' },
      src: [['新浪财经', 'Sina Finance', 'https://finance.sina.com.cn/jjxw/2026-01-27/doc-inhiucru5573522.shtml']],
    },
    {
      date: '2026-01-15 ~ 02-02',
      event: { zh: '减持：11 只救市宽基 ETF 累计', en: 'Selling: cumulative, 11 rescue broad-based ETFs' },
      media: { zh: '累计 9,471 亿元，01-28 峰值 1,384 亿元', en: 'CNY 947.1bn in total, peak CNY 138.4bn on 01-28' },
      ours: { zh: '−9,523 亿元，01-28 −1,439 亿元', en: '−CNY 952.3bn, −CNY 143.9bn on 01-28' },
      verdict: 'match',
      note: { zh: '差 0.5% / 4%', en: '0.5% / 4% apart' },
      src: [['新浪', 'Sina', 'https://k.sina.com.cn/article_7879922977_1d5ae152106801azsm.html']],
    },
    {
      date: '2026-01-26',
      event: { zh: '华泰柏瑞沪深300 汇金至少减持', en: 'Minimum Huijin sale in Huatai-PB CSI 300' },
      media: { zh: '735.13 − 605.17 ≈ 130 亿份、621.86 亿元', en: '73.513 − 60.517 ≈ 13.0bn units, CNY 62.19bn' },
      ours: { zh: '汇金年末持仓 735.13、当日总份额 605.17 亿份', en: 'Huijin year-end holding 73.513bn, total units that day 60.517bn' },
      verdict: 'match',
      note: { zh: '媒体用的就是本页的"份额地板"算法；第一财经把 735.13 写成了"总份额"，实为汇金持仓', en: 'The press used the same share-floor method as this page; Yicai labelled 73.513bn as total units, but it is Huijin\'s holding' },
      src: [['第一财经', 'Yicai', 'https://www.yicai.com/news/103026365.html']],
    },
    {
      date: '2026-10-15',
      event: { zh: '易方达沪深300 单日净申购', en: 'E Fund CSI 300 single-day net creation' },
      media: { zh: '+188 亿元', en: '+CNY 18.8bn' },
      ours: { zh: '+187.9 亿元', en: '+CNY 18.79bn' },
      verdict: 'match',
      note: { zh: '', en: '' },
      src: [['新浪财经', 'Sina Finance', 'https://finance.sina.com.cn/stock/bxjj/2026-10-16/doc-inivkncx8250108.shtml']],
    },
    {
      date: '2026-09-28 ~ 10-23',
      event: { zh: '华泰柏瑞沪深300 净申购', en: 'Huatai-PB CSI 300 net creation' },
      media: { zh: '+475.02 亿元', en: '+CNY 47.50bn' },
      ours: { zh: '+476.4 亿元', en: '+CNY 47.64bn' },
      verdict: 'match',
      note: { zh: '', en: '' },
      src: [['21 世纪经济报道', '21 Jingji', 'https://www.21jingji.com/article/20261025/herald/d33b9fd57cd823952a1eca683044989c.html']],
    },
  ];
  const VERDICTS = ['match', 'scope', 'date', 'blind'];
  const MARK = { match: '✓', scope: '≈', date: '±1', blind: '✗' };

  const t = (k, v) => i18n.t(k, v);
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };

  function draw() {
    const lang = i18n.lang === 'zh' ? 'zh' : 'en';
    const count = Object.fromEntries(VERDICTS.map((v) => [v, ROWS.filter((r) => r.verdict === v).length]));
    document.getElementById('ck-sum').textContent = t('ck.sum', { n: ROWS.length, ...count });
    const head = el('tr');
    ['date', 'event', 'media', 'ours', 'verdict', 'src'].forEach((c) => head.append(el('th', null, t(`ck.${c}`))));
    const table = document.getElementById('ck-table');
    table.tHead.replaceChildren(head);
    table.tBodies[0].replaceChildren(...ROWS.map((r) => {
      const tr = el('tr');
      const v = el('td', 'ck-v');
      v.append(el('span', `pill ck-${r.verdict}`, `${MARK[r.verdict]} ${t(`ck.v.${r.verdict}`)}`));
      if (r.note[lang]) v.append(el('div', 'ck-note', r.note[lang]));
      const src = el('td');
      r.src.forEach(([zh, en, url], i) => {
        if (i) src.append(' · ');
        const a = el('a', null, lang === 'zh' ? zh : en); a.href = url; a.target = '_blank'; a.rel = 'noopener';
        src.append(a);
      });
      tr.append(el('td', 'ck-date', r.date), el('td', null, r.event[lang]), el('td', null, r.media[lang]), el('td', null, r.ours[lang]), v, src);
      return tr;
    }));
  }

  draw();
  i18n.onChange(draw);
})();
