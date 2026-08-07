(function () {
  var target = window.AtlasDaysAppAliasTarget;
  if (!target) return;

  // How long the alias may stay blank before we admit something is happening.
  // On a warm same-origin fetch the swap lands well inside this, so the usual
  // case shows no message at all instead of a flashing "Loading" that appears
  // and vanishes within a frame or two.
  var STATUS_DELAY_MS = 600;

  var settled = false;

  var statusTimer = setTimeout(function () {
    if (settled) return;
    var status = document.querySelector('[data-alias-status]');
    if (status) status.hidden = false;
  }, STATUS_DELAY_MS);

  function showFallback(message) {
    settled = true;
    clearTimeout(statusTimer);

    var status = document.querySelector('[data-alias-status]');
    if (status) status.hidden = true;

    var fallback = document.querySelector('[data-alias-fallback]');
    var link = document.querySelector('[data-alias-target-link]');
    if (link) {
      // Carry ?theme= and ?lang= through, so the manual route keeps the
      // appearance and language the app asked for.
      if (location.search) link.href = link.getAttribute('href') + location.search;
    }
    if (fallback) {
      var note = fallback.querySelector('[data-alias-message]');
      if (note && message) note.textContent = message;
      fallback.hidden = false;
    }
    if (link) link.focus();
  }

  function removeCloudflareBeacon(html) {
    return html
      .replace(/\s*<!-- Cloudflare Web Analytics -->\s*/gi, '')
      .replace(/\s*<script\b[^>]*src=["']https:\/\/static\.cloudflareinsights\.com\/beacon\.min\.js["'][^>]*><\/script>\s*/gi, '')
      .replace(/\s*<!-- End Cloudflare Web Analytics -->\s*/gi, '');
  }

  function addAliasMetadata(html) {
    var aliasMetadata = '<base href="/"><meta name="robots" content="noindex,follow">';
    return removeCloudflareBeacon(html).replace(/<head([^>]*)>/i, '<head$1>' + aliasMetadata);
  }

  fetch(target, { credentials: 'same-origin' })
    .then(function (response) {
      if (!response.ok) throw new Error('Unable to load page alias target.');
      return response.text();
    })
    .then(function (html) {
      settled = true;
      clearTimeout(statusTimer);
      document.open();
      document.write(addAliasMetadata(html));
      document.close();
    })
    .catch(function () {
      showFallback('This page could not be loaded.');
    });
})();
