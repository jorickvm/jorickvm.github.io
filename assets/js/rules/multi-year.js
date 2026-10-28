/* Tax residence day tests that look back over earlier tax years, for the
   AtlasDays day calendar (assets/js/day-calendar.js). The app's
   MultiYearTrackerRule.swift, which owns the law and the numbers:

   - Ireland (TCA 1997 s. 819): 183 days in the calendar year, or 280 across
     this year and last. A year counts toward the 280 only above 30 days, and
     the 280 applies only once this year is above 30.
   - Mauritius (Income Tax Act 1995 s. 73(a)): 183 days in the July-to-June
     income year, or 270 across it and the two before.
   - India (Income-tax Act 2025 s. 6): 182 days in the April-to-March tax
     year. Once the four previous tax years hold 365 days, the limit is 60, or
     120 for visiting citizens and people of Indian origin with Indian income
     above ₹15 lakh. The person's situation, asked as the app's editor asks
     it (nationality, situation, Indian income), decides which.

   The card is the app's: Ireland and Mauritius show a bar per test at its
   stated number and one "Day test met" pill; India is an ordinary
   single-limit card, whose Stay Below shows the last safe day. Unlike the
   app's card, which counts up to today, every marked day counts, planned
   ones included, as on every calculator here. */
(function () {
  "use strict";

  var SPECS = {
    ireland: { country: "IE", startMonth: 1, annual: 183, second: { prior: 1, need: 280, creditAbove: 30, applicableAbove: 30 } },
    mauritius: { country: "MU", startMonth: 7, annual: 183, second: { prior: 2, need: 270, creditAbove: 0, applicableAbove: null } },
    india: { country: "IN", startMonth: 4, annual: 182, lookback: { prior: 4, need: 365 } }
  };
  // India's situations (MultiYearSituation raw values) and the limit each
  // takes once the lookback holds; none keeps 182.
  var REDUCED = { nri: 0, nriHighIncome: 120, resident: 60, leavingForWork: 0, foreign: 60 };

  function spec(c) { return SPECS[c.settings.spec] || SPECS.ireland; }
  function taxYearOf(c, n) {
    var p = c.D.parts(n), s = spec(c).startMonth;
    return p.m + 1 < s ? p.y - 1 : p.y;
  }
  function setting(c, key) {
    return c.settings[key] || { goal: "stay", year: String(taxYearOf(c, c.today)), nationality: "indian", presence: "visiting", income: "upTo" }[key];
  }
  // The app's three questions, folded into its one stored answer.
  function situation(c) {
    if (setting(c, "nationality") === "other") return "foreign";
    var where = setting(c, "presence");
    if (where === "living") return "resident";
    if (where === "work") return "leavingForWork";
    return setting(c, "income") === "above" ? "nriHighIncome" : "nri";
  }
  function bounds(c, y) {
    var s = spec(c).startMonth;
    return { from: c.D.fromParts(y, s, 1), to: c.D.fromParts(y + 1, s, 1) - 1 };
  }
  // Earlier tax years the rule reads: the second test's, or India's lookback
  // when the situation can lower the limit.
  function priorYears(c) {
    var sp = spec(c);
    if (sp.second) return sp.second.prior;
    return REDUCED[situation(c)] ? sp.lookback.prior : 0;
  }
  function daysIn(trips, b) {
    var set = new Set();
    trips.forEach(function (t) { for (var d = Math.max(t.start, b.from); d <= Math.min(t.end, b.to); d++) set.add(d); });
    return set.size;
  }

  window.AtlasDaysRules = window.AtlasDaysRules || {};
  window.AtlasDaysRules.multiYear = {
    travelDaysCount: true,
    singleDayTrips: true,
    quietHint: true,
    fixedRange: true,
    linkId: "multi-year",
    // The app's preset for the year tested, with the goal and India's situation.
    trackerOffer: function (trips, c) {
      if (!c.offer) return "";
      return c.offer + ",goal:" + setting(c, "goal") + ",year:" + setting(c, "year") + (spec(c).lookback ? ",situation:" + situation(c) : "");
    },

    countries: function (all, preset) { return [SPECS[(preset && preset.spec) || "ireland"].country]; },

    range: function (c) {
      var y = +setting(c, "year");
      return { from: bounds(c, y - priorYears(c)).from, to: bounds(c, y).to };
    },

    tripLabel: function (t, c) { return c.text("tripDays", { n: t.end - t.start + 1 }); },

    evaluate: function (trips, c) {
      var sp = spec(c), y = +setting(c, "year"), target = setting(c, "goal") === "reach", now = taxYearOf(c, c.today), years = [];
      for (var k = now + 1; k >= now - 5; k--) {
        var b = bounds(c, k);
        years.push({ value: String(k), label: sp.startMonth === 1 ? String(k) : c.dateRange(b.from, b.to) });
      }
      var controls = [
        { key: "goal", icon: "target", label: c.text("goal"), value: setting(c, "goal"), options: [
          { value: "stay", label: c.text("goalStay"), detail: c.text("captionStay") },
          { value: "reach", label: c.text("goalReach"), detail: c.text("captionReach") }
        ] },
        { key: "year", icon: "calendar", label: c.text("year"), value: String(y), options: years, moveCalendar: true }
      ];
      var current = daysIn(trips, bounds(c, y)), prior = [];
      for (var i = 1; i <= priorYears(c); i++) prior.push(daysIn(trips, bounds(c, y - i)));
      var here = bounds(c, y);

      if (sp.lookback) {
        // India's questions, each shown once the one before it allows it.
        controls.push({ key: "nationality", icon: "idcard", label: c.text("nationality"), value: setting(c, "nationality"), moveCalendar: true, options: [
          { value: "indian", label: c.text("nationalityIndian"), short: c.text("nationalityIndianShort") },
          { value: "other", label: c.text("nationalityOther"), short: c.text("nationalityOtherShort") }
        ] });
        if (setting(c, "nationality") !== "other") {
          controls.push({ key: "presence", icon: "person", label: c.text("situation"), value: setting(c, "presence"), moveCalendar: true, options: [
            { value: "living", label: c.text("situationLiving"), short: c.text("situationLivingShort") },
            { value: "visiting", label: c.text("situationVisiting"), short: c.text("situationVisitingShort") },
            { value: "work", label: c.text("situationWork"), short: c.text("situationWorkShort") }
          ] });
          if (setting(c, "presence") === "visiting") controls.push({ key: "income", icon: "rupee", label: c.text("income"), value: setting(c, "income"), moveCalendar: true, options: [
            { value: "upTo", label: c.text("incomeUpTo") },
            { value: "above", label: c.text("incomeAbove") }
          ] });
        }
        var reduced = REDUCED[situation(c)], before = prior.reduce(function (a, b) { return a + b; }, 0);
        var residentAt = reduced && before >= sp.lookback.need ? reduced : sp.annual;
        if (reduced) controls.push({ type: "value", key: "limit", icon: "calendar", label: c.text("limitThisYear"),
          value: c.text("tripDays", { n: residentAt }), caption: c.text("lookbackCaption", { n: before }) });
        // As the 183-day calculator: Stay Below counts to the last safe day.
        var safe = residentAt - 1, left = safe - current, needed = residentAt - current;
        return {
          controls: controls,
          meter: { title: c.text("title"), flag: sp.country, label: c.dateRange(here.from, here.to), days: current, limit: target ? residentAt : safe,
            tone: target ? c.tone(current, residentAt, true) : c.tone(current, safe, false) },
          statusText: target
            ? (needed > 0 ? c.text("needed", { n: needed }) : c.text("reachedTarget"))
            : (left > 0 ? c.text("remaining", { n: left }) : left === 0 ? c.text("atLimit") : c.text("overBy", { n: -left })),
          lines: []
        };
      }

      var t = sp.second, credit = function (n) { return n > t.creditAbove ? n : 0; };
      var progress = current + prior.map(credit).reduce(function (a, b) { return a + b; }, 0);
      var applies = t.applicableAbove == null || current > t.applicableAbove;
      var secondMet = applies && credit(current) + prior.map(credit).reduce(function (a, b) { return a + b; }, 0) >= t.need;
      var met = current >= sp.annual || secondMet;
      var span = { from: bounds(c, y - t.prior).from, to: here.to };
      return {
        controls: controls,
        meter: {
          title: c.text("title"), flag: sp.country, label: c.dateRange(here.from, here.to), days: current, limit: sp.annual,
          tone: current >= sp.annual ? (target ? "achieved" : "warning") : "normal",
          more: [{ label: c.dateRange(span.from, span.to), days: progress, limit: t.need,
            tone: secondMet ? (target ? "achieved" : "warning") : "normal" }]
        },
        statusText: c.text(met ? "met" : "notMet"),
        statusTone: met ? (target ? "achieved" : "critical") : "normal",
        // Ireland's minimum, always, as the app's card does.
        lines: t.applicableAbove == null ? [] : [c.text("minimum", { year: y })]
      };
    },

    exportRows: function (trips, c) {
      return trips.map(function (t) { return { country: spec(c).country, start: t.start, end: t.end, notes: c.settings.note || "Tax residence calculator" }; });
    },

    strings: {
      hintStart: "Tap a day to add a stay.",
      hintEnd: "Tap the other end of the stay.",
      hintSelected: "Drag either end of the stay to change its dates, or delete it below.",
      inTrip: "in the country",
      pending: "start of a new stay",
      empty: "No stays yet.",
      deleteTrip: "Delete stay",
      title: "Country",
      goal: "Goal",
      goalStay: "Stay below",
      goalReach: "Reach target",
      captionStay: "Avoid tax residency.",
      captionReach: "Become a tax resident.",
      year: "Year",
      tripDays: { one: "{n} day", other: "{n} days" },
      remaining: { one: "{n} day remaining", other: "{n} days remaining" },
      atLimit: "At limit",
      needed: { one: "{n} more day needed", other: "{n} more days needed" },
      reachedTarget: "Target reached",
      overBy: { one: "Over limit by {n} day", other: "Over limit by {n} days" },
      // The app's wording (MultiYearTrackerRule.swift, MultiYearTrackerPresentation.swift)
      met: "Day test met",
      notMet: "Day test not met",
      minimum: "Requires at least 31 days in {year}.",
      nationality: "Nationality",
      nationalityIndian: "Indian citizen or of Indian origin",
      nationalityIndianShort: "Indian",
      nationalityOther: "Other nationality",
      nationalityOtherShort: "Other",
      situation: "Situation",
      situationLiving: "Living in India",
      situationLivingShort: "In India",
      situationVisiting: "Visiting India from abroad",
      situationVisitingShort: "Visiting",
      situationWork: "Leaving India to work abroad",
      situationWorkShort: "Working abroad",
      income: "Indian income",
      incomeUpTo: "Up to ₹15 lakh",
      incomeAbove: "Above ₹15 lakh",
      limitThisYear: "Limit this year",
      lookbackCaption: { one: "{n} day in India in the four tax years before.", other: "{n} days in India in the four tax years before." },
      fileName: "atlasdays-stays.csv"
    }
  };
})();
