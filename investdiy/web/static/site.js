/* Shared disclaimers and site frame (load after i18n.js).
   Pages can opt into a prominent forecast notice; its copy stays centralized here. */
(function () {
  i18n.add({
    zh: {
      'site.forecastDisclaimer': '<strong>免责声明</strong>本工具仅供研究参考，不构成投资建议。数据、模型及测算结果可能存在错误或偏差，不保证准确性、完整性或时效性。本工具及维护者不对据此作出的决策或损失承担责任；请独立核实，并自行承担使用风险。',
    },
    en: {
      'site.forecastDisclaimer': '<strong>Disclaimer</strong>This tool is for research only and is not investment advice. Data, models and estimates may contain errors; accuracy, completeness and timeliness are not guaranteed. The tool and its maintainers accept no responsibility for decisions or losses arising from its use. Verify independently and use at your own risk.',
    },
  });
  function mount() {
    if (document.body.dataset.siteDisclaimer === 'profit-forecast') {
      const main = document.querySelector('main');
      if (main && !main.querySelector('.site-disclaimer-notice')) {
        const notice = document.createElement('aside');
        notice.className = 'site-disclaimer-notice';
        notice.setAttribute('role', 'note');
        notice.dataset.i18nHtml = 'site.forecastDisclaimer';
        main.prepend(notice);
        i18n.apply(main);
      }
    }
    let footer = document.querySelector('.site-footer');
    if (!footer) {
      footer = document.createElement('footer');
      footer.className = 'site-footer';
      const inner = document.createElement('div');
      inner.className = 'site-footer-in';
      inner.dataset.i18nHtml = 'common.disclaimer';
      footer.appendChild(inner);
      document.body.appendChild(footer);
    }
    i18n.apply(footer);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
})();
