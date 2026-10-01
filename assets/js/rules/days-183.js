/* The generic 183-day rule for the AtlasDays day calendar (assets/js/day-calendar.js).

   Days present in one country in one year-long period, against 183. Any part
   of a day counts, so the day you arrive and the day you leave are both days
   in that country, and a travel day between two countries counts for both.

   Two menus in the result box (Jorick, 2026-10-01): the country, from the
   countries marked, and the period, which is always one year long: the last
   12 months, a calendar year, or a tax year starting 6 April, 1 July or
   1 April. The calendar shows that period only; a stay that crosses its edge
   counts only its days inside. Country rules with midnights or other tests
   get their own calculators. */
(function () {
  "use strict";

  var LIMIT = 183;
  // Tax years that start on a fixed day: [key, month, day].
  var STARTS = [["cal", 1, 1], ["apr6", 4, 6], ["jul1", 7, 1], ["apr1", 4, 1]];

  function bounds(id, c) {
    var D = c.D;
    if (id === "rolling") return { from: D.shiftYears(c.today, -1) + 1, to: c.today };
    var parts = String(id).split(":"), start = STARTS.filter(function (s) { return s[0] === parts[0]; })[0] || STARTS[0];
    var y = +parts[1] || D.parts(c.today).y;
    var from = D.fromParts(y, start[1], start[2]);
    return { from: from, to: D.fromParts(y + 1, start[1], start[2]) - 1 };
  }
  function current(c) { return c.settings.period || "cal:" + c.D.parts(c.today).y; }

  function periods(c) {
    var y = c.D.parts(c.today).y, out = [{ value: "rolling", label: c.text("rolling") }];
    var groups = { cal: c.text("groupCalendar"), apr6: c.text("groupApr6"), jul1: c.text("groupJul1"), apr1: c.text("groupApr1") };
    STARTS.forEach(function (s) {
      [y - 1, y, y + 1].forEach(function (year) {
        var id = s[0] + ":" + year, b = bounds(id, c);
        out.push({ value: id, label: c.dateRange(b.from, b.to), group: groups[s[0]] });
      });
    });
    return out;
  }

  window.AtlasDaysRules = window.AtlasDaysRules || {};
  window.AtlasDaysRules.days183 = {
    travelDaysCount: true,
    singleDayTrips: true,
    carryCountry: true,
    fixedRange: true,

    range: function (c) { return bounds(current(c), c); },

    tripLabel: function (t, c) {
      return c.text("tripDays", { n: t.end - t.start + 1 });
    },

    evaluate: function (trips, c) {
      var b = bounds(current(c), c), byCountry = {};
      trips.forEach(function (t) {
        var code = t.country || "";
        for (var d = Math.max(t.start, b.from); d <= Math.min(t.end, b.to); d++) (byCountry[code] = byCountry[code] || new Set()).add(d);
      });
      var countries = Object.keys(byCountry).filter(Boolean)
        .map(function (code) { return { code: code, n: byCountry[code].size }; })
        .sort(function (x, z) { return z.n - x.n; });
      var chosen = countries.filter(function (x) { return x.code === c.settings.country; })[0] || countries[0];
      var controls = [];
      if (chosen) controls.push({
        key: "country", prefix: c.text("daysIn"), label: c.text("country"), value: chosen.code,
        options: countries.map(function (x) { return { value: x.code, label: c.placeName(x.code) }; })
      });
      controls.push({ key: "period", label: c.text("period"), value: current(c), options: periods(c), moveCalendar: true });
      var loose = byCountry[""] ? byCountry[""].size : 0, lines = [];
      if (loose) lines.push(c.text("lineNoCountry", { n: loose }));
      if (!chosen) {
        if (!loose) lines.push(c.text("emptyResult"));
        return { controls: controls, headlineText: c.text("headlineEmpty"), ok: true, lines: lines };
      }
      return {
        controls: controls,
        headlineText: c.text("headline", { n: chosen.n }),
        statusText: chosen.n >= LIMIT ? c.text("reached") : c.text("left", { n: LIMIT - chosen.n }),
        ok: chosen.n < LIMIT,
        lines: lines
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
      period: "Period",
      addCountry: "Add country",
      noMatch: "No matching country",
      daysIn: "Days in",
      rolling: "Last 12 months",
      groupCalendar: "Calendar year",
      groupApr6: "Tax year from 6 April",
      groupJul1: "Tax year from 1 July",
      groupApr1: "Tax year from 1 April",
      tripDays: { one: "{n} day", other: "{n} days" },
      headline: "{n} of 183 days",
      headlineEmpty: "0 of 183 days",
      left: "{n} left",
      reached: "183 reached",
      lineNoCountry: { one: "{n} day without a country", other: "{n} days without a country" },
      emptyResult: "Mark the days you spent in a country to count them.",
      fileName: "atlasdays-stays.csv"
    }
  };
})();
