/* UK ILR absence rule for the AtlasDays day calendar (assets/js/day-calendar.js).

   Continuous residence for indefinite leave to remain: no more than 180 whole
   days outside the UK in any 12-month period (Immigration Rules, Appendix
   Continuous Residence, CR 3.1). Whole days only: the day you leave and the
   day you return are not absences.

   The card reads like the app's tracker card (Jorick, 2026-10-04): days away
   in the 12 months up to a "Count up to" date (today unless the visitor picks
   another), against 180, with the app's pill. Like the Schengen calculator,
   the calendar shows exactly those 12 months and the visitor picks the date
   to check (Jorick, 2026-10-04): a planned trip is checked on the day of
   return, when its count is highest.

   Naturalisation uses the same whole-day absences over a longer window
   (British Nationality Act 1981, Schedule 1): an embed with `citizenship`
   set counts the 5 years up to the date against 450 (the spouse or civil
   partner route: 3 years, 270), and a second bar checks the final 12
   months against 90. `note` (English, for the importer) labels exported rows. */
(function () {
  "use strict";

  // Trips that touch or overlap (Germany to the 10th, the Netherlands from the
  // 10th) are one absence: the handoff day was spent abroad. Only the day you
  // left the UK and the day you came back are not absence days.
  function absences(trips) {
    var out = [];
    trips.slice().sort(function (a, b) { return a.start - b.start; }).forEach(function (t) {
      var last = out[out.length - 1];
      if (last && t.start <= last.end) last.end = Math.max(last.end, t.end);
      else out.push({ start: t.start, end: t.end });
    });
    return out;
  }
  function absentDays(trips) {
    var set = new Set();
    absences(trips).forEach(function (t) { for (var d = t.start + 1; d < t.end; d++) set.add(d); });
    return set;
  }
  var LIMIT = 180;
  var ROUTES = { standard: { years: 5, limit: 450 }, spouse: { years: 3, limit: 270 } }, RECENT = 90;
  function rule(c) {
    if (!c.settings.citizenship) return { years: 1, limit: LIMIT };
    return ROUTES[c.settings.route] || ROUTES.standard;
  }
  function checkOn(c) {
    var iso = c.settings.checkOn;
    if (!iso) return c.today;
    var p = iso.split("-").map(Number);
    return c.D.fromParts(p[0], p[1], p[2]) || c.today;
  }

  window.AtlasDaysRules = window.AtlasDaysRules || {};
  window.AtlasDaysRules.ukIlr = {
    travelDaysCount: false,
    singleDayTrips: false,
    quietHint: true,
    fixedRange: true,

    // Trips are absences, so they can be anywhere but the UK.
    countries: function (all) { return all.filter(function (code) { return code !== "GB"; }); },

    range: function (c) {
      var on = checkOn(c);
      return { from: c.D.shiftYears(on, -rule(c).years) + 1, to: on };
    },

    // A trip's own whole days away. The day it takes over from another trip
    // abroad counts here, so the cards add up to the absence.
    tripLabel: function (t, c) {
      var takesOver = (c.trips || []).some(function (o) { return o !== t && o.end === t.start; });
      return c.text("tripAway", { n: Math.max(0, t.end - t.start - 1) + (takesOver ? 1 : 0) });
    },

    evaluate: function (trips, c) {
      var r = rule(c), set = absentDays(trips), on = checkOn(c), from = c.D.shiftYears(on, -r.years) + 1;
      var recentFrom = c.D.shiftYears(on, -1) + 1, away = 0, recent = 0;
      set.forEach(function (d) {
        if (d >= from && d <= on) away++;
        if (d >= recentFrom && d <= on) recent++;
      });
      var left = r.limit - away, controls = [], more = [];
      if (c.settings.citizenship) {
        controls.push({ key: "route", icon: "target", label: c.text("route"), value: c.settings.route || "standard", moveCalendar: true, options: [
          { value: "standard", label: c.text("routeStandard") },
          { value: "spouse", label: c.text("routeSpouse") }
        ] });
        // The final 12 months as a second bar; the pill follows whichever
        // limit leaves less room.
        more.push({ label: c.text("barRecent"), days: recent, limit: RECENT, tone: c.tone(recent, RECENT, false) });
        left = Math.min(left, RECENT - recent);
      }
      controls.push({ type: "date", key: "checkOn", icon: "calendar", label: c.text("checkOn"), caption: c.text("checkOnCaption"), value: c.D.iso(on), display: c.dateRange(on, on), moveCalendar: true });
      return {
        controls: controls,
        meter: { title: c.text("title"), flag: "GB", label: c.dateRange(from, on), days: away, limit: r.limit, tone: c.tone(away, r.limit, false), more: more },
        statusText: left > 0 ? c.text("remaining", { n: left }) : left === 0 ? c.text("atLimit") : c.text("overBy", { n: -left }),
        statusTone: c.settings.citizenship ? c.tone(r.limit - left, r.limit, false) : undefined,
        lines: []
      };
    },

    // A "days away" tracker in AtlasDays counts every day no UK stay touches,
    // so the file carries your time in the UK between past trips, starting a
    // year before the first one. Stays share the travel days with the trips,
    // which AtlasDays does not treat as an overlap.
    linkId: "uk-ilr",
    exportRows: function (trips, c) {
      var past = trips.filter(function (t) { return t.start <= c.today; });
      if (!past.length) return trips.filter(function (t) { return t.country; }).map(function (t) { return { country: t.country, start: t.start, end: t.end, notes: c.settings.note || "ILR absence calculator" }; });
      var rows = [], cursor = c.D.shiftYears(past[0].start, -1);
      past.forEach(function (t) {
        if (t.start > cursor) rows.push({ country: "GB", start: cursor, end: t.start, notes: c.settings.note || "ILR absence calculator" });
        cursor = Math.max(cursor, t.end);
      });
      if (cursor <= c.today) rows.push({ country: "GB", start: cursor, end: null, notes: c.settings.note || "ILR absence calculator" });
      // Trips given a country go in too (past and planned), so the app shows
      // where the time away was spent.
      trips.forEach(function (t) { if (t.country) rows.push({ country: t.country, start: t.start, end: t.end, notes: c.settings.note || "ILR absence calculator" }); });
      rows.sort(function (x, y) { return x.start - y.start; });
      return rows;
    },

    strings: {
      hintStart: "Tap the day you left the UK, then the day you came back.",
      hintEnd: "Tap the other end of the trip.",
      inTrip: "outside the UK",
      pending: "start of a new trip",
      empty: "No trips yet.",
      deleteTrip: "Delete trip",
      country: "Country",
      addCountry: "Add country",
      noMatch: "No matching country",
      hintSelected: "Drag either end of the trip to change its dates, or delete it below.",
      fileName: "atlasdays-uk-stays.csv",
      tripAway: { one: "{n} day away", other: "{n} days away" },
      title: "Days outside the UK",
      checkOn: "Count up to",
      checkOnCaption: "Your days abroad in the 12 months up to this date. For a planned trip, pick the day you come back.",
      remaining: { one: "{n} day remaining", other: "{n} days remaining" },
      atLimit: "At limit",
      overBy: { one: "Over limit by {n} day", other: "Over limit by {n} days" },
      route: "Route",
      routeStandard: "Standard",
      routeSpouse: "Spouse or civil partner",
      barRecent: "Last 12 months"
    }
  };
})();
