(function () {
  "use strict";

  // The ?lang= redirect runs inline in the page head so it happens before
  // first paint (the AtlasDays app opens Learn articles with
  // ?lang=<its interface language>). This script handles visits without ?lang=.
  //
  // Those visits are never redirected, on any page: the reader asked for this
  // page, and a redirect based on the browser locale would override that
  // choice, break shared links, and is discouraged for crawlable pages.
  // Instead a dismissible bar offers a translation, chosen from
  // navigator.languages only. No language preference is stored.
  var locales = window.AtlasDaysPageLocales;
  if (!locales) return;

  var DISMISS_PREFIX = "lang-offer-dismissed:";
  // A dismissal expires, so the reader is not nagged but not opted out forever.
  var DISMISS_DAYS = 90;

  function dismissedRecently(code) {
    var raw;
    try {
      raw = localStorage.getItem(DISMISS_PREFIX + code);
    } catch (error) {
      return false;
    }
    if (!raw) return false;
    var at = parseInt(raw, 10);
    // A value that is not a timestamp counts as expired.
    if (!at) return false;
    return Date.now() - at < DISMISS_DAYS * 24 * 60 * 60 * 1000;
  }

  function rememberDismissal(code) {
    try {
      localStorage.setItem(DISMISS_PREFIX + code, String(Date.now()));
    } catch (error) {
      /* Storage unavailable (private mode): the offer shows again next visit. */
    }
  }

  if (new URLSearchParams(location.search).get("lang")) return;

  // Browser tag to locale matching is shared with the inline ?lang= redirect
  // that build_site.py emits above this script, so both resolve script subtags
  // (zh-Hant, zh-Hans) the same way. The fallback matches exact codes only:
  // no offer is better than a wrong one.
  var matchLocale = window.AtlasDaysMatchLocale || function (tag, map) {
    var want = String(tag || "").trim().replace(/_/g, "-").toLowerCase();
    for (var code in map) if (code.toLowerCase() === want) return code;
    return "";
  };

  // The page's own language as a one-entry map, so the same matcher decides
  // whether the reader is already on their language (en-GB on an English page
  // is; zh-Hans on a zh-Hant page is not).
  var pageLanguage = String(document.documentElement.lang || "en");
  var self = {};
  self[pageLanguage] = true;

  // First browser preference that this page actually has a translation for.
  // navigator.languages is in the reader's own priority order, so someone who
  // lists English above Dutch is not offered Dutch.
  var preferred = (navigator.languages && navigator.languages.length
    ? navigator.languages
    : [navigator.language || ""]);
  var match = null;
  for (var i = 0; i < preferred.length; i += 1) {
    var tag = String(preferred[i] || "");
    if (!tag) continue;
    // The page's own language ranks above a translation of it: an English page
    // is the right page for an en-GB reader, so stop looking.
    if (matchLocale(tag, self)) return;
    var code = matchLocale(tag, locales);
    if (code) {
      match = { code: code, entry: locales[code] };
      break;
    }
  }
  if (!match) return;
  if (match.entry.url === location.pathname) return;
  if (dismissedRecently(match.code)) return;

  function build() {
    var bar = document.createElement("div");
    bar.className = "lang-offer";
    bar.lang = match.code;

    var link = document.createElement("a");
    link.className = "lang-offer-link";
    link.href = match.entry.url;
    link.hreflang = match.code;
    link.textContent = match.entry.label;

    var close = document.createElement("button");
    close.className = "lang-offer-close";
    close.type = "button";
    close.setAttribute("aria-label", match.entry.dismiss);
    close.innerHTML = '<svg aria-hidden="true" viewBox="0 0 20 20" fill="none" width="14" height="14"><path d="m6 6 8 8M14 6l-8 8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>';
    close.addEventListener("click", function () {
      rememberDismissal(match.code);
      bar.remove();
    });

    var inner = document.createElement("div");
    inner.className = "lang-offer-inner";
    inner.append(link, close);
    bar.append(inner);
    var header = document.querySelector(".top-bar");
    if (header && header.parentNode) {
      header.parentNode.insertBefore(bar, header.nextSibling);
    } else {
      document.body.insertBefore(bar, document.body.firstChild);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", build);
  } else {
    build();
  }
})();
