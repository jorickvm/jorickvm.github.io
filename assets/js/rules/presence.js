/* Physical presence over five years, for the AtlasDays day calendar
   (assets/js/day-calendar.js): the permanent-residence and citizenship tests
   that need a number of days in one country before a date.

   Each article embeds it set to its own program (data-cal-preset settings):
     country      the one country the stays are in (CA, US, NZ)
     need         the days to reach (730, 1095, 913)
     before       true when the five years end the day before the date
                  (Canadian citizenship: the eligibility period runs to the
                  day before you sign)
     note         English label for exported stays (read by the importer)

   It counts what the app's presets count, every day in full (Jorick,
   2026-10-06: the website does not run ahead of the app). Canada's half-day
   credit before permanent residence and New Zealand's 240 days in each year
   wait for the app; the articles explain both.

   Any day a stay touches counts, arrival and departure included: the rules
   either count any part of a day (Canada PR, New Zealand) or subtract only
   whole days abroad (Canadian citizenship, US naturalization), which is the
   same count seen from the other side. Overlapping stays count once.

   The card reads like the app's tracker card set to "Reach target": days
   present against the need, "N days needed" until "Target reached". */
(function () {
  "use strict";

  function dateSetting(c, key, fallback) {
    var iso = c.settings[key];
    if (!iso) return fallback;
    var p = iso.split("-").map(Number);
    var n = c.D.fromParts(p[0], p[1], p[2]);
    return n === null ? fallback : n;
  }
  function window5(c) {
    var on = dateSetting(c, "checkOn", c.today), end = c.settings.before ? on - 1 : on;
    return { on: on, from: c.D.shiftYears(end, -5) + 1, to: end };
  }
  function presentDays(trips) {
    var set = new Set();
    trips.forEach(function (t) { for (var d = t.start; d <= t.end; d++) set.add(d); });
    return set;
  }
  function count(set, from, to) {
    var n = 0;
    set.forEach(function (d) { if (d >= from && d <= to) n++; });
    return n;
  }

  window.AtlasDaysRules = window.AtlasDaysRules || {};
  window.AtlasDaysRules.presence = {
    travelDaysCount: true,
    singleDayTrips: true,
    quietHint: true,
    fixedRange: true,

    countries: function (all, preset) { return preset && preset.country ? [preset.country] : all; },

    range: function (c) { var w = window5(c); return { from: w.from, to: w.to }; },

    tripLabel: function (t, c) { return c.text("tripDays", { n: t.end - t.start + 1 }); },

    evaluate: function (trips, c) {
      var w = window5(c), set = presentDays(trips), need = +c.settings.need || 1095;
      var days = count(set, w.from, w.to);
      var controls = [
        { type: "date", key: "checkOn", icon: "calendar", label: c.text("checkOn"), caption: c.text("checkOnCaption"), value: c.D.iso(w.on), display: c.dateRange(w.on, w.on), moveCalendar: true }
      ];
      var needed = need - days;
      return {
        controls: controls,
        meter: { title: c.text("title"), flag: c.settings.country, label: c.dateRange(w.from, w.to), days: days, limit: need, tone: c.tone(days, need, true) },
        statusText: needed > 0 ? c.text("needed", { n: needed }) : c.text("reachedTarget"),
        lines: []
      };
    },

    exportRows: function (trips, c) {
      return trips.map(function (t) {
        return { country: t.country || c.settings.country, start: t.start, end: t.end, notes: c.settings.note || "Presence calculator" };
      });
    },

    strings: {
      hintStart: "Tap a day to add a stay.",
      hintEnd: "Tap the other end of the stay.",
      hintSelected: "Drag either end of the stay to change its dates, or delete it below.",
      inTrip: "present",
      pending: "start of a new stay",
      empty: "No stays yet.",
      deleteTrip: "Delete stay",
      title: "Days present",
      checkOn: "Count up to",
      checkOnCaption: "The five years up to this date. Pick the date you plan to apply.",
      tripDays: { one: "{n} day", other: "{n} days" },
      needed: { one: "{n} day needed", other: "{n} days needed" },
      reachedTarget: "Target reached",
      fileName: "atlasdays-presence-stays.csv"
    }
  };
})();
