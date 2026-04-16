(function () {
  var target = window.AtlasDaysAppAliasTarget;
  if (!target) return;

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
      document.open();
      document.write(addAliasMetadata(html));
      document.close();
    })
    .catch(function () {
      var link = document.querySelector('[data-alias-target-link]');
      if (link) {
        link.hidden = false;
        link.focus();
      }
    });
})();
