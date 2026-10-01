/* AtlasDays day calendar: the reusable engine behind the rule calculators on
   the Learn pages (UK ILR absences today, Schengen 90/180 and others later).

   It draws the app's own calendar: one continuous column of week rows, the
   month name on the 1st, today as an accent pill, each trip as one rounded
   bar under the day numbers, a faint disc on days without a trip. Days
   outside the month in view are dimmed, as in the app. Deliberately small:
   one rule per page, and anything beyond a quick check is what the app is for.

   Tapping, as designed with Jorick (2026-09-30):
     - make a trip: tap its first day (the circle turns trip-blue), then its
       last; with a mouse, a half-strength bar previews the trip as you move
     - tap the first day again to cancel, or to make a one-day trip when the
       rule counts single days (rule.singleDayTrips)
     - a new trip that reaches into an existing one extends it
     - tap a trip (bar or card) to select it: it turns darker and gets a drag
       handle on each end; Delete sits in its card (or the Delete key)
     - tap it again, tap outside, or press Escape to let go

   A rule plugs in through window.AtlasDaysRules[name]:
     range(ctx)              { from, to } day numbers the calendar must cover
     travelDaysCount         whether the rule counts travel days (informational;
                             bars always cover both end days)
     singleDayTrips          true when a one-day trip counts for the rule
     evaluate(trips, ctx)    { ok, total, remaining, status, from, to }, or the
                             result written out: { headlineText, statusText,
                             ok, lines: [], controls: [] }. A control is a menu
                             in the result box: { key, prefix, label, value,
                             options: [{ value, label, group }], moveCalendar };
                             its choice lands in ctx.settings[key]
     fixedRange              optional: the calendar shows range() only, even
                             when a trip runs past it
     tripLabel(trip, ctx)    short text for a trip in the list
     exportRows(trips, ctx)  rows for the AtlasDays CSV import
     countries(all)          optional: the country codes a trip may have
                             (one code: the country is fixed, no picker)
     defaultCountry          optional: the country a new trip starts with
     carryCountry            optional: a new trip starts with the last country
                             picked
     strings                 labels shown by the engine

   Everything runs in the browser. Nothing is sent, logged or stored. */
(function () {
  "use strict";

  var DAY = 86400000;
  var D = {
    fromParts: function (y, m, d) {
      var t = Date.UTC(y, m - 1, d), c = new Date(t);
      if (c.getUTCFullYear() !== y || c.getUTCMonth() !== m - 1 || c.getUTCDate() !== d) return null;
      return Math.round(t / DAY);
    },
    parts: function (n) { var d = new Date(n * DAY); return { y: d.getUTCFullYear(), m: d.getUTCMonth(), d: d.getUTCDate(), w: d.getUTCDay() }; },
    iso: function (n) { return new Date(n * DAY).toISOString().slice(0, 10); },
    today: function () { var n = new Date(); return D.fromParts(n.getFullYear(), n.getMonth() + 1, n.getDate()); },
    shiftYears: function (n, years) {
      var p = D.parts(n), y = p.y + years, last = new Date(Date.UTC(y, p.m + 1, 0)).getUTCDate();
      return Math.round(Date.UTC(y, p.m, Math.min(p.d, last)) / DAY);
    },
    monday: function (n) { return n - (D.parts(n).w + 6) % 7; },
    monthKey: function (n) { var p = D.parts(n); return p.y * 12 + p.m; },
    monthStart: function (key) { return Math.round(Date.UTC(Math.floor(key / 12), key % 12, 1) / DAY); },
    monthEnd: function (key) { return D.monthStart(key + 1) - 1; }
  };
  var locale = document.documentElement.lang || "en";
  // Flag images sit next to this script's folder: assets/js/ -> assets/flags/.
  var FLAGS = ((document.currentScript && document.currentScript.src) || "").replace(/js\/day-calendar\.js.*$/, "flags/");
  // Every place AtlasDays tracks (the app's CountryLists: 197 countries and 53
  // territories). A rule may narrow it with countries().
  var PLACES = "AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LL LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG US UY UZ VA VC VE VG VI VN VU WF WS XK YE YT ZA ZM ZW".split(" ");
  var regionNames = null;
  try { regionNames = new Intl.DisplayNames([locale], { type: "region" }); } catch (e) {}
  function placeName(code) {
    if (code === "XK") return regionNames ? (regionNames.of("XK") || "Kosovo") : "Kosovo";
    if (code === "LL") return "Liberland";
    return (regionNames && regionNames.of(code)) || code;
  }
  var plurals = new Intl.PluralRules(locale);
  function dateFormat(options) { return new Intl.DateTimeFormat(locale, Object.assign({ timeZone: "UTC" }, options)); }
  var fullDate = dateFormat({ day: "numeric", month: "long", year: "numeric" });
  var monthDate = dateFormat({ month: "long", year: "numeric" });
  var shortMonth = dateFormat({ month: "short" });
  var shortDate = dateFormat({ day: "numeric", month: "short" });
  var shortDateYear = dateFormat({ day: "numeric", month: "short", year: "numeric" });
  var weekday = dateFormat({ weekday: "narrow" });
  function label(n) { return fullDate.format(new Date(n * DAY)); }
  function short(n, withYear) {
    return (withYear ? shortDateYear : shortDate).format(new Date(n * DAY));
  }
  // 1-10 Jul 2026 / 1 Jul - 10 Aug 2026 / 1 Jul 2026 - 10 Jan 2027, collapsed
  // the way each language does it.
  var rangeFormat = new Intl.DateTimeFormat(locale === "en" ? "en-GB" : locale, { timeZone: "UTC", day: "numeric", month: "short", year: "numeric" });
  // Japanese and Chinese: V8's formatRange falls back to numeric dates there,
  // so the range is built the way both write it, the end date dropping the
  // year (and month) it shares with the start: 2026年7月1日～10日.
  var hanzi = /^(ja|zh)/.test(locale);
  function hanziDate(p, from) {
    return (from > 0 ? "" : p.y + "年") + (from > 1 ? "" : (p.m + 1) + "月") + p.d + "日";
  }
  function dateRange(a, b) {
    if (hanzi) {
      var pa = D.parts(a), pb = D.parts(b), sep = locale === "ja" ? "～" : "–";
      if (a === b) return hanziDate(pa, 0);
      var shared = pa.y !== pb.y ? 0 : pa.m !== pb.m ? 1 : 2;
      return hanziDate(pa, 0) + sep + hanziDate(pb, shared);
    }
    var out = a === b ? rangeFormat.format(new Date(a * DAY))
      : rangeFormat.formatRange ? rangeFormat.formatRange(new Date(a * DAY), new Date(b * DAY))
      : short(a, true) + " – " + short(b, true);
    // en-GB writes September as "Sept"; the app writes "Sep".
    return locale === "en" ? out.replace(/\bSept\b/g, "Sep") : out;
  }
  function plural(n, variants) { return variants[plurals.select(n)] || variants.other; }
  function el(tag, attrs, text) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { if (attrs[k] != null) node.setAttribute(k, attrs[k]); });
    if (text != null) node.textContent = text;
    return node;
  }

  function DayCalendar(root) {
    var rule = (window.AtlasDaysRules || {})[root.getAttribute("data-day-calendar")];
    if (!rule) return;
    var S = Object.assign({}, rule.strings);
    var stringsNode = root.querySelector("[data-cal-strings]");
    if (stringsNode) {
      try { Object.assign(S, JSON.parse(stringsNode.textContent)); }
      catch (error) { console.error("Invalid calendar translations", error); }
    }
    function text(key, values) {
      values = values || {};
      var value = S[key];
      if (value && typeof value === "object") value = plural(values.n, value);
      return String(value == null ? "" : value).replace(/\{(\w+)\}/g, function (_, name) {
        return values[name] == null ? "" : String(values[name]);
      });
    }
    root.querySelectorAll(".cal-weekdays span").forEach(function (node, i) {
      node.textContent = weekday.format(new Date(Date.UTC(2024, 0, 1 + i)));
    });
    var $ = function (sel) { return root.querySelector(sel); };
    var win = $("[data-cal-window]"), head = $(".cal-head"), weeksBox = $("[data-cal-weeks]"), monthTitle = $("[data-cal-month]");
    var hint = $("[data-cal-hint]"), list = $("[data-cal-list]"), result = $("[data-cal-result]");
    var dialog = $("[data-cal-dialog]");

    var today = D.today();
    // anchor: first day of a trip being made; hover: the day under the mouse
    // while making one (desktop preview); selected: index of the trip being
    // edited; drag: a handle being dragged.
    var trips = [], anchor = null, hover = null, selected = -1, drag = null;
    var allowed = (rule.countries && rule.countries(PLACES)) || PLACES;
    var defaultCountry = allowed.length === 1 ? allowed[0] : (rule.defaultCountry || "");
    var recent = [];
    var settings = {}; // choices made in the rule's result menus (rule.evaluate -> controls)
    var finePointer = !!(window.matchMedia && window.matchMedia("(hover: hover) and (pointer: fine)").matches);
    var rows = [], cells = {}, firstMonday = 0, activeMonth = null;
    var englishNames = null;
    try { englishNames = new Intl.DisplayNames(["en"], { type: "region" }); } catch (e) {}

    function ctx() { return { today: today, D: D, label: label, plural: plural, text: text, trips: trips, placeName: placeName, settings: settings, dateRange: dateRange }; }
    // A new trip starts with the rule's fixed country, or (rule.carryCountry)
    // the country picked last, so a run of stays in one country is quick.
    function newCountry() { return defaultCountry || (rule.carryCountry && recent[0]) || ""; }

    // ---- trips -----------------------------------------------------------------
    function tripAt(day) {
      for (var i = 0; i < trips.length; i++) if (day >= trips[i].start && day <= trips[i].end) return i;
      return -1;
    }
    // Two trips that share only a travel day (a handoff: out of one country,
    // into the next) stay two trips. Trips that share a night are one trip when
    // their countries agree (or one has none).
    function compatible(a, b) { return !a.country || !b.country || a.country === b.country; }
    function normalise() {
      trips.sort(function (a, b) { return a.start - b.start || a.end - b.end; });
      var out = [];
      trips.forEach(function (t) {
        var last = out[out.length - 1];
        if (last && t.start < last.end && compatible(last, t)) { last.end = Math.max(last.end, t.end); if (!last.country) last.country = t.country || ""; }
        else out.push({ start: t.start, end: t.end, country: t.country || "" });
      });
      trips = out;
    }
    // Set a trip to [a, b]. A trip it now shares a night with is absorbed when
    // the countries agree; when they differ, the edited trip wins and the other
    // is trimmed back to the shared day (or dropped if nothing of it is left).
    function place(span, a, b) {
      span.start = Math.min(a, b); span.end = Math.max(a, b);
      var again = true;
      while (again) {
        again = false;
        trips = trips.filter(function (t) {
          if (t === span || t.end <= span.start || t.start >= span.end) return true;   // apart, or a handoff
          if (compatible(span, t)) {
            var grew = t.start < span.start || t.end > span.end;
            span.start = Math.min(span.start, t.start); span.end = Math.max(span.end, t.end);
            if (!span.country) span.country = t.country || "";
            if (grew) again = true;
            return false;
          }
          if (t.start < span.start) { t.end = span.start; return true; }
          if (t.end > span.end) { t.start = span.end; return true; }
          return false;
        });
      }
    }

    // Tapping, as designed with Jorick (2026-09-30):
    //   tap an empty day, then another: a new trip (the mouse previews it)
    //   tap a trip: select it; drag its end handles to change the dates;
    //   tap it again, tap elsewhere or press Escape to let go
    function tap(day) {
      if (anchor != null) {
        var from = anchor;
        anchor = null; hover = null;
        if (day === from) {
          if (!rule.singleDayTrips) return refresh();
          trips.push({ start: day, end: day, country: newCountry() });
          return created(day);
        }
        var span = { start: from, end: day, country: newCountry() };
        trips.push(span);
        place(span, from, day);
        return created(span.start);
      }
      var hit = tripAt(day);
      if (hit >= 0) { selected = selected === hit ? -1 : hit; return refresh(); }
      selected = -1;
      anchor = day;
      refresh();
    }
    function created(day) {
      selected = -1;
      normalise();
      render();
    }
    function removeTrip(i) { trips.splice(i, 1); selected = -1; commit(); }
    function commit() { normalise(); render(); }
    function refresh() { paint(); renderList(); }

    // ---- the calendar: continuous week rows ------------------------------------
    function build() {
      var r = rule.range(ctx()), from = r.from, to = r.to;
      if (!rule.fixedRange) trips.forEach(function (t) { from = Math.min(from, t.start); to = Math.max(to, t.end); });
      var first = D.monday(from), last = D.monday(to) + 6;
      if (rows.length && first === firstMonday && rows.length === (last - first + 1) / 7) return;
      var anchor = rows.length ? topDay() : null;
      firstMonday = first;
      rows = []; cells = {};
      weeksBox.textContent = "";
      for (var mon = first; mon <= last; mon += 7) {
        var row = el("div", { "class": "cal-week" });
        row.dataset.monday = mon;
        for (var c = 0; c < 7; c++) {
          var day = mon + c, p = D.parts(day);
          var b = el("button", { type: "button", "class": "cal-day" + (p.d === 1 ? " is-month-start" : "") + (day === today ? " is-today" : ""), "data-day": day });
          b.appendChild(el("span", { "class": "cal-num" }, p.d === 1 ? shortMonth.format(new Date(day * DAY)).toLocaleUpperCase(locale) : String(p.d)));
          cells[day] = b;
          row.appendChild(b);
        }
        row.appendChild(el("div", { "class": "cal-bars", "aria-hidden": "true" }));
        weeksBox.appendChild(row);
        rows.push(row);
      }
      activeMonth = null;
      if (anchor != null) reveal(anchor);
    }

    // One bar per trip per week, drawn from the outer edge of the first day's
    // circle to the outer edge of the last day's (at a handoff, to the middle
    // of the shared day, leaving a small gap). A trip with a country carries
    // its flag at the start of its bar. While a trip is being made
    // with the mouse, a half-strength preview bar follows the pointer. The
    // selected trip is darker and carries a drag handle on each end.
    var DISC = 10; // half the width of a day circle, in px (see .cal-day::after)
    var GAP = 1.5; // half the gap between two bars meeting at a handoff, as in the app
    // At its start a trip is handed over when another trip ends that day; at
    // its end, when another trip starts that day.
    function handoff(t, atStart) { return trips.some(function (o) { return o !== t && (atStart ? o.end === t.start : o.start === t.end); }); }
    function segment(bars, mon, t, cls, real) {
      var sun = mon + 6;
      if (t.end < mon || t.start > sun) return;
      var a = Math.max(t.start, mon), z = Math.min(t.end, sun);
      var starts = a === t.start, ends = z === t.end;
      var cutStart = real && starts && t.start !== t.end && handoff(t, true);
      var cutEnd = real && ends && t.start !== t.end && handoff(t, false);
      var left = !starts ? "0px" : "calc(" + ((a - mon + 0.5) / 7 * 100) + "% " + (cutStart ? "+ " + GAP : "- " + DISC) + "px)";
      var right = !ends ? "100%" : "calc(" + ((z - mon + 0.5) / 7 * 100) + "% " + (cutEnd ? "- " + GAP : "+ " + DISC) + "px)";
      var bar = el("span", { "class": "cal-bar" + cls + (starts ? " starts" : "") + (ends ? " ends" : "") });
      bar.style.left = left;
      bar.style.width = "calc(" + right + " - " + left + ")";
      bars.appendChild(bar);
      // The trip's flag stamped on the start of its bar, as in the app.
      if (real && starts && t.country) {
        var flag = el("img", { "class": "cal-bar-flag", src: FLAGS + t.country.toLowerCase() + ".png", alt: "" });
        flag.style.left = left;
        bars.appendChild(flag);
      }
    }
    function handleAt(bars, mon, day, end) {
      if (day < mon || day > mon + 6) return;
      var h = el("span", { "class": "cal-handle", "data-end": end });
      h.style.left = ((day - mon + 0.5) / 7 * 100) + "%";
      h.addEventListener("pointerdown", startDrag);
      bars.appendChild(h);
    }
    function drawBars() {
      var preview = anchor != null && hover != null && hover !== anchor
        ? { start: Math.min(anchor, hover), end: Math.max(anchor, hover) } : null;
      rows.forEach(function (row) {
        var mon = +row.dataset.monday, bars = row.lastChild;
        bars.textContent = "";
        trips.forEach(function (t, i) { segment(bars, mon, t, i === selected ? " is-selected" : "", true); });
        if (preview) segment(bars, mon, preview, " is-preview", false);
        if (selected >= 0 && trips[selected]) {
          handleAt(bars, mon, trips[selected].start, "start");
          handleAt(bars, mon, trips[selected].end, "end");
        }
      });
    }

    // ---- dragging a trip end ---------------------------------------------------
    // Pointer events cover mouse and touch alike. The handle refuses scrolling
    // (touch-action: none), the window scrolls itself near its edges, and the
    // day under the pointer is found by hit-testing, so a drag can cross weeks.
    var lastPoint = null, autoScroll = 0;
    function dayUnder(x, y) {
      var node = document.elementFromPoint(x, y);
      var b = node && node.closest && node.closest(".cal-day");
      return b && weeksBox.contains(b) ? +b.getAttribute("data-day") : null;
    }
    function startDrag(e) {
      if (selected < 0) return;
      e.preventDefault(); e.stopPropagation();
      var t = trips[selected], end = e.currentTarget.getAttribute("data-end");
      drag = { trip: t, fixed: end === "start" ? t.end : t.start };
      lastPoint = { x: e.clientX, y: e.clientY };
      root.classList.add("is-dragging");
      window.addEventListener("pointermove", moveDrag);
      window.addEventListener("pointerup", endDrag);
      window.addEventListener("pointercancel", endDrag);
    }
    function applyDrag() {
      var day = dayUnder(lastPoint.x, lastPoint.y);
      if (day == null) return;
      var t = drag.trip, a = Math.min(drag.fixed, day), z = Math.max(drag.fixed, day);
      if (a === t.start && z === t.end) return;
      if (a === z && !rule.singleDayTrips) return;
      t.start = a; t.end = z;
      paint();
    }
    function moveDrag(e) {
      if (!drag) return;
      e.preventDefault();
      lastPoint = { x: e.clientX, y: e.clientY };
      applyDrag();
      var box = win.getBoundingClientRect(), edge = 44;
      var speed = e.clientY < box.top + head.offsetHeight + edge ? -1 : e.clientY > box.bottom - edge ? 1 : 0;
      if (speed && !autoScroll) scrollLoop(speed);
      autoScroll = speed;
    }
    function scrollLoop() {
      if (!drag || !autoScroll) { autoScroll = 0; return; }
      win.scrollTop += autoScroll * 8;
      applyDrag();
      requestAnimationFrame(scrollLoop);
    }
    function endDrag() {
      if (!drag) return;
      var t = drag.trip;
      drag = null; autoScroll = 0;
      root.classList.remove("is-dragging");
      window.removeEventListener("pointermove", moveDrag);
      window.removeEventListener("pointerup", endDrag);
      window.removeEventListener("pointercancel", endDrag);
      place(t, t.start, t.end);
      normalise();
      selected = tripAt(t.start);
      render();
    }

    function paint() {
      Object.keys(cells).forEach(function (k) {
        var day = +k, b = cells[k], i = tripAt(day);
        b.classList.toggle("has-trip", i >= 0);
        b.classList.toggle("is-anchor", day === anchor);
        b.setAttribute("aria-pressed", i >= 0 ? "true" : "false");
        b.setAttribute("aria-label", label(day) + (i >= 0 ? ", " + S.inTrip : "") + (day === anchor ? ", " + S.pending : ""));
      });
      drawBars();
      hint.textContent = selected >= 0 ? text("hintSelected")
        : anchor != null ? text("hintEnd", { date: label(anchor) })
        : text("hintStart");
    }

    // ---- trips list ---------------------------------------------------------------
    // Each card: the flag, the country (or a field to add one), the dates and
    // the count. Tapping a card selects its trip; the selected card offers Delete.
    function fold(s) { return String(s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase(); }
    var catalogue = null;
    function places() {
      if (!catalogue) catalogue = allowed.map(function (c) {
        var name = placeName(c), en = englishNames ? (englishNames.of(c) || "") : "";
        return { code: c, name: name, key: fold(name + " " + en + " " + c) };
      }).sort(function (a, b) { return a.name.localeCompare(b.name, locale); });
      return catalogue;
    }
    function matches(query) {
      var q = fold(query.trim());
      if (!q) {
        var picked = recent.map(function (c) { return places().filter(function (p) { return p.code === c; })[0]; }).filter(Boolean);
        return picked.length ? picked : places().slice(0, 8);
      }
      // Best first: the name starts with what was typed, then a word in it
      // does (or the English name or the code), then it appears anywhere.
      var lead = [], word = [], rest = [];
      places().forEach(function (p) {
        var at = p.key.indexOf(q);
        if (at < 0) return;
        (at === 0 ? lead : p.key.charAt(at - 1) === " " ? word : rest).push(p);
      });
      return lead.concat(word, rest).slice(0, 8);
    }
    function flagImg(code, size) {
      return el("img", { src: FLAGS + code.toLowerCase() + ".png", alt: "", width: String(size), height: String(Math.round(size * 0.75)), loading: "lazy" });
    }
    function countryField(idx, current) {
      var wrap = el("div", { "class": "cal-country-field" });
      var input = el("input", { type: "text", "class": "cal-country-input", placeholder: text("addCountry"), "aria-label": text("country"), autocomplete: "off", spellcheck: "false", role: "combobox", "aria-expanded": "false", "aria-autocomplete": "list" });
      if (current) input.value = placeName(current);
      var box = el("ul", { "class": "cal-country-list", role: "listbox", hidden: "" });
      var options = [], active = 0;
      function choose(code) {
        trips[idx].country = code;
        recent = [code].concat(recent.filter(function (c) { return c !== code; })).slice(0, 3);
        commit();
      }
      function show() {
        options = matches(current && input.value === placeName(current) ? "" : input.value);
        active = 0;
        box.textContent = "";
        if (!options.length) box.appendChild(el("li", { "class": "cal-country-none" }, text("noMatch")));
        options.forEach(function (p, i) {
          var li = el("li", { role: "option", "class": "cal-country-option" + (i === active ? " is-active" : "") });
          li.appendChild(flagImg(p.code, 20));
          li.appendChild(el("span", null, p.name));
          li.addEventListener("mousedown", function (e) { e.preventDefault(); choose(p.code); });
          box.appendChild(li);
        });
        box.hidden = false;
        input.setAttribute("aria-expanded", "true");
      }
      function mark() { Array.prototype.forEach.call(box.children, function (li, i) { li.classList.toggle("is-active", i === active); }); }
      input.addEventListener("focus", function () { if (current) input.select(); show(); });
      input.addEventListener("input", show);
      input.addEventListener("blur", function () { box.hidden = true; input.setAttribute("aria-expanded", "false"); if (current) input.value = placeName(current); });
      input.addEventListener("keydown", function (e) {
        if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); if (!options.length) return; active = (active + (e.key === "ArrowDown" ? 1 : options.length - 1)) % options.length; mark(); }
        else if (e.key === "Enter") { e.preventDefault(); if (options[active]) choose(options[active].code); }
        else if (e.key === "Escape") { input.blur(); }
      });
      input.addEventListener("click", function (e) { e.stopPropagation(); });
      wrap.appendChild(input);
      wrap.appendChild(box);
      return wrap;
    }
    function renderList() {
      list.textContent = "";
      // Import sits in the Trips card and shows once there is something to import.
      var rowsOut = trips.length ? rule.exportRows(trips, ctx()).length : 0;
      root.querySelectorAll("[data-cal-import]").forEach(function (btn) { btn.hidden = !rowsOut; });
      if (!trips.length) { list.appendChild(el("p", { "class": "cal-empty" }, S.empty)); return; }
      trips.forEach(function (t, idx) {
        var isSel = idx === selected;
        var card = el("div", { "class": "cal-trip" + (isSel ? " is-selected" : "") });
        var flag = el("span", { "class": "cal-flag" + (t.country ? "" : " is-empty") });
        if (t.country) flag.appendChild(flagImg(t.country, 28));
        card.appendChild(flag);
        var name = el("div", { "class": "cal-trip-country" });
        if (allowed.length < 2) name.appendChild(el("span", null, placeName(t.country)));
        else name.appendChild(countryField(idx, t.country));
        card.appendChild(name);
        var line = el("div", { "class": "cal-trip-line" });
        line.appendChild(el("span", { "class": "cal-trip-dates" }, dateRange(t.start, t.end)));
        line.appendChild(el("span", { "class": "cal-trip-count" }, rule.tripLabel(t, ctx())));
        card.appendChild(line);
        if (isSel) {
          var del = el("button", { type: "button", "class": "cal-delete" }, S.deleteTrip);
          del.addEventListener("click", function (e) { e.stopPropagation(); removeTrip(idx); });
          card.appendChild(del);
        }
        card.addEventListener("click", function (e) {
          if (e.target.closest(".cal-country-field")) return;
          selected = isSel ? -1 : idx;
          anchor = null;
          refresh();
          if (!isSel && finePointer) reveal(t.start - 7);
        });
        list.appendChild(card);
      });
    }

    function renderResult() {
      var r = rule.evaluate(trips, ctx());
      result.textContent = "";
      if (r.controls && r.controls.length) {
        var bar = el("div", { "class": "cal-controls" });
        r.controls.forEach(function (ctl) {
          var wrap = el("label", { "class": "cal-control" });
          if (ctl.prefix) wrap.appendChild(el("span", { "class": "cal-control-prefix" }, ctl.prefix));
          var pick = el("select", { "aria-label": ctl.label || ctl.prefix || "" });
          var groups = {};
          ctl.options.forEach(function (o) {
            var parent = pick;
            if (o.group) {
              if (!groups[o.group]) { groups[o.group] = el("optgroup", { label: o.group }); pick.appendChild(groups[o.group]); }
              parent = groups[o.group];
            }
            var opt = el("option", { value: o.value }, o.label);
            if (o.value === ctl.value) opt.selected = true;
            parent.appendChild(opt);
          });
          pick.addEventListener("change", function () {
            settings[ctl.key] = pick.value;
            var moved = rule.fixedRange && ctl.moveCalendar;
            render();
            if (moved) { var rr = rule.range(ctx()); reveal(today >= rr.from && today <= rr.to ? today - 21 : rr.from); updateMonth(); }
          });
          wrap.appendChild(pick);
          bar.appendChild(wrap);
        });
        result.appendChild(bar);
      }
      if (r.headlineText != null) {
        var head = el("div", { "class": "cal-result-head" });
        head.appendChild(el("p", { "class": "cal-headline" }, r.headlineText));
        if (r.statusText) head.appendChild(el("span", { "class": "cal-status " + (r.ok ? "is-ok" : "is-over") }, r.statusText));
        result.appendChild(head);
        (r.lines || []).forEach(function (line) { result.appendChild(el("p", { "class": "cal-line" }, line)); });
        return;
      }
      var top = el("div", { "class": "cal-result-head" });
      top.appendChild(el("p", { "class": "cal-headline" }, text(r.total ? "headline" : "headlineEmpty", { n: r.total })));
      if (r.status) top.appendChild(el("span", { "class": "cal-status " + (r.ok ? "is-ok" : "is-over") }, text(r.status, { n: r.remaining })));
      result.appendChild(top);
      result.appendChild(el("p", { "class": "cal-line" }, r.total ? text("worstWindow", { from: label(r.from), to: label(r.to) }) : text("emptyResult")));
    }

    function render() { build(); paint(); renderList(); renderResult(); updateMonth(); }

    // ---- scrolling ---------------------------------------------------------------
    function band() {
      var top = win.scrollTop + head.offsetHeight;
      return { top: top, bottom: win.scrollTop + win.clientHeight };
    }
    function topDay() {
      var b = band();
      for (var i = 0; i < rows.length; i++) if (rows[i].offsetTop + rows[i].offsetHeight > b.top + 2) return +rows[i].dataset.monday;
      return today;
    }
    function reveal(day) {
      var row = rows[Math.floor((D.monday(day) - firstMonday) / 7)];
      if (row) win.scrollTop = Math.max(0, row.offsetTop - head.offsetHeight);
    }
    // The title names the latest month that is completely in view, so it
    // changes as soon as a whole month has scrolled in from below; when no
    // month fits, the one with the most days in view.
    function updateMonth() {
      if (!rows.length) return;
      var b = band(), seen = {}, i;
      for (i = 0; i < rows.length; i++) {
        var r = rows[i], top = r.offsetTop, bottom = top + r.offsetHeight;
        if (bottom <= b.top || top >= b.bottom) continue;
        var full = top >= b.top - 1 && bottom <= b.bottom + 1;
        for (var c = 0; c < 7; c++) {
          var day = +r.dataset.monday + c, k = D.monthKey(day);
          seen[k] = seen[k] || { days: 0, full: 0 };
          seen[k].days++;
          if (full) seen[k].full++;
        }
      }
      var keys = Object.keys(seen).map(Number).sort(function (a, z) { return a - z; }), pick = null;
      keys.forEach(function (k) {
        var len = D.monthEnd(k) - D.monthStart(k) + 1;
        if (seen[k].full >= len) pick = k;
      });
      if (pick == null) keys.forEach(function (k) { if (pick == null || seen[k].days > seen[pick].days) pick = k; });
      if (pick === activeMonth) return;
      activeMonth = pick;
      monthTitle.textContent = monthDate.format(new Date(D.monthStart(pick) * DAY));
      Object.keys(cells).forEach(function (k) { cells[k].classList.toggle("is-other-month", D.monthKey(+k) !== pick); });
    }

    // ---- import into AtlasDays -----------------------------------------------------
    function csvField(v) { v = String(v == null ? "" : v); return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }
    function downloadCsv() {
      var lines = ["Country,Start Date,End Date,Notes"].concat(rule.exportRows(trips, ctx()).map(function (r) {
        return [r.country, D.iso(r.start), r.end == null ? "" : D.iso(r.end), r.notes || ""].map(csvField).join(",");
      }));
      var a = el("a", { href: URL.createObjectURL(new Blob([lines.join("\r\n") + "\r\n"], { type: "text/csv;charset=utf-8" })), download: S.fileName });
      document.body.appendChild(a); a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
    }

    // ---- events ------------------------------------------------------------------------
    weeksBox.addEventListener("click", function (e) {
      if (e.target.closest(".cal-handle")) return;
      var b = e.target.closest(".cal-day");
      if (b) tap(+b.getAttribute("data-day"));
    });
    weeksBox.addEventListener("mouseover", function (e) {
      if (anchor == null || !finePointer) return;
      var b = e.target.closest(".cal-day"), d = b ? +b.getAttribute("data-day") : null;
      if (d != null && d !== hover) { hover = d; drawBars(); }
    });
    weeksBox.addEventListener("keydown", function (e) {
      var b = e.target.closest(".cal-day");
      if (!b) return;
      var step = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[e.key];
      var next = step && cells[+b.getAttribute("data-day") + step];
      if (next) {
        e.preventDefault(); next.focus();
        if (anchor != null) { hover = +next.getAttribute("data-day"); drawBars(); }
      }
    });
    root.addEventListener("keydown", function (e) {
      if (e.target.closest && e.target.closest("input, select, textarea")) return;
      if (e.key === "Escape" && (anchor != null || selected >= 0)) { anchor = null; hover = null; selected = -1; refresh(); }
      else if ((e.key === "Delete" || e.key === "Backspace") && selected >= 0) { e.preventDefault(); removeTrip(selected); }
    });
    // Tapping anywhere but a trip card, a day or the import dialog lets go of
    // the selected trip (days and cards handle their own taps).
    document.addEventListener("pointerdown", function (e) {
      if (selected < 0) return;
      var t = e.target;
      if (t.closest && t.closest(".cal-trip, .cal-week, .cal-dialog")) return;
      selected = -1;
      refresh();
    });
    win.addEventListener("scroll", updateMonth, { passive: true });
    root.querySelectorAll("[data-cal-import]").forEach(function (btn) {
      btn.addEventListener("click", function () { if (dialog && dialog.showModal) dialog.showModal(); else downloadCsv(); });
    });
    root.querySelectorAll("[data-cal-download]").forEach(function (btn) { btn.addEventListener("click", downloadCsv); });
    root.querySelectorAll("[data-cal-close]").forEach(function (btn) { btn.addEventListener("click", function () { dialog.close(); }); });
    if (dialog) dialog.addEventListener("click", function (e) { if (e.target === dialog) dialog.close(); });

    render();
    var start = rule.range(ctx());
    reveal(today >= start.from && today <= start.to ? today - 21 : start.from);
    updateMonth();
  }

  // mount(root) lets a host page start a calendar it adds later (or inside a
  // shadow root, which the automatic scan below cannot see).
  window.AtlasDaysCalendar = { D: D, label: label, plural: plural, mount: DayCalendar };
  document.querySelectorAll("[data-day-calendar]").forEach(DayCalendar);
})();
