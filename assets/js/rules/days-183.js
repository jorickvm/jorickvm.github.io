/* The generic 183-day rule for the AtlasDays day calendar (assets/js/day-calendar.js).

   Days present in a country per calendar year, against 183. Any part of a day
   counts, so the day you arrive and the day you leave are both days in that
   country, and a travel day between two countries counts for both. This is
   the plain version of the test most countries start from; country rules that
   count midnights, use a different tax year or a rolling 12 months get their
   own calculators. The result leads with the country closest to 183 in the
   current year (or the latest year you marked), then lists the rest. */
(function () {
  "use strict";

  var LIMIT = 183;

  // { year: { country: Set(day) } }, each day counted once per country.
  function tally(trips, D) {
    var byYear = {};
    trips.forEach(function (t) {
      var c = t.country || "";
      for (var d = t.start; d <= t.end; d++) {
        var y = D.parts(d).y;
        byYear[y] = byYear[y] || {};
        (byYear[y][c] = byYear[y][c] || new Set()).add(d);
      }
    });
    return byYear;
  }

  window.AtlasDaysRules = window.AtlasDaysRules || {};
  window.AtlasDaysRules.days183 = {
    travelDaysCount: true,
    singleDayTrips: true,
    carryCountry: true,

    // Last year, this year and next, whole calendar years.
    range: function (c) {
      var y = c.D.parts(c.today).y;
      return { from: c.D.fromParts(y - 1, 1, 1), to: c.D.fromParts(y + 1, 12, 31) };
    },

    tripLabel: function (t, c) {
      return c.text("tripDays", { n: t.end - t.start + 1 });
    },

    evaluate: function (trips, c) {
      var byYear = tally(trips, c.D);
      var years = Object.keys(byYear).map(Number).sort(function (a, b) { return b - a; });
      if (!years.length) return { headlineText: c.text("headlineEmpty"), lines: [c.text("emptyResult")], ok: true };
      var now = c.D.parts(c.today).y;
      var focus = byYear[now] ? now : years[0];
      function rows(year) {
        return Object.keys(byYear[year]).map(function (code) { return { code: code, n: byYear[year][code].size }; })
          .sort(function (a, b) { return (a.code ? 0 : 1) - (b.code ? 0 : 1) || b.n - a.n; });
      }
      var main = rows(focus), top = main[0];
      var headline = top.code
        ? c.text("headline", { country: c.placeName(top.code), n: top.n, year: focus })
        : c.text("headlineNoCountry", { n: top.n, year: focus });
      var lines = [];
      function line(year, r) {
        lines.push(r.code ? c.text("line", { country: c.placeName(r.code), n: r.n, year: year })
          : c.text("lineNoCountry", { n: r.n, year: year }));
      }
      main.slice(1).forEach(function (r) { line(focus, r); });
      years.filter(function (y) { return y !== focus; }).forEach(function (y) { rows(y).forEach(function (r) { line(y, r); }); });
      return {
        headlineText: headline,
        statusText: top.n >= LIMIT ? c.text("reached") : c.text("left", { n: LIMIT - top.n }),
        ok: top.n < LIMIT,
        lines: lines.slice(0, 6)
      };
    },

    // Every stay with a country, past and planned.
    exportRows: function (trips) {
      return trips.filter(function (t) { return t.country; }).map(function (t) {
        return { country: t.country, start: t.start, end: t.end, notes: "183-day calculator" };
      });
    },

    strings: {
      hintStart: "Tap the day you arrived in a country, then the day you left.",
      hintEnd: "Now tap the other end of the stay, or {date} again to make it one day.",
      hintSelected: "Drag either end of the stay to change its dates, or delete it below.",
      inTrip: "in a country",
      pending: "start of a new stay",
      empty: "No stays yet.",
      deleteTrip: "Delete stay",
      country: "Country",
      addCountry: "Add country",
      noMatch: "No matching country",
      tripDays: { one: "{n} day", other: "{n} days" },
      headline: "{country}: {n} of 183 days in {year}",
      headlineNoCountry: "{n} of 183 days in {year}",
      headlineEmpty: "0 of 183 days",
      left: "{n} left",
      reached: "183 reached",
      line: { one: "{country}: {n} day in {year}", other: "{country}: {n} days in {year}" },
      lineNoCountry: { one: "{n} day without a country in {year}", other: "{n} days without a country in {year}" },
      emptyResult: "Mark the days you spent in a country to count them per calendar year.",
      fileName: "atlasdays-stays.csv"
    }
  };
})();
