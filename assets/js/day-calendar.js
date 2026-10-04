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
     quietHint               optional: the hint floats in the calendar, the
                             idle one only while there are no trips, the others
                             only the first time
     fixedRange              optional: the calendar shows range() only, even
                             when a trip runs past it
     tripLabel(trip, ctx)    short text for a trip in the list
     exportRows(trips, ctx)  rows for the AtlasDays CSV import
     countries(all)          optional: the country codes a trip may have
                             (one code: the country is fixed, no picker)
     defaultCountry          optional: the country a new trip starts with
     carryCountry            optional: a new trip starts with the last country
                             picked
     linkId                  optional: the calculator's `c` in the import link
     strings                 labels shown by the engine

   "Track this in AtlasDays" opens the page's dialog, which shows one of its
   [data-cal-on] parts: "phone" on an iPhone or iPad, or inside the app's own
   browser (from=app), with [data-cal-open] linking the stays into the app;
   "computer" elsewhere, with a QR code of the same link in [data-cal-qr];
   "file" when there are too many stays for a link. The link format and its
   limits are owned by the app repo: AtlasDays/Docs/reference/IMPORT_LINK.md.

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
  // Line icons in the spirit of the app's SF Symbols (target, calendar,
  // calendar.badge.clock); SF Symbols themselves are licensed for Apple
  // platforms only, so these are drawn here.
  var ICONS = {
    trash: '<path d="M4.5 6h11M8 6V4.5h4V6M6 6l.7 9.5h6.6L14 6"/>',
    target: '<circle cx="10" cy="10" r="7.25"/><circle cx="10" cy="10" r="4"/><circle cx="10" cy="10" r="0.9" fill="currentColor"/>',
    calendar: '<rect x="3" y="4.5" width="14" height="12.5" rx="2.5"/><path d="M3 8.5h14M7 2.75v3M13 2.75v3"/>',
    starts: '<rect x="3" y="4.5" width="11" height="11" rx="2.5"/><path d="M3 8.5h11M6.5 2.75v3M10.5 2.75v3"/><circle cx="14.25" cy="14.25" r="3.6" fill="var(--bg-card)"/><path d="M14.25 12.6v1.8l1.2.8"/>',
    updown: '<path d="M6.5 7.5L10 4l3.5 3.5M6.5 12.5L10 16l3.5-3.5"/>'
  };
  function icon(name, cls) {
    var span = document.createElement("span");
    span.className = "cal-icon" + (cls ? " " + cls : "");
    span.setAttribute("aria-hidden", "true");
    span.innerHTML = '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' + ICONS[name] + '</svg>';
    return span;
  }
  var regionNames = null;
  try { regionNames = new Intl.DisplayNames([locale], { type: "region" }); } catch (e) {}
  function placeName(code) {
    if (code === "XK") return regionNames ? (regionNames.of("XK") || "Kosovo") : "Kosovo";
    if (code === "LL") return "Liberland";
    return (regionNames && regionNames.of(code)) || code;
  }
  var plurals = new Intl.PluralRules(locale);
  function dateFormat(options) { return new Intl.DateTimeFormat(locale, Object.assign({ timeZone: "UTC" }, options)); }
  // English pages write dates the British way, as the app does: 25 December 2026.
  var fullDate = new Intl.DateTimeFormat(locale === "en" ? "en-GB" : locale, { timeZone: "UTC", day: "numeric", month: "long", year: "numeric" });
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

  // ---- the import link (AtlasDays/Docs/reference/IMPORT_LINK.md) ----------------------
  var ENGINE_SRC = (document.currentScript && document.currentScript.src) || "";
  var LINK = { universal: "https://go.atlasdays.app/import/#", scheme: "atlasdays://import#", maxStays: 150, maxQrStays: 60 };
  var appleTouch = /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  // The app adds from=app to every atlasdays.app address it opens; a page one
  // tap further still sees it in its referrer. Kept for the browser session.
  var inApp = (function () {
    var seen = false, here = false, before = false;
    try { seen = sessionStorage.getItem("atlasdays-from") === "app"; } catch (e) {}
    try { here = new URLSearchParams(location.search).get("from") === "app"; } catch (e) {}
    try { var r = new URL(document.referrer); before = r.origin === location.origin && r.searchParams.get("from") === "app"; } catch (e) {}
    if (here || before) { seen = true; try { sessionStorage.setItem("atlasdays-from", "app"); } catch (e) {} }
    return seen;
  })();
  // v=1&c=183&b=2026-01-05&n=…&s=ES:0:19,PT:19:8: each stay is its country,
  // its first day counted from b, and its length in days after that day.
  function importFragment(rows, linkId) {
    var base = Math.min.apply(null, rows.map(function (r) { return r.start; }));
    var parts = ["v=1"];
    if (linkId) parts.push("c=" + encodeURIComponent(linkId));
    parts.push("b=" + D.iso(base));
    var note = rows.length && rows[0].notes;
    if (note && rows.every(function (r) { return r.notes === note; })) parts.push("n=" + encodeURIComponent(note.slice(0, 100)));
    parts.push("s=" + rows.map(function (r) {
      return String(r.country).toUpperCase() + ":" + (r.start - base) + ":" + (r.end == null ? "" : r.end - r.start);
    }).join(","));
    return parts.join("&");
  }
  function loadQr(done) {
    if (window.qrcode) return done();
    var s = document.createElement("script");
    s.src = ENGINE_SRC.replace(/day-calendar\.js(\?[^#]*)?$/, "vendor/qrcode-generator.js$1");
    s.onload = done;
    document.head.appendChild(s);
  }
  // Styled like the homepage's App Store code (Jorick's QR tool, 2026-10-03):
  // navy connected-rounded modules on light grey in both themes, rounded finder
  // eyes, the app icon in a cleared centre. Q error correction carries the icon;
  // on bigger codes the icon shrinks so the cleared area stays a small share.
  var QR = { dark: "#0a1420", light: "#ebebeb", quiet: 2, round: 0.9 };
  function qrSvg(text) {
    var q = window.qrcode(0, "Q");
    q.addData(text);
    q.make();
    // Past version 13 (69 modules), M error correction keeps the code a size
    // smaller; the icon is small enough there for M to carry it.
    if (q.getModuleCount() > 69) { q = window.qrcode(0, "M"); q.addData(text); q.make(); }
    var n = q.getModuleCount(), m = QR.quiet, total = n + 2 * m;
    var img = total * (n <= 45 ? 0.3 : n <= 69 ? 0.24 : 0.17), box = img * 1.12, at = (total - box) / 2, imgAt = (total - img) / 2;
    function finder(r, c) { return (r < 7 && c < 7) || (r < 7 && c >= n - 7) || (r >= n - 7 && c < 7); }
    function cleared(r, c) { var x = c + m + 0.5, y = r + m + 0.5; return x >= at && x <= at + box && y >= at && y <= at + box; }
    function on(r, c) { return r >= 0 && c >= 0 && r < n && c < n && q.isDark(r, c) && !finder(r, c) && !cleared(r, c); }
    // One cell, its corners rounded only where no neighbour touches them.
    function cell(x, y, tl, tr, br, bl) {
      return "M" + (x + tl) + " " + y + "H" + (x + 1 - tr) + (tr ? "Q" + (x + 1) + " " + y + " " + (x + 1) + " " + (y + tr) : "") +
        "V" + (y + 1 - br) + (br ? "Q" + (x + 1) + " " + (y + 1) + " " + (x + 1 - br) + " " + (y + 1) : "") +
        "H" + (x + bl) + (bl ? "Q" + x + " " + (y + 1) + " " + x + " " + (y + 1 - bl) : "") +
        "V" + (y + tl) + (tl ? "Q" + x + " " + y + " " + (x + tl) + " " + y : "") + "Z";
    }
    // Big codes have small modules on screen: softer rounding keeps them sharp.
    var rad = 0.5 * (n <= 69 ? QR.round : 0.4), d = "";
    for (var r = 0; r < n; r++) for (var c = 0; c < n; c++) {
      if (!on(r, c)) continue;
      var up = on(r - 1, c), right = on(r, c + 1), down = on(r + 1, c), left = on(r, c - 1);
      d += cell(c + m, r + m, !up && !left ? rad : 0, !up && !right ? rad : 0, !down && !right ? rad : 0, !down && !left ? rad : 0);
    }
    function rect(x, y, w, k, fill) { return '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + w + '" rx="' + w * k + '" fill="' + fill + '"/>'; }
    var eyes = "";
    [[m, m], [m + n - 7, m], [m, m + n - 7]].forEach(function (o) {
      eyes += rect(o[0], o[1], 7, 0.23, QR.dark) + rect(o[0] + 1, o[1] + 1, 5, 0.24, QR.light) + rect(o[0] + 2, o[1] + 2, 3, 0.28, QR.dark);
    });
    var icon = ENGINE_SRC.replace(/js\/day-calendar\.js(\?[^#]*)?$/, "brand/app-icon-qr.webp");
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + total + " " + total + '" role="img" aria-hidden="true">' +
      '<rect width="' + total + '" height="' + total + '" fill="' + QR.light + '"/>' +
      '<path d="' + d + '" fill="' + QR.dark + '"/>' + eyes + rect(at, at, box, 0.18, QR.light) +
      '<defs><clipPath id="cal-qr-icon"><rect x="' + imgAt + '" y="' + imgAt + '" width="' + img + '" height="' + img + '" rx="' + img * 0.22 + '"/></clipPath></defs>' +
      '<image href="' + icon + '" x="' + imgAt + '" y="' + imgAt + '" width="' + img + '" height="' + img + '" clip-path="url(#cal-qr-icon)"/></svg>';
  }

  // The code sits beside the steps at a compact size. On a 1x screen a big code
  // opens larger (about 4 px a module), because a camera cannot read it smaller.
  function sizeQr(box) {
    var modules = box.firstChild.viewBox.baseVal.width;
    box.style.width = Math.round(box.classList.contains("is-large")
      ? Math.min(492, Math.max(260, modules * 4.4))
      : Math.min(240, Math.max(200, modules * 3))) + "px";
    stackQr(box);
  }
  // When the steps no longer fit beside the code they go under it, and the
  // code moves in to line up with the text.
  function stackQr(box) {
    var scan = box.parentNode;
    scan.classList.remove("is-stacked");
    var stacked = scan.classList.contains("is-large") || scan.clientWidth < box.offsetWidth + 18 + 200;
    scan.classList.toggle("is-stacked", stacked);
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
    // A rule's choices (country, goal, period) sit in their own row above the
    // result card, so the card itself reads like the app's tracker card.
    var settingsRow = el("div", { "class": "cal-settings", hidden: "" });
    if (rule.quietHint) { hint.classList.add("is-floating"); win.appendChild(hint); root.classList.add("has-floating-hint"); }
    root.insertBefore(settingsRow, root.querySelector(".cal-side") || win);

    var today = D.today();
    // anchor: first day of a trip being made; hover: the day under the mouse
    // while making one (desktop preview); selected: index of the trip being
    // edited; drag: a handle being dragged.
    var trips = [], anchor = null, hover = null, selected = -1, drag = null;
    var allowed = (rule.countries && rule.countries(PLACES)) || PLACES;
    var defaultCountry = allowed.length === 1 ? allowed[0] : (rule.defaultCountry || "");
    var recent = [];
    // An article can embed a calculator preset to its own rule:
    // data-cal-preset = { settings, lock, link }. Locked choices show no
    // control, a locked country shows as a plain title, and link replaces the
    // rule's own `c` in the import link (e.g. 183-es).
    var preset = {};
    try { preset = JSON.parse(root.getAttribute("data-cal-preset") || "{}"); } catch (e) { preset = {}; }
    var locked = preset.lock || [];
    var settings = Object.assign({}, preset.settings || {}); // choices made in the rule's result menus (rule.evaluate -> controls)
    var finePointer = !!(window.matchMedia && window.matchMedia("(hover: hover) and (pointer: fine)").matches);
    var rows = [], cells = {}, firstMonday = 0, activeMonth = null, clipFrom = null, clipTo = null;
    var englishNames = null;
    try { englishNames = new Intl.DisplayNames(["en"], { type: "region" }); } catch (e) {}

    function ctx() { return { today: today, D: D, label: label, plural: plural, text: text, trips: trips, placeName: placeName, settings: settings, dateRange: dateRange, tone: tone, embedded: !!preset.settings }; }
    // A new trip starts with the rule's fixed country, or (rule.carryCountry)
    // the country picked last, so a run of stays in one country is quick.
    function newCountry() {
      if (defaultCountry) return defaultCountry;
      if (rule.newTripCountry) return rule.newTripCountry(ctx()) || "";
      return (rule.carryCountry && recent[0]) || "";
    }
    function remember(code) { recent = [code].concat(recent.filter(function (c) { return c !== code; })).slice(0, 3); }
    // The app's tracker colours (TrackerMeterTone): for a limit, blue, orange
    // when 7 or fewer days (or 15% of it) are left, red at or over it; for a
    // target, blue until it is reached, then green.
    function tone(days, limit, target) {
      if (target) return days >= limit ? "achieved" : "normal";   // a target only turns green
      var left = limit - days;
      return left <= 0 ? "critical" : (left <= 7 || left / limit <= 0.15) ? "warning" : "normal";
    }
    // With rule.fixedRange the calendar shows range() only; days outside it are
    // shown for the week's sake but cannot be tapped, and bars stop at its edge.
    function span() { return rule.fixedRange ? rule.range(ctx()) : null; }

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
      var r = rule.range(ctx()), from = r.from, to = r.to, clip = span();
      if (!rule.fixedRange) trips.forEach(function (t) { from = Math.min(from, t.start); to = Math.max(to, t.end); });
      var first = D.monday(from), last = D.monday(to) + 6;
      if (rows.length && first === firstMonday && rows.length === (last - first + 1) / 7 && (!clip || (clip.from === clipFrom && clip.to === clipTo))) return;
      clipFrom = clip ? clip.from : null; clipTo = clip ? clip.to : null;
      var anchor = rows.length ? topDay() : null;
      firstMonday = first;
      rows = []; cells = {};
      weeksBox.textContent = "";
      for (var mon = first; mon <= last; mon += 7) {
        var row = el("div", { "class": "cal-week" });
        row.dataset.monday = mon;
        for (var c = 0; c < 7; c++) {
          var day = mon + c, p = D.parts(day);
          var out = clip && (day < clip.from || day > clip.to);
          var b = el("button", { type: "button", "class": "cal-day" + (p.d === 1 ? " is-month-start" : "") + (day === today ? " is-today" : "") + (out ? " is-outside" : ""), "data-day": day });
          if (out) b.disabled = true;
          b.appendChild(el("span", { "class": "cal-num" }, p.d === 1 ? shortMonth.format(new Date(day * DAY)).toLocaleUpperCase(locale) : String(p.d)));
          cells[day] = b;
          row.appendChild(b);
        }
        // the month in view gets an accent line over its days, as in the app
        row.appendChild(el("span", { "class": "cal-month-line", "aria-hidden": "true" }));
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
    function segment(bars, mon, t, cls, real, clip) {
      var sun = mon + 6;
      var s0 = clip ? Math.max(t.start, clip.from) : t.start, e0 = clip ? Math.min(t.end, clip.to) : t.end;
      if (s0 > e0 || e0 < mon || s0 > sun) return;
      var a = Math.max(s0, mon), z = Math.min(e0, sun);
      var starts = a === s0, ends = z === e0;
      var cutS = starts && s0 > t.start, cutE = ends && e0 < t.end;   // stopped by the period's edge: square
      var cutStart = real && starts && !cutS && t.start !== t.end && handoff(t, true);
      var cutEnd = real && ends && !cutE && t.start !== t.end && handoff(t, false);
      var left = !starts ? "0px" : cutS ? ((a - mon) / 7 * 100) + "%" : "calc(" + ((a - mon + 0.5) / 7 * 100) + "% " + (cutStart ? "+ " + GAP : "- " + DISC) + "px)";
      var right = !ends ? "100%" : cutE ? ((z - mon + 1) / 7 * 100) + "%" : "calc(" + ((z - mon + 0.5) / 7 * 100) + "% " + (cutEnd ? "- " + GAP : "+ " + DISC) + "px)";
      starts = starts && !cutS; ends = ends && !cutE;
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
    function handleAt(bars, mon, day, end, clip) {
      if (day < mon || day > mon + 6 || (clip && (day < clip.from || day > clip.to))) return;
      var h = el("span", { "class": "cal-handle", "data-end": end });
      h.style.left = ((day - mon + 0.5) / 7 * 100) + "%";
      h.addEventListener("pointerdown", startDrag);
      bars.appendChild(h);
    }
    function drawBars() {
      var preview = anchor != null && hover != null && hover !== anchor
        ? { start: Math.min(anchor, hover), end: Math.max(anchor, hover) } : null;
      var clip = span();
      rows.forEach(function (row) {
        var mon = +row.dataset.monday, bars = row.lastChild;
        bars.textContent = "";
        trips.forEach(function (t, i) { segment(bars, mon, t, i === selected ? " is-selected" : "", true, clip); });
        if (preview) segment(bars, mon, preview, " is-preview", false, clip);
        if (selected >= 0 && trips[selected]) {
          handleAt(bars, mon, trips[selected].start, "start", clip);
          handleAt(bars, mon, trips[selected].end, "end", clip);
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
      var clip = span();
      if (clip) day = Math.min(Math.max(day, clip.from), clip.to);
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

    var hintsSeen = {}, lastHint = "";
    function paint() {
      Object.keys(cells).forEach(function (k) {
        var day = +k, b = cells[k], i = tripAt(day);
        b.classList.toggle("has-trip", i >= 0);
        b.classList.toggle("is-anchor", day === anchor);
        b.setAttribute("aria-pressed", i >= 0 ? "true" : "false");
        b.setAttribute("aria-label", label(day) + (i >= 0 ? ", " + S.inTrip : "") + (day === anchor ? ", " + S.pending : ""));
      });
      drawBars();
      var hintKey = selected >= 0 ? "hintSelected" : anchor != null ? "hintEnd"
        : rule.quietHint && trips.length ? "" : "hintStart";
      // A quiet rule shows the idle hint only while the calendar is empty, and
      // the others once each: the first stay, the first selection.
      if (rule.quietHint && hintKey !== lastHint) { if (lastHint) hintsSeen[lastHint] = true; lastHint = hintKey; }
      if (rule.quietHint && hintsSeen[hintKey]) hintKey = "";
      hint.textContent = hintKey === "hintEnd" ? text("hintEnd", { date: label(anchor) }) : hintKey ? text(hintKey) : "";
      hint.hidden = !hint.textContent;
    }

    // ---- trips list ---------------------------------------------------------------
    // Each card: the flag, the country (or a field to add one), the dates and
    // the count. Tapping a card selects its trip; the selected card offers Delete.
    // Apostrophes vary by keyboard (В’єтнам, Вʼєтнам), so they fold to one.
    function fold(s) { return String(s).normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[’ʼ‘`]/g, "'").toLowerCase(); }
    // Names people type that the browser's region names leave out: the short
    // or long form the site's own articles use where Intl picks the other one.
    var ALIASES = {
      AE: "UAE ОАЭ ОАЕ Объединённые Арабские Эмираты Обʼєднані Арабські Емірати",
      AU: "호주 澳洲 澳大利亚",
      CZ: "Czech Republic",
      GB: "UK Great Britain",
      US: "USA"
    };
    var catalogue = null;
    function places() {
      if (!catalogue) catalogue = allowed.map(function (c) {
        var name = placeName(c), en = englishNames ? (englishNames.of(c) || "") : "";
        return { code: c, name: name, key: fold(name + " " + en + " " + c + " " + (ALIASES[c] || "")) };
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
    function countryField(current, onChoose) {
      var wrap = el("div", { "class": "cal-country-field" });
      var input = el("input", { type: "text", "class": "cal-country-input", placeholder: text("addCountry"), "aria-label": text("country"), autocomplete: "off",
        // "search" in the name keeps Safari from offering contact AutoFill here
        name: "cal-place-search", spellcheck: "false", role: "combobox", "aria-expanded": "false", "aria-autocomplete": "list" });
      if (current) input.value = placeName(current);
      var box = el("ul", { "class": "cal-country-list", role: "listbox", hidden: "" });
      var options = [], active = 0;
      function choose(code) { close(); remember(code); onChoose(code); }
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
        place();
        window.addEventListener("scroll", place, true);
        window.addEventListener("resize", place);
      }
      // The list floats over the page (position: fixed), so a scrolling
      // Timeline or a card edge can never cut it off. It opens below the field,
      // or above it when the screen has no room below.
      function place() {
        if (box.hidden) return;
        var r = input.getBoundingClientRect(), head = wrap.closest(".cal-card-head");
        var left = head ? r.left - 30 : r.left - 6, width = head ? Math.max(r.width + 30, 256) : r.width + 6;
        width = Math.min(width, window.innerWidth - 16);
        left = Math.max(8, Math.min(left, window.innerWidth - width - 8));
        box.style.left = left + "px";
        box.style.width = width + "px";
        width = Math.max(width, Math.min(256, window.innerWidth - 16));
        left = Math.max(8, Math.min(left, window.innerWidth - width - 8));
        box.style.left = left + "px";
        box.style.width = width + "px";
        var below = window.innerHeight - r.bottom - 12, h = Math.min(box.scrollHeight, 260);
        box.style.top = (below >= Math.min(h, 160) || below >= r.top ? r.bottom + 6 : Math.max(8, r.top - 6 - h)) + "px";
      }
      function close() {
        box.hidden = true;
        input.setAttribute("aria-expanded", "false");
        window.removeEventListener("scroll", place, true);
        window.removeEventListener("resize", place);
      }
      function mark() { Array.prototype.forEach.call(box.children, function (li, i) { li.classList.toggle("is-active", i === active); }); }
      input.addEventListener("focus", function () { if (current) input.select(); show(); });
      input.addEventListener("input", show);
      input.addEventListener("blur", function () { close(); if (current) input.value = placeName(current); fitInput(input); });
      // The field is as wide as the name, so only the name itself opens the list.
      input.addEventListener("input", function () { fitInput(input); });
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
      var clip = span();
      trips.forEach(function (t, idx) {
        var isSel = idx === selected;
        var away = clip && (t.end < clip.from || t.start > clip.to);
        var card = el("div", { "class": "cal-trip" + (isSel ? " is-selected" : "") + (away ? " is-outside" : "") });
        var flag = el("span", { "class": "cal-flag" + (t.country ? "" : " is-empty") });
        if (t.country) flag.appendChild(flagImg(t.country, 28));
        card.appendChild(flag);
        var name = el("div", { "class": "cal-trip-country" });
        if (allowed.length < 2) name.appendChild(el("span", null, placeName(t.country)));
        else name.appendChild(countryField(t.country, function (code) { trips[idx].country = code; commit(); }));
        card.appendChild(name);
        var line = el("div", { "class": "cal-trip-line" });
        line.appendChild(el("span", { "class": "cal-trip-dates" }, dateRange(t.start, t.end)));
        // The selected card swaps its day count for Delete, on the same line,
        // so nothing opens up below it.
        if (isSel) {
          var del = el("button", { type: "button", "class": "cal-delete" });
          del.appendChild(icon("trash"));
          del.appendChild(document.createTextNode(S.deleteTrip));
          del.addEventListener("click", function (e) { e.stopPropagation(); removeTrip(idx); });
          line.appendChild(del);
        } else {
          line.appendChild(el("span", { "class": "cal-trip-count" }, rule.tripLabel(t, ctx())));
        }
        card.appendChild(line);
        card.addEventListener("click", function (e) {
          if (e.target.closest(".cal-country-field")) return;
          selected = isSel ? -1 : idx;
          anchor = null;
          refresh();
          if (!isSel && finePointer) reveal(t.start - 7);
        });
        list.appendChild(card);
      });
      list.querySelectorAll(".cal-country-input").forEach(fitInput);
    }

    // A rule's result can carry menus (controls), an app-style meter and a
    // status pill; or the older headline form (ILR).
    function changed(ctl) {
      render();
      if (rule.fixedRange && ctl.moveCalendar) { var rr = rule.range(ctx()); reveal(today >= rr.from && today <= rr.to ? today - 21 : rr.from); updateMonth(); }
    }
    function control(ctl) {
      var wrap = el(ctl.type === "country" ? "div" : "label", { "class": "cal-control" + (ctl.type ? " is-" + ctl.type : "") });
      if (ctl.prefix) wrap.appendChild(el("span", { "class": "cal-control-prefix" }, ctl.prefix));
      if (ctl.type === "country") {
        var pill = el("span", { "class": "cal-control-pill" });
        var flag = el("span", { "class": "cal-flag" + (ctl.value ? "" : " is-empty") });
        if (ctl.value) flag.appendChild(flagImg(ctl.value, 28));
        pill.appendChild(flag);
        var field = countryField(ctl.value, function (code) {
          settings[ctl.key] = code;
          // stays marked before a country was chosen take it now
          trips.forEach(function (t) { if (!t.country) t.country = code; });
          commit();
        });
        var fieldInput = field.querySelector("input");
        fieldInput.addEventListener("input", function () { fitInput(fieldInput); });
        pill.appendChild(field);
        wrap.appendChild(pill);
        return wrap;
      }
      if (ctl.type === "date") {
        // A native date field shows the browser's own format (04/06/2026 in
        // the US), so the pill shows the page's format and the native picker
        // sits invisibly over it: a tap opens the system calendar.
        var shown = el("span", { "class": "cal-value" }, ctl.display || ctl.value);
        shown.appendChild(icon("updown", "cal-chevron"));
        var input = el("input", { type: "date", value: ctl.value, "aria-label": ctl.label || ctl.prefix || "", title: ctl.label || "" });
        input.addEventListener("click", function () { try { if (input.showPicker) input.showPicker(); } catch (e) {} });
        input.addEventListener("change", function () { if (input.value) { settings[ctl.key] = input.value; changed(ctl); } });
        wrap.appendChild(shown);
        wrap.appendChild(input);
        return wrap;
      }
      var pick = el("select", { "aria-label": ctl.label || ctl.prefix || "" });
      var current = ctl.options.filter(function (o) { return o.value === ctl.value; })[0] || ctl.options[0];
      ctl.options.forEach(function (o) {
        var opt = el("option", { value: o.value }, o.detail ? o.label + " · " + o.detail.replace(/[.。]$/, "") : o.label);
        if (o.value === ctl.value) opt.selected = true;
        pick.appendChild(opt);
      });
      pick.addEventListener("change", function () { settings[ctl.key] = pick.value; changed(ctl); });
      var shownValue = el("span", { "class": "cal-value" }, current ? current.label : "");
      shownValue.appendChild(icon("updown", "cal-chevron"));
      wrap.classList.add("is-select");
      wrap.appendChild(shownValue);
      wrap.appendChild(pick);
      return wrap;
    }
    // The country in the card header is as wide as its name.
    function fitInput(input) {
      var probe = el("span", { "class": "cal-measure" }, input.value || input.placeholder || "");
      probe.style.font = getComputedStyle(input).font;
      document.body.appendChild(probe);
      // padding and border (14px) plus generous slack, so no font size truncates it
      input.style.width = Math.ceil(probe.getBoundingClientRect().width) + 32 + "px";
      probe.remove();
    }
    function renderResult() {
      var r = rule.evaluate(trips, ctx());
      result.textContent = "";
      settingsRow.textContent = "";
      var shown = (r.controls || []).filter(function (ctl) { return locked.indexOf(ctl.key) < 0; });
      settingsRow.hidden = !shown.length;
      shown.forEach(function (ctl) {
        var row = el("div", { "class": "cal-setting" });
        if (ctl.icon) row.appendChild(icon(ctl.icon));
        row.appendChild(el("span", { "class": "cal-setting-label" }, ctl.label || ""));
        row.appendChild(control(ctl));
        settingsRow.appendChild(row);
        // A setting can explain itself in one quiet line under its row.
        if (ctl.caption) settingsRow.appendChild(el("p", { "class": "cal-setting-caption" }, ctl.caption));
      });
      if (r.meter) {
        var m = r.meter;
        // The app's card header: flag and title on the left, status pill on the right.
        if (m.title != null) {
          var head = el("div", { "class": "cal-card-head" });
          if (m.countryKey && locked.indexOf(m.countryKey) < 0) {
            head.appendChild(control({ type: "country", key: m.countryKey, value: m.flag || "", label: m.title }));
          } else {
            var flag = el("span", { "class": "cal-flag" + (m.flag ? "" : " is-empty") });
            if (m.flag) flag.appendChild(flagImg(m.flag, 28));
            head.appendChild(flag);
            head.appendChild(el("span", { "class": "cal-card-title" + (m.flag ? "" : " is-placeholder") }, m.countryKey && m.flag ? placeName(m.flag) : m.title));
          }
          if (r.statusText) head.appendChild(el("span", { "class": "cal-pill tone-" + m.tone }, r.statusText));
          result.appendChild(head);
          var titleInput = head.querySelector(".cal-country-input");
          if (titleInput) fitInput(titleInput);
        }
        var meter = el("div", { "class": "cal-meter tone-" + m.tone });
        var row = el("div", { "class": "cal-meter-row" });
        row.appendChild(el("span", { "class": "cal-meter-period" }, m.label));
        var count = el("span", { "class": "cal-meter-count" });
        count.appendChild(el("b", null, String(m.days)));
        count.appendChild(document.createTextNode(" / " + m.limit));
        row.appendChild(count);
        meter.appendChild(row);
        var track = el("div", { "class": "cal-meter-track" }), fill = el("span", { "class": "cal-meter-fill" });
        fill.style.width = Math.min(100, Math.max(0, m.days / m.limit * 100)) + "%";
        track.appendChild(fill);
        meter.appendChild(track);
        result.appendChild(meter);
        if (r.statusText && m.title == null) result.appendChild(el("span", { "class": "cal-pill tone-" + m.tone }, r.statusText));
        (r.lines || []).forEach(function (line) { result.appendChild(el("p", { "class": "cal-line" }, line)); });
        return;
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
      // A heading starts with a capital, though Dutch, Polish or Russian write
      // month names lowercase in running text ("wrzesień 2026").
      var title = monthDate.format(new Date(D.monthStart(pick) * DAY));
      monthTitle.textContent = title.charAt(0).toLocaleUpperCase(locale) + title.slice(1);
      Object.keys(cells).forEach(function (k) { cells[k].classList.toggle("is-other-month", D.monthKey(+k) !== pick); });
      rows.forEach(function (r) {
        var mon = +r.dataset.monday, first = -1, last = -1;
        for (var c = 0; c < 7; c++) if (D.monthKey(mon + c) === pick) { if (first < 0) first = c; last = c; }
        var line = r.querySelector(".cal-month-line");
        line.hidden = first < 0;
        if (first >= 0) { line.style.left = (first / 7 * 100) + "%"; line.style.width = ((last - first + 1) / 7 * 100) + "%"; }
      });
    }

    // ---- import into AtlasDays -----------------------------------------------------
    function csvField(v) { v = String(v == null ? "" : v); return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }
    function openImport() {
      var rows = rule.exportRows(trips, ctx()).slice().sort(function (a, b) { return a.start - b.start; });
      if (!dialog || !dialog.showModal) return downloadCsv();
      var frag = rows.length ? importFragment(rows, preset.link || rule.linkId) : "";
      var mode = rows.length > LINK.maxStays ? "file"
        : inApp || appleTouch ? "phone"
        : rows.length <= LINK.maxQrStays ? "computer" : "file";
      dialog.querySelectorAll("[data-cal-on]").forEach(function (part) {
        part.hidden = part.getAttribute("data-cal-on").split(" ").indexOf(mode) < 0;
      });
      // Inside the app there is nothing to install.
      dialog.querySelectorAll("[data-cal-store]").forEach(function (part) { part.hidden = inApp; });
      // A single step needs no number.
      dialog.querySelectorAll(".cal-steps").forEach(function (list) {
        var visible = [].filter.call(list.children, function (li) { return !li.hidden; }).length;
        list.classList.toggle("is-single", visible === 1);
      });
      dialog.querySelectorAll("[data-cal-open]").forEach(function (a) { a.href = (inApp ? LINK.scheme : LINK.universal) + frag; });
      dialog.classList.toggle("is-file", mode === "file");
      // "Import with a file instead" is the quiet alternative, unless the file
      // is all there is; its follow-up line shows once the file is saved.
      dialog.querySelectorAll("[data-cal-alt]").forEach(function (part) { part.hidden = mode === "file"; });
      dialog.querySelectorAll("[data-cal-downloaded]").forEach(function (part) { part.hidden = true; part.previousElementSibling.hidden = false; });
      var box = dialog.querySelector("[data-cal-qr]");
      if (box) {
        box.textContent = "";
        if (mode === "computer") loadQr(function () {
          box.innerHTML = qrSvg(LINK.universal + frag);
          // On a 1x screen a big code is too fine at the compact size: start large.
          var big = (window.devicePixelRatio || 1) < 1.5 && box.firstChild.viewBox.baseVal.width * 3 > 240;
          box.classList.toggle("is-large", big);
          box.parentNode.classList.toggle("is-large", big);
          sizeQr(box);
        });
      }
      dialog.showModal();
      // Focus the dialog itself, so no button looks preselected.
      dialog.setAttribute("tabindex", "-1");
      dialog.focus();
    }
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
      var b = e.target.closest(".cal-day"), d = b && !b.disabled ? +b.getAttribute("data-day") : null;
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
      btn.addEventListener("click", openImport);
    });
    root.querySelectorAll("[data-cal-download]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        downloadCsv();
        var done = btn.nextElementSibling;
        if (done && done.hasAttribute("data-cal-downloaded")) { btn.hidden = true; done.hidden = false; }
      });
    });
    root.querySelectorAll("[data-cal-close]").forEach(function (btn) { btn.addEventListener("click", function () { dialog.close(); }); });
    if (dialog) dialog.addEventListener("click", function (e) { if (e.target === dialog) dialog.close(); });
    var qrBox = dialog && dialog.querySelector("[data-cal-qr]");
    window.addEventListener("resize", function () { if (dialog.open && qrBox && qrBox.firstChild) stackQr(qrBox); });

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
