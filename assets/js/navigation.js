(function () {
  // The menu button's open and close labels depend on runtime state, so this
  // script sets them. build_site.py emits window.AtlasDaysNavStrings per
  // locale; the English strings are the fallback.
  var strings = window.AtlasDaysNavStrings || {};
  var labelOpen = strings.menuOpen || 'Open navigation menu';
  var labelClose = strings.menuClose || 'Close navigation menu';

  var menus = document.querySelectorAll('.mobile-menu');
  // Header disclosures that close on Escape or on an outside click. Only the
  // mobile menu relabels its summary; the dropdowns already show a visible,
  // translated label. .mobile-nav-group sits inside .mobile-menu, so a click
  // elsewhere in the open drawer collapses the group but not the drawer.
  var disclosures = document.querySelectorAll('.mobile-menu, .mobile-nav-group, .nav-group, .lang-switch');

  // `:scope > summary` targets the menu's own summary, not the one of the
  // nested use-cases disclosure inside the drawer.
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

  // Every other App Store link shows the header's QR code on hover or
  // keyboard focus, on wide screens with a pointer. The popover is a copy of
  // the header's, so it carries the same image, link and translated caption.
  var headerQr = document.querySelector('.nav-qr-popup');
  var wide = window.matchMedia && matchMedia('(min-width: 861px) and (hover: hover)');
  if (headerQr && wide) {
    var popover = null;
    var owner = null;
    var hideTimer = null;
    var place = function (link) {
      // A full-width link (the article app line) anchors under its call to action.
      var rect = (link.querySelector('.app-line-cta') || link).getBoundingClientRect();
      var width = popover.offsetWidth;
      var height = popover.offsetHeight;
      var left = Math.min(Math.max(rect.left + rect.width / 2 - width / 2, 12), document.documentElement.clientWidth - width - 12);
      var below = rect.bottom + 10 + height <= innerHeight;
      var top = below ? rect.bottom + 10 : rect.top - 10 - height;
      popover.classList.toggle('is-above', !below);
      popover.style.left = (left + scrollX) + 'px';
      popover.style.top = (top + scrollY) + 'px';
    };
    var show = function (link) {
      if (!wide.matches) return;
      clearTimeout(hideTimer);
      if (!popover) {
        popover = headerQr.cloneNode(true);
        popover.className = 'qr-popover';
        popover.tabIndex = -1;
        popover.querySelector('img').removeAttribute('loading');
        popover.addEventListener('mouseenter', function () { clearTimeout(hideTimer); });
        popover.addEventListener('mouseleave', function () { hide(); });
        document.body.appendChild(popover);
      }
      owner = link;
      popover.classList.add('is-open');
      place(link);
    };
    var hide = function (now) {
      clearTimeout(hideTimer);
      hideTimer = setTimeout(function () {
        if (popover) popover.classList.remove('is-open');
        owner = null;
      }, now ? 0 : 120);
    };
    document.querySelectorAll('a[href^="https://apps.apple.com/"]').forEach(function (link) {
      if (link.closest('.nav-cta-wrap, .hx-final-button, .daycal, .qr-popover')) return;
      link.addEventListener('mouseenter', function () { show(link); });
      link.addEventListener('mouseleave', function () { hide(); });
      link.addEventListener('focus', function () { show(link); });
      link.addEventListener('blur', function () { hide(); });
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && owner) hide(true);
    });
    addEventListener('scroll', function () { if (owner) place(owner); }, {passive: true});
  }

  // Contact links carry the address split across data-email-user and
  // data-email-domain, so the markup holds no scrapeable email. Every page
  // loads this script, so the address is assembled here.
  document.querySelectorAll('[data-email-user][data-email-domain]').forEach(function (link) {
    var address = link.getAttribute('data-email-user') + '@' + link.getAttribute('data-email-domain');
    link.textContent = address;
    link.href = 'mai' + 'lto:' + address;
  });

  // A browser opted out with ?notrack sends no analytics; its footer says so
  // next to the copyright. ?notrack=off opts back in. Other browsers see no
  // change. The query parameter is read here too, so the note is right on the
  // page that sets or clears the flag, whatever order the scripts run in.
  try {
    var notrack = new URLSearchParams(location.search).get('notrack');
    var optedOut = notrack === null ? !!localStorage.getItem('atlasdays-notrack') : notrack !== 'off';
    var credit = document.querySelector('.site-footer-credit');
    if (optedOut && credit) {
      var group = document.createElement('span');
      group.className = 'site-footer-credit-group';
      group.style.whiteSpace = 'nowrap';
      credit.parentNode.insertBefore(group, credit);
      group.appendChild(credit);
      var note = document.createElement('span');
      note.lang = 'en';
      note.textContent = ' · notrack';
      note.style.opacity = '0.7';
      group.appendChild(note);
    }
  } catch (e) {}
})();
