(function () {
  var menus = document.querySelectorAll('.mobile-menu, .home-mobile-menu');
  // Every disclosure in the header that should close on Escape or on an
  // outside click. The mobile menus additionally relabel their summary; the
  // use-cases dropdown does not, because its summary carries a visible label
  // already and rewriting it would fight the translated string.
  var disclosures = document.querySelectorAll('.mobile-menu, .home-mobile-menu, .nav-group, .lang-switch');

  menus.forEach(function (menu) {
    menu.addEventListener('toggle', function () {
      var summary = menu.querySelector('summary');
      if (summary) {
        summary.setAttribute('aria-label', menu.open ? 'Close navigation menu' : 'Open navigation menu');
      }
    });
  });

  document.addEventListener('keydown', function (event) {
    if (event.key !== 'Escape') return;
    disclosures.forEach(function (menu) {
      if (!menu.open) return;
      menu.open = false;
      var summary = menu.querySelector('summary');
      if (summary) summary.focus();
    });
  });

  document.addEventListener('click', function (event) {
    disclosures.forEach(function (menu) {
      if (menu.open && !menu.contains(event.target)) menu.open = false;
    });
  });
})();
