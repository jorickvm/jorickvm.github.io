(function () {
  "use strict";

  var input = document.querySelector("[data-filter-input]");
  var chips = Array.prototype.slice.call(document.querySelectorAll("[data-filter-chip]"));
  if (!input && !chips.length) return;

  var clearBtn = document.querySelector("[data-filter-clear]");
  var items = Array.prototype.slice.call(document.querySelectorAll("[data-filter-item]"));
  var groups = Array.prototype.slice.call(document.querySelectorAll("[data-filter-group]"));
  var sections = Array.prototype.slice.call(document.querySelectorAll("[data-filter-section]"));
  var counts = Array.prototype.slice.call(document.querySelectorAll("[data-filter-count]"));
  var empty = document.querySelector("[data-filter-empty]");
  var category = "all";

  // Cache each item's searchable text: an explicit data-search wins, otherwise
  // fall back to the item's own visible text (name, titles, descriptions).
  items.forEach(function (item) {
    item._haystack = (item.getAttribute("data-search") || item.textContent || "")
      .toLowerCase()
      .replace(/\s+/g, " ")
      .trim();
  });

  // A chip matches an item when the item lists that chip's value in data-groups.
  function matchesChip(item) {
    if (category === "all") return true;
    var groups = (item.getAttribute("data-groups") || "").split(/\s+/);
    return groups.indexOf(category) !== -1;
  }

  function apply() {
    var term = input ? input.value.trim().toLowerCase() : "";
    var anyVisible = false;

    items.forEach(function (item) {
      var show = matchesChip(item) && (!term || item._haystack.indexOf(term) !== -1);
      item.hidden = !show;
      if (show) anyVisible = true;
    });

    // Hide a group or section once everything inside it is filtered out.
    groups.forEach(function (group) {
      group.hidden = !group.querySelector("[data-filter-item]:not([hidden])");
    });
    sections.forEach(function (section) {
      section.hidden = !section.querySelector("[data-filter-item]:not([hidden])");
    });

    // Live counts reflect the visible items inside each count's own section.
    counts.forEach(function (count) {
      var section = count.closest("[data-filter-section]");
      var scope = section || document;
      count.textContent = scope.querySelectorAll("[data-filter-item]:not([hidden])").length;
    });

    if (empty) empty.hidden = anyVisible;
    if (clearBtn) clearBtn.hidden = !(input && input.value);
  }

  if (input) input.addEventListener("input", apply);

  if (clearBtn && input) {
    clearBtn.addEventListener("click", function () {
      input.value = "";
      apply();
      input.focus();
    });
  }

  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      category = chip.getAttribute("data-filter-chip") || "all";
      chips.forEach(function (other) {
        other.setAttribute("aria-pressed", String(other === chip));
      });
      apply();
    });
  });

  apply();
})();
