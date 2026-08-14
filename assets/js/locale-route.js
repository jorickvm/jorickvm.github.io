(function () {
  "use strict";

  // The redirect half of this lives inline in the page head, because it has to
  // beat first paint: the AtlasDays app opens a Learn article with
  // ?lang=<its interface language>, and a flash of English before the swap is
  // worse than no swap. What is left here is the case with no ?lang= at all.
  //
  // That case deliberately does NOT redirect. A reader who searched in English
  // and clicked an English result asked for this page, and bouncing them
  // somewhere else on the strength of their browser locale takes the choice
  // away and is advised against for crawlable pages. Offer, do not move.
  var locales = window.AtlasDaysPageLocales;
  if (!locales) return;
  if (new URLSearchParams(location.search).get("lang")) return;

  var STORE_PREFIX = "lang-offer-dismissed:";

  function stored(key) {
    try {
      return localStorage.getItem(key);
    } catch (error) {
      return null;
    }
  }

  function remember(key) {
    try {
      localStorage.setItem(key, "1");
    } catch (error) {
      /* Private mode. The banner comes back next visit, which is survivable. */
    }
  }

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
    if (locales[base]) {
      match = { code: base, entry: locales[base] };
      break;
    }
    // The page's own language ranks above a translation of it: an English page
    // is the right page for an en-GB reader, so stop looking.
    if (base === String(document.documentElement.lang || "en").toLowerCase().split("-")[0]) return;
  }
  if (!match) return;
  if (match.entry.url === location.pathname) return;
  if (stored(STORE_PREFIX + match.code)) return;

  function build() {
    var bar = document.createElement("div");
    bar.className = "lang-offer";
    bar.setAttribute("role", "region");
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
      remember(STORE_PREFIX + match.code);
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
