(function () {
  "use strict";
  if (window.AtlasDaysCalculatorUsage) return;
  var endpoint = document.currentScript && document.currentScript.getAttribute("data-endpoint");
  var calculators = ["days183", "schengen", "ukIlr", "presence", "spt", "multiYear", "ukSrt", "feie"];
  var visits = Object.create(null);
  function permitted() {
    if (location.hostname !== "atlasdays.app" || location.protocol !== "https:" || !endpoint) return false;
    if (navigator.globalPrivacyControl || navigator.doNotTrack === "1") return false;
    try {
      var q = new URLSearchParams(location.search).get("notrack");
      return q === "off" || (q === null && !localStorage.getItem("atlasdays-notrack"));
    } catch (e) { return false; }
  }
  window.AtlasDaysCalculatorUsage = {
    create: function (calculator, placement) {
      if (calculators.indexOf(calculator) < 0 || ["standalone", "embedded"].indexOf(placement) < 0) return function () {};
      var key = calculator + ":" + placement, seen = visits[key] || (visits[key] = Object.create(null));
      return function (stage) {
        if (["started", "used", "continued"].indexOf(stage) < 0 || seen[stage] || !permitted()) return;
        seen[stage] = true;
        // Only fixed categories enter the payload. Input values never do.
        try {
          var pending = fetch(endpoint, { method: "POST", mode: "cors", credentials: "omit", referrerPolicy: "no-referrer",
            keepalive: true, headers: { "Content-Type": "text/plain;charset=UTF-8" },
            body: JSON.stringify({ calculator: calculator, placement: placement, stage: stage }) });
          if (pending && pending.catch) pending.catch(function () {});
        } catch (e) {}
      };
    }
  };
})();
