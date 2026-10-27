// Marketing layout behaviour for the homepage and the use-case pages. Runs only
// when the new markup (`main.hx`) is on the page; localized pages that still
// carry the previous design are untouched.
(function () {
  var page = document.querySelector('main.hx');
  if (!page) return;

  var root = document.documentElement;
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var hasObserver = 'IntersectionObserver' in window;
  root.classList.add('hx-page');

  // ---------- Scroll: one rAF-throttled handler for the effects below ----------
  var ticking = false;
  var scrollHandlers = [];
  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () {
      ticking = false;
      root.classList.toggle('hx-scrolled', window.scrollY > 24);
      scrollHandlers.forEach(function (fn) { fn(); });
    });
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  root.classList.toggle('hx-scrolled', window.scrollY > 24);

  // On narrow screens the header button waits until the hero button has
  // scrolled away, so the first screen shows one download button, not two.
  // site-header.css owns the rule; this only sets the class.
  var heroCta = page.querySelector('[data-hx-hero-cta]');
  if (heroCta) {
    var box = heroCta.getBoundingClientRect();
    document.body.classList.toggle('hero-cta-in-view', box.bottom > 0 && box.top < window.innerHeight);
    if (hasObserver) {
      new IntersectionObserver(function (entries) {
        document.body.classList.toggle('hero-cta-in-view', entries[0].isIntersecting);
      }).observe(heroCta);
    }
  }

  // ---------- Hero: a short scroll handoff from dashboard to tracker ----------
  (function heroMotion() {
    var stage = page.querySelector('[data-hx-hero-stage]');
    var phones = page.querySelector('[data-hx-phones]');
    if (!stage || !phones) return;
    var hero = stage.querySelector('.hx-hero');
    var tracker = phones.querySelector('.hx-phone-back');
    var dashboard = phones.querySelector('.hx-phone-front');
    var header = document.querySelector('.top-bar');
    var motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    var desktop = window.matchMedia('(min-width: 900px)');
    var distance = 280;
    var pinned = false;
    var phoneWidth = 0;
    var headerHeight = 0;
    var progress = 0;
    var mobilePlayed = false;
    var frame = 0;
    var observer;

    function mix(a, b, t) { return a + (b - a) * t; }
    function paint(p) {
      progress = Math.min(1, Math.max(0, p));
      // Pull the phones apart before changing their stacking order, then
      // settle the tracker in front. All movement uses compositor transforms.
      var second = progress >= 0.5;
      var t = second ? (progress - 0.5) * 2 : progress * 2;
      t = t * t * (3 - 2 * t);
      var backX = second ? mix(-0.11, 0.08, t) : mix(0, -0.11, t);
      var backY = second ? mix(-0.10, -0.30, t) : mix(0, -0.10, t);
      var backScale = second ? mix(0.90, 1 / 0.84, t) : mix(1, 0.90, t);
      var frontX = second ? mix(0.11, -0.08, t) : mix(0, 0.11, t);
      var frontY = second ? mix(0.16, 0.30, t) : mix(0, 0.16, t);
      var frontScale = second ? mix(0.78, 0.84, t) : mix(1, 0.78, t);
      tracker.style.transform = 'translate3d(' + backX * phoneWidth + 'px,' + backY * phoneWidth + 'px,0) scale(' + backScale + ')';
      dashboard.style.transform = 'translate3d(' + frontX * phoneWidth + 'px,' + frontY * phoneWidth + 'px,0) scale(' + frontScale + ')';
      phones.classList.toggle('is-tracker-front', second);
    }

    function update() {
      if (!pinned || motion.matches) return;
      paint((headerHeight - stage.getBoundingClientRect().top) / distance);
    }

    function playOnce() {
      if (pinned || mobilePlayed || motion.matches) return;
      mobilePlayed = true;
      var start;
      function tick(now) {
        if (start === undefined) start = now;
        paint((now - start) / 1400);
        frame = progress < 1 ? requestAnimationFrame(tick) : 0;
      }
      frame = requestAnimationFrame(tick);
    }

    function configure() {
      if (observer) observer.disconnect();
      headerHeight = header ? header.offsetHeight : 0;
      phoneWidth = dashboard.offsetWidth;
      // Keep all hero content visible while pinned; its trailing padding may
      // extend below the window. Short windows use the unpinned handoff.
      var contentHeight = hero.offsetHeight - parseFloat(getComputedStyle(hero).paddingBottom);
      pinned = !motion.matches && desktop.matches && contentHeight <= window.innerHeight - headerHeight;
      stage.classList.toggle('is-animated', !motion.matches);
      stage.classList.toggle('is-pinned', pinned);
      stage.style.setProperty('--hx-hero-top', headerHeight + 'px');
      stage.style.setProperty('--hx-hero-distance', distance + 'px');
      if (frame && (pinned || motion.matches)) {
        cancelAnimationFrame(frame);
        frame = 0;
      }
      if (motion.matches) {
        tracker.style.removeProperty('transform');
        dashboard.style.removeProperty('transform');
        phones.classList.remove('is-tracker-front');
        return;
      }
      if (pinned) {
        update();
      } else {
        if (!frame) paint(mobilePlayed ? 1 : 0);
        if (!mobilePlayed && hasObserver) {
          observer = new IntersectionObserver(function (entries) {
            if (entries[0].intersectionRatio < 0.55) return;
            observer.disconnect();
            playOnce();
          }, { threshold: 0.55 });
          observer.observe(phones);
        }
      }
    }

    scrollHandlers.push(update);
    window.addEventListener('resize', configure);
    motion.addEventListener('change', configure);
    configure();
    // Fonts and restored navigation can change the initial hero geometry.
    window.addEventListener('pageshow', configure);
    if (document.fonts) document.fonts.ready.then(configure);
  })();

  // ---------- Reveal: only what starts below the fold is hidden first ----------
  if (!reduceMotion && hasObserver) {
    var revealer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.remove('is-pre');
        revealer.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -8% 0px' });
    page.querySelectorAll('[data-hx-reveal]').forEach(function (el) {
      if (el.getBoundingClientRect().top > window.innerHeight) {
        el.classList.add('is-pre');
        revealer.observe(el);
      }
    });
  }

  // ---------- How it works: one pinned phone, three screens ----------
  (function story() {
    var story = page.querySelector('[data-hx-story]');
    if (!story) return;
    var steps = Array.prototype.slice.call(story.querySelectorAll('[data-hx-step]'));
    var shots = Array.prototype.slice.call(story.querySelectorAll('[data-hx-step-shot]'));
    var dots = Array.prototype.slice.call(story.querySelectorAll('.hx-step-dots i'));
    var wide = window.matchMedia('(min-width: 900px)');
    var active = 0;
    function activate(n) {
      if (n === active) return;
      active = n;
      steps.forEach(function (step, i) { step.classList.toggle('is-active', i === n); });
      shots.forEach(function (shot) { shot.classList.toggle('is-shown', +shot.getAttribute('data-hx-step-shot') === n); });
      dots.forEach(function (dot, i) { dot.classList.toggle('is-active', i === n); });
    }
    function update() {
      if (wide.matches) {
        // The step nearest the middle of the screen is the active one.
        var middle = window.innerHeight / 2;
        var best = 0;
        var bestDistance = Infinity;
        steps.forEach(function (step, i) {
          var r = step.getBoundingClientRect();
          var d = Math.abs(r.top + r.height / 2 - middle);
          if (d < bestDistance) { bestDistance = d; best = i; }
        });
        activate(best);
      } else {
        // The block is pinned; progress through its height picks the step.
        var r = story.getBoundingClientRect();
        var pin = story.firstElementChild.offsetHeight;
        var top = parseFloat(getComputedStyle(page).getPropertyValue('--hx-sticky-top')) || 76;
        var p = Math.min(0.999, Math.max(0, (top - r.top) / Math.max(1, r.height - pin)));
        activate(Math.floor(p * steps.length));
      }
    }
    scrollHandlers.push(update);
    update();
  })();

  // ---------- Reviews on translated pages ----------
  // The translation into the page's language shows first; the button swaps in
  // the reviewer's own words and back. English pages have no button.
  page.querySelectorAll('[data-hx-review]').forEach(function (review) {
    var button = review.querySelector('.hx-quote-toggle');
    var original = review.querySelector('[data-hx-original]');
    var translation = review.querySelector('[data-hx-translation]');
    if (!button || !original || !translation) return;
    button.addEventListener('click', function () {
      var translated = button.getAttribute('aria-pressed') !== 'true';
      button.setAttribute('aria-pressed', String(translated));
      original.hidden = translated;
      translation.hidden = !translated;
      button.textContent = translated ? button.dataset.hide : button.dataset.show;
    });
  });
})();
