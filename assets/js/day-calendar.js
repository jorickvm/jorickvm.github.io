/* AtlasDays day calendar: the reusable engine behind the rule calculators on
   the Learn pages (UK absence today, Schengen 90/180 and others later).

   It draws the app's own calendar: one continuous column of week rows, the
   month name on the 1st, today as an accent pill, and each trip as a single
   rounded bar under the day numbers. Tap two days to add a trip; the trips
   list and the outcome update at once. Deliberately small: anything beyond a
   quick check is what the app is for.

   A rule plugs in through window.AtlasDaysRules[name]:
     settings(root)          read the page's controls (rule choice, application date)
     range(ctx)              { from, to } day numbers the calendar must cover
     travelDaysCount         false: bars start and end mid-day on travel days (UK
                             whole-days-away rules); true: full days (Schengen)
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
    parse: function (text) {
      var m = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(String(text || "").trim());
      return m ? D.fromParts(+m[1], +m[2], +m[3]) : null;
    },
    parts: function (n) { var d = new Date(n * DAY); return { y: d.getUTCFullYear(), m: d.getUTCMonth(), d: d.getUTCDate(), w: d.getUTCDay() }; },
    iso: function (n) { return new Date(n * DAY).toISOString().slice(0, 10); },
    today: function () { var n = new Date(); return D.fromParts(n.getFullYear(), n.getMonth() + 1, n.getDate()); },
    shiftYears: function (n, years) {
      var p = D.parts(n), y = p.y + years, last = new Date(Date.UTC(y, p.m + 1, 0)).getUTCDate();
      return Math.round(Date.UTC(y, p.m, Math.min(p.d, last)) / DAY);
    },
    monday: function (n) { return n - (D.parts(n).w + 6) % 7; }
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
    var undoBtn = $("[data-cal-undo]"), download = $("[data-cal-download]");

    var today = D.today();
    var trips = [], pending = null, hover = null, history = [], openTrip = -1;
    var rows = [], cells = {}, firstMonday = 0;

    function ctx() { return { today: today, settings: rule.settings(root, trips, today), D: D, label: label, plural: plural }; }

    // ---- trips: the tap rules ----------------------------------------------
    function tripAt(day) {
      for (var i = 0; i < trips.length; i++) if (day >= trips[i].start && day <= trips[i].end) return i;
      return -1;
    }
    function snapshot() { history.push(JSON.stringify(trips)); if (history.length > 100) history.shift(); }
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
    function tap(day) {
      var i = tripAt(day);
      openTrip = -1;
      if (pending == null) {
        if (i < 0) { pending = day; paint(); return; }
        // A tap inside a trip shortens it from the nearest end (the end when central).
        snapshot();
        var t = trips[i];
        if (t.start === t.end) trips.splice(i, 1);
        else if (day === t.start) t.start += 1;
        else if (day === t.end) t.end -= 1;
        else if (day - t.start < t.end - day) t.start = day;
        else t.end = day;
        commit();
        return;
      }
      if (day === pending) { pending = null; hover = null; paint(); return; }
      snapshot();
      var span = i >= 0 ? trips[i] : { start: day, end: day, country: "" };
      if (i < 0) trips.push(span);
      // A range that reaches into a trip extends it, and absorbs any trip it covers.
      span.start = Math.min(span.start, pending, day);
      span.end = Math.max(span.end, pending, day);
      trips = trips.filter(function (t) {
        if (t === span || t.end < span.start || t.start > span.end) return true;
        span.start = Math.min(span.start, t.start); span.end = Math.max(span.end, t.end);
        return false;
      });
      pending = null; hover = null;
      commit();
    }
    function commit() { normalise(); render(); }

    // ---- the calendar: continuous week rows ----------------------------------
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
      if (anchor != null) reveal(anchor);
    }

    // One bar per trip per week. On whole-days-away rules the bar starts and
    // ends halfway through the travel days, as in the app; that is also how
    // those rules count them.
    function drawBars() {
      var half = !rule.travelDaysCount;
      var ranges = trips.map(function (t) { return { start: t.start, end: t.end, cls: "" }; });
      if (pending != null) {
        var h = hover == null ? pending : hover;
        ranges.push({ start: Math.min(pending, h), end: Math.max(pending, h), cls: " is-preview" });
      }
      rows.forEach(function (row) {
        var mon = +row.dataset.monday, sun = mon + 6, bars = row.lastChild;
        bars.textContent = "";
        ranges.forEach(function (t) {
          if (t.end < mon || t.start > sun) return;
          var a = Math.max(t.start, mon), z = Math.min(t.end, sun), single = t.start === t.end;
          var left = (a - mon) + (half && a === t.start && !single ? 0.5 : 0);
          var right = (z - mon + 1) - (half && z === t.end && !single ? 0.5 : 0);
          var bar = el("span", { "class": "cal-bar" + t.cls + (a === t.start ? " starts" : "") + (z === t.end ? " ends" : "") });
          bar.style.left = (left / 7 * 100) + "%";
          bar.style.width = ((right - left) / 7 * 100) + "%";
          bars.appendChild(bar);
        });
      });
    }

    function paint() {
      Object.keys(cells).forEach(function (k) {
        var day = +k, b = cells[k], i = tripAt(day);
        b.classList.toggle("has-trip", i >= 0);
        b.classList.toggle("is-pending", day === pending);
        b.setAttribute("aria-pressed", i >= 0 ? "true" : "false");
        b.setAttribute("aria-label", label(day) + (i >= 0 ? ", " + S.inTrip : "") + (day === pending ? ", " + S.pending : ""));
      });
      drawBars();
      hint.textContent = pending == null ? S.hintStart : S.hintEnd.replace("{date}", label(pending));
      if (undoBtn) undoBtn.hidden = !history.length;
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
        main.addEventListener("click", function () { openTrip = open ? -1 : idx; renderList(); if (!open) reveal(t.start); });
        card.appendChild(main);
        if (open) {
          var del = el("button", { type: "button", "class": "cal-delete" }, S.deleteTrip);
          del.addEventListener("click", function () { snapshot(); trips.splice(idx, 1); openTrip = -1; commit(); });
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
      top.appendChild(el("span", { "class": "cal-status " + (r.ok ? "is-ok" : "is-over") }, r.status));
      result.appendChild(top);
      (r.lines || []).forEach(function (line) { result.appendChild(el("p", { "class": "cal-line" }, line)); });
    }

    function render() { build(); paint(); renderList(); renderResult(); updateMonth(); }

    // ---- scrolling: sticky month title, open at this week --------------------
    function topDay() {
      var y = win.scrollTop + head.offsetHeight + 2;
      for (var i = 0; i < rows.length; i++) if (rows[i].offsetTop + rows[i].offsetHeight > y) return +rows[i].dataset.monday;
      return today;
    }
    function reveal(day) {
      var row = rows[Math.floor((D.monday(day) - firstMonday) / 7)];
      if (row) win.scrollTop = Math.max(0, row.offsetTop - head.offsetHeight - 6);
    }
    function updateMonth() {
      var p = D.parts(topDay() + 3);
      monthTitle.textContent = MONTHS[p.m] + " " + p.y;
    }

    // ---- CSV for AtlasDays -----------------------------------------------------
    function csvField(v) { v = String(v == null ? "" : v); return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }
    function downloadCsv() {
      var lines = ["Country,Start Date,End Date,Notes"].concat(rule.exportRows(trips, ctx()).map(function (r) {
        return [r.country, D.iso(r.start), r.end == null ? "" : D.iso(r.end), r.notes || ""].map(csvField).join(",");
      }));
      var a = el("a", { href: URL.createObjectURL(new Blob([lines.join("\r\n") + "\r\n"], { type: "text/csv;charset=utf-8" })), download: S.fileName });
      document.body.appendChild(a); a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
    }

    // ---- events ----------------------------------------------------------------
    weeksBox.addEventListener("click", function (e) {
      var b = e.target.closest(".cal-day");
      if (b) tap(+b.getAttribute("data-day"));
    });
    weeksBox.addEventListener("mouseover", function (e) {
      if (pending == null) return;
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
        if (pending != null) { hover = +next.getAttribute("data-day"); drawBars(); }
      } else if (e.key === "Escape" && pending != null) { pending = null; hover = null; paint(); }
    });
    win.addEventListener("scroll", updateMonth, { passive: true });
    if (undoBtn) undoBtn.addEventListener("click", function () {
      if (!history.length) return;
      trips = JSON.parse(history.pop()); pending = null; openTrip = -1; commit();
    });
    if (download) download.addEventListener("click", downloadCsv);
    root.querySelectorAll("[data-cal-setting]").forEach(function (n) {
      // A setting the reader changes is theirs from then on; until then the
      // rule may keep it in step with the trips (the application date does).
      n.addEventListener("change", function () { n.dataset.userSet = "1"; render(); });
    });

    render();
    reveal(today - 21);
    updateMonth();
  }

  window.AtlasDaysCalendar = { D: D, label: label, plural: plural };
  document.querySelectorAll("[data-day-calendar]").forEach(DayCalendar);
})();
