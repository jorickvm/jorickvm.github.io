(function () {
  // The two labels the script has to write itself. Everything else in the
  // header is localized in the markup by the build; these are not, because the
  // open/closed distinction only exists at runtime. navigation.js is one file
  // served to /ja/, /nl/, /de/, /es/, /fr/ and /ru/ alike, so hardcoding them
  // meant the summary's accessible name switched to English the moment a
  // reader on a translated page opened the drawer. build_site.py emits
  // window.AtlasDaysNavStrings per locale; the English literals below are the
  // fallback for a page built before that existed.
  var strings = window.AtlasDaysNavStrings || {};
  var labelOpen = strings.menuOpen || 'Open navigation menu';
  var labelClose = strings.menuClose || 'Close navigation menu';

  var menus = document.querySelectorAll('.mobile-menu');
  // Every disclosure in the header that should close on Escape or on an
  // outside click. The mobile menu additionally relabels its summary; the
  // use-cases dropdowns do not, because their summary carries a visible label
  // already and rewriting it would fight the translated string.
  // .mobile-nav-group lives inside .mobile-menu, so an outside click on it is
  // a click elsewhere in the open drawer, which should indeed collapse it.
  var disclosures = document.querySelectorAll('.mobile-menu, .mobile-nav-group, .nav-group, .lang-switch');

  // `:scope > summary`, not `summary`: the drawer now contains a nested
  // disclosure for use cases, and a plain descendant query would be one DOM
  // change away from relabelling or focusing the wrong one.
  menus.forEach(function (menu) {
    menu.addEventListener('toggle', function () {
      var summary = menu.querySelector(':scope > summary');
      if (summary) {
        summary.setAttribute('aria-label', menu.open ? labelClose : labelOpen);
      }
    });
  });

  document.addEventListener('keydown', function (event) {
    if (event.key !== 'Escape') return;
    disclosures.forEach(function (menu) {
      if (!menu.open) return;
      menu.open = false;
      var summary = menu.querySelector(':scope > summary');
      if (summary) summary.focus();
    });
  });

  document.addEventListener('click', function (event) {
    disclosures.forEach(function (menu) {
      if (menu.open && !menu.contains(event.target)) menu.open = false;
    });
  });

  // QR popovers remain open across the button, hover bridge and QR link.
  var qrButtons = document.querySelectorAll('.nav-cta-wrap, .hx-final-button');
  qrButtons.forEach(function (wrap) {
    wrap.addEventListener('mouseleave', function () {
      if (!wrap.contains(document.activeElement)) wrap.classList.remove('is-qr-dismissed');
    });
    wrap.addEventListener('focusout', function (event) {
      if (!wrap.matches(':hover') && !wrap.contains(event.relatedTarget)) wrap.classList.remove('is-qr-dismissed');
    });
  });
  document.addEventListener('keydown', function (event) {
    if (event.key !== 'Escape') return;
    qrButtons.forEach(function (wrap) {
      var focused = wrap.contains(document.activeElement);
      if (!wrap.matches(':hover') && !focused) return;
      wrap.classList.add('is-qr-dismissed');
      if (focused) {
        var button = wrap.querySelector('.top-cta, .hx-btn');
        if (button) button.focus({preventScroll: true});
      }
    });
  });

  // Contact links ship without an address (data-email-user plus
  // data-email-domain) so the markup carries no scrapeable email. The privacy
  // and terms pages use them in every locale, and this file is the one script
  // every locale loads, so the address is assembled here.
  document.querySelectorAll('[data-email-user][data-email-domain]').forEach(function (link) {
    var address = link.getAttribute('data-email-user') + '@' + link.getAttribute('data-email-domain');
    link.textContent = address;
    link.href = 'mai' + 'lto:' + address;
  });
})();
