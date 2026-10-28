/* One absence against a limit, for the AtlasDays day calendar
   (assets/js/day-calendar.js): the app's per-entry days-away trackers
   (TrackerDayCountCore.currentAbsence), the "do not stay away longer than"
   rules of green cards, residence permits and benefits.

   The trips are absences from the home places. An absence counts its whole
   days away: the day you leave and the day you come back are days at home,
   as in the app's days-away trackers and the UK ILR calculator. Trips abroad
   that share a day are one absence.

   The card measures one absence, as the app's tracker does (Jorick,
   2026-10-28, plan phase 1): the one running on the "Count up to" date
   (today unless the visitor picks another), or otherwise the latest one
   before it. A planned trip is checked by picking the day you come back, as
   on the ILR calculator.

   Each article embeds it set to its own programme (data-cal-preset settings):
     away     true: absences (days in the country per visit are the
              sibling rule perVisit, below)
     home     the place codes an absence is from: one code ("US"), a list,
              or a named set ("EU")
     stay     with a set, the country exported as the home stays (ES for
              Spain's long-term residents, who count absence from the EU)
     limit    the last permitted number of days away (the app preset's)
     flag     optional: the card's flag (a named set shows its own)
     note     English label for exported rows (read by the importer)

   The card reads like the app's tracker card: days away in that absence
   against the limit, and the pill with the days left. The article explains
   the rule. */
(function () {
  "use strict";

  // Named home sets, the app's own lists: EU is
  // CountryLists.europeanUnionTerritoryCodes (the 27 and their territories).
  // Schengen is CountryLists.schengenCountryCodes, as in schengen.js.
  var SETS = {
    EU: ["AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV",
      "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE", "GF", "GP", "MQ", "YT", "RE", "MF", "AX"],
    Schengen: ["AT", "BE", "BG", "HR", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IS", "IT", "LV", "LI",
      "LT", "LU", "MC", "MT", "NL", "NO", "PL", "PT", "RO", "SK", "SI", "SM", "ES", "SE", "CH", "VA", "GI"]
  };
  function homeList(h) { h = h || []; return typeof h === "string" ? (SETS[h] || [h]) : h; }
  function homes(c) { return homeList(c.settings.home); }
  function limitOf(c) { return +c.settings.limit || 180; }
  function checkOn(c) {
    var iso = c.settings.checkOn;
    if (!iso) return c.today;
    var p = iso.split("-").map(Number);
    return c.D.fromParts(p[0], p[1], p[2]) || c.today;
  }
  // Trips that touch or overlap (France to the 10th, Spain from the 10th) are
  // one absence: the handoff day was spent abroad.
  function absences(trips) {
    var out = [];
    trips.slice().sort(function (a, b) { return a.start - b.start; }).forEach(function (t) {
      var last = out[out.length - 1];
      if (last && t.start <= last.end) last.end = Math.max(last.end, t.end);
      else out.push({ start: t.start, end: t.end });
    });
    return out;
  }
  // The absence the card measures on `on`: the one running then, or the
  // latest before it. Merged absences never overlap, so that is the last one
  // to start before `on`. Its days away stop at `on` while it runs.
  function measured(trips, on) {
    var pick = null;
    absences(trips).forEach(function (a) { if (a.start < on) pick = a; });
    if (!pick) return null;
    var to = Math.min(pick.end - 1, on);
    return { from: pick.start + 1, to: to, days: Math.max(0, to - pick.start) };
  }

  window.AtlasDaysRules = window.AtlasDaysRules || {};
  window.AtlasDaysRules.perEntry = {
    travelDaysCount: false,
    singleDayTrips: false,
    quietHint: true,
    fixedRange: true,

    // Trips are absences, so they can be anywhere but home.
    countries: function (all, preset) {
      var home = homeList(preset && preset.home);
      return all.filter(function (code) { return home.indexOf(code) < 0; });
    },

    // Enough past for the longest absence the limit allows to show whole.
    range: function (c) {
      var on = checkOn(c);
      return { from: c.D.shiftYears(on, -(Math.floor(limitOf(c) / 365) + 1)) + 1, to: on };
    },

    // A trip's own whole days away. The day it takes over from another trip
    // abroad counts here, so the cards add up to the absence.
    tripLabel: function (t, c) {
      var takesOver = (c.trips || []).some(function (o) { return o !== t && o.end === t.start; });
      return c.text("tripAway", { n: Math.max(0, t.end - t.start - 1) + (takesOver ? 1 : 0) });
    },

    evaluate: function (trips, c) {
      var on = checkOn(c), limit = limitOf(c), a = measured(trips, on);
      var days = a ? a.days : 0, left = limit - days;
      return {
        controls: [{ type: "date", key: "checkOn", icon: "calendar", label: c.text("checkOn"), caption: c.text("checkOnCaption"), value: c.D.iso(on), display: c.dateRange(on, on), moveCalendar: true }],
        meter: { title: c.text("title"), flag: c.settings.flag || (SETS[c.settings.home] ? c.settings.home : homes(c)[0]), label: days ? c.dateRange(a.from, a.to) : c.dateRange(on, on), days: days, limit: limit, tone: c.tone(days, limit, false) },
        statusText: left > 0 ? c.text("remaining", { n: left }) : left === 0 ? c.text("atLimit") : c.text("overBy", { n: -left }),
        lines: []
      };
    },

    linkId: "per-entry",
    // The embed's app preset (its article's app_preset).
    trackerOffer: function (trips, c) { return c.offer; },

    // A days-away tracker in AtlasDays counts the days no home stay touches,
    // so the file carries the time at home between past trips, starting a
    // year before the first one, as the ILR calculator's does.
    exportRows: function (trips, c) {
      var home = c.settings.stay || homes(c)[0], note = c.settings.note || "Absence calculator";
      var past = trips.filter(function (t) { return t.start <= c.today; });
      if (!past.length) return trips.filter(function (t) { return t.country; }).map(function (t) { return { country: t.country, start: t.start, end: t.end, notes: note }; });
      var rows = [], cursor = c.D.shiftYears(past[0].start, -1);
      past.forEach(function (t) {
        if (t.start > cursor) rows.push({ country: home, start: cursor, end: t.start, notes: note });
        cursor = Math.max(cursor, t.end);
      });
      if (cursor <= c.today) rows.push({ country: home, start: cursor, end: null, notes: note });
      // Trips given a country go in too (past and planned), so the app shows
      // where the time away was spent.
      trips.forEach(function (t) { if (t.country) rows.push({ country: t.country, start: t.start, end: t.end, notes: note }); });
      rows.sort(function (x, y) { return x.start - y.start; });
      return rows;
    },

    strings: {
      hintStart: "Tap the day you left, then the day you came back.",
      hintEnd: "Tap the other end of the trip.",
      hintSelected: "Drag either end of the trip to change its dates, or delete it below.",
      inTrip: "away",
      pending: "start of a new trip",
      empty: "No trips yet.",
      deleteTrip: "Delete trip",
      country: "Country",
      addCountry: "Add country",
      noMatch: "No matching country",
      tripAway: { one: "{n} day away", other: "{n} days away" },
      title: "Days away",
      checkOn: "Count up to",
      checkOnCaption: "The absence running on this date, or the last one before it. For a planned trip, pick the day you come back.",
      remaining: { one: "{n} day remaining", other: "{n} days remaining" },
      atLimit: "At limit",
      overBy: { one: "Over limit by {n} day", other: "Over limit by {n} days" },
      fileName: "atlasdays-stays.csv"
    }
  };

  /* One visit against a limit (plan phase 4, 2026-10-28): the app's
     per-entry stay trackers (TrackerDayCountCore.perEntryStays and
     currentEntry), the "stay no longer than N days per entry" rules of
     visitor visas and visa exemptions. A sibling rule, not a setting, because
     a one-day visit counts as a day in the country while one day away is no
     whole day of absence.

     The trips are stays in the country. Every day a stay touches counts,
     the arrival day as day 1. Stays that overlap or follow on consecutive
     days are one visit, because no exit lies between them. The card measures
     the visit running on the "Count up to" date, or otherwise the latest one
     before it, its days stopping at that date while it runs.

     Settings (data-cal-preset):
       country     the places a visit is in: a code ("JP") or a named set
                   ("Schengen")
       limit       the days the visit may last (the app preset's)
       daysControl true where the app asks for the days granted (the
                   Schengen single-entry visa, Mexico's FMM): a Days field,
                   up to `limit`
       flag        optional: the card's flag (a named set shows its own)
       note        English label for exported rows (read by the importer) */
  function visitLimit(c) { return +c.settings.limitInput || +c.settings.limit || 90; }
  function visits(trips) {
    var out = [];
    trips.slice().sort(function (a, b) { return a.start - b.start; }).forEach(function (t) {
      var last = out[out.length - 1];
      if (last && t.start <= last.end + 1) last.end = Math.max(last.end, t.end);
      else out.push({ start: t.start, end: t.end });
    });
    return out;
  }
  function measuredVisit(trips, on) {
    var pick = null;
    visits(trips).forEach(function (v) { if (v.start <= on) pick = v; });
    if (!pick) return null;
    var to = Math.min(pick.end, on);
    return { from: pick.start, to: to, days: to - pick.start + 1 };
  }

  window.AtlasDaysRules.perVisit = {
    travelDaysCount: true,
    singleDayTrips: true,
    quietHint: true,
    fixedRange: true,

    // Stays are in the country (or one of the set's), so one place is fixed.
    countries: function (all, preset) {
      var places = homeList(preset && preset.country);
      return places.length ? all.filter(function (code) { return places.indexOf(code) >= 0; }) : all;
    },

    range: function (c) {
      var on = checkOn(c);
      return { from: c.D.shiftYears(on, -(Math.floor(visitLimit(c) / 365) + 1)) + 1, to: on };
    },

    tripLabel: function (t, c) { return c.text("tripDays", { n: t.end - t.start + 1 }); },

    evaluate: function (trips, c) {
      var on = checkOn(c), limit = visitLimit(c), v = measuredVisit(trips, on), controls = [];
      var days = v ? v.days : 0, left = limit - days, country = c.settings.country;
      if (c.settings.daysControl) controls.push({ type: "number", key: "limitInput", icon: "number", label: c.text("days"), value: limit, min: 1, max: +c.settings.limit || 90 });
      controls.push({ type: "date", key: "checkOn", icon: "calendar", label: c.text("checkOn"), caption: c.text("checkOnCaption"), value: c.D.iso(on), display: c.dateRange(on, on), moveCalendar: true });
      return {
        controls: controls,
        meter: { title: c.text("title"), flag: c.settings.flag || (SETS[country] ? country : homeList(country)[0]), label: days ? c.dateRange(v.from, v.to) : c.dateRange(on, on), days: days, limit: limit, tone: c.tone(days, limit, false) },
        statusText: left > 0 ? c.text("remaining", { n: left }) : left === 0 ? c.text("atLimit") : c.text("overBy", { n: -left }),
        lines: []
      };
    },

    linkId: "per-visit",
    // The embed's app preset, with the days granted where the visitor set them.
    trackerOffer: function (trips, c) {
      if (!c.offer) return "";
      return c.offer + (c.settings.daysControl && c.settings.limitInput ? ",days:" + visitLimit(c) : "");
    },

    // The stays themselves, past and planned: a per-entry tracker counts them.
    exportRows: function (trips, c) {
      var note = c.settings.note || "Stay calculator";
      return trips.filter(function (t) { return t.country; }).map(function (t) { return { country: t.country, start: t.start, end: t.end, notes: note }; });
    }
  };
})();
