/* The US substantial presence test for the AtlasDays day calendar
   (assets/js/day-calendar.js). Internal Revenue Code § 7701(b)(3): the test
   is met for a year when you were in the United States at least 31 days that
   year and the weighted total reaches 183: every day of that year, one third
   of the days of the year before, one sixth of the days of the year before
   that. Any part of a day counts. The fractions are kept until the
   comparison (120 + 40 + 20 = 180 does not meet it; 120 + 40 + 25 = 185 does).

   The calendar shows the three calendar years; the reader picks the year to
   test. Goal works as on the 183-day calculator: staying below shows the
   days left before the test is met (182 is the last weighted total that does
   not meet it), reaching shows the days still needed. Days a visa class or
   medical condition exempts are left out by not marking them. */
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
  // One decimal where a third or a sixth leaves a fraction, so the total
  // shown is the one compared.
  function show(x) { return Math.abs(x - Math.round(x)) < 1e-9 ? String(Math.round(x)) : (Math.floor(x * 10) / 10).toFixed(1); }

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
      var total = d0 + d1 / 3 + d2 / 6;
      // Days still to add in the tested year until both minimums are met.
      var toMeet = Math.max(CURRENT_MIN - d0, Math.ceil(NEED - total - 1e-9), 0);
      var met = toMeet === 0;
      var lines = [
        c.text("lineYear0", { year: y, n: d0 }),
        c.text("lineYear1", { year: y - 1, n: d1, x: show(d1 / 3) }),
        c.text("lineYear2", { year: y - 2, n: d2, x: show(d2 / 6) }),
        c.text(d0 >= CURRENT_MIN ? "lineMinMet" : "lineMinShort", { n: d0 })
      ];
      var status, shownLimit = target ? NEED : NEED - 1;
      if (target) status = met ? c.text("reachedTarget") : c.text("needed", { n: toMeet });
      else status = met ? c.text("met") : toMeet === 1 ? c.text("atLimit") : c.text("remaining", { n: toMeet - 1 });
      return {
        controls: [
          { key: "goal", icon: "target", label: c.text("goal"), value: setting(c, "goal"), options: [
            { value: "stay", label: c.text("goalStay"), detail: c.text("captionStay") },
            { value: "reach", label: c.text("goalReach"), detail: c.text("captionReach") }
          ] },
          { key: "year", icon: "calendar", label: c.text("year"), value: String(y), options: years, moveCalendar: true }
        ],
        meter: { title: c.text("title"), flag: "US", label: c.text("meterLabel", { total: show(total), year: y }), days: Math.floor(total + 1e-9), limit: shownLimit,
          tone: target ? c.tone(total, NEED, true) : c.tone(total, NEED - 1, false) },
        statusText: status,
        lines: lines
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
      title: "Weighted days",
      meterLabel: "{total} weighted days for {year}",
      goal: "Goal",
      goalStay: "Stay below",
      goalReach: "Reach target",
      captionStay: "Stay a nonresident for US tax.",
      captionReach: "Meet the test.",
      year: "Year",
      tripDays: { one: "{n} day", other: "{n} days" },
      lineYear0: { one: "{year}: {n} day, counted in full", other: "{year}: {n} days, counted in full" },
      lineYear1: { one: "{year}: {n} day, a third is {x}", other: "{year}: {n} days, a third is {x}" },
      lineYear2: { one: "{year}: {n} day, a sixth is {x}", other: "{year}: {n} days, a sixth is {x}" },
      lineMinMet: "At least 31 days in the year tested: yes",
      lineMinShort: "At least 31 days in the year tested: not yet",
      remaining: { one: "{n} day remaining", other: "{n} days remaining" },
      atLimit: "At limit",
      met: "Test met",
      needed: { one: "{n} day needed", other: "{n} days needed" },
      reachedTarget: "Test met",
      fileName: "atlasdays-us-stays.csv"
    }
  };
})();
