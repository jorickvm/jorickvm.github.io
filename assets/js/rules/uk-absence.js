/* UK absence rule for the AtlasDays day calendar (assets/js/day-calendar.js).

   ILR continuous residence: no more than 180 whole days outside the UK in any
   12-month period, the qualifying period counted back from the date that
   helps most (the application date or up to 28 days after it, CR 1.1).
   Naturalisation: 450 whole days in five years and 90 in the final 12 months
   (270 in three years on the spouse route).
   Whole days only: the day you leave and the day you return are not absences. */
(function () {
  "use strict";

  function absentDays(trips) {
    var set = new Set();
    trips.forEach(function (t) { for (var d = t.start + 1; d < t.end; d++) set.add(d); });
    return set;
  }
  function countIn(set, from, to) {
    var n = 0;
    set.forEach(function (d) { if (d >= from && d <= to) n++; });
    return n;
  }
  // Highest total in any 12-month window inside [start, end]; the worst
  // window always ends on an absence day, so only those are checked.
  function worstWindow(D, set, start, end) {
    var days = Array.from(set).filter(function (d) { return d >= start && d <= end; }).sort(function (a, b) { return a - b; });
    var best = { total: 0, from: start, to: end };
    days.forEach(function (e) {
      var from = Math.max(start, D.shiftYears(e, -1) + 1), total = 0;
      for (var i = 0; i < days.length; i++) if (days[i] >= from && days[i] <= e) total++;
      if (total > best.total) best = { total: total, from: from, to: e };
    });
    return best;
  }

  var MODES = {
    "ilr-5": { kind: "ilr", years: 5 },
    "ilr-10": { kind: "ilr", years: 10 },
    "cit": { kind: "cit", years: 5, cap: 450 },
    "cit-spouse": { kind: "cit", years: 3, cap: 270 }
  };

  window.AtlasDaysRules = window.AtlasDaysRules || {};
  window.AtlasDaysRules.ukAbsence = {
    travelDaysCount: false,

    // Until the reader picks an application date, it follows the plan: today,
    // or the end of the last planned trip, so future trips count straight away.
    settings: function (root, trips, today) {
      var D = window.AtlasDaysCalendar.D;
      var refInput = root.querySelector('[data-cal-setting="ref"]');
      var ref = refInput.dataset.userSet === "1" ? D.parse(refInput.value) : null;
      if (ref == null) {
        ref = today;
        (trips || []).forEach(function (t) { ref = Math.max(ref, t.end); });
        refInput.value = D.iso(ref);
      }
      return { ref: ref, mode: MODES[root.querySelector('[data-cal-setting="mode"]').value] || MODES["ilr-5"] };
    },

    range: function (c) {
      var D = c.D, s = c.settings;
      return { from: D.shiftYears(s.ref, -s.mode.years), to: Math.max(s.ref, D.shiftYears(c.today, 1)) };
    },

    tripLabel: function (t, c) {
      return c.plural(Math.max(0, t.end - t.start - 1), "day", "days") + " away";
    },

    evaluate: function (trips, c) {
      var D = c.D, s = c.settings, m = s.mode, label = c.label, plural = c.plural;
      var set = absentDays(trips);
      var start = D.shiftYears(s.ref, -m.years) + 1;

      if (m.kind === "ilr") {
        var worst = worstWindow(D, set, start, s.ref);
        var lines = worst.total
          ? ["Your worst 12 months run from " + label(worst.from) + " to " + label(worst.to) + "."]
          : ["Tap the calendar to add your trips outside the UK."];
        if (worst.total > 180) {
          for (var shift = 1; shift <= 28; shift++) {
            var w2 = worstWindow(D, set, D.shiftYears(s.ref + shift, -m.years) + 1, s.ref + shift);
            if (w2.total <= 180) {
              lines.push("Applying on " + label(s.ref + shift) + " instead would bring it to " + plural(w2.total, "day", "days") + ".");
              break;
            }
          }
        }
        return {
          ok: worst.total <= 180,
          headline: worst.total + " of 180 days away in any 12 months",
          status: worst.total <= 180 ? (180 - worst.total) + " left" : plural(worst.total - 180, "day", "days") + " over",
          lines: lines
        };
      }

      var total = countIn(set, start, s.ref);
      var finalYear = countIn(set, D.shiftYears(s.ref, -1) + 1, s.ref);
      var ok = total <= m.cap && finalYear <= 90;
      return {
        ok: ok,
        headline: total + " of " + m.cap + " days away in " + m.years + " years",
        status: ok ? "Within both limits" : total > m.cap ? plural(total - m.cap, "day", "days") + " over" : "Final year over",
        lines: [
          finalYear + " of 90 days away in the final 12 months.",
          "You also need to have been in the UK on " + label(start) + "."
        ]
      };
    },

    // A "days away" tracker in AtlasDays counts every day no UK stay touches,
    // so the file carries your time in the UK between past trips. Stays share
    // the travel days with the trips, which AtlasDays does not treat as overlap.
    exportRows: function (trips, c) {
      var D = c.D, s = c.settings, rows = [];
      var cursor = D.shiftYears(s.ref, -s.mode.years) + 1;
      trips.forEach(function (t) {
        if (t.start > c.today || t.end < cursor) return;
        if (t.start > cursor) rows.push({ country: "United Kingdom", start: cursor, end: t.start, notes: "UK absence calculator" });
        cursor = Math.max(cursor, t.end);
      });
      if (cursor <= c.today) rows.push({ country: "United Kingdom", start: cursor, end: null, notes: "UK absence calculator" });
      return rows;
    },

    strings: {
      hintStart: "Tap the day you left the UK, then the day you came back.",
      hintEnd: "Now tap the other end of the trip, or {date} again to cancel.",
      inTrip: "outside the UK",
      pending: "start of a new trip",
      empty: "No trips yet.",
      deleteTrip: "Delete trip",
      fileName: "atlasdays-uk-stays.csv"
    }
  };
})();
