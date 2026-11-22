/* Country selections stay in this page's memory. */
(function () {
  "use strict";
  var SVG_NS = "http://www.w3.org/2000/svg";
  var reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  document.querySelectorAll("[data-country-checklist]").forEach(function (root) {
    var lang = document.documentElement.lang;
    var picker = root.querySelector("[data-country-picker]");
    var options = root.querySelector("[data-country-options]");
    var output = root.querySelector("[data-country-count]");
    var progress = root.querySelector("[data-country-progress]");
    var result = root.querySelector("[data-country-result]");
    var invitation = root.querySelector(".country-checklist-cta");
    var track = root.querySelector("[data-country-track]");
    var dialog = root.querySelector("[data-country-dialog]");
    var search = root.querySelector("[data-country-search]");
    var empty = root.querySelector("[data-country-empty]");
    var picked = root.querySelector("[data-country-picked]");
    var territoriesToggle = root.querySelector("[data-country-territories]");
    var chips = Array.prototype.slice.call(root.querySelectorAll("[data-country-continent]"));
    var strings = JSON.parse(root.querySelector("[data-country-strings]").textContent);
    var buttons = Array.prototype.slice.call(options.querySelectorAll("[data-country-code]"));
    var byCode = {};
    buttons.forEach(function (button) { byCode[button.dataset.countryCode] = button; });

    var plural = new Intl.PluralRules(lang);
    var list = new Intl.ListFormat(lang, { style: "long", type: "conjunction" });
    var formatter = new Intl.NumberFormat(lang, { useGrouping: false });
    var collator = new Intl.Collator(lang, { sensitivity: "base" });
    var totalCountries = buttons.filter(function (button) { return button.dataset.countryKind === "country"; }).length;
    var continent = "all";

    function isOn(button) { return button.getAttribute("aria-pressed") === "true"; }
    function name(button) { return button.querySelector(".country-checklist-name").textContent; }
    function selected() { return buttons.filter(isOn).map(function (button) { return button.dataset.countryCode; }); }
    function showsTerritories() { return territoriesToggle.getAttribute("aria-checked") === "true"; }
    function countPhrase(forms, count) { return (forms[plural.select(count)] || forms.other).replace("{n}", formatter.format(count)); }
    function normalize(value) { return value.normalize("NFD").replace(/[̀-ͯ]/g, "").toLocaleLowerCase(lang); }

    Array.prototype.slice.call(options.children).sort(function (a, b) {
      return collator.compare(a.textContent.trim(), b.textContent.trim());
    }).forEach(function (label) { options.appendChild(label); });
    buttons = Array.prototype.slice.call(options.querySelectorAll("[data-country-code]"));

    /* ---- Import popup ---- */

    var appleTouch = /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    var inApp = false;
    try { inApp = new URLSearchParams(location.search).get("from") === "app" || sessionStorage.getItem("atlasdays-from") === "app"; } catch (e) {}
    function fragment() { return "v=3&c=countries&u=" + selected().join(","); }
    function downloadCsv() {
      var csv = "Country,Start Date,End Date,Notes\r\n" + selected().map(function (code) { return code + ",,,"; }).join("\r\n") + "\r\n";
      var url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
      var a = document.createElement("a");
      a.href = url; a.download = "atlasdays-countries.csv";
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
      if (dialog) dialog.querySelectorAll("[data-cal-downloaded]").forEach(function (part) { part.hidden = false; part.previousElementSibling.hidden = true; });
    }
    function openImport() {
      if (!selected().length) return;
      if (!dialog || !dialog.showModal) return downloadCsv();
      var mode = inApp || appleTouch ? "phone" : "computer";
      var universal = "https://go.atlasdays.app/import/#" + fragment();
      dialog.querySelectorAll("[data-cal-on]").forEach(function (part) { part.hidden = part.getAttribute("data-cal-on").split(" ").indexOf(mode) < 0; });
      dialog.querySelectorAll("[data-cal-store]").forEach(function (part) { part.hidden = inApp; });
      dialog.querySelectorAll("[data-cal-open]").forEach(function (a) { a.href = inApp ? "atlasdays://import#" + fragment() : universal; });
      dialog.querySelectorAll(".cal-steps").forEach(function (steps) {
        steps.classList.toggle("is-single", Array.prototype.filter.call(steps.children, function (li) { return !li.hidden; }).length === 1);
      });
      dialog.querySelectorAll("[data-cal-downloaded]").forEach(function (part) { part.hidden = true; part.previousElementSibling.hidden = false; });
      dialog.showModal(); dialog.setAttribute("tabindex", "-1"); dialog.focus();
      var box = dialog.querySelector("[data-cal-qr]");
      if (mode === "computer" && box && window.AtlasDaysImportQr) window.AtlasDaysImportQr.draw(box, universal);
    }
    if (track) track.addEventListener("click", openImport);
    if (dialog) {
      dialog.querySelectorAll("[data-cal-close]").forEach(function (button) { button.addEventListener("click", function () { dialog.close(); }); });
      dialog.querySelectorAll("[data-cal-download]").forEach(function (button) { button.addEventListener("click", downloadCsv); });
      dialog.addEventListener("click", function (event) { if (event.target === dialog) dialog.close(); });
      window.addEventListener("resize", function () {
        var box = dialog.querySelector("[data-cal-qr]");
        if (dialog.open && box && window.AtlasDaysImportQr) window.AtlasDaysImportQr.restack(box);
      });
    }

    /* ---- Map: click to mark, zoom and pan ---- */

    var map = root.querySelector("[data-country-map]");
    var canvas = map && map.querySelector("[data-country-map-canvas]");
    var svg = null, shapes = [], base = null, view = null, animation = 0;
    var MAX_ZOOM = 14;

    var gradient = null;
    // Visited land shares one vertical gradient that spans the visited
    // shapes, lighter toward the top.
    function updateMap() {
      var top = Infinity, bottom = -Infinity;
      shapes.forEach(function (shape) {
        var button = byCode[shape.getAttribute("data-map-country")];
        var visited = !!button && isOn(button);
        shape.classList.toggle("is-visited", visited);
        if (!visited || !shape.getBBox) return;
        var box = shape.getBBox();
        top = Math.min(top, box.y); bottom = Math.max(bottom, box.y + box.height);
      });
      if (!gradient || !base) return;
      if (!(bottom > top)) { top = base.y; bottom = base.y + base.h; }
      gradient.setAttribute("y1", bottom); gradient.setAttribute("y2", top);
    }
    function buildGradient() {
      var defs = svg.querySelector("defs") || svg.insertBefore(document.createElementNS(SVG_NS, "defs"), svg.firstChild);
      gradient = document.createElementNS(SVG_NS, "linearGradient");
      gradient.setAttribute("id", "country-checklist-visited");
      gradient.setAttribute("gradientUnits", "userSpaceOnUse");
      gradient.setAttribute("x1", 0); gradient.setAttribute("x2", 0);
      ["country-checklist-visited-from", "country-checklist-visited-to"].forEach(function (name, index) {
        var stop = document.createElementNS(SVG_NS, "stop");
        stop.setAttribute("offset", index); stop.setAttribute("class", name);
        gradient.appendChild(stop);
      });
      defs.appendChild(gradient);
    }
    function clampView(next) {
      var w = Math.min(base.w, Math.max(base.w / MAX_ZOOM, next.w)), h = w * base.h / base.w;
      return {
        x: Math.min(base.x + base.w - w, Math.max(base.x, next.x)),
        y: Math.min(base.y + base.h - h, Math.max(base.y, next.y)),
        w: w, h: h
      };
    }
    function applyView(next) {
      view = clampView(next);
      svg.setAttribute("viewBox", [view.x, view.y, view.w, view.h].join(" "));
      var zoomed = view.w < base.w * 0.999;
      canvas.classList.toggle("is-zoomed", zoomed);
      svg.classList.toggle("is-close", view.w < base.w / 3);
      var tools = map.querySelectorAll("[data-map-tool]");
      if (tools.length) {
        tools[0].disabled = view.w <= base.w / MAX_ZOOM * 1.001;
        tools[1].disabled = !zoomed;
        tools[2].disabled = !zoomed;
      }
    }
    function animateTo(target) {
      cancelAnimationFrame(animation);
      target = clampView(target);
      if (reducedMotion) return applyView(target);
      var from = view, start = null;
      function step(now) {
        if (start === null) start = now;
        var t = Math.min(1, (now - start) / 280), k = 1 - Math.pow(1 - t, 3);
        applyView({ x: from.x + (target.x - from.x) * k, y: from.y + (target.y - from.y) * k, w: from.w + (target.w - from.w) * k, h: 0 });
        if (t < 1) animation = requestAnimationFrame(step);
      }
      animation = requestAnimationFrame(step);
    }
    // The point of the map under a screen position, in map units.
    function mapPoint(clientX, clientY) {
      var rect = canvas.getBoundingClientRect();
      return { x: view.x + (clientX - rect.left) / rect.width * view.w, y: view.y + (clientY - rect.top) / rect.height * view.h };
    }
    function zoomAround(factor, point, animate) {
      var w = view.w / factor;
      var next = { x: point.x - (point.x - view.x) * (w / view.w), y: point.y - (point.y - view.y) * (w / view.w), w: w, h: 0 };
      if (animate) animateTo(next); else applyView(next);
    }
    function zoomCentre(factor) { zoomAround(factor, { x: view.x + view.w / 2, y: view.y + view.h / 2 }, true); }
    function focusContinent(key) {
      if (!svg) return;
      if (key === "all") return animateTo(base);
      var box = null;
      shapes.forEach(function (shape) {
        var button = byCode[shape.getAttribute("data-map-country")];
        if (!button || button.dataset.continent !== key || shape.tagName !== "path") return;
        // Remote territories (Svalbard, French Polynesia) would stretch the frame, except where they are all there is.
        if (key !== "antarctica" && button.dataset.countryKind !== "country") return;
        var b = shape.getBBox();
        // A country that wraps the map (Russia, the United States) would widen the frame to the whole world.
        if (b.width > base.w * 0.35) return;
        box = box ? { x1: Math.min(box.x1, b.x), y1: Math.min(box.y1, b.y), x2: Math.max(box.x2, b.x + b.width), y2: Math.max(box.y2, b.y + b.height) }
          : { x1: b.x, y1: b.y, x2: b.x + b.width, y2: b.y + b.height };
      });
      if (!box) return animateTo(base);
      var w = Math.max((box.x2 - box.x1) * 1.16, (box.y2 - box.y1) * 1.16 * base.w / base.h);
      var h = w * base.h / base.w;
      animateTo({ x: (box.x1 + box.x2) / 2 - w / 2, y: (box.y1 + box.y2) / 2 - h / 2, w: w, h: h });
    }
    function toggleCode(code) {
      var button = byCode[code];
      if (!button) return;
      // A territory marked on the map shows up in the list too.
      if (button.dataset.countryKind !== "country" && !showsTerritories() && !isOn(button)) setTerritories(true);
      button.setAttribute("aria-pressed", isOn(button) ? "false" : "true");
      update();
    }
    function buildTools() {
      var tools = document.createElement("div");
      tools.className = "country-checklist-map-tools";
      [["zoomIn", "M10 5v10M5 10h10", function () { zoomCentre(1.8); }],
       ["zoomOut", "M5 10h10", function () { zoomCentre(1 / 1.8); }],
       ["resetMap", "M5 8V5h3M15 8V5h-3M5 12v3h3M15 12v3h-3", function () { setContinent("all"); animateTo(base); }]
      ].forEach(function (tool) {
        var button = document.createElement("button");
        button.type = "button"; button.setAttribute("data-map-tool", tool[0]);
        button.setAttribute("aria-label", strings[tool[0]]); button.title = strings[tool[0]];
        button.innerHTML = '<svg aria-hidden="true" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="' + tool[1] + '"/></svg>';
        button.addEventListener("click", tool[2]);
        tools.appendChild(button);
      });
      canvas.parentNode.insertBefore(tools, canvas.nextSibling);
    }
    function bindMap() {
      var tip = document.createElement("div");
      tip.className = "country-checklist-map-tip"; tip.hidden = true;
      canvas.appendChild(tip);
      var pointers = {}, moved = 0, pinch = 0, last = null;
      function count() { return Object.keys(pointers).length; }
      function target(event) { return event.target.closest ? event.target.closest("[data-map-country]") : null; }
      canvas.addEventListener("wheel", function (event) {
        // A plain scroll moves the page. Pinch on a trackpad, or scroll with Ctrl or ⌘, zooms the map.
        if (!event.ctrlKey && !event.metaKey) return;
        event.preventDefault();
        cancelAnimationFrame(animation);
        zoomAround(Math.exp(-event.deltaY * 0.01), mapPoint(event.clientX, event.clientY), false);
      }, { passive: false });
      canvas.addEventListener("dblclick", function (event) {
        event.preventDefault();
        zoomAround(2, mapPoint(event.clientX, event.clientY), true);
      });
      canvas.addEventListener("pointerdown", function (event) {
        if (event.pointerType === "mouse" && event.button !== 0) return;
        cancelAnimationFrame(animation);
        pointers[event.pointerId] = { x: event.clientX, y: event.clientY, shape: target(event) };
        if (count() === 1) { moved = 0; last = { x: event.clientX, y: event.clientY }; }
        if (count() === 2) {
          var p = Object.keys(pointers).map(function (id) { return pointers[id]; });
          pinch = Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y); moved = 99;
        }
        tip.hidden = true;
      });
      canvas.addEventListener("pointermove", function (event) {
        var pointer = pointers[event.pointerId];
        if (!pointer) {
          if (event.pointerType !== "mouse") return;
          var shape = target(event), button = shape && byCode[shape.getAttribute("data-map-country")];
          tip.hidden = !button;
          if (button) {
            var rect = canvas.getBoundingClientRect();
            tip.textContent = name(button);
            tip.style.left = Math.min(rect.width - 8, Math.max(8, event.clientX - rect.left)) + "px";
            tip.style.top = (event.clientY - rect.top) + "px";
          }
          return;
        }
        pointer.x = event.clientX; pointer.y = event.clientY;
        if (count() === 2) {
          var p = Object.keys(pointers).map(function (id) { return pointers[id]; });
          var distance = Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y);
          if (pinch) zoomAround(distance / pinch, mapPoint((p[0].x + p[1].x) / 2, (p[0].y + p[1].y) / 2), false);
          pinch = distance;
          return;
        }
        var dx = event.clientX - last.x, dy = event.clientY - last.y;
        moved += Math.abs(dx) + Math.abs(dy);
        last = { x: event.clientX, y: event.clientY };
        if (moved > 6 && view.w < base.w) {
          if (!canvas.hasPointerCapture(event.pointerId)) canvas.setPointerCapture(event.pointerId);
          canvas.classList.add("is-dragging");
          var rect2 = canvas.getBoundingClientRect();
          applyView({ x: view.x - dx / rect2.width * view.w, y: view.y - dy / rect2.height * view.h, w: view.w, h: view.h });
        }
      });
      function release(event) {
        var pointer = pointers[event.pointerId];
        if (!pointer) return;
        delete pointers[event.pointerId];
        canvas.classList.remove("is-dragging");
        if (event.type === "pointerup" && moved <= 6 && count() === 0 && pointer.shape) toggleCode(pointer.shape.getAttribute("data-map-country"));
        if (count() < 2) pinch = 0;
        if (count() === 1) { var rest = pointers[Object.keys(pointers)[0]]; last = { x: rest.x, y: rest.y }; }
      }
      canvas.addEventListener("pointerup", release);
      canvas.addEventListener("pointercancel", release);
      canvas.addEventListener("pointerleave", function () { tip.hidden = true; });
    }
    function loadMap() {
      fetch("/assets/maps/world.svg").then(function (response) {
        if (!response.ok) throw new Error("Map unavailable");
        return response.text();
      }).then(function (text) {
        var parsed = new DOMParser().parseFromString(text, "image/svg+xml");
        if (parsed.querySelector("parsererror")) throw new Error("Invalid map");
        svg = document.importNode(parsed.documentElement, true);
        var metadata = svg.querySelector("[data-map-markers]");
        var markers = metadata ? JSON.parse(metadata.textContent) : {};
        svg.classList.add("country-checklist-world");
        svg.setAttribute("aria-hidden", "true");
        svg.setAttribute("focusable", "false");
        svg.style.visibility = "hidden";
        canvas.appendChild(svg);
        map.hidden = false;
        var box = svg.getBBox();
        base = { x: box.x - 3, y: box.y - 3, w: box.width + 6, h: box.height + 6 };
        canvas.style.aspectRatio = base.w + " / " + base.h;
        buildGradient();
        svg.querySelectorAll(".land[id]").forEach(function (shape) { shape.setAttribute("data-map-country", shape.id); });
        Object.keys(markers).forEach(function (code) {
          var dot = document.createElementNS(SVG_NS, "circle");
          dot.setAttribute("cx", markers[code][0]); dot.setAttribute("cy", markers[code][1]);
          dot.setAttribute("r", "1.8"); dot.setAttribute("class", "country-checklist-map-dot");
          dot.setAttribute("data-map-country", code); svg.appendChild(dot);
        });
        shapes = Array.prototype.slice.call(svg.querySelectorAll("[data-map-country]"));
        buildTools();
        applyView(base);
        bindMap();
        updateMap();
        svg.style.visibility = "";
      }).catch(function () { map.hidden = true; });
    }

    /* ---- List, continents, visited chips ---- */

    function renderPicked() {
      if (!picked) return;
      var holder = picked.querySelector("[data-country-picked-list]");
      var on = buttons.filter(isOn);
      picked.hidden = on.length === 0;
      holder.textContent = "";
      on.forEach(function (button) {
        var chip = document.createElement("button");
        chip.type = "button"; chip.className = "country-checklist-chip";
        chip.setAttribute("data-remove", button.dataset.countryCode);
        chip.setAttribute("aria-label", strings.remove.replace("{name}", name(button)));
        var flag = button.querySelector("img");
        if (flag) { var copy = flag.cloneNode(); copy.removeAttribute("loading"); chip.appendChild(copy); }
        chip.appendChild(document.createTextNode(name(button)));
        chip.insertAdjacentHTML("beforeend", '<svg aria-hidden="true" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="m6 6 8 8M14 6l-8 8"/></svg>');
        holder.appendChild(chip);
      });
    }
    function update() {
      var counts = { country: 0, territory: 0, other: 0 }, perContinent = {};
      buttons.forEach(function (button) {
        if (!isOn(button)) return;
        counts[button.dataset.countryKind] += 1;
        perContinent[button.dataset.continent] = (perContinent[button.dataset.continent] || 0) + 1;
      });
      var count = counts.country + counts.territory + counts.other;
      var extras = [];
      if (counts.territory || showsTerritories()) extras.push(countPhrase(strings.territoryCount, counts.territory));
      if (counts.other) extras.push(countPhrase(strings.otherCount, counts.other));
      output.textContent = (extras.length ? strings.countWithExtras : output.dataset.countTemplate)
        .replace("{count}", formatter.format(counts.country))
        .replace("{total}", formatter.format(totalCountries))
        .replace("{extras}", list.format(extras));
      if (progress) progress.style.width = (counts.country / totalCountries * 100) + "%";
      chips.forEach(function (chip) {
        var badge = chip.querySelector("[data-continent-count]");
        var n = chip.value === "all" ? count : (perContinent[chip.value] || 0);
        if (badge) { badge.textContent = n ? formatter.format(n) : ""; badge.hidden = !n; }
      });
      updateMap();
      renderPicked();
      if (result) result.hidden = count === 0;
      if (invitation) invitation.hidden = count > 0 && !!track;
      if (track) track.disabled = count === 0;
    }
    function filter() {
      var query = normalize(search.value.trim());
      var visible = 0;
      buttons.forEach(function (button) {
        button.hidden = (!showsTerritories() && button.dataset.countryKind !== "country" && !isOn(button))
          || (continent !== "all" && button.dataset.continent !== continent)
          || normalize(button.textContent + " " + button.dataset.countryCode).indexOf(query) < 0;
        if (!button.hidden) visible += 1;
      });
      empty.hidden = visible > 0;
      options.scrollTop = 0;
    }
    function setContinent(key) {
      continent = key;
      chips.forEach(function (chip) { chip.setAttribute("aria-pressed", chip.value === key ? "true" : "false"); });
      filter();
    }
    function setTerritories(enabled) {
      territoriesToggle.setAttribute("aria-checked", enabled ? "true" : "false");
      chips.forEach(function (chip) { if (chip.value === "antarctica") chip.hidden = !enabled; });
      if (!enabled && continent === "antarctica") { setContinent("all"); focusContinent("all"); }
      filter();
    }

    options.addEventListener("click", function (event) {
      var button = event.target.closest("[data-country-code]");
      if (!button || !options.contains(button)) return;
      button.setAttribute("aria-pressed", isOn(button) ? "false" : "true");
      update();
    });
    if (picked) {
      picked.addEventListener("click", function (event) {
        var chip = event.target.closest("[data-remove]");
        if (chip) { byCode[chip.getAttribute("data-remove")].setAttribute("aria-pressed", "false"); update(); filter(); return; }
        if (event.target.closest("[data-country-clear]")) {
          buttons.forEach(function (button) { button.setAttribute("aria-pressed", "false"); });
          update(); filter();
        }
      });
    }
    chips.forEach(function (chip) {
      chip.addEventListener("click", function () { setContinent(chip.value); focusContinent(chip.value); });
    });
    search.addEventListener("input", filter);
    territoriesToggle.addEventListener("click", function () { setTerritories(!showsTerritories()); update(); });

    setContinent("all");
    window.addEventListener("pageshow", update);
    update();
    picker.hidden = false;
    if (map) loadMap();
  });
})();
