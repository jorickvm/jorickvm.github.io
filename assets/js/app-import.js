/* atlasdays.app/app/import/: where an "Open in AtlasDays" link from a
   calculator lands when the app is not installed (go.atlasdays.app forwards
   here with the fragment unchanged). The link format is owned by the app repo:
   AtlasDays/Docs/reference/IMPORT_LINK.md.

   Loaded before the analytics script on purpose: the stays leave the address
   bar first (kept in this tab's sessionStorage), so no analytics request can
   ever carry them. Then the page offers the App Store, Open in AtlasDays again
   (the go. link, which works once the app is installed), and the CSV file. */
(function () {
  "use strict";
  var KEY = "atlasdays-import";
  var frag = "";
  try {
    if (/(^|&)v=/.test(location.hash.slice(1))) {
      frag = location.hash.slice(1);
      sessionStorage.setItem(KEY, frag);
      history.replaceState(null, "", location.pathname + location.search);
    } else {
      frag = sessionStorage.getItem(KEY) || "";
    }
  } catch (e) {
    frag = location.hash.slice(1);
  }

  // The English page sends readers on to their language's version, if the
  // site has one; the stays wait in sessionStorage.
  if (document.documentElement.lang === "en" && frag) {
    var tags = [];
    (navigator.languages || [navigator.language || ""]).forEach(function (l) {
      var parts = String(l).split("-");
      for (var n = parts.length; n > 0; n--) { var t = parts.slice(0, n).join("-"); if (tags.indexOf(t) < 0) tags.push(t); }
    });
    tags = tags.filter(function (t) { return !/^en(-|$)/i.test(t) && /^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$/.test(t); });
    (function next(i) {
      if (i >= tags.length) return;
      var path = "/" + tags[i] + "/app/import/";
      fetch(path, { method: "HEAD", credentials: "same-origin" })
        .then(function (r) { if (r.ok) location.replace(path); else next(i + 1); })
        .catch(function () { next(i + 1); });
    })(0);
  }

  function rows() {
    var q = {};
    frag.split("&").forEach(function (pair) { var i = pair.indexOf("="); if (i > 0) q[pair.slice(0, i)] = pair.slice(i + 1); });
    if (q.v !== "1" || !q.b || !q.s) return [];
    var b = Date.parse(q.b + "T00:00:00Z");
    if (isNaN(b)) return [];
    var note = "";
    try { note = decodeURIComponent(q.n || ""); } catch (e) {}
    var day = function (offset) { return new Date(b + offset * 86400000).toISOString().slice(0, 10); };
    return q.s.split(",").map(function (stay) {
      var f = stay.split(":"), start = +f[1];
      if (!/^[A-Z]{2}$/.test(f[0]) || !/^\d+$/.test(f[1]) || !/^\d*$/.test(f[2] || "")) return null;
      return [f[0], day(start), f[2] ? day(start + +f[2]) : "", note];
    }).filter(Boolean);
  }

  function ready() {
    var main = document.querySelector("[data-app-import]");
    if (!main) return;
    var list = rows();
    main.querySelector("[data-app-import-ready]").hidden = !list.length;
    main.querySelector("[data-app-import-empty]").hidden = !!list.length;
    if (!list.length) return;
    main.querySelectorAll("[data-app-import-open]").forEach(function (a) { a.href = "https://go.atlasdays.app/import/#" + frag; });
    main.querySelectorAll("[data-app-import-download]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var field = function (v) { return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; };
        var csv = ["Country,Start Date,End Date,Notes"].concat(list.map(function (r) { return r.map(field).join(","); })).join("\r\n") + "\r\n";
        var a = document.createElement("a");
        a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
        a.download = main.getAttribute("data-file-name") || "atlasdays-stays.csv";
        document.body.appendChild(a); a.click();
        setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
      });
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ready); else ready();
})();
