(function () {
  "use strict";

  Array.prototype.slice.call(document.querySelectorAll("[data-place-browser]")).forEach(function (browser) {
    var buttons = Array.prototype.slice.call(browser.querySelectorAll("[data-place-filter]"));
    var cards = Array.prototype.slice.call(browser.querySelectorAll("[data-place-type]"));
    var empty = browser.querySelector("[data-place-empty]");

    function filterPlaces(value) {
      var visible = 0;
      cards.forEach(function (card) {
        var show = value === "all" || card.getAttribute("data-place-type") === value;
        card.hidden = !show;
        if (show) visible += 1;
      });
      buttons.forEach(function (button) {
        button.setAttribute("aria-pressed", String(button.getAttribute("data-place-filter") === value));
      });
      if (empty) empty.hidden = visible !== 0;
    }

    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        filterPlaces(button.getAttribute("data-place-filter"));
      });
    });
  });

  var roots = Array.prototype.slice.call(document.querySelectorAll("[data-library-search]"));
  if (!roots.length) return;
  var copy = window.AtlasDaysSearchStrings || {
    resultOne: "{count} result found",
    resultMany: "{count} results found",
    emptyHelp: "No matching Help article. Try a feature name, task, or shorter phrase.",
    emptyLearn: "No matching rule or guide. Try a country, US state, region, or broader topic.",
    unavailable: "Search is unavailable; browse the topics below."
  };

  // Kept characters include the CJK and Cyrillic ranges. Before this,
  // [^a-z0-9] stripped every Japanese character, so a Japanese query
  // normalised to "" and scored every entry at 1 - the search silently
  // returned the whole list. Cyrillic was the same bug waiting for Russian:
  // "\u0442\u0440\u0435\u043a\u0435\u0440" also normalised to "".
  var CJK = "\u3040-\u309f\u30a0-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uff66-\uff9f";
  var CYRILLIC = "\u0400-\u04ff\u0500-\u052f";
  var STRIP = new RegExp("[^a-z0-9" + CJK + CYRILLIC + "]+", "g");
  // Scripts that delimit words with spaces, so a query can be split into
  // terms. Cyrillic belongs here; CJK deliberately does not.
  var HAS_SEGMENTED_WORD = new RegExp("[a-z0-9" + CYRILLIC + "]");

  function normalize(value) {
    // Fold accents on Latin letters so Dutch queries such as "Georgië" and
    // "georgie" behave alike, without decomposing Japanese kana into a
    // different search term. Recompose non-Latin scripts before stripping.
    var folded = String(value || "").toLowerCase().normalize("NFD")
      .replace(/([a-z])[\u0300-\u036f]+/g, "$1")
      .normalize("NFC");
    // The site writes ё where it belongs, per the app translation guidelines,
    // but readers routinely type е for it. Fold so "счетчик" finds "счётчик".
    folded = folded.replace(/ё/g, "е");
    // Turkish dotless ı has no decomposition, so the Latin fold above skips it
    // and STRIP then deletes it outright: "genel bakış" normalised to
    // "genel bak s" and "sınır" to "s n r", which shredded 86 of the 103
    // Turkish titles into single letters. Fold it to i, which keeps the word
    // whole and lets an ASCII query ("genel bakis") reach it, exactly as ü and
    // ş already fold. Dotted İ needs no rule of its own: toLowerCase leaves
    // i + U+0307 and the combining-mark strip above removes the dot.
    folded = folded.replace(/\u0131/g, "i");
    return folded.replace(STRIP, " ").replace(/\bdays\b/g, "day").trim();
  }

  // Japanese does not delimit words with spaces, so splitting on whitespace
  // produces one long token and the stop-word pass is meaningless. Such a
  // query is scored on substring containment alone. That gives exact and
  // prefix matching rather than morphological search, which is enough for a
  // few dozen articles carrying translated synonyms.
  function isSpaceless(query) {
    return query.length > 0 && !HAS_SEGMENTED_WORD.test(query);
  }

  // Words that carry no signal on their own. Dropping them lets a natural
  // question ("how do i add a trip") be judged on "add" and "trip" alone.
  var STOP_WORDS = [
    "a", "an", "and", "are", "can", "did", "do", "does", "for", "from", "get",
    "has", "have", "how", "i", "if", "in", "is", "it", "me", "my", "of", "on",
    "or", "the", "to", "what", "when", "where", "why", "with", "you", "your"
  ];

  function meaningfulTerms(query) {
    if (isSpaceless(query)) return [];
    return query.split(" ").filter(function (term) {
      return term.length > 1 && STOP_WORDS.indexOf(term) === -1;
    });
  }

  function score(entry, query) {
    if (!query) return entry.pillar ? 2 : 1;
    var title = normalize(entry.title);
    var jurisdiction = normalize(entry.jurisdiction);
    var keywords = normalize(entry.keywords.join(" "));
    var description = normalize(entry.description);
    var value = 0;

    // Whole-phrase matches stay the strongest signal.
    if (title === query) value += 160;
    else if (title.indexOf(query) === 0) value += 120;
    else if (title.indexOf(query) !== -1) value += 90;
    if (jurisdiction === query) value += 80;
    else if (jurisdiction.indexOf(query) !== -1) value += 45;
    // An exact keyword beats a keyword that merely contains the query. This
    // matters most in Japanese, where there are no word boundaries to break a
    // false match: "リセット" (reset) is a substring of "プリセット" (preset),
    // and "書き出し" of "書き出しの言語". Without this the collision outranks
    // the article the reader actually wanted.
    if (entry.keywords.some(function (word) { return normalize(word) === query; })) value += 45;
    if (keywords.indexOf(query) !== -1) value += 35;
    if (description.indexOf(query) !== -1) value += 20;

    // Then each meaningful word on its own, so a phrasing we did not
    // anticipate still reaches the right article.
    var terms = meaningfulTerms(query);
    var matched = 0;
    terms.forEach(function (term) {
      var hit = 0;
      if (title.indexOf(term) !== -1) hit = 12;
      else if (keywords.indexOf(term) !== -1) hit = 8;
      else if (jurisdiction.indexOf(term) !== -1) hit = 8;
      else if (description.indexOf(term) !== -1) hit = 5;
      if (hit) {
        matched += 1;
        value += hit;
      }
    });

    // Require most of the query to be accounted for. Without this a single
    // incidental word would surface unrelated entries.
    if (terms.length && matched * 2 < terms.length) return 0;

    if (entry.pillar && value > 0) value += query.indexOf(" ") === -1 ? 150 : 5;
    return value;
  }

  fetch("/assets/search-index.json")
    .then(function (response) {
      if (!response.ok) throw new Error("Search index unavailable");
      return response.json();
    })
    .then(function (payload) {
      roots.forEach(function (root) {
        var section = root.getAttribute("data-section");
        // A hub only ever searches its own language: the Japanese Help hub
        // must not return English articles it cannot link to sensibly.
        var lang = root.getAttribute("data-lang") || "en";
        var entries = payload.entries.filter(function (entry) {
          return entry.section === section && (entry.lang || "en") === lang;
        });
        var input = root.querySelector("[data-search-input]");
        var filter = root.querySelector("[data-search-filter]");
        var clear = root.querySelector("[data-search-clear]");
        var close = root.querySelector("[data-search-close]");
        var status = root.querySelector("[data-search-status]");
        var results = root.querySelector("[data-search-results]");
        var initialStatus = status.textContent;
        var resultsId = section + "-search-results";
        var mobileSearch = root.hasAttribute("data-simple-search") && window.matchMedia("(max-width: 640px)");
        var mobilePlaceholder = null;

        results.id = resultsId;
        input.setAttribute("aria-controls", resultsId);
        input.setAttribute("aria-expanded", "false");

        function syncMobileViewport() {
          if (!root.classList.contains("search-mobile-active")) return;
          var viewport = window.visualViewport;
          root.style.setProperty("--search-viewport-top", (viewport ? viewport.offsetTop : 0) + "px");
          root.style.setProperty("--search-viewport-height", (viewport ? viewport.height : window.innerHeight) + "px");
        }

        function openMobileSearch() {
          if (!mobileSearch || !mobileSearch.matches || root.classList.contains("search-mobile-active")) return;
          mobilePlaceholder = document.createComment("library search position");
          root.parentNode.insertBefore(mobilePlaceholder, root);
          document.body.appendChild(root);
          root.classList.add("search-mobile-active");
          root.setAttribute("role", "dialog");
          root.setAttribute("aria-modal", "true");
          document.documentElement.classList.add("search-overlay-open");
          syncMobileViewport();
          input.focus({ preventScroll: true });
        }

        function closeMobileSearch() {
          if (!root.classList.contains("search-mobile-active")) return;
          input.blur();
          root.classList.remove("search-mobile-active");
          root.removeAttribute("role");
          root.removeAttribute("aria-modal");
          document.documentElement.classList.remove("search-overlay-open");
          root.style.removeProperty("--search-viewport-top");
          root.style.removeProperty("--search-viewport-height");
          if (mobilePlaceholder && mobilePlaceholder.parentNode) {
            mobilePlaceholder.parentNode.insertBefore(root, mobilePlaceholder);
            mobilePlaceholder.remove();
          }
          mobilePlaceholder = null;
          render(false);
        }

        function render(showResults) {
          var query = normalize(input.value);
          var category = filter ? filter.value : "";
          var active = Boolean(query || category);
          var matches = entries
            .map(function (entry) { return { entry: entry, score: score(entry, query) }; })
            .filter(function (item) {
              // score() already discards entries that match too little of the
              // query, so any positive score here is a genuine hit.
              return (!category || item.entry.category === category) && (!query || item.score > 0);
            })
            .sort(function (a, b) {
              return b.score - a.score
                || a.entry.title.length - b.entry.title.length
                || a.entry.title.localeCompare(b.entry.title);
            });

          results.replaceChildren();
          results.hidden = !active || showResults === false;
          clear.hidden = !query;
          input.setAttribute("aria-expanded", String(active && showResults !== false));
          status.textContent = active
            ? (matches.length === 1 ? copy.resultOne : copy.resultMany).replace("{count}", matches.length)
            : initialStatus;
          if (!active) return;
          if (!matches.length) {
            var empty = document.createElement("p");
            empty.className = "search-empty";
            empty.textContent = section === "help" ? copy.emptyHelp : copy.emptyLearn;
            results.appendChild(empty);
            return;
          }
          matches.slice(0, 12).forEach(function (item) {
            var link = document.createElement("a");
            link.className = "search-result";
            link.href = item.entry.url;
            var heading = document.createElement("strong");
            heading.textContent = item.entry.title;
            var copy = document.createElement("span");
            copy.textContent = item.entry.description;
            link.append(heading, copy);
            results.appendChild(link);
          });
        }

        input.addEventListener("input", function () { render(true); });
        input.addEventListener("focus", function () {
          openMobileSearch();
          render(true);
        });
        if (filter) {
          filter.addEventListener("change", function () { render(true); });
          filter.addEventListener("focus", function () {
            if (input.value || filter.value) render(true);
          });
        }
        clear.addEventListener("click", function () {
          input.value = "";
          render(Boolean(filter && filter.value));
          input.focus();
        });
        if (close) close.addEventListener("click", closeMobileSearch);
        root.addEventListener("keydown", function (event) {
          if (event.key !== "Escape") return;
          if (root.classList.contains("search-mobile-active")) {
            closeMobileSearch();
            return;
          }
          if (results.hidden) return;
          render(false);
        });
        document.addEventListener("click", function (event) {
          if (!root.contains(event.target) && !results.hidden) render(false);
        });
        if (window.visualViewport) {
          window.visualViewport.addEventListener("resize", syncMobileViewport);
          window.visualViewport.addEventListener("scroll", syncMobileViewport);
        }
        if (mobileSearch) {
          mobileSearch.addEventListener("change", function (event) {
            if (!event.matches) closeMobileSearch();
          });
        }
        render(false);
      });
    })
    .catch(function () {
      roots.forEach(function (root) {
        root.querySelector("[data-search-status]").textContent = copy.unavailable;
      });
    });
})();
