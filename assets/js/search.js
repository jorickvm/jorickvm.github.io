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

  function normalize(value) {
    return String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").replace(/\bdays\b/g, "day").trim();
  }

  function score(entry, query) {
    if (!query) return entry.pillar ? 2 : 1;
    var title = normalize(entry.title);
    var jurisdiction = normalize(entry.jurisdiction);
    var keywords = normalize(entry.keywords.join(" "));
    var description = normalize(entry.description);
    var value = 0;
    if (title === query) value += 160;
    else if (title.indexOf(query) === 0) value += 120;
    else if (title.indexOf(query) !== -1) value += 90;
    if (jurisdiction === query) value += 80;
    else if (jurisdiction.indexOf(query) !== -1) value += 45;
    if (keywords.indexOf(query) !== -1) value += 35;
    if (description.indexOf(query) !== -1) value += 20;
    query.split(" ").forEach(function (term) {
      if (term.length > 1 && title.indexOf(term) !== -1) value += 8;
    });
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
        var entries = payload.entries.filter(function (entry) { return entry.section === section; });
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
              return (!category || item.entry.category === category) && (!query || item.score > 0);
            })
            .sort(function (a, b) { return b.score - a.score || a.entry.title.localeCompare(b.entry.title); });

          results.replaceChildren();
          results.hidden = !active || showResults === false;
          clear.hidden = !query;
          input.setAttribute("aria-expanded", String(active && showResults !== false));
          status.textContent = active ? matches.length + (matches.length === 1 ? " result found" : " results found") : initialStatus;
          if (!active) return;
          if (!matches.length) {
            var empty = document.createElement("p");
            empty.className = "search-empty";
            empty.textContent = "No matching rule or guide. Try a country, US state, region, or broader topic.";
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
        root.querySelector("[data-search-status]").textContent = "Search is unavailable; browse the two sections below.";
      });
    });
})();
