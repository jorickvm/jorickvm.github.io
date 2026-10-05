/* The US substantial presence test for the AtlasDays day calendar
   (assets/js/day-calendar.js). Internal Revenue Code § 7701(b)(3): the test
   is met for a year when you were in the United States at least 31 days that
   year and the weighted total reaches 183: every day of that year, one third
   of the days of the year before, one sixth of the days of the year before
   that. Any part of a day counts. The fractions are kept until the
   comparison (120 + 40 + 20 = 180 does not meet it; 120 + 40 + 25 = 185 does).

   The calendar shows the three calendar years; the reader picks the year to
   test. The card is the app's (SPTTrackerPresentation.swift): a bar for the
   year's days against 31, a bar for the weighted days against 183, and one
   pill saying whether both are met. Days a visa class or medical condition
   exempts are left out by not marking them. */
(function () {
  "use strict";

  var NEED = 183, CURRENT_MIN = 31;

  function setting(c, key) {
    var p = c.D.parts(c.today);
    return c.settings[key] || { goal: "stay", year: String(p.y) }[key];
  }
  function yearBounds(c, y) { return { from: c.D.fromParts(y, 1, 1), to: c.D.fromParts(y, 12, 31) }; }
  function daysIn(trips, b) {
    var set = new Set();
    trips.forEach(function (t) { for (var d = Math.max(t.start, b.from); d <= Math.min(t.end, b.to); d++) set.add(d); });
    return set.size;
  }

  window.AtlasDaysRules = window.AtlasDaysRules || {};
  window.AtlasDaysRules.spt = {
    travelDaysCount: true,
    singleDayTrips: true,
    quietHint: true,
    fixedRange: true,
    linkId: "spt",

    countries: function () { return ["US"]; },

    range: function (c) {
      var y = +setting(c, "year");
      return { from: c.D.fromParts(y - 2, 1, 1), to: c.D.fromParts(y, 12, 31) };
    },

    tripLabel: function (t, c) { return c.text("tripDays", { n: t.end - t.start + 1 }); },

    evaluate: function (trips, c) {
      var y = +setting(c, "year"), target = setting(c, "goal") === "reach", years = [];
      var thisYear = c.D.parts(c.today).y;
      for (var k = thisYear + 1; k >= thisYear - 5; k--) years.push({ value: String(k), label: String(k) });
      var d0 = daysIn(trips, yearBounds(c, y)), d1 = daysIn(trips, yearBounds(c, y - 1)), d2 = daysIn(trips, yearBounds(c, y - 2));
      // Sixths keep the comparison exact: 6 × (d0 + d1/3 + d2/6).
      var sixths = 6 * d0 + 2 * d1 + d2, met = d0 >= CURRENT_MIN && sixths >= NEED * 6;
      // As the app's card: one bar per condition, the thresholds themselves
      // (both must be met, so neither bar alone is a limit), and one pill.
      var tone = met ? (target ? "achieved" : "critical") : "normal";
      return {
        controls: [
          { key: "goal", icon: "target", label: c.text("goal"), value: setting(c, "goal"), options: [
            { value: "stay", label: c.text("goalStay"), detail: c.text("captionStay") },
            { value: "reach", label: c.text("goalReach"), detail: c.text("captionReach") }
          ] },
          { key: "year", icon: "calendar", label: c.text("year"), value: String(y), options: years, moveCalendar: true }
        ],
        meter: {
          title: c.text("title"), flag: "US", label: c.text("barYear", { year: y }), days: d0, limit: CURRENT_MIN,
          tone: d0 >= CURRENT_MIN ? (target ? "achieved" : "warning") : "normal",
          more: [{ label: c.text("barWeighted"), days: Math.floor(sixths / 6), limit: NEED, progress: sixths / (NEED * 6),
            tone: sixths >= NEED * 6 ? (target ? "achieved" : "warning") : "normal" }]
        },
        statusText: c.text(met ? "met" : "notMet"),
        statusTone: tone,
        lines: []
      };
    },

    exportRows: function (trips) {
      return trips.map(function (t) { return { country: "US", start: t.start, end: t.end, notes: "Substantial presence calculator" }; });
    },

    strings: {
      hintStart: "Tap a day to add a stay in the US.",
      hintEnd: "Tap the other end of the stay.",
      hintSelected: "Drag either end of the stay to change its dates, or delete it below.",
      inTrip: "in the US",
      pending: "start of a new stay",
      empty: "No stays yet.",
      deleteTrip: "Delete stay",
      title: "United States",
      goal: "Goal",
      goalStay: "Stay below",
      goalReach: "Reach target",
      captionStay: "Stay a nonresident for US tax.",
      captionReach: "Meet the test.",
      year: "Year",
      tripDays: { one: "{n} day", other: "{n} days" },
      // The app's wording (SPTTrackerRule.swift)
      barYear: "Days in {year}",
      barWeighted: "Weighted days",
      met: "Day thresholds met",
      notMet: "Day thresholds not met",
      fileName: "atlasdays-us-stays.csv"
    }
  };
})();
