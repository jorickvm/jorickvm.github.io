/* Country selections stay in this page's memory. */
(function () {
  "use strict";
  document.querySelectorAll("[data-country-checklist]").forEach(function (root) {
    var picker = root.querySelector("[data-country-picker]");
    var options = root.querySelector("[data-country-options]");
    var output = root.querySelector("[data-country-count]");
    var result = root.querySelector("[data-country-result]");
    var invitation = root.querySelector(".country-checklist-cta");
    var track = root.querySelector("[data-country-track]");
    var dialog = root.querySelector("[data-country-dialog]");
    var appleTouch = /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    var inApp = false;
    try { inApp = new URLSearchParams(location.search).get("from") === "app" || sessionStorage.getItem("atlasdays-from") === "app"; } catch (e) {}
    function selected() { return buttons.filter(function (button) { return button.getAttribute("aria-pressed") === "true"; }).map(function (button) { return button.dataset.countryCode; }); }
    function fragment() { return "v=3&c=countries&u=" + selected().join(","); }
    function downloadCsv() {
      var csv = "Country,Start Date,End Date,Notes\r\n" + selected().map(function (code) { return code + ",,,"; }).join("\r\n") + "\r\n";
      var url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
      var a = document.createElement("a");
      a.href = url; a.download = "atlasdays-countries.csv";
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
      dialog.querySelectorAll("[data-cal-downloaded]").forEach(function (part) { part.hidden = false; part.previousElementSibling.hidden = true; });
    }
    function showQr(url) {
      var box = dialog.querySelector("[data-cal-qr]");
      function draw() {
        var qr = window.qrcode(0, "M");
        qr.addData(url); qr.make();
        box.innerHTML = qr.createSvgTag(4, 16);
        var large = (qr.getModuleCount() + 8) * 3 > 208;
        box.classList.toggle("is-large", large);
        box.parentNode.classList.toggle("is-large", large);
      }
      box.textContent = "";
      if (window.qrcode) draw();
      else {
        var script = document.createElement("script");
        script.src = "/assets/js/vendor/qrcode-generator.js";
        script.onload = draw;
        document.head.appendChild(script);
      }
    }
    function openImport() {
      if (!selected().length) return;
      if (!dialog.showModal) return downloadCsv();
      var mode = inApp || appleTouch ? "phone" : "computer";
      var universal = "https://go.atlasdays.app/import/#" + fragment();
      dialog.querySelectorAll("[data-cal-on]").forEach(function (part) { part.hidden = part.getAttribute("data-cal-on").split(" ").indexOf(mode) < 0; });
      dialog.querySelectorAll("[data-cal-store]").forEach(function (part) { part.hidden = inApp; });
      dialog.querySelectorAll("[data-cal-open]").forEach(function (a) { a.href = inApp ? "atlasdays://import#" + fragment() : universal; });
      dialog.querySelectorAll(".cal-steps").forEach(function (list) {
        list.classList.toggle("is-single", Array.prototype.filter.call(list.children, function (li) { return !li.hidden; }).length === 1);
      });
      dialog.querySelectorAll("[data-cal-downloaded]").forEach(function (part) { part.hidden = true; part.previousElementSibling.hidden = false; });
      if (mode === "computer") showQr(universal);
      dialog.showModal(); dialog.setAttribute("tabindex", "-1"); dialog.focus();
    }
    if (track && dialog) {
    track.addEventListener("click", openImport);
    dialog.querySelectorAll("[data-cal-close]").forEach(function (button) { button.addEventListener("click", function () { dialog.close(); }); });
    dialog.querySelectorAll("[data-cal-download]").forEach(function (button) { button.addEventListener("click", downloadCsv); });
    dialog.addEventListener("click", function (event) { if (event.target === dialog) dialog.close(); });
    }
    var buttons = Array.prototype.slice.call(options.querySelectorAll("[data-country-code]"));
    var search = root.querySelector("[data-country-search]");
    var empty = root.querySelector("[data-country-empty]");
    var continentFilter = root.querySelector("[data-country-continent]");
    var territoriesToggle = root.querySelector("[data-country-territories]");
    var strings = JSON.parse(root.querySelector("[data-country-strings]").textContent);
    var plural = new Intl.PluralRules(document.documentElement.lang);
    var list = new Intl.ListFormat(document.documentElement.lang, { style: "long", type: "conjunction" });
    var totalCountries = buttons.filter(function (button) { return button.dataset.countryKind === "country"; }).length;
    function countPhrase(forms, count) { return (forms[plural.select(count)] || forms.other).replace("{n}", formatter.format(count)); }
    var formatter = new Intl.NumberFormat(document.documentElement.lang, { useGrouping: false });
    var collator = new Intl.Collator(document.documentElement.lang, { sensitivity: "base" });
    Array.prototype.slice.call(options.children).sort(function (a, b) {
      return collator.compare(a.textContent.trim(), b.textContent.trim());
    }).forEach(function (label) { options.appendChild(label); });
    var map = root.querySelector("[data-country-map]");
    var mapShapes = [];
    function updateMap() {
      var visited = new Set(selected());
      mapShapes.forEach(function (shape) {
        shape.classList.toggle("is-visited", visited.has(shape.getAttribute("data-map-country")));
      });
    }
    function loadMap() {
      fetch("/assets/maps/world.svg").then(function (response) {
        if (!response.ok) throw new Error("Map unavailable");
        return response.text();
      }).then(function (text) {
        var parsed = new DOMParser().parseFromString(text, "image/svg+xml");
        if (parsed.querySelector("parsererror")) throw new Error("Invalid map");
        var svg = document.importNode(parsed.documentElement, true);
        var metadata = svg.querySelector("[data-map-markers]");
        var markers = metadata ? JSON.parse(metadata.textContent) : {};
        svg.classList.add("country-checklist-world");
        svg.setAttribute("aria-hidden", "true");
        svg.setAttribute("focusable", "false");
        svg.style.visibility = "hidden";
        map.querySelector("[data-country-map-canvas]").appendChild(svg);
        map.hidden = false;
        var box = svg.getBBox();
        svg.setAttribute("viewBox", [box.x - 3, box.y - 3, box.width + 6, box.height + 6].join(" "));
        svg.querySelectorAll(".land[id]").forEach(function (shape) {
          shape.setAttribute("data-map-country", shape.id);
        });
        Object.keys(markers).forEach(function (code) {
          var dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
          dot.setAttribute("cx", markers[code][0]); dot.setAttribute("cy", markers[code][1]);
          dot.setAttribute("r", "1.8"); dot.setAttribute("class", "country-checklist-map-dot");
          dot.setAttribute("data-map-country", code); svg.appendChild(dot);
        });
        mapShapes = Array.prototype.slice.call(svg.querySelectorAll("[data-map-country]"));
        updateMap();
        svg.style.visibility = "";
      }).catch(function () { map.hidden = true; });
    }
    function update() {
      var counts = { country: 0, territory: 0, other: 0 };
      buttons.forEach(function (button) {
        if (button.getAttribute("aria-pressed") === "true") counts[button.dataset.countryKind] += 1;
      });
      var count = counts.country + counts.territory + counts.other;
      var extras = [];
      if (counts.territory || territoriesToggle.getAttribute("aria-checked") === "true") extras.push(countPhrase(strings.territoryCount, counts.territory));
      if (counts.other) extras.push(countPhrase(strings.otherCount, counts.other));
      output.textContent = (extras.length ? strings.countWithExtras : output.dataset.countTemplate)
        .replace("{count}", formatter.format(counts.country))
        .replace("{total}", formatter.format(totalCountries))
        .replace("{extras}", list.format(extras));
      updateMap();
      result.hidden = count === 0;
      if (invitation) invitation.hidden = count > 0 && !!track;
      if (track) track.disabled = count === 0;
    }
    options.addEventListener("click", function (event) {
      var button = event.target.closest("[data-country-code]");
      if (!button || !options.contains(button)) return;
      button.setAttribute("aria-pressed", button.getAttribute("aria-pressed") === "true" ? "false" : "true");
      update();
    });
    function normalize(value) { return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase(document.documentElement.lang); }
    function filter() {
      var query = normalize(search.value.trim());
      var continent = continentFilter.value;
      var showTerritories = territoriesToggle.getAttribute("aria-checked") === "true";
      var visible = 0;
      buttons.forEach(function (button) {
        button.hidden = (!showTerritories && button.dataset.countryKind !== "country")
          || (continent !== "all" && button.dataset.continent !== continent)
          || normalize(button.textContent + " " + button.dataset.countryCode).indexOf(query) < 0;
        if (!button.hidden) visible += 1;
      });
      empty.hidden = visible > 0;
      options.scrollTop = 0;
    }
    search.addEventListener("input", filter);
    var continentOpen = root.querySelector("[data-country-continent-open]");
    var continentMenu = root.querySelector("[data-country-continent-menu]");
    var continentOptions = [];
    Array.prototype.forEach.call(continentFilter.options, function (option) {
      var button = document.createElement("button");
      button.type = "button"; button.className = "cal-country-option";
      button.setAttribute("role", "option"); button.setAttribute("tabindex", "-1");
      button.value = option.value; button.textContent = option.textContent;
      continentMenu.appendChild(button); continentOptions.push(button);
    });
    function syncContinents() {
      root.querySelector("[data-country-continent-value]").textContent = continentFilter.selectedOptions[0].textContent;
      continentOptions.forEach(function (button, index) {
        button.disabled = continentFilter.options[index].disabled;
        button.setAttribute("aria-selected", button.value === continentFilter.value ? "true" : "false");
      });
    }
    function closeContinents(restoreFocus) {
      continentMenu.hidden = true; continentOpen.setAttribute("aria-expanded", "false");
      if (restoreFocus) continentOpen.focus();
    }
    function openContinents() {
      syncContinents();
      continentMenu.hidden = false; continentOpen.setAttribute("aria-expanded", "true");
      var bounds = continentOpen.getBoundingClientRect();
      var below = window.innerHeight - bounds.bottom - 16, above = bounds.top - 16;
      var flip = below < 280 && above > below;
      continentMenu.style.top = flip ? "auto" : "calc(100% + 6px)";
      continentMenu.style.bottom = flip ? "calc(100% + 6px)" : "auto";
      continentMenu.style.maxHeight = Math.max(96, Math.min(336, flip ? above : below)) + "px";
      continentOptions.filter(function (button) { return !button.disabled && button.value === continentFilter.value; })[0].focus();
    }
    continentOpen.addEventListener("click", function () {
      if (continentMenu.hidden) openContinents(); else closeContinents(false);
    });
    continentOpen.addEventListener("keydown", function (event) {
      if (event.key === "ArrowDown" || event.key === "ArrowUp") { event.preventDefault(); openContinents(); }
    });
    continentMenu.addEventListener("click", function (event) {
      var option = event.target.closest('[role="option"]');
      if (!option || option.disabled) return;
      continentFilter.value = option.value; syncContinents(); filter(); closeContinents(true);
    });
    continentMenu.addEventListener("keydown", function (event) {
      var available = continentOptions.filter(function (button) { return !button.disabled; });
      var index = available.indexOf(document.activeElement);
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault(); available[(index + (event.key === "ArrowDown" ? 1 : -1) + available.length) % available.length].focus();
      } else if (event.key === "Home" || event.key === "End") {
        event.preventDefault(); available[event.key === "Home" ? 0 : available.length - 1].focus();
      } else if (event.key === "Escape") { event.preventDefault(); closeContinents(true); }
      else if (event.key === "Tab") {
        event.preventDefault(); closeContinents(false);
        (event.shiftKey ? continentOpen : territoriesToggle).focus();
      }
    });
    document.addEventListener("click", function (event) {
      if (!continentOpen.parentNode.contains(event.target)) closeContinents(false);
    });
    continentFilter.addEventListener("change", function () { syncContinents(); filter(); });
    syncContinents();
    territoriesToggle.addEventListener("click", function () {
      var enabled = territoriesToggle.getAttribute("aria-checked") !== "true";
      territoriesToggle.setAttribute("aria-checked", enabled ? "true" : "false");
      continentFilter.querySelector('[value="antarctica"]').disabled = !enabled;
      if (!enabled && continentFilter.value === "antarctica") {
        continentFilter.value = "all";
        root.querySelector("[data-country-continent-value]").textContent = strings.allContinents;
      }
      syncContinents(); filter(); update();
    });
    filter();
    window.addEventListener("pageshow", update);
    update();
    picker.hidden = false;
    if (map) loadMap();
  });
})();
