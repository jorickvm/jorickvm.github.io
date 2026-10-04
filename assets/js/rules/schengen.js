/* The Schengen 90/180 rule for the AtlasDays day calendar (assets/js/day-calendar.js).

   At most 90 days in the Schengen Area in any 180-day period. Any part of a
   day counts, so the day you arrive and the day you leave are both days in
   the area, and a day spent in two Schengen countries counts once. The
   countries are the app's own list (CountryLists.schengenCountryCodes).

   The card reads like the app's tracker card: days used in the 180 days
   that end on the date being checked (today unless the visitor picks another,
   such as a planned entry), against 90, with the app's pill ("N days
   remaining", "At limit", "Over limit by N days"). The calendar shows exactly
   those 180 days (Jorick, 2026-10-04), like the EU's own calculator. During a
   stay the count can only rise (each day in the area adds one, at most one
   old day drops out), so checking a planned trip's last day checks the whole
   trip. */
(function () {
  "use strict";

  var LIMIT = 90, WINDOW = 180;
  var SCHENGEN = ["AT", "BE", "BG", "HR", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IS", "IT", "LV", "LI",
    "LT", "LU", "MC", "MT", "NL", "NO", "PL", "PT", "RO", "SK", "SI", "SM", "ES", "SE", "CH", "VA"];

  function checkOn(c) {
    var iso = c.settings.checkOn;
    if (!iso) return c.today;
    var p = iso.split("-").map(Number);
    return c.D.fromParts(p[0], p[1], p[2]) || c.today;
  }
  // Every day in the area, once, however many stays or countries touch it.
  function daysIn(trips) {
    var set = new Set();
    trips.forEach(function (t) { for (var d = t.start; d <= t.end; d++) set.add(d); });
    return set;
  }
  function usedOn(set, day) {
    var n = 0;
    for (var d = day - WINDOW + 1; d <= day; d++) if (set.has(d)) n++;
    return n;
  }

  window.AtlasDaysRules = window.AtlasDaysRules || {};
  window.AtlasDaysRules.schengen = {
    travelDaysCount: true,
    singleDayTrips: true,
    quietHint: true,
    fixedRange: true,
    carryCountry: true,
    linkId: "schengen",

    countries: function (all) { return all.filter(function (code) { return SCHENGEN.indexOf(code) >= 0; }); },

    range: function (c) {
      var on = checkOn(c);
      return { from: on - WINDOW + 1, to: on };
    },

    tripLabel: function (t, c) {
      return c.text("tripDays", { n: t.end - t.start + 1 });
    },

    evaluate: function (trips, c) {
      var on = checkOn(c), set = daysIn(trips), used = usedOn(set, on), left = LIMIT - used;
      var controls = [
        { type: "date", key: "checkOn", icon: "calendar", label: c.text("checkOn"), value: c.D.iso(on),
          display: c.dateRange(on, on), moveCalendar: true }
      ];
      var lines = [];
      var loose = trips.filter(function (t) { return !t.country; }).reduce(function (n, t) { return n + t.end - t.start + 1; }, 0);
      if (loose) lines.push(c.text("lineNoCountry", { n: loose }));
      var status = left > 0 ? c.text("remaining", { n: left }) : left === 0 ? c.text("atLimit") : c.text("overBy", { n: -left });
      return {
        controls: controls,
        meter: { title: c.text("area"), flag: "EU", label: c.dateRange(on - WINDOW + 1, on), days: used, limit: LIMIT, tone: c.tone(used, LIMIT, false) },
        statusText: status,
        lines: lines
      };
    },

    // Every stay with a country, past and planned.
    exportRows: function (trips) {
      return trips.filter(function (t) { return t.country; }).map(function (t) {
        return { country: t.country, start: t.start, end: t.end, notes: "Schengen calculator" };
      });
    },

    strings: {
      hintStart: "Tap a day to add a stay.",
      hintEnd: "Tap the other end of the stay.",
      hintSelected: "Drag either end of the stay to change its dates, or delete it below.",
      inTrip: "in the Schengen Area",
      pending: "start of a new stay",
      empty: "No stays yet.",
      deleteTrip: "Delete stay",
      country: "Country",
      addCountry: "Add country",
      noMatch: "No matching Schengen country",
      area: "Schengen Area",
      checkOn: "Check on",
      tripDays: { one: "{n} day", other: "{n} days" },
      remaining: { one: "{n} day remaining", other: "{n} days remaining" },
      atLimit: "At limit",
      overBy: { one: "Over limit by {n} day", other: "Over limit by {n} days" },
      lineNoCountry: { one: "{n} day without a country", other: "{n} days without a country" },
      fileName: "atlasdays-schengen-stays.csv"
    }
  };
})();
