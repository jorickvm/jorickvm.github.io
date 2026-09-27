/* UK ILR absence rule for the AtlasDays day calendar (assets/js/day-calendar.js).

   Continuous residence for indefinite leave to remain: no more than 180 whole
   days outside the UK in any 12-month period (Immigration Rules, Appendix
   Continuous Residence, CR 3.1). Whole days only: the day you leave and the
   day you return are not absences. The check runs over every trip marked,
   planned ones included, so a future trip shows at once whether it fits. */
(function () {
  "use strict";

  function absentDays(trips) {
    var set = new Set();
    trips.forEach(function (t) { for (var d = t.start + 1; d < t.end; d++) set.add(d); });
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

    range: function (c) {
      return { from: c.D.shiftYears(c.today, -5), to: c.D.shiftYears(c.today, 1) };
    },

    tripLabel: function (t, c) {
      return c.plural(Math.max(0, t.end - t.start - 1), "day", "days") + " away";
    },

    evaluate: function (trips, c) {
      var worst = worstWindow(c.D, absentDays(trips));
      if (!worst.total) {
        return { ok: true, headline: "0 of 180 days away", status: "", lines: ["Mark your trips outside the UK to see your worst 12 months."] };
      }
      return {
        ok: worst.total <= 180,
        headline: worst.total + " of 180 days away in any 12 months",
        status: worst.total <= 180 ? (180 - worst.total) + " left" : c.plural(worst.total - 180, "day", "days") + " over",
        lines: ["Your worst 12 months run from " + c.label(worst.from) + " to " + c.label(worst.to) + "."]
      };
    },

    // A "days away" tracker in AtlasDays counts every day no UK stay touches,
    // so the file carries your time in the UK between past trips, starting a
    // year before the first one. Stays share the travel days with the trips,
    // which AtlasDays does not treat as an overlap.
    exportRows: function (trips, c) {
      var past = trips.filter(function (t) { return t.start <= c.today; });
      if (!past.length) return [];
      var rows = [], cursor = c.D.shiftYears(past[0].start, -1);
      past.forEach(function (t) {
        if (t.start > cursor) rows.push({ country: "United Kingdom", start: cursor, end: t.start, notes: "ILR absence calculator" });
        cursor = Math.max(cursor, t.end);
      });
      if (cursor <= c.today) rows.push({ country: "United Kingdom", start: cursor, end: null, notes: "ILR absence calculator" });
      return rows;
    },

    strings: {
      hintStart: "Tap the day you left the UK, then the day you came back.",
      hintEnd: "Now tap the other end of the trip, or {date} again to cancel.",
      hintMove: "Tap a new date for this end of the trip, or {date} again to keep it.",
      inTrip: "outside the UK",
      pending: "start of a new trip",
      held: "trip end picked up",
      empty: "No trips yet.",
      deleteTrip: "Delete trip",
      fileName: "atlasdays-uk-stays.csv"
    }
  };
})();
