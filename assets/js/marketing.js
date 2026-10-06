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

  // ---------- Hero: the phones rise into place once ----------
  var phones = page.querySelector('[data-hx-phones]');
  if (phones) {
    if (reduceMotion) {
      phones.classList.remove('is-pre');
    } else {
      requestAnimationFrame(function () {
        setTimeout(function () { phones.classList.remove('is-pre'); }, 80);
      });
    }
  }

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
  // The reviewer's own words show first; the button swaps in the translation
  // into the page's language and back. English pages have no button.
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
