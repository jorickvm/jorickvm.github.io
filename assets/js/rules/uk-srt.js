/* UK tax-year midnights, sufficient ties and deemed daytime visits. */
(function () {
  "use strict";

  function year(c) {
    var p = c.D.parts(c.today);
    return +c.settings.year || p.y - (p.m < 3 || (p.m === 3 && p.d < 6) ? 1 : 0);
  }
  function bounds(c, y) { return { from: c.D.fromParts(y, 4, 6), to: c.D.fromParts(y + 1, 4, 6) - 1 }; }
  function add(set, from, to) { for (var d = from; d <= to; d++) set.add(d); }
  function count(set, b) {
    var n = 0;
    set.forEach(function (d) { if (d >= b.from && d <= b.to) n++; });
    return n;
  }
  function complete(c) {
    return ["prior", "family", "accommodation", "work"].every(function (k) {
      return c.settings[k] === "yes" || c.settings[k] === "no";
    });
  }
  function facts(trips, c) {
    var y = year(c), b = bounds(c, y), days = new Set(), midnights = {}, earliest = bounds(c, y - 2).from;
    trips.forEach(function (t) {
      if (!t.country || t.end < t.start) return;
      var nights = midnights[t.country] || (midnights[t.country] = new Set());
      add(nights, Math.max(t.start, earliest), Math.min(t.end - 1, b.to));
      if (t.country === "GB") add(days, Math.max(t.start, b.from), Math.min(t.end, b.to));
    });
    var uk = midnights.GB || new Set(), nights = count(uk, b), qualifying = 0;
    days.forEach(function (d) { if (!uk.has(d)) qualifying++; });
    var previous = [count(uk, bounds(c, y - 1)), count(uk, bounds(c, y - 2))];
    var ninety = previous.some(function (n) { return n > 90; });
    var other = Math.max.apply(null, [0].concat(Object.keys(midnights).filter(function (code) { return code !== "GB"; })
      .map(function (code) { return count(midnights[code], b); })));
    var prior = c.settings.prior === "yes", country = prior && nights > 0 && nights >= other;
    var ties = ["family", "accommodation", "work"].filter(function (key) { return c.settings[key] === "yes"; }).length
      + (ninety ? 1 : 0) + (country ? 1 : 0);
    var first = prior ? (ties >= 4 ? 16 : ties === 3 ? 46 : ties === 2 ? 91 : ties === 1 ? 121 : 183)
      : (ties >= 4 ? 46 : ties === 3 ? 91 : ties === 2 ? 121 : 183);
    var deemed = prior && ties >= 3 ? Math.max(0, qualifying - 30) : 0;
    return { days: nights + deemed, first: first, ninety: ninety, previous: Math.max.apply(null, previous), country: country };
  }
  function question(key, c, caption) {
    return { key: key, icon: "person", label: c.text(key), value: c.settings[key] || "",
      options: [{ value: "", label: c.text("select") }, { value: "yes", label: c.text("yes"), detail: caption }, { value: "no", label: c.text("no") }] };
  }

  window.AtlasDaysRules = window.AtlasDaysRules || {};
  window.AtlasDaysRules.ukSrt = {
    travelDaysCount: false,
    singleDayTrips: true,
    quietHint: true,
    fixedRange: true,
    defaultCountry: "GB",
    linkId: "uk-srt",
    usageReady: complete,
    range: function (c) { return { from: bounds(c, year(c) - 2).from, to: bounds(c, year(c)).to }; },
    tripLabel: function (t, c) { return c.text("tripNights", { n: Math.max(0, t.end - t.start) }); },
    trackerOffer: function (trips, c) {
      var offer = (c.offer || "residence-united-kingdom-srt") + ",goal:" + (c.settings.goal || "stay") + ",year:" + year(c);
      ["prior", "family", "accommodation", "work"].forEach(function (key) {
        if (c.settings[key] === "yes" || c.settings[key] === "no") offer += "," + key + ":" + c.settings[key];
      });
      return offer;
    },
    evaluate: function (trips, c) {
      var y = year(c), b = bounds(c, y), f = facts(trips, c), target = c.settings.goal === "reach";
      var controls = [{ key: "goal", icon: "target", label: c.text("goal"), value: c.settings.goal || "stay", options: [
        { value: "stay", label: c.text("goalStay") }, { value: "reach", label: c.text("goalReach") }
      ] }, question("prior", c, c.text("priorCaption"))];
      if (c.settings.prior) controls.push(question("family", c, c.text("familyCaption")));
      if (c.settings.prior && c.settings.family) controls.push(question("accommodation", c, c.text("accommodationCaption")));
      if (c.settings.prior && c.settings.family && c.settings.accommodation) controls.push(question("work", c, c.text("workCaption")));
      if (complete(c)) {
        controls.push({ type: "value", key: "ninety", label: c.text("ninety"), value: c.text(f.ninety ? "ninetyYes" : "ninetyNo", { n: f.previous }) });
        if (c.settings.prior === "yes") controls.push({ type: "value", key: "countryTie", label: c.text("countryTie"), value: c.text(f.country ? "yes" : "no") });
        controls.push({ type: "value", key: "limit", label: c.text("limitThisYear"), value: c.text("tripDays", { n: f.first }) });
      }
      var thisYear = c.D.parts(c.today).y, years = [];
      for (var k = thisYear + 1; k >= Math.max(2010, thisYear - 5); k--) {
        years.push({ value: String(k), label: c.dateRange(bounds(c, k).from, bounds(c, k).from) });
      }
      controls.push({ key: "year", icon: "starts", label: c.text("starts"), value: String(y), options: years, moveCalendar: true });
      if (!complete(c)) return { controls: controls, headlineText: c.text(c.settings.prior ? "promptTies" : "promptPrior"), lines: [] };
      var limit = f.first - (target ? 0 : 1), left = limit - f.days;
      return {
        controls: controls,
        meter: { title: c.text("title"), flag: "GB", label: c.dateRange(b.from, b.to), days: f.days, limit: limit, tone: c.tone(f.days, limit, target) },
        statusText: target ? (left > 0 ? c.text("needed", { n: left }) : c.text("reachedTarget"))
          : (left > 0 ? c.text("remaining", { n: left }) : left === 0 ? c.text("atLimit") : c.text("overBy", { n: -left })),
        lines: []
      };
    },
    exportRows: function (trips) {
      return trips.filter(function (t) { return t.country; }).map(function (t) {
        return { country: t.country, start: t.start, end: t.end, notes: "UK SRT calculator" };
      });
    },
    strings: {}
  };
})();
