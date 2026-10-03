/* The generic 183-day rule for the AtlasDays day calendar (assets/js/day-calendar.js).

   Days present in one country in one year-long period, against 183. Any part
   of a day counts, so the day you arrive and the day you leave are both days
   in that country, and a travel day between two countries counts for both.

   The result box (Jorick, 2026-10-03) reads like an app tracker:
     Days in [flag Country]  [Calendar year | Tax year | Last 12 months] [2026 | first day]
     6 Apr 2026 – 5 Apr 2027                                  108 / 183
     ======================-----------
     [75 days remaining]
   The country is the one being checked; new stays start with it. A calendar
   year comes with a year menu (next year back to five years ago), a tax year
   with a date field for its first day, the last 12 months with nothing more.
   The calendar shows that period only. The pill and colours are the app's
   (TrackerCard: "N days remaining", "At limit", "Over limit by N days"). */
(function () {
  "use strict";

  var LIMIT = 183;

  function defaults(c) {
    var p = c.D.parts(c.today), aprilSixth = c.D.fromParts(p.y, 4, 6);
    return {
      periodType: "calendar",
      year: String(p.y),
      // the UK tax year as the starting point: 6 April of the current one
      taxStart: c.D.iso(c.today >= aprilSixth ? aprilSixth : c.D.fromParts(p.y - 1, 4, 6))
    };
  }
  function setting(c, key) { return c.settings[key] || defaults(c)[key]; }

  function bounds(c) {
    var D = c.D, type = setting(c, "periodType");
    if (type === "rolling") return { from: D.shiftYears(c.today, -1) + 1, to: c.today };
    if (type === "tax") {
      var iso = setting(c, "taxStart").split("-").map(Number), from = D.fromParts(iso[0], iso[1], iso[2]);
      return { from: from, to: D.shiftYears(from, 1) - 1 };
    }
    var y = +setting(c, "year");
    return { from: D.fromParts(y, 1, 1), to: D.fromParts(y, 12, 31) };
  }

  window.AtlasDaysRules = window.AtlasDaysRules || {};
  window.AtlasDaysRules.days183 = {
    travelDaysCount: true,
    singleDayTrips: true,
    fixedRange: true,

    range: function (c) { return bounds(c); },
    newTripCountry: function (c) { return c.settings.country || ""; },

    tripLabel: function (t, c) {
      return c.text("tripDays", { n: t.end - t.start + 1 });
    },

    evaluate: function (trips, c) {
      var b = bounds(c), byCountry = {};
      trips.forEach(function (t) {
        var code = t.country || "";
        for (var d = Math.max(t.start, b.from); d <= Math.min(t.end, b.to); d++) (byCountry[code] = byCountry[code] || new Set()).add(d);
      });
      // Without a choice yet, check the country with the most days.
      if (!c.settings.country) {
        var top = Object.keys(byCountry).filter(Boolean).sort(function (x, z) { return byCountry[z].size - byCountry[x].size; })[0];
        if (top) c.settings.country = top;
      }
      var country = c.settings.country || "";
      var y = c.D.parts(c.today).y, years = [];
      for (var k = y + 1; k >= y - 5; k--) years.push({ value: String(k), label: String(k) });
      var type = setting(c, "periodType");
      var controls = [
        { type: "country", key: "country", prefix: c.text("daysIn"), label: c.text("country"), value: country },
        { key: "periodType", label: c.text("period"), value: type, moveCalendar: true, options: [
          { value: "calendar", label: c.text("periodCalendar") },
          { value: "tax", label: c.text("periodTax") },
          { value: "rolling", label: c.text("periodRolling") }
        ] }
      ];
      if (type === "calendar") controls.push({ key: "year", label: c.text("year"), value: setting(c, "year"), options: years, moveCalendar: true });
      if (type === "tax") controls.push({ type: "date", key: "taxStart", prefix: c.text("taxStart"), value: setting(c, "taxStart"), moveCalendar: true });

      var days = country && byCountry[country] ? byCountry[country].size : 0;
      var loose = byCountry[""] ? byCountry[""].size : 0, lines = [];
      if (loose) lines.push(c.text("lineNoCountry", { n: loose }));
      if (!trips.length) lines.push(c.text("emptyResult"));
      var left = LIMIT - days;
      return {
        controls: controls,
        meter: { label: c.dateRange(b.from, b.to), days: days, limit: LIMIT, tone: c.tone(days, LIMIT) },
        statusText: left > 0 ? c.text("remaining", { n: left }) : left === 0 ? c.text("atLimit") : c.text("overBy", { n: -left }),
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
      addCountry: "Add country",
      noMatch: "No matching country",
      daysIn: "Days in",
      period: "Period",
      periodCalendar: "Calendar year",
      periodTax: "Tax year",
      periodRolling: "Last 12 months",
      year: "Year",
      taxStart: "First day of the tax year",
      tripDays: { one: "{n} day", other: "{n} days" },
      remaining: { one: "{n} day remaining", other: "{n} days remaining" },
      atLimit: "At limit",
      overBy: { one: "Over limit by {n} day", other: "Over limit by {n} days" },
      lineNoCountry: { one: "{n} day without a country", other: "{n} days without a country" },
      emptyResult: "Mark the days you spent in a country to count them.",
      fileName: "atlasdays-stays.csv"
    }
  };
})();
