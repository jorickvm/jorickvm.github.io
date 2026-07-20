(function () {
  var main = document.querySelector('main[data-legal-page]');
  var translations = window.AtlasDaysLegalTranslations;
  if (!main || !translations) return;

  var page = main.getAttribute('data-legal-page');
  var englishHTML = main.innerHTML;
  var englishTitle = document.title;
  var supported = ['en-US', 'en-GB', 'nl', 'de', 'es', 'fr', 'ru'];
  var languageNames = {
    'en-US': 'English (US)',
    'en-GB': 'English (UK)',
    nl: 'Nederlands',
    de: 'Deutsch',
    es: 'Español',
    fr: 'Français',
    ru: 'Русский'
  };
  var languageLabels = {
    'en-US': 'Language',
    'en-GB': 'Language',
    nl: 'Taal',
    de: 'Sprache',
    es: 'Idioma',
    fr: 'Langue',
    ru: 'Язык'
  };

  function normalizeLanguage(value) {
    if (!value) return '';
    var language = String(value).trim().replace(/_/g, '-').toLowerCase();
    if (language === 'en-gb') return 'en-GB';
    if (language === 'en' || language === 'en-us') return 'en-US';
    var baseLanguage = language.split('-')[0];
    return supported.indexOf(baseLanguage) === -1 ? '' : baseLanguage;
  }

  function storedLanguage() {
    try {
      return normalizeLanguage(localStorage.getItem('atlasdays-legal-language'));
    } catch (_) {
      return '';
    }
  }

  function browserLanguage() {
    var candidates = navigator.languages && navigator.languages.length
      ? navigator.languages
      : [navigator.language];
    for (var index = 0; index < candidates.length; index += 1) {
      var language = normalizeLanguage(candidates[index]);
      if (language) return language;
    }
    return '';
  }

  function initialLanguage() {
    var queryLanguage = '';
    try {
      queryLanguage = normalizeLanguage(new URL(window.location.href).searchParams.get('lang'));
    } catch (_) {}
    return queryLanguage || storedLanguage() || browserLanguage() || 'en-US';
  }

  function rememberLanguage(language) {
    try {
      localStorage.setItem('atlasdays-legal-language', language);
    } catch (_) {}
  }

  function updateAddress(language) {
    try {
      var url = new URL(window.location.href);
      url.searchParams.set('lang', language);
      history.replaceState(null, '', url.href);
    } catch (_) {}
  }

  function hydrateEmailLinks() {
    main.querySelectorAll('[data-email-user][data-email-domain]').forEach(function (link) {
      var address = link.getAttribute('data-email-user') + '@' + link.getAttribute('data-email-domain');
      link.textContent = address;
      link.href = 'mai' + 'lto:' + address;
    });
  }

  function languagePicker(language) {
    var wrapper = document.createElement('label');
    wrapper.className = 'legal-language-picker';
    wrapper.innerHTML =
      '<span class="visually-hidden">' + languageLabels[language] + '</span>' +
      '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' +
        '<circle cx="12" cy="12" r="9"></circle>' +
        '<path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"></path>' +
      '</svg>' +
      '<select aria-label="' + languageLabels[language] + '">' +
        supported.map(function (code) {
          return '<option value="' + code + '">' + languageNames[code] + '</option>';
        }).join('') +
      '</select>';

    var select = wrapper.querySelector('select');
    select.value = language;
    select.addEventListener('change', function () {
      var selected = normalizeLanguage(select.value) || 'en-US';
      rememberLanguage(selected);
      updateAddress(selected);
      render(selected);
    });
    return wrapper;
  }

  function addTopline(language) {
    var back = main.querySelector(':scope > p:first-child');
    if (!back) return;
    var topline = document.createElement('div');
    topline.className = 'legal-topline';
    back.before(topline);
    topline.append(back, languagePicker(language));
  }

  function render(language) {
    var localizedPage = language !== 'en-US' && translations[language] && translations[language][page];
    main.innerHTML = localizedPage ? localizedPage.html : englishHTML;
    document.documentElement.lang = language;
    document.title = localizedPage ? localizedPage.title : englishTitle;
    addTopline(language);
    hydrateEmailLinks();
  }

  var language = initialLanguage();
  rememberLanguage(language);
  render(language);
})();
