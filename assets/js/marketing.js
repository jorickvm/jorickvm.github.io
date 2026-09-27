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

  // ---------- Header: floats as a pill once the page scrolls ----------
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

  // ---------- Rolling-window explainer (use-case pages) ----------
  // The same arithmetic the app runs: look back `span` days from a date,
  // count every day inside a trip (arrival and departure included, overlaps
  // once), compare with `limit`. Tones follow the app: red at or over the
  // limit, orange within 7 days or 15% of it.
  (function windowExplainer() {
    var box = page.querySelector('[data-hx-window]');
    if (!box) return;
    var DAY = 86400000;
    function parse(value) { var p = value.split('-'); return Date.UTC(+p[0], +p[1] - 1, +p[2]); }
    var from = parse(box.dataset.from), to = parse(box.dataset.to), today = parse(box.dataset.today);
    var limit = +box.dataset.limit, span = +box.dataset.span;
    var trips = JSON.parse(box.querySelector('[data-hx-trips]').textContent).map(function (t) {
      return { a: parse(t.a), b: parse(t.b), planned: !!t.planned };
    });
    var total = Math.round((to - from) / DAY) + 1;
    var svg = box.querySelector('[data-hx-chart]');
    var slider = box.querySelector('[data-hx-slider]');
    var usedEl = box.querySelector('[data-hx-used]');
    var captionEl = box.querySelector('[data-hx-caption]');
    var stateEl = box.querySelector('[data-hx-state]');
    var rangeEl = box.querySelector('[data-hx-range]');
    var lang = document.documentElement.lang || 'en';
    var dayFmt = new Intl.DateTimeFormat(lang, { day: 'numeric', month: 'short', timeZone: 'UTC' });
    var monthFmt = new Intl.DateTimeFormat(lang, { month: 'short', timeZone: 'UTC' });
    function fill(template, values) {
      return template.replace(/\{(\w+)\}/g, function (_, key) { return values[key]; });
    }
    function x(ms) { return (ms - from) / DAY / total * 1000; }

    var NS = 'http://www.w3.org/2000/svg';
    function node(name, attrs) {
      var e = document.createElementNS(NS, name);
      for (var k in attrs) e.setAttribute(k, attrs[k]);
      return e;
    }
    // Static layer: month ticks (lines in the SVG, labels in HTML so they do
    // not stretch with the chart) and the trips.
    var labels = document.createElement('div');
    labels.className = 'hx-window-labels';
    labels.setAttribute('aria-hidden', 'true');
    svg.parentNode.insertBefore(labels, svg.nextSibling);
    var m = new Date(from);
    while (m.getTime() <= to) {
      var mx = x(m.getTime());
      svg.appendChild(node('line', { 'class': 'tick', x1: mx, x2: mx, y1: 6, y2: 126 }));
      var label = document.createElement('span');
      label.style.left = ((mx + x(m.getTime() + 15 * DAY)) / 2 / 10) + '%';
      label.textContent = monthFmt.format(m);
      labels.appendChild(label);
      m.setUTCMonth(m.getUTCMonth() + 1);
    }
    var band = node('rect', { 'class': 'band', y: 14, height: 104, rx: 6 });
    svg.appendChild(band);
    var tripNodes = trips.map(function (t) {
      var base = node('rect', { 'class': 'trip' + (t.planned ? ' is-planned' : ''), x: x(t.a), width: x(t.b + DAY) - x(t.a), y: 46, height: 40, rx: 3 });
      var inside = node('rect', { 'class': 'trip is-in' + (t.planned ? ' is-planned' : ''), y: 46, height: 40, rx: 3 });
      svg.appendChild(base);
      svg.appendChild(inside);
      return { trip: t, inside: inside };
    });
    var todayLine = node('line', { 'class': 'today', y1: 6, y2: 126 });
    svg.appendChild(todayLine);

    function used(date) {
      var start = date - (span - 1) * DAY, seen = {}, count = 0;
      trips.forEach(function (t) {
        for (var d = Math.max(t.a, start); d <= Math.min(t.b, date); d += DAY) {
          if (!seen[d]) { seen[d] = true; count++; }
        }
      });
      return count;
    }
    function render(index) {
      var date = from + index * DAY;
      var start = date - (span - 1) * DAY;
      var bandStart = Math.max(from, start);
      band.setAttribute('x', x(bandStart));
      band.setAttribute('width', Math.max(0, x(date + DAY) - x(bandStart)));
      todayLine.setAttribute('x1', x(date + DAY));
      todayLine.setAttribute('x2', x(date + DAY));
      tripNodes.forEach(function (n) {
        var a = Math.max(n.trip.a, start), b = Math.min(n.trip.b, date);
        if (b < a) { n.inside.setAttribute('width', 0); return; }
        n.inside.setAttribute('x', x(a));
        n.inside.setAttribute('width', x(b + DAY) - x(a));
      });
      var count = used(date), left = limit - count;
      var tone = count >= limit ? 'crit' : (left <= 7 || left <= limit * 0.15 ? 'warn' : 'ok');
      box.dataset.tone = tone;
      stateEl.dataset.tone = tone;
      stateEl.textContent = count > limit ? fill(box.dataset.tOver, { n: count - limit })
        : count === limit ? box.dataset.tAt
        : left === 1 ? box.dataset.tOneLeft : fill(box.dataset.tLeft, { n: left });
      usedEl.textContent = count;
      var dateText = dayFmt.format(new Date(date));
      captionEl.textContent = fill(box.dataset.tLabel, { used: count, date: dateText });
      rangeEl.textContent = fill(box.dataset.tRange, { from: dayFmt.format(new Date(start)), to: dateText })
        + (date > today ? ' · ' + box.dataset.tPlanned : '');
    }

    slider.min = 0;
    slider.max = total - 1;
    slider.step = 1;
    var todayIndex = Math.round((today - from) / DAY);
    slider.value = todayIndex;
    render(todayIndex);
    var playing = false;
    slider.addEventListener('input', function () { playing = false; render(+slider.value); });

    // Play once from early summer to today when the explainer first comes
    // into view, so the window visibly slides. Touching the slider stops it.
    if (reduceMotion || !hasObserver || !box.dataset.playFrom) return;
    var playIndex = Math.round((parse(box.dataset.playFrom) - from) / DAY);
    var played = false;
    new IntersectionObserver(function (entries, obs) {
      if (!entries[0].isIntersecting || played) return;
      played = true; obs.disconnect();
      playing = true;
      var t0 = null, duration = 2600;
      function step(ts) {
        if (!playing) return;
        if (t0 === null) t0 = ts;
        var p = Math.min(1, (ts - t0) / duration);
        var eased = 1 - Math.pow(1 - p, 3);
        var index = Math.round(playIndex + (todayIndex - playIndex) * eased);
        slider.value = index;
        render(index);
        if (p < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    }, { threshold: 0.5 }).observe(box);
  })();
})();
