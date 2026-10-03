/* UK ILR absence rule for the AtlasDays day calendar (assets/js/day-calendar.js).

   Continuous residence for indefinite leave to remain: no more than 180 whole
   days outside the UK in any 12-month period (Immigration Rules, Appendix
   Continuous Residence, CR 3.1). Whole days only: the day you leave and the
   day you return are not absences. The check runs over every trip marked,
   planned ones included, so a future trip shows at once whether it fits. */
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

  window.AtlasDaysRules = window.AtlasDaysRules || {};
  window.AtlasDaysRules.ukIlr = {
    travelDaysCount: false,
    singleDayTrips: false,

    // Trips are absences, so they can be anywhere but the UK.
    countries: function (all) { return all.filter(function (code) { return code !== "GB"; }); },

    range: function (c) {
      return { from: c.D.shiftYears(c.today, -5), to: c.D.shiftYears(c.today, 1) };
    },

    // A trip's own whole days away. The day it takes over from another trip
    // abroad counts here, so the cards add up to the absence.
    tripLabel: function (t, c) {
      var takesOver = (c.trips || []).some(function (o) { return o !== t && o.end === t.start; });
      return c.text("tripAway", { n: Math.max(0, t.end - t.start - 1) + (takesOver ? 1 : 0) });
    },

    evaluate: function (trips, c) {
      var worst = worstWindow(c.D, absentDays(trips));
      return {
        ok: worst.total <= 180,
        total: worst.total,
        remaining: Math.abs(180 - worst.total),
        status: !worst.total ? "" : worst.total <= 180 ? "left" : "over",
        from: worst.from,
        to: worst.to
      };
    },

    // A "days away" tracker in AtlasDays counts every day no UK stay touches,
    // so the file carries your time in the UK between past trips, starting a
    // year before the first one. Stays share the travel days with the trips,
    // which AtlasDays does not treat as an overlap.
    exportRows: function (trips, c) {
      var past = trips.filter(function (t) { return t.start <= c.today; });
      if (!past.length) return trips.filter(function (t) { return t.country; }).map(function (t) { return { country: t.country, start: t.start, end: t.end, notes: "ILR absence calculator" }; });
      var rows = [], cursor = c.D.shiftYears(past[0].start, -1);
      past.forEach(function (t) {
        if (t.start > cursor) rows.push({ country: "United Kingdom", start: cursor, end: t.start, notes: "ILR absence calculator" });
        cursor = Math.max(cursor, t.end);
      });
      if (cursor <= c.today) rows.push({ country: "United Kingdom", start: cursor, end: null, notes: "ILR absence calculator" });
      // Trips given a country go in too (past and planned), so the app shows
      // where the time away was spent.
      trips.forEach(function (t) { if (t.country) rows.push({ country: t.country, start: t.start, end: t.end, notes: "ILR absence calculator" }); });
      rows.sort(function (x, y) { return x.start - y.start; });
      return rows;
    },

    strings: {
      hintStart: "Tap the day you left the UK, then the day you came back.",
      hintEnd: "Now tap the other end of the trip, or {date} again to cancel.",
      inTrip: "outside the UK",
      pending: "start of a new trip",
      empty: "No trips yet.",
      deleteTrip: "Delete trip",
      country: "Country",
      addCountry: "Add country",
      noMatch: "No matching country",
      hintSelected: "Drag either end of the trip to change its dates, or delete it below.",
      fileName: "atlasdays-uk-stays.csv",
      "tripAway": {"one": "{n} day away", "other": "{n} days away"},
      "headline": "{n} of 180 days away in any 12 months",
      "headlineEmpty": "0 of 180 days away",
      "left": "{n} left",
      "over": {"one": "{n} day over", "other": "{n} days over"},
      "emptyResult": "Mark your trips outside the UK to see your worst 12 months.",
      "worstWindow": "Your worst 12 months run from {from} to {to}."
    }
  };
})();
