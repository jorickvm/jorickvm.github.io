/* Personal presence counting. Reuses the calendar arithmetic, not legal presets. */
(function () {
  "use strict";
  var base = window.AtlasDaysRules.days183;
  function goal(c) { return ["stay", "reach"].indexOf(c.settings.goal) >= 0 ? c.settings.goal : "count"; }
  function limit(c) {
    var n = Number(c.settings.limitInput);
    return Number.isInteger(n) && n >= 1 && n <= 366 ? n : null;
  }
  function clean(c) {
    var s = {}, keys = ["country", "periodType", "year", "taxStart", "checkOn"];
    keys.forEach(function (key) { if (c.settings[key] != null) s[key] = c.settings[key]; });
    if (!s.taxStart) s.taxStart = c.D.iso(c.D.fromParts(Number(s.year) || c.D.parts(c.today).y, 1, 1));
    s.goal = goal(c) === "reach" ? "reach" : "stay";
    if (limit(c) !== null) s.limitInput = limit(c);
    return Object.assign({}, c, { settings: s, offer: "", offers: {} });
  }
  window.AtlasDaysRules.dayCount = Object.assign({}, base, {
    linkId: "daycount",
    fromQuery: function (q, c) {
      var s = {}, code = (q.get("country") || "").toUpperCase();
      if (c.allowed.indexOf(code) >= 0) s.country = code;
      if (["calendar", "tax", "rolling"].indexOf(q.get("period")) >= 0) s.periodType = q.get("period");
      if (/^\d{4}$/.test(q.get("year") || "") && +q.get("year") >= c.D.parts(c.today).y - 5 && +q.get("year") <= c.D.parts(c.today).y + 1) s.year = q.get("year");
      if (["stay", "reach"].indexOf(q.get("goal")) >= 0) s.goal = q.get("goal");
      var n = Number(q.get("limit"));
      if (Number.isInteger(n) && n >= 1 && n <= 366) s.limitInput = n;
      return { settings: s, link: "daycount" };
    },
    range: function (c) { return base.range(clean(c)); },
    tripLabel: function (t, c) { return base.tripLabel(t, clean(c)); },
    evaluate: function (trips, c) {
      var context = clean(c), result = base.evaluate(trips, context), selectedGoal = goal(c), chosenLimit = limit(c);
      if (!c.settings.country && context.settings.country) c.settings.country = context.settings.country;
      result.controls = result.controls.filter(function (control) {
        return control.key !== "limitInput" || selectedGoal !== "count";
      }).map(function (control) {
        if (control.key === "goal") {
          control.value = selectedGoal;
          control.options = [
            {value: "count", label: c.text("goalCount"), detail: c.text("captionCount")},
            {value: "stay", label: c.text("goalStay"), detail: c.text("captionStay")},
            {value: "reach", label: c.text("goalReach"), detail: c.text("captionReach")}
          ];
        }
        if (control.key === "limitInput") { control.value = chosenLimit === null ? "" : chosenLimit; control.label = c.text("personalDays"); control.strictInteger = true; }
        return control;
      });
      if (selectedGoal === "count" || chosenLimit === null) {
        result.meter.limit = null;
        result.meter.tone = "normal";
        result.statusText = "";
      }
      result.lines.push(c.text(selectedGoal !== "count" && chosenLimit === null ? "enterPersonalDays" : "personalCountNote"));
      return result;
    },
    trackerOffer: function (trips, c) {
      // A count-only import carries trips, not a fabricated app limit.
      return "";
    },
    exportRows: function (trips) {
      return base.exportRows(trips).map(function (row) { row.notes = "Day count calculator"; return row; });
    },
    strings: Object.assign({}, base.strings, {
      goalCount: "Count days", captionCount: "Keep a record without a limit.",
      captionStay: "Use your own personal cap.", captionReach: "Work toward your own target.",
      personalDays: "Personal day goal", enterPersonalDays: "Enter your own day limit or target. No legal allowance is assumed.",
      personalCountNote: "Counts include planned stays you enter. This is a day record, not a tax or visa assessment.",
      periodTax: "Custom year"
    })
  });
})();
