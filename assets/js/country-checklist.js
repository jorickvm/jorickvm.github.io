/* Country selections stay in this page's memory. */
(function () {
  "use strict";
  document.querySelectorAll("[data-country-checklist]").forEach(function (root) {
    var picker = root.querySelector("[data-country-picker]");
    var options = root.querySelector("[data-country-options]");
    var output = root.querySelector("[data-country-count]");
    var result = root.querySelector("[data-country-result]");
    var inputs = Array.prototype.slice.call(options.querySelectorAll('input[type="checkbox"]'));
    var formatter = new Intl.NumberFormat(document.documentElement.lang, { useGrouping: false });
    var collator = new Intl.Collator(document.documentElement.lang, { sensitivity: "base" });
    Array.prototype.slice.call(options.children).sort(function (a, b) {
      return collator.compare(a.textContent.trim(), b.textContent.trim());
    }).forEach(function (label) { options.appendChild(label); });
    function update() {
      var count = inputs.filter(function (input) { return input.checked; }).length;
      output.textContent = output.dataset.countTemplate
        .replace("{count}", formatter.format(count))
        .replace("{total}", formatter.format(inputs.length));
      result.hidden = count === 0;
    }
    options.addEventListener("change", update);
    window.addEventListener("pageshow", update);
    update();
    picker.hidden = false;
  });
})();
