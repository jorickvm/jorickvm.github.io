function toggleTheme() {
  var html = document.documentElement;
  var current = html.getAttribute('data-theme');
  var next = current === 'light' ? 'dark' : 'light';
  html.setAttribute('data-theme', next);

  // Pages opened from the iOS app carry ?theme= and store it in sessionStorage.
  // Inside that session the toggle stays session-scoped: the app's in-app browser
  // shares storage with Safari, so writing localStorage there would silently flip
  // the visitor's site-wide preference in Safari too.
  var scoped = false;
  try {
    if (sessionStorage.getItem('theme')) {
      sessionStorage.setItem('theme', next);
      scoped = true;
    }
  } catch (e) {}

  if (!scoped) {
    try { localStorage.setItem('theme', next); } catch (e) {}
  }
}
