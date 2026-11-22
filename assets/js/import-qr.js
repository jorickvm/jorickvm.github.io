/* The import link as a QR code, drawn the same way in every tool. */
(function () {
  "use strict";
  function load(done) {
    if (window.qrcode) return done();
    var s = document.createElement("script");
    s.src = "/assets/js/vendor/qrcode-generator.js";
    s.onload = done;
    document.head.appendChild(s);
  }
  // Styled like the homepage's App Store QR code: navy connected-rounded
  // modules on light grey in both themes, rounded finder eyes, the app icon in
  // a cleared centre. Q error correction carries the icon; on bigger codes the
  // icon shrinks so the cleared area stays a small share.
  var QR = { dark: "#0a1420", light: "#ebebeb", quiet: 2, round: 0.9 };
  function qrSvg(text) {
    var q = window.qrcode(0, "Q");
    q.addData(text);
    q.make();
    // Past version 13 (69 modules), M error correction keeps the code a size
    // smaller; the icon is small enough there for M to carry it.
    if (q.getModuleCount() > 69) { q = window.qrcode(0, "M"); q.addData(text); q.make(); }
    var n = q.getModuleCount(), m = QR.quiet, total = n + 2 * m;
    var img = total * (n <= 45 ? 0.3 : n <= 69 ? 0.24 : 0.17), box = img * 1.12, at = (total - box) / 2, imgAt = (total - img) / 2;
    function finder(r, c) { return (r < 7 && c < 7) || (r < 7 && c >= n - 7) || (r >= n - 7 && c < 7); }
    function cleared(r, c) { var x = c + m + 0.5, y = r + m + 0.5; return x >= at && x <= at + box && y >= at && y <= at + box; }
    function on(r, c) { return r >= 0 && c >= 0 && r < n && c < n && q.isDark(r, c) && !finder(r, c) && !cleared(r, c); }
    // One cell, its corners rounded only where no neighbour touches them.
    function cell(x, y, tl, tr, br, bl) {
      return "M" + (x + tl) + " " + y + "H" + (x + 1 - tr) + (tr ? "Q" + (x + 1) + " " + y + " " + (x + 1) + " " + (y + tr) : "") +
        "V" + (y + 1 - br) + (br ? "Q" + (x + 1) + " " + (y + 1) + " " + (x + 1 - br) + " " + (y + 1) : "") +
        "H" + (x + bl) + (bl ? "Q" + x + " " + (y + 1) + " " + x + " " + (y + 1 - bl) : "") +
        "V" + (y + tl) + (tl ? "Q" + x + " " + y + " " + (x + tl) + " " + y : "") + "Z";
    }
    // Big codes have small modules on screen: softer rounding keeps them sharp.
    var rad = 0.5 * (n <= 69 ? QR.round : 0.4), d = "";
    for (var r = 0; r < n; r++) for (var c = 0; c < n; c++) {
      if (!on(r, c)) continue;
      var up = on(r - 1, c), right = on(r, c + 1), down = on(r + 1, c), left = on(r, c - 1);
      d += cell(c + m, r + m, !up && !left ? rad : 0, !up && !right ? rad : 0, !down && !right ? rad : 0, !down && !left ? rad : 0);
    }
    function rect(x, y, w, k, fill) { return '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + w + '" rx="' + w * k + '" fill="' + fill + '"/>'; }
    var eyes = "";
    [[m, m], [m + n - 7, m], [m, m + n - 7]].forEach(function (o) {
      eyes += rect(o[0], o[1], 7, 0.23, QR.dark) + rect(o[0] + 1, o[1] + 1, 5, 0.24, QR.light) + rect(o[0] + 2, o[1] + 2, 3, 0.28, QR.dark);
    });
    var icon = "/assets/brand/app-icon-qr.webp";
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + total + " " + total + '" role="img" aria-hidden="true">' +
      '<rect width="' + total + '" height="' + total + '" fill="' + QR.light + '"/>' +
      '<path d="' + d + '" fill="' + QR.dark + '"/>' + eyes + rect(at, at, box, 0.18, QR.light) +
      '<defs><clipPath id="cal-qr-icon"><rect x="' + imgAt + '" y="' + imgAt + '" width="' + img + '" height="' + img + '" rx="' + img * 0.22 + '"/></clipPath></defs>' +
      '<image href="' + icon + '" x="' + imgAt + '" y="' + imgAt + '" width="' + img + '" height="' + img + '" clip-path="url(#cal-qr-icon)"/></svg>';
  }

  // The code sits beside the steps at a compact size. On a 1x screen a big code
  // opens larger (about 4 px a module), because a camera cannot read it smaller.
  function sizeQr(box) {
    var modules = box.firstChild.viewBox.baseVal.width;
    box.style.width = Math.round(box.classList.contains("is-large")
      ? Math.min(492, Math.max(260, modules * 4.4))
      : Math.min(240, Math.max(200, modules * 3))) + "px";
    stackQr(box);
  }
  // When the steps no longer fit beside the code they go under it, and the
  // code moves in to line up with the text.
  function stackQr(box) {
    var scan = box.parentNode;
    scan.classList.remove("is-stacked");
    var stacked = scan.classList.contains("is-large") || scan.clientWidth < box.offsetWidth + 18 + 200;
    scan.classList.toggle("is-stacked", stacked);
  }
  // Draws `text` into `box`, a [data-cal-qr] element inside .cal-dialog-scan.
  function draw(box, text, done) {
    box.textContent = "";
    load(function () {
      box.innerHTML = qrSvg(text);
      // On a 1x screen a big code is too fine at the compact size: start large.
      var big = (window.devicePixelRatio || 1) < 1.5 && box.firstChild.viewBox.baseVal.width * 3 > 240;
      box.classList.toggle("is-large", big);
      box.parentNode.classList.toggle("is-large", big);
      sizeQr(box);
      if (done) done();
    });
  }
  window.AtlasDaysImportQr = { draw: draw, restack: function (box) { if (box.firstChild) stackQr(box); } };
})();
