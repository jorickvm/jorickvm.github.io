/* The generic 183-day rule for the AtlasDays day calendar (assets/js/day-calendar.js).

   Days present in one country in one year-long period, against 183. Any part
   of a day counts, so the day you arrive and the day you leave are both days
   in that country, and a travel day between two countries counts for both.

   The result box (Jorick, 2026-10-03) reads like an app tracker:
     choices, above the card:
       [flag Country] [Stay under 183 days | Reach 183 days] [Calendar year | Tax year | Last 12 months] [2026 | from 6 Apr 2026]
     the card, as the app's tracker card:
       flag Country                                   [75 days remaining]
     6 Apr 2026 – 5 Apr 2027                                  108 / 183
     ======================-----------
     [75 days remaining]
   The country is the one being checked; new stays start with it. A calendar
   year comes with a year menu (next year back to five years ago), a tax year
   with a date field for its first day, the last 12 months with nothing more.
   The calendar shows that period only. The pill and colours are the app's
   (TrackerCard: "N days remaining", "At limit", "Over limit by N days"; for a
   target, "N more days needed" and "Target reached" in green), as is the
   choice between a limit and a target (the tracker editor's "Stay Below" /
   "Reach Target"): some people want to become resident somewhere. */
(function () {
  "use strict";

  var LIMIT = 183;

  function defaults(c) {
    var p = c.D.parts(c.today), aprilSixth = c.D.fromParts(p.y, 4, 6);
    return {
      goal: "stay",
      periodType: "calendar",
      year: String(p.y),
      // the UK tax year as the starting point: 6 April of the current one
      taxStart: c.D.iso(c.today >= aprilSixth ? aprilSixth : c.D.fromParts(p.y - 1, 4, 6))
    };
  }
  function setting(c, key) { return c.settings[key] || defaults(c)[key]; }
  function countUpTo(c) {
    var iso = c.settings.checkOn;
    if (!iso) return c.today;
    var p = iso.split("-").map(Number);
    return c.D.fromParts(p[0], p[1], p[2]) || c.today;
  }

  function bounds(c) {
    var D = c.D, type = setting(c, "periodType");
    if (type === "rolling") { var on = countUpTo(c); return { from: D.shiftYears(on, -1) + 1, to: on }; }
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
    quietHint: true,
    linkId: "183",

    range: function (c) { return bounds(c); },

    // ?country=BG&period=calendar|tax|rolling&start=07-01&resident=184: an
    // article's link opens the calculator set to its own rule. `start` is the
    // tax year's first day (the latest one not after today); `resident` is
    // the first day count that makes you resident (184 for "more than 183").
    fromQuery: function (q, c) {
      var code = (q.get("country") || "").toUpperCase();
      if (!/^[A-Z]{2}$/.test(code) || c.allowed.indexOf(code) < 0) return null;
      var s = { country: code, linkedCountry: code };
      var period = q.get("period");
      if (period === "calendar" || period === "tax" || period === "rolling") s.periodType = period;
      var start = /^(\d\d)-(\d\d)$/.exec(q.get("start") || "");
      if (start && s.periodType === "tax") {
        var y = c.D.parts(c.today).y, from = c.D.fromParts(y, +start[1], +start[2]);
        if (from !== null && from > c.today) from = c.D.fromParts(y - 1, +start[1], +start[2]);
        if (from !== null) s.taxStart = c.D.iso(from);
      }
      var resident = Math.round(+q.get("resident"));
      if (resident >= 1 && resident <= 366) s.residentAt = resident;
      return { settings: s, link: "183-" + code.toLowerCase() };
    },
    newTripCountry: function (c) { return c.settings.country || ""; },

    // A country that counts nights (Portugal) leaves out the day you leave.
    tripLabel: function (t, c) {
      return c.text("tripDays", { n: t.end - t.start + (c.settings.nights ? 0 : 1) });
    },

    evaluate: function (trips, c) {
      var b = bounds(c), byCountry = {};
      trips.forEach(function (t) {
        var code = t.country || "";
        var last = c.settings.nights ? t.end - 1 : t.end;
        for (var d = Math.max(t.start, b.from); d <= Math.min(last, b.to); d++) (byCountry[code] = byCountry[code] || new Set()).add(d);
      });
      // Without a choice yet, check the country with the most days.
      if (!c.settings.country) {
        var top = Object.keys(byCountry).filter(Boolean).sort(function (x, z) { return byCountry[z].size - byCountry[x].size; })[0];
        if (top) c.settings.country = top;
      }
      var country = c.settings.country || "";
      var y = c.D.parts(c.today).y, years = [];
      for (var k = y + 1; k >= y - 5; k--) years.push({ value: String(k), label: String(k) });
      var type = setting(c, "periodType"), target = setting(c, "goal") === "reach";
      // The settings card, as the app's tracker editor: Goal (with its
      // residence captions), Window, then Year or Starts.
      var controls = [
        { key: "goal", icon: "target", label: c.text("goal"), value: setting(c, "goal"), options: [
          { value: "stay", label: c.text("goalStay"), detail: c.text("captionStay") },
          { value: "reach", label: c.text("goalReach"), detail: c.text("captionReach") }
        ] },
        { key: "periodType", icon: "calendar", label: c.text("window"), value: type, moveCalendar: true, options: [
          { value: "calendar", label: c.text("periodCalendar") },
          { value: "tax", label: c.text("periodTax") },
          { value: "rolling", label: c.text("periodRolling") }
        ] }
      ];
      if (type === "calendar") controls.push({ key: "year", icon: "calendar", label: c.text("year"), value: setting(c, "year"), options: years, moveCalendar: true });
      if (type === "rolling") controls.push({ type: "date", key: "checkOn", icon: "calendar", label: c.text("checkOn"), caption: c.text("checkOnCaption"),
        value: c.D.iso(b.to), display: c.dateRange(b.to, b.to), moveCalendar: true });
      if (type === "tax") controls.push({ type: "date", key: "taxStart", icon: "starts", label: c.text("starts"), value: setting(c, "taxStart"),
        display: c.dateRange(b.from, b.from), moveCalendar: true });

      var days = country && byCountry[country] ? byCountry[country].size : 0;
      var loose = byCountry[""] ? byCountry[""].size : 0, lines = [];
      if (loose) lines.push(c.text("lineNoCountry", { n: loose }));
      // An embedded calculator knows its country's exact threshold
      // (residentAt: 184 for "more than 183", 183 for "183 or more"); the
      // generic page counts against 183.
      // A linked threshold belongs to the linked country only.
      var residentAt = c.settings.linkedCountry && c.settings.linkedCountry !== country ? 0 : +c.settings.residentAt || 0;
      var limit = +c.settings.limit || LIMIT;
      var safe = residentAt ? residentAt - 1 : limit, left = safe - days;
      var needed = (residentAt || limit) - days;
      // The app's wording: a limit counts down to "At limit"; a target counts
      // the days still needed until "Target reached".
      var status = target
        ? (needed > 0 ? c.text("needed", { n: needed }) : c.text("reachedTarget"))
        : (left > 0 ? c.text("remaining", { n: left }) : left === 0 ? c.text("atLimit") : c.text("overBy", { n: -left }));
      return {
        controls: controls,
        meter: { countryKey: "country", title: c.text("country"), flag: country, label: c.dateRange(b.from, b.to), days: days, limit: limit, tone: target ? c.tone(days, residentAt || limit, true) : c.tone(days, safe, false) },
        statusText: status,
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
      hintStart: "Tap a day to add a stay.",
      hintEnd: "Tap the other end of the stay.",
      hintSelected: "Drag either end of the stay to change its dates, or delete it below.",
      inTrip: "in a country",
      pending: "start of a new stay",
      empty: "No stays yet.",
      deleteTrip: "Delete stay",
      country: "Country",
      addCountry: "Add country",
      noMatch: "No matching country",
      goal: "Goal",
      goalStay: "Stay below",
      goalReach: "Reach target",
      captionStay: "Avoid tax residency.",
      captionReach: "Become a tax resident.",
      window: "Window",
      starts: "Starts",
      periodCalendar: "Calendar year",
      periodTax: "Tax year",
      periodRolling: "Last 12 months",
      year: "Year",
      tripDays: { one: "{n} day", other: "{n} days" },
      remaining: { one: "{n} day remaining", other: "{n} days remaining" },
      atLimit: "At limit",
      needed: { one: "{n} more day needed", other: "{n} more days needed" },
      reachedTarget: "Target reached",
      overBy: { one: "Over limit by {n} day", other: "Over limit by {n} days" },
      lineNoCountry: { one: "{n} day without a country", other: "{n} days without a country" },
      checkOn: "Count up to",
      checkOnCaption: "Your days in the 12 months up to this date. For a planned trip, pick its last day.",
      fileName: "atlasdays-stays.csv"
    }
  };
})();
