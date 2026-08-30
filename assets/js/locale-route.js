(function () {
  "use strict";

  // The redirect half of this lives inline in the page head, because it has to
  // beat first paint: the AtlasDays app opens a Learn article with
  // ?lang=<its interface language>, and a flash of English before the swap is
  // worse than no swap. What is left here is the case with no ?lang= at all.
  //
  // That case deliberately does NOT redirect, on any page, the homepage
  // included. A reader who searched in English and clicked an English result
  // asked for this page, and bouncing them somewhere else on the strength of
  // their browser locale takes the choice away, breaks every shared link, and
  // is advised against for crawlable pages. Offer, do not move.
  //
  // The offer is derived from navigator.languages and nothing else. An earlier
  // version also remembered the language you last clicked in the switcher and
  // ranked that above your browser preferences; a single stray click then stuck
  // that language to the browser forever, with no expiry and no way to see why.
  // A guess that a reader can wave away is fine. A guess that outlives the
  // reason for it is not, so there is no stored preference here any more.
  var locales = window.AtlasDaysPageLocales;
  if (!locales) return;

  var DISMISS_PREFIX = "lang-offer-dismissed:";
  // A dismissal is "not now", not "never". Ninety days is long enough that
  // nobody is nagged, short enough that a language added later still gets one
  // chance with a reader who dismissed a different one long ago.
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
    // Anything unparseable is a dismissal written by the older build, which
    // stored "1" and meant forever. Treat it as expired rather than honouring
    // a decision with no date on it.
    if (!at) return false;
    return Date.now() - at < DISMISS_DAYS * 24 * 60 * 60 * 1000;
  }

  function rememberDismissal(code) {
    try {
      localStorage.setItem(DISMISS_PREFIX + code, String(Date.now()));
    } catch (error) {
      /* Private mode. The banner comes back next visit, which is survivable. */
    }
  }

  if (new URLSearchParams(location.search).get("lang")) return;

  // Matching a browser tag to a locale is shared with the ?lang= redirect that
  // build_site.py inlines above this script, and must stay shared. This used to
  // truncate the tag with split("-")[0] and look up locales[base], which was
  // right while every locale code was two letters and silently broke the moment
  // one carried a script: the map is keyed zh-Hant and the lookup asked for zh,
  // so Taiwan, Hong Kong and Macau readers were never offered Chinese at all.
  // The fallback is deliberately conservative -- no offer beats the wrong one.
  var matchLocale = window.AtlasDaysMatchLocale || function (tag, map) {
    var want = String(tag || "").trim().replace(/_/g, "-").toLowerCase();
    for (var code in map) if (code.toLowerCase() === want) return code;
    return "";
  };

  // The page's own language, as a one-entry map so the same matcher decides it.
  // A plain base-code compare said an en-GB reader is home on an English page,
  // which is right, and would also say a zh-Hans reader is home on a zh-Hant
  // page, which is wrong and becomes reachable the moment Simplified ships.
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
