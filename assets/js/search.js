(function () {
  "use strict";

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
        var status = root.querySelector("[data-search-status]");
        var results = root.querySelector("[data-search-results]");

        function render() {
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
          results.hidden = !active;
          clear.hidden = !active;
          status.textContent = active ? matches.length + (matches.length === 1 ? " result" : " results") : "Browse all guides below";
          if (!active) return;
          if (!matches.length) {
            var empty = document.createElement("p");
            empty.className = "search-empty";
            empty.textContent = "No matching guide. Try a country, rule, feature, or broader category.";
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

        input.addEventListener("input", render);
        if (filter) filter.addEventListener("change", render);
        clear.addEventListener("click", function () {
          input.value = "";
          if (filter) filter.value = "";
          render();
          input.focus();
        });
        render();
      });
    })
    .catch(function () {
      roots.forEach(function (root) {
        root.querySelector("[data-search-status]").textContent = "Search is unavailable; browse all guides below.";
      });
    });
})();
