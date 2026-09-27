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
     travelDaysCount         false: bars start and end mid-day on travel days
                             (whole-days-away rules); true: full days (Schengen)
     singleDayTrips          true when a one-day trip counts for the rule
     evaluate(trips, ctx)    { ok, status, headline, lines: [text] }
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
  var MONTHS = ["January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December"];
  function label(n) { var p = D.parts(n); return p.d + " " + MONTHS[p.m] + " " + p.y; }
  function short(n, withYear) { var p = D.parts(n); return p.d + " " + MONTHS[p.m].slice(0, 3) + (withYear ? " " + p.y : ""); }
  function plural(n, one, many) { return n + " " + (n === 1 ? one : many); }
  function el(tag, attrs, text) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { if (attrs[k] != null) node.setAttribute(k, attrs[k]); });
    if (text != null) node.textContent = text;
    return node;
  }

  function DayCalendar(root) {
    var rule = (window.AtlasDaysRules || {})[root.getAttribute("data-day-calendar")];
    if (!rule) return;
    var S = rule.strings || {};
    var $ = function (sel) { return root.querySelector(sel); };
    var win = $("[data-cal-window]"), head = $(".cal-head"), weeksBox = $("[data-cal-weeks]"), monthTitle = $("[data-cal-month]");
    var hint = $("[data-cal-hint]"), list = $("[data-cal-list]"), result = $("[data-cal-result]");
    var dialog = $("[data-cal-dialog]");

    var today = D.today();
    var trips = [], pending = null, handle = null, hover = null, openTrip = -1;
    var rows = [], cells = {}, firstMonday = 0, activeMonth = null;

    function ctx() { return { today: today, D: D, label: label, plural: plural }; }

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
        if (last && t.start < last.end) last.end = Math.max(last.end, t.end);
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
        return false;
      });
    }
    function tap(day) {
      openTrip = -1;
      if (handle) {
        var t = trips[handle.index], fixed = handle.end === "start" ? t.end : t.start;
        var moved = handle.end === "start" ? t.start : t.end;
        handle = null; hover = null;
        if (day === moved) { paint(); return; }          // put it down unchanged
        place(t, fixed, day);
        return commit();
      }
      var i = tripAt(day);
      if (pending != null) {
        var from = pending;
        pending = null; hover = null;
        if (day === from) {
          if (rule.singleDayTrips) { trips.push({ start: day, end: day, country: "" }); return commit(); }
          return paint();
        }
        var span = i >= 0 ? trips[i] : { start: day, end: day, country: "" };
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
          b.appendChild(el("span", { "class": "cal-num" }, p.d === 1 ? MONTHS[p.m].slice(0, 3).toUpperCase() : String(p.d)));
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

    // One bar per trip per week. On whole-days-away rules the bar starts and
    // ends halfway through the travel days, as in the app; that is also how
    // those rules count them.
    function previewRange() {
      if (handle && hover != null) {
        var t = trips[handle.index];
        return [handle.end === "start" ? t.end : t.start, hover];
      }
      if (pending != null) return [pending, hover == null ? pending : hover];
      return null;
    }
    function drawBars() {
      var half = !rule.travelDaysCount;
      var ranges = trips.map(function (t, i) {
        return handle && hover != null && handle.index === i ? null : { start: t.start, end: t.end, cls: "" };
      }).filter(Boolean);
      var pv = previewRange();
      if (pv) ranges.push({ start: Math.min(pv[0], pv[1]), end: Math.max(pv[0], pv[1]), cls: " is-preview" });
      rows.forEach(function (row) {
        var mon = +row.dataset.monday, sun = mon + 6, bars = row.lastChild;
        bars.textContent = "";
        ranges.forEach(function (t) {
          if (t.end < mon || t.start > sun) return;
          var a = Math.max(t.start, mon), z = Math.min(t.end, sun), single = t.start === t.end;
          var left = (a - mon) + (half && a === t.start && !single ? 0.5 : 0);
          var right = (z - mon + 1) - (half && z === t.end && !single ? 0.5 : 0);
          var bar = el("span", { "class": "cal-bar" + t.cls + (a === t.start ? " starts" : "") + (z === t.end ? " ends" : "") });
          bar.style.left = "calc(" + (left / 7 * 100) + "% + " + (a === t.start ? 2 : 0) + "px)";
          bar.style.width = "calc(" + ((right - left) / 7 * 100) + "% - " + ((a === t.start ? 2 : 0) + (z === t.end ? 2 : 0)) + "px)";
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

    function renderList() {
      list.textContent = "";
      if (!trips.length) { list.appendChild(el("p", { "class": "cal-empty" }, S.empty)); return; }
      trips.forEach(function (t, idx) {
        var open = idx === openTrip;
        var card = el("div", { "class": "cal-trip" + (open ? " is-open" : "") });
        var main = el("button", { type: "button", "class": "cal-trip-main", "aria-expanded": open ? "true" : "false" });
        var sameYear = D.parts(t.start).y === D.parts(t.end).y;
        main.appendChild(el("span", { "class": "cal-trip-dates" }, short(t.start, !sameYear) + " – " + short(t.end, true)));
        main.appendChild(el("span", { "class": "cal-trip-count" }, rule.tripLabel(t, ctx())));
        main.addEventListener("click", function () { openTrip = open ? -1 : idx; renderList(); if (!open) reveal(t.start - 7); });
        card.appendChild(main);
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
      top.appendChild(el("p", { "class": "cal-headline" }, r.headline));
      if (r.status) top.appendChild(el("span", { "class": "cal-status " + (r.ok ? "is-ok" : "is-over") }, r.status));
      result.appendChild(top);
      (r.lines || []).forEach(function (line) { result.appendChild(el("p", { "class": "cal-line" }, line)); });
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
      monthTitle.textContent = MONTHS[pick % 12] + " " + Math.floor(pick / 12);
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
    weeksBox.addEventListener("mouseover", function (e) {
      if (pending == null && !handle) return;
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
        if (pending != null || handle) { hover = +next.getAttribute("data-day"); drawBars(); }
      } else if (e.key === "Escape" && (pending != null || handle)) { pending = null; handle = null; hover = null; paint(); }
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

  window.AtlasDaysCalendar = { D: D, label: label, plural: plural };
  document.querySelectorAll("[data-day-calendar]").forEach(DayCalendar);
})();
