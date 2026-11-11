/* atlasdays.app/app/import/: where an "Open in AtlasDays" link from a
   calculator lands when the app is not installed (go.atlasdays.app forwards
   here with the fragment unchanged). The fragment format is described in
   importFragment() in day-calendar.js.

   This script loads before the analytics script: the stays move from the
   address bar into this tab's sessionStorage first, so no analytics request
   carries them. The page then offers the App Store, Open in AtlasDays again
   (the go. link, which works once the app is installed), and the CSV file. A
   version 2 link with a tracker and no stays gets the first two only, under
   the tracker heading.

   The build writes the custom product pages per tracker preset into this
   script's data-product-pages attribute (from _site-src/data/product-pages.json),
   so the App Store button opens the page for the link's tracker. */
(function () {
  "use strict";
  var KEY = "atlasdays-import";
  var PAGES = (document.currentScript && document.currentScript.getAttribute("data-product-pages")) || "";
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

  // Use the published page map and the site's script-aware language matcher.
  // Redirect only after the import is retained in this tab, and respect an
  // explicit language or an English-first browser preference.
  if (document.documentElement.lang === "en" && frag && !new URLSearchParams(location.search).has("lang")) {
    var retained = false;
    try { retained = sessionStorage.getItem(KEY) === frag; } catch (e) {}
    var matchLocale = window.AtlasDaysMatchLocale;
    var published = window.AtlasDaysPageLocales;
    if (retained && typeof matchLocale === "function" && published) {
      var choices = { en: { url: location.pathname } };
      Object.keys(published).forEach(function (code) { choices[code] = published[code]; });
      var preferred = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || ""];
      for (var i = 0; i < preferred.length; i += 1) {
        var code = matchLocale(preferred[i], choices);
        if (!code) continue;
        if (code !== "en" && choices[code].url !== location.pathname) {
          location.replace(choices[code].url + location.search);
        }
        break;
      }
    }
  }

  function fields() {
    var q = {};
    frag.split("&").forEach(function (pair) { var i = pair.indexOf("="); if (i > 0) q[pair.slice(0, i)] = pair.slice(i + 1); });
    return q;
  }

  // Version 2 also takes a US state (US-CO) as a stay's place; the CSV
  // import reads that code in the Country column.
  function rows(q) {
    if ((q.v !== "1" && q.v !== "2") || !q.b || !q.s) return [];
    var b = Date.parse(q.b + "T00:00:00Z");
    if (isNaN(b)) return [];
    var note = "";
    try { note = decodeURIComponent(q.n || ""); } catch (e) {}
    var place = q.v === "2" ? /^(?:[A-Z]{2}|US-[A-Z]{2})$/ : /^[A-Z]{2}$/;
    var day = function (offset) { return new Date(b + offset * 86400000).toISOString().slice(0, 10); };
    return q.s.split(",").map(function (stay) {
      var f = stay.split(":"), start = +f[1];
      if (!place.test(f[0]) || !/^\d+$/.test(f[1]) || !/^\d*$/.test(f[2] || "")) return null;
      return [f[0], day(start), f[2] ? day(start + +f[2]) : "", note];
    }).filter(Boolean);
  }

  // The tracker's preset id: `p` up to its first setting.
  function preset(q) {
    var p = "";
    try { p = decodeURIComponent(q.p || ""); } catch (e) {}
    return /^[a-z0-9-]+(,|$)/.test(p) ? p.split(",")[0] : "";
  }

  function productPage(id) {
    var found = "";
    PAGES.split(",").forEach(function (pair) {
      var i = pair.indexOf("=");
      if (!found && id && i > 0 && id.indexOf(pair.slice(0, i)) === 0) found = pair.slice(i + 1);
    });
    return found;
  }

  function ready() {
    var main = document.querySelector("[data-app-import]");
    if (!main) return;
    var q = fields(), list = rows(q), id = preset(q);
    var usable = list.length > 0 || (q.v === "2" && !!id);
    main.querySelector("[data-app-import-ready]").hidden = !usable;
    main.querySelector("[data-app-import-empty]").hidden = usable;
    if (!usable) return;
    var page = productPage(id);
    if (page) main.querySelectorAll('a[href^="https://apps.apple.com/"]').forEach(function (a) { a.href += "&ppid=" + page; });
    main.querySelectorAll("[data-app-import-open]").forEach(function (a) { a.href = "https://go.atlasdays.app/import/#" + frag; });
    if (!list.length) {
      // A tracker alone: its own heading (and tab title), and no file or note,
      // which are about stays.
      var stays = main.querySelector('[data-app-import-heading="stays"]');
      var tracker = main.querySelector('[data-app-import-heading="tracker"]');
      if (stays && tracker) {
        document.title = document.title.replace(stays.textContent, tracker.textContent);
        stays.hidden = true;
        tracker.hidden = false;
      }
      [main.querySelector(".note")].concat(
        [].slice.call(main.querySelectorAll("[data-app-import-download]")).map(function (btn) { return btn.closest("p"); })
      ).forEach(function (el) { if (el) el.hidden = true; });
      return;
    }
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
