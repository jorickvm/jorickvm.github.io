/* AtlasDays day calendar: the reusable engine behind the rule calculators on
   the Learn pages (UK ILR absences today, Schengen 90/180 and others later).

   It draws the app's own calendar: one continuous column of week rows, the
   month name on the 1st, today as an accent pill, each trip as one rounded
   bar under the day numbers, a faint disc on days without a trip. Days
   outside the month in view are dimmed, as in the app. Deliberately small:
   one rule per page, and anything beyond a quick check is what the app is for.

   Tapping, as designed with Jorick:
     - tap an empty day, then another: a new trip, in either order
     - tap a trip's first or last day: that end is picked up; the next tap
       moves it there (later extends, earlier shortens); tap it again to
       put it down unchanged
     - tap inside a trip: it shortens from the nearest end (the end when central)
     - a new range that reaches into a trip extends that trip
     - tapping the pending day again cancels, or makes a one-day trip when the
       rule counts single days (rule.singleDayTrips)

   A rule plugs in through window.AtlasDaysRules[name]:
     range(ctx)              { from, to } day numbers the calendar must cover
     travelDaysCount         whether the rule counts travel days (informational;
                             bars always cover both end days)
     singleDayTrips          true when a one-day trip counts for the rule
     evaluate(trips, ctx)    { ok, total, remaining, status, from, to }
     tripLabel(trip, ctx)    short text for a trip in the list
     exportRows(trips, ctx)  rows for the AtlasDays CSV import
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
    if (a === b) return rangeFormat.format(new Date(a * DAY));
    if (!rangeFormat.formatRange) return short(a, true) + " – " + short(b, true);
    return rangeFormat.formatRange(new Date(a * DAY), new Date(b * DAY));
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
    var trips = [], pending = null, handle = null, openTrip = -1;
    var allowed = (rule.countries && rule.countries(PLACES)) || PLACES;
    var defaultCountry = allowed.length === 1 ? allowed[0] : (rule.defaultCountry || "");
    var rows = [], cells = {}, firstMonday = 0, activeMonth = null;

    function ctx() { return { today: today, D: D, label: label, plural: plural, text: text }; }

    // ---- trips -----------------------------------------------------------------
    function tripAt(day) {
      for (var i = 0; i < trips.length; i++) if (day >= trips[i].start && day <= trips[i].end) return i;
      return -1;
    }
    function normalise() {
      trips.sort(function (a, b) { return a.start - b.start; });
      var out = [];
      trips.forEach(function (t) {
        var last = out[out.length - 1];
        // Trips sharing a night merge; a shared travel day alone does not.
        if (last && t.start < last.end) { last.end = Math.max(last.end, t.end); if (!last.country) last.country = t.country || ""; }
        else out.push({ start: t.start, end: t.end, country: t.country || "" });
      });
      trips = out;
    }
    // Set a trip to [a, b] and let it absorb every trip it now overlaps.
    function place(span, a, b) {
      span.start = Math.min(a, b); span.end = Math.max(a, b);
      trips = trips.filter(function (t) {
        if (t === span || t.end < span.start || t.start > span.end) return true;
        span.start = Math.min(span.start, t.start); span.end = Math.max(span.end, t.end);
        if (!span.country) span.country = t.country || "";
        return false;
      });
    }
    function tap(day) {
      openTrip = -1;
      if (handle) {
        var t = trips[handle.index], fixed = handle.end === "start" ? t.end : t.start;
        var moved = handle.end === "start" ? t.start : t.end;
        handle = null;
        if (day === moved) { paint(); return; }          // put it down unchanged
        place(t, fixed, day);
        return commit();
      }
      var i = tripAt(day);
      if (pending != null) {
        var from = pending;
        pending = null;
        if (day === from) {
          if (rule.singleDayTrips) { trips.push({ start: day, end: day, country: defaultCountry }); return commit(); }
          return paint();
        }
        var span = i >= 0 ? trips[i] : { start: day, end: day, country: defaultCountry };
        if (i < 0) trips.push(span);
        place(span, Math.min(span.start, from, day), Math.max(span.end, from, day));
        return commit();
      }
      if (i < 0) { pending = day; return paint(); }
      var trip = trips[i];
      if (day === trip.start || day === trip.end) {
        handle = { index: i, end: day === trip.end ? "end" : "start" };
        return paint();
      }
      if (day - trip.start < trip.end - day) trip.start = day; else trip.end = day;
      commit();
    }
    function commit() { normalise(); render(); }

    // ---- the calendar: continuous week rows ------------------------------------
    function build() {
      var r = rule.range(ctx()), from = r.from, to = r.to;
      trips.forEach(function (t) { from = Math.min(from, t.start); to = Math.max(to, t.end); });
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
          b.appendChild(el("span", { "class": "cal-num" }, p.d === 1 ? shortMonth.format(new Date(day * DAY)) : String(p.d)));
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
    // circle to the outer edge of the last day's, so both end days read as part
    // of the trip. How a rule counts the travel days lives in the rule, not in
    // the drawing. A day picked as the first end of a new trip (or an end
    // picked up to move) shows only as a light-blue circle; there is no preview.
    var DISC = 10; // half the width of a day circle, in px (see .cal-day::after)
    function drawBars() {
      rows.forEach(function (row) {
        var mon = +row.dataset.monday, sun = mon + 6, bars = row.lastChild;
        bars.textContent = "";
        trips.forEach(function (t) {
          if (t.end < mon || t.start > sun) return;
          var a = Math.max(t.start, mon), z = Math.min(t.end, sun);
          var starts = a === t.start, ends = z === t.end;
          var left = starts ? "calc(" + ((a - mon + 0.5) / 7 * 100) + "% - " + DISC + "px)" : "0px";
          var right = ends ? "calc(" + ((z - mon + 0.5) / 7 * 100) + "% + " + DISC + "px)" : "100%";
          var bar = el("span", { "class": "cal-bar" + (starts ? " starts" : "") + (ends ? " ends" : "") });
          bar.style.left = left;
          bar.style.width = "calc(" + right + " - " + left + ")";
          bars.appendChild(bar);
        });
      });
    }

    function paint() {
      var held = handle ? (handle.end === "start" ? trips[handle.index].start : trips[handle.index].end) : null;
      Object.keys(cells).forEach(function (k) {
        var day = +k, b = cells[k], i = tripAt(day);
        b.classList.toggle("has-trip", i >= 0);
        b.classList.toggle("is-pending", day === pending || day === held);
        b.setAttribute("aria-pressed", i >= 0 ? "true" : "false");
        b.setAttribute("aria-label", label(day) + (i >= 0 ? ", " + S.inTrip : "") + (day === pending ? ", " + S.pending : "") + (day === held ? ", " + S.held : ""));
      });
      drawBars();
      hint.textContent = handle ? S.hintMove.replace("{date}", label(held))
        : pending != null ? S.hintEnd.replace("{date}", label(pending))
        : S.hintStart;
    }

    // The flag is the country picker: a native select laid over the flag, so a
    // tap opens the system list. When the rule allows one country only, the
    // flag is fixed.
    function flagFor(t, idx) {
      var wrap = el("span", { "class": "cal-flag" + (t.country ? "" : " is-empty") });
      if (t.country) wrap.appendChild(el("img", { src: FLAGS + t.country.toLowerCase() + ".png", alt: "", width: "28", height: "21", loading: "lazy" }));
      if (allowed.length < 2) return wrap;
      var pick = el("select", { "class": "cal-flag-pick", "aria-label": (t.country ? placeName(t.country) + ", " : "") + text("country") });
      pick.appendChild(el("option", { value: "" }, text("country")));
      allowed.map(function (c) { return [placeName(c), c]; })
        .sort(function (a, b) { return a[0].localeCompare(b[0], locale); })
        .forEach(function (n) { var o = el("option", { value: n[1] }, n[0]); if (n[1] === t.country) o.selected = true; pick.appendChild(o); });
      pick.addEventListener("change", function () { trips[idx].country = pick.value; commit(); });
      wrap.appendChild(pick);
      return wrap;
    }
    function renderList() {
      list.textContent = "";
      // Import sits in the Trips card and shows once there is something to import.
      var rows = trips.length ? rule.exportRows(trips, ctx()).length : 0;
      root.querySelectorAll("[data-cal-import]").forEach(function (btn) { btn.hidden = !rows; });
      if (!trips.length) { list.appendChild(el("p", { "class": "cal-empty" }, S.empty)); return; }
      trips.forEach(function (t, idx) {
        var open = idx === openTrip;
        var card = el("div", { "class": "cal-trip" + (open ? " is-open" : "") });
        var row = el("div", { "class": "cal-trip-row" });
        row.appendChild(flagFor(t, idx));
        var main = el("button", { type: "button", "class": "cal-trip-main", "aria-expanded": open ? "true" : "false" });
        main.appendChild(el("span", { "class": "cal-trip-dates" }, dateRange(t.start, t.end)));
        main.appendChild(el("span", { "class": "cal-trip-count" }, rule.tripLabel(t, ctx())));
        main.addEventListener("click", function () { openTrip = open ? -1 : idx; renderList(); if (!open) reveal(t.start - 7); });
        row.appendChild(main);
        card.appendChild(row);
        if (open) {
          var del = el("button", { type: "button", "class": "cal-delete" }, S.deleteTrip);
          del.addEventListener("click", function () { trips.splice(idx, 1); openTrip = -1; handle = null; commit(); });
          card.appendChild(del);
        }
        list.appendChild(card);
      });
    }

    function renderResult() {
      var r = rule.evaluate(trips, ctx());
      result.textContent = "";
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
      var b = e.target.closest(".cal-day");
      if (b) tap(+b.getAttribute("data-day"));
    });
    weeksBox.addEventListener("keydown", function (e) {
      var b = e.target.closest(".cal-day");
      if (!b) return;
      var step = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[e.key];
      var next = step && cells[+b.getAttribute("data-day") + step];
      if (next) {
        e.preventDefault(); next.focus();
      } else if (e.key === "Escape" && (pending != null || handle)) { pending = null; handle = null; paint(); }
    });
    win.addEventListener("scroll", updateMonth, { passive: true });
    root.querySelectorAll("[data-cal-import]").forEach(function (btn) {
      btn.addEventListener("click", function () { if (dialog && dialog.showModal) dialog.showModal(); else downloadCsv(); });
    });
    root.querySelectorAll("[data-cal-download]").forEach(function (btn) { btn.addEventListener("click", downloadCsv); });
    root.querySelectorAll("[data-cal-close]").forEach(function (btn) { btn.addEventListener("click", function () { dialog.close(); }); });
    if (dialog) dialog.addEventListener("click", function (e) { if (e.target === dialog) dialog.close(); });

    render();
    reveal(today - 21);
    updateMonth();
  }

  // mount(root) lets a host page start a calendar it adds later (or inside a
  // shadow root, which the automatic scan below cannot see).
  window.AtlasDaysCalendar = { D: D, label: label, plural: plural, mount: DayCalendar };
  document.querySelectorAll("[data-day-calendar]").forEach(DayCalendar);
})();
