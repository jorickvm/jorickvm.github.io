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

  var currentLanguage = String(document.documentElement.lang || "en").toLowerCase().split("-")[0];

  // First browser preference that this page actually has a translation for.
  // navigator.languages is in the reader's own priority order, so someone who
  // lists English above Dutch is not offered Dutch.
  var preferred = (navigator.languages && navigator.languages.length
    ? navigator.languages
    : [navigator.language || ""]);
  var match = null;
  for (var i = 0; i < preferred.length; i += 1) {
    var base = String(preferred[i] || "").toLowerCase().split("-")[0];
    if (!base) continue;
    // The page's own language ranks above a translation of it: an English page
    // is the right page for an en-GB reader, so stop looking.
    if (base === currentLanguage) return;
    if (locales[base]) {
      match = { code: base, entry: locales[base] };
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
