/* UK ILR absence rule for the AtlasDays day calendar (assets/js/day-calendar.js).

   Continuous residence for indefinite leave to remain: no more than 180 whole
   days outside the UK in any 12-month period (Immigration Rules, Appendix
   Continuous Residence, CR 3.1). Whole days only: the day you leave and the
   day you return are not absences.

   The card reads like the app's tracker card (Jorick, 2026-10-04): days away
   in the 12 months up to a "Check on" date (today unless the visitor picks
   another), against 180, with the app's pill. The rule covers every 12
   months of the qualifying period, so the calendar keeps five years and a
   line under the card names the worst 12 months when they hold more days
   away than the window being checked. */
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
  // Highest total in any 12-month window; the worst window always ends on an
  // absence day, so only those are checked.
  function worstWindow(D, set) {
    var days = Array.from(set).sort(function (a, b) { return a - b; });
    var best = { total: 0, from: null, to: null };
    days.forEach(function (e) {
      var from = D.shiftYears(e, -1) + 1, total = 0;
      for (var i = 0; i < days.length; i++) if (days[i] >= from && days[i] <= e) total++;
      if (total > best.total) best = { total: total, from: from, to: e };
    });
    return best;
  }

  var LIMIT = 180;
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

    // Trips are absences, so they can be anywhere but the UK.
    countries: function (all) { return all.filter(function (code) { return code !== "GB"; }); },

    range: function (c) {
      var on = checkOn(c);
      return { from: Math.min(c.D.shiftYears(c.today, -5), c.D.shiftYears(on, -1) + 1), to: Math.max(c.D.shiftYears(c.today, 1), on) };
    },

    // A trip's own whole days away. The day it takes over from another trip
    // abroad counts here, so the cards add up to the absence.
    tripLabel: function (t, c) {
      var takesOver = (c.trips || []).some(function (o) { return o !== t && o.end === t.start; });
      return c.text("tripAway", { n: Math.max(0, t.end - t.start - 1) + (takesOver ? 1 : 0) });
    },

    evaluate: function (trips, c) {
      var set = absentDays(trips), on = checkOn(c), from = c.D.shiftYears(on, -1) + 1, away = 0;
      set.forEach(function (d) { if (d >= from && d <= on) away++; });
      var left = LIMIT - away, worst = worstWindow(c.D, set), lines = [];
      // The rule is any 12 months: say so when another stretch is worse.
      if (worst.total > away) lines.push(c.text("lineWorst", { n: worst.total, from: c.dateRange(worst.from, worst.to) }));
      return {
        controls: [
          { type: "date", key: "checkOn", icon: "calendar", label: c.text("checkOn"), value: c.D.iso(on), display: c.dateRange(on, on), moveCalendar: true }
        ],
        meter: { title: c.text("title"), flag: "GB", label: c.dateRange(from, on), days: away, limit: LIMIT, tone: c.tone(away, LIMIT, false) },
        statusText: left > 0 ? c.text("remaining", { n: left }) : left === 0 ? c.text("atLimit") : c.text("overBy", { n: -left }),
        lines: lines
      };
    },

    // A "days away" tracker in AtlasDays counts every day no UK stay touches,
    // so the file carries your time in the UK between past trips, starting a
    // year before the first one. Stays share the travel days with the trips,
    // which AtlasDays does not treat as an overlap.
    linkId: "uk-ilr",
    exportRows: function (trips, c) {
      var past = trips.filter(function (t) { return t.start <= c.today; });
      if (!past.length) return trips.filter(function (t) { return t.country; }).map(function (t) { return { country: t.country, start: t.start, end: t.end, notes: "ILR absence calculator" }; });
      var rows = [], cursor = c.D.shiftYears(past[0].start, -1);
      past.forEach(function (t) {
        if (t.start > cursor) rows.push({ country: "GB", start: cursor, end: t.start, notes: "ILR absence calculator" });
        cursor = Math.max(cursor, t.end);
      });
      if (cursor <= c.today) rows.push({ country: "GB", start: cursor, end: null, notes: "ILR absence calculator" });
      // Trips given a country go in too (past and planned), so the app shows
      // where the time away was spent.
      trips.forEach(function (t) { if (t.country) rows.push({ country: t.country, start: t.start, end: t.end, notes: "ILR absence calculator" }); });
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
      checkOn: "Check on",
      remaining: { one: "{n} day remaining", other: "{n} days remaining" },
      atLimit: "At limit",
      overBy: { one: "Over limit by {n} day", other: "Over limit by {n} days" },
      lineWorst: { one: "Worst 12 months: {n} day away, {from}.", other: "Worst 12 months: {n} days away, {from}." }
    }
  };
})();
