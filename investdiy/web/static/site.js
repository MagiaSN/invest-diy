/* Site frame shared by every page (load after i18n.js).
   It appends the footer disclaimer: every tool here organises public information and is not
   investment advice, so pages do not repeat it. */
(function () {
  function mount() {
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
