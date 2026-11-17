/* Full days outside the FEIE non-foreign places over 12 calendar months. */
(function () {
  "use strict";
  var EXCLUDED = ["US", "PR", "GU", "MP", "VI", "AS", "XW", "AQ"], NEED = 330;
  function inSet(t) { return EXCLUDED.indexOf(t.country) >= 0; }
  function on(c) {
    if (!c.settings.checkOn) return c.today;
    var p = c.settings.checkOn.split("-").map(Number);
    return c.D.fromParts(p[0], p[1], p[2]) || c.today;
  }
  function bounds(c) { var end = on(c); return { from: c.D.shiftYears(end, -1) + 1, to: end }; }
  function excludedDays(trips, b) {
    var valid = trips.filter(function (t) { return t.end >= t.start; });
    var foreign = valid.filter(function (t) { return t.country && !inSet(t); });
    var starts = new Set(foreign.map(function (t) { return t.start; })), ends = new Set(foreign.map(function (t) { return t.end; }));
    var merged = [];
    valid.filter(inSet).slice().sort(function (a, z) { return a.start - z.start; }).forEach(function (t) {
      var last = merged[merged.length - 1];
      if (last && t.start <= last.end + 1) last.end = Math.max(last.end, t.end);
      else merged.push({ start: t.start, end: t.end });
    });
    var days = new Set();
    merged.forEach(function (t) {
      // Infer travel before clipping, including stays just outside the window.
      var from = t.start - (ends.has(t.start) ? 0 : 1), to = t.end + (starts.has(t.end) ? 0 : 1);
      for (var d = Math.max(from, b.from); d <= Math.min(to, b.to); d++) days.add(d);
    });
    return days.size;
  }
  window.AtlasDaysRules = window.AtlasDaysRules || {};
  window.AtlasDaysRules.feie = {
    travelDaysCount: false,
    singleDayTrips: true,
    quietHint: true,
    fixedRange: true,
    defaultCountry: "US",
    linkId: "us-feie",
    usageReady: function (c) { return !!c.settings.checkOn; },
    countries: function (all) { return all.indexOf("XW") >= 0 ? all : all.concat(["XW"]); },
    placeNames: { XW: "waters" },
    range: bounds,
    tripLabel: function (t, c) { return c.text("tripDays", { n: t.end - t.start + 1 }); },
    trackerOffer: function (trips, c) { return (c.offer || "tax-us-feie-physical-presence") + ",goal:reach"; },
    evaluate: function (trips, c) {
      var b = bounds(c), excluded = excludedDays(trips, b), allowance = b.to - b.from + 1 - NEED;
      var days = NEED + allowance - excluded, needed = NEED - days, left = allowance - excluded;
      var qualifying = c.settings.countView === "qualifying";
      var tone = qualifying ? c.tone(days, NEED, true)
        : left === 0 ? "warning" : c.tone(excluded, allowance, false);
      return {
        controls: [{ key: "countView", icon: "target", label: c.text("countView"), value: qualifying ? "qualifying" : "excluded",
          options: [{ value: "excluded", label: c.text("excludedView") }, { value: "qualifying", label: c.text("qualifyingView") }] },
          { type: "date", key: "checkOn", icon: "calendar", label: c.text("checkOn"), caption: c.text("checkOnCaption"),
          value: c.D.iso(b.to), display: c.dateRange(b.to, b.to), moveCalendar: true }],
        meter: { title: c.text(qualifying ? "qualifyingView" : "excludedView"), flag: "US", label: c.dateRange(b.from, b.to),
          days: qualifying ? days : excluded, limit: qualifying ? NEED : allowance, tone: tone },
        statusText: qualifying ? (needed > 0 ? c.text("needed", { n: needed }) : c.text("reachedTarget"))
          : left > 0 ? c.text("allowanceLeft", { n: left }) : left === 0 ? c.text("allowanceUsed") : c.text("allowanceOver", { n: -left }),
        lines: [qualifying ? c.text("excludedSummary", { n: excluded, limit: allowance })
          : c.text("qualifyingSummary", { n: days, target: NEED })]
      };
    },
    exportRows: function (trips) {
      // Real records only; the app derives its own travel days from them.
      return trips.filter(function (t) { return t.country; }).map(function (t) {
        return { country: t.country, start: t.start, end: t.end, notes: "FEIE calculator" };
      });
    },
    strings: {}
  };
})();
