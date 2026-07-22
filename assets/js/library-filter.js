(function () {
  "use strict";

  var input = document.querySelector("[data-filter-input]");
  if (!input) return;

  var clearBtn = document.querySelector("[data-filter-clear]");
  var chips = Array.prototype.slice.call(document.querySelectorAll("[data-filter-chip]"));
  var items = Array.prototype.slice.call(document.querySelectorAll("[data-filter-item]"));
  var groups = Array.prototype.slice.call(document.querySelectorAll("[data-filter-group]"));
  var sections = Array.prototype.slice.call(document.querySelectorAll("[data-filter-section]"));
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

  // Chips narrow places only; general guides (and any untyped item) stay visible.
  function matchesChip(item) {
    if (category === "all") return true;
    var type = item.getAttribute("data-type");
    if (!type || type === "guide") return true;
    if (category === "country") return type !== "state"; // country + region
    if (category === "state") return type === "state";
    return true;
  }

  function apply() {
    var term = input.value.trim().toLowerCase();
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

    if (empty) empty.hidden = anyVisible;
    if (clearBtn) clearBtn.hidden = !input.value;
  }

  input.addEventListener("input", apply);

  if (clearBtn) {
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
