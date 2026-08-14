import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import locales  # noqa: E402
import build_site  # noqa: E402


class LocaleRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.locales = locales.load_locales()
        self.strings = locales.load_ui_strings()

    def test_default_locale_is_registered(self) -> None:
        self.assertIn(locales.default_locale_code(), self.locales)

    def test_exactly_one_x_default(self) -> None:
        """hreflang allows a single x-default; two would make the set invalid."""
        flagged = [code for code, entry in self.locales.items() if entry.get("x_default")]
        self.assertEqual(len(flagged), 1, flagged)

    def test_every_published_locale_has_every_string(self) -> None:
        published = [str(entry["code"]) for entry in locales.published_locales(self.locales)]
        missing = [
            f"{key}:{code}"
            for key, values in self.strings.items()
            for code in published
            if not values.get(code)
        ]
        self.assertEqual(missing, [])

    def test_attribute_strings_are_quote_safe(self) -> None:
        """Markers substitute raw, so an attribute value must not break the tag.

        help.contact_body is the deliberate exception: it carries its own anchor
        so no language is forced into English word order.
        """
        for key, values in self.strings.items():
            if key == "help.contact_body":
                continue
            for code, value in values.items():
                self.assertNotIn('"', value, f"{key}:{code}")
                self.assertNotIn("<", value, f"{key}:{code}")


class MarkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.locale = locales.load_locales()[locales.default_locale_code()]
        self.strings = locales.load_ui_strings()

    def test_resolves_strings_and_routes(self) -> None:
        rendered = locales.localize(
            '<a href="{{r:/help/}}">{{t:nav.help}}</a>', self.locale, self.strings
        )
        self.assertEqual(rendered, '<a href="/help/">Help Center</a>')

    def test_unknown_key_is_fatal(self) -> None:
        with self.assertRaises(SystemExit):
            locales.localize("{{t:nav.nope}}", self.locale, self.strings)

    def test_missing_locale_value_is_fatal(self) -> None:
        with self.assertRaises(SystemExit):
            locales.localize("{{t:nav.help}}", {"code": "zz"}, self.strings)

    def test_route_markers_respect_available_routes(self) -> None:
        """Regression: the pilot page linked to /ja/about, which was never built.

        localize() defaulted available_routes to None, so every {{r:}} marker in
        the shared header and footer got a locale prefix whether or not that
        page existed. Only the audit's broken-local-ref check caught it.
        """
        ja = {"code": "ja", "route_prefix": "/ja", "native_name": "日本語"}
        strings = {"nav.help": {"ja": "ヘルプ"}, "nav.about": {"ja": "概要"}}
        markup = '<a href="{{r:/help/}}">{{t:nav.help}}</a><a href="{{r:/about}}">{{t:nav.about}}</a>'
        rendered = locales.localize(markup, ja, strings, available_routes={"/help/"})
        self.assertIn('href="/ja/help/"', rendered)
        self.assertIn('href="/about"', rendered)


class RouteTests(unittest.TestCase):
    JA = {"code": "ja", "route_prefix": "/ja"}

    def test_default_locale_routes_are_unprefixed(self) -> None:
        locale = locales.load_locales()[locales.default_locale_code()]
        self.assertEqual(locales.localized_route("/help/", locale), "/help/")

    def test_prefixes_when_the_page_exists(self) -> None:
        self.assertEqual(locales.localized_route("/help/", self.JA, {"/help/"}), "/ja/help/")
        self.assertEqual(locales.localized_route("/", self.JA, {"/"}), "/ja/")

    def test_falls_back_when_the_page_does_not_exist(self) -> None:
        """Partial coverage is legal, so an unlocalized page keeps its English link."""
        self.assertEqual(locales.localized_route("/learn/", self.JA, {"/help/"}), "/learn/")

    def test_app_locale_routing_normalizes_a_regional_language_code(self) -> None:
        """The app sends nl-NL/de-DE; page routing works with the base language."""
        registry = {
            "en": {
                "code": "en",
                "hreflang": "en",
                "native_name": "English",
                "status": "published",
                "x_default": True,
            },
            "nl": {
                "code": "nl",
                "hreflang": "nl",
                "native_name": "Nederlands",
                "status": "published",
            },
        }
        translations = {"nl": {"learn/example.html": {}}}
        strings = {
            "locale.offer": {"nl": "Lees deze pagina in het Nederlands"},
            "locale.dismiss": {"nl": "Sluiten"},
        }

        markup = build_site.render_locale_routing(
            "learn/example.html",
            registry,
            translations,
            "en",
            strings,
            "../",
        )

        self.assertIn('"nl":{"url":"/nl/learn/example"', markup)
        self.assertIn("q.toLowerCase().split('-')[0]", markup)

    def test_language_switcher_uses_one_menu_for_all_available_locales(self) -> None:
        registry = {
            "en": {
                "code": "en",
                "hreflang": "en",
                "native_name": "English",
                "status": "published",
                "x_default": True,
            },
            "nl": {
                "code": "nl",
                "hreflang": "nl",
                "native_name": "Nederlands",
                "status": "published",
            },
        }
        translations = {"nl": {"learn/example.html": {}}}
        strings = {"a11y.language": {"en": "Language", "nl": "Taal"}}

        markup = build_site.render_language_switcher(
            "learn/example.html", registry, translations, "nl", strings
        )

        self.assertIn('<details class="lang-switch">', markup)
        self.assertIn('<span class="lang-switch-current">Nederlands</span>', markup)
        self.assertIn('aria-current="true"', markup)
        self.assertIn('href="/learn/example"', markup)
        self.assertEqual(markup.count('class="lang-switch-panel"'), 1)


class LearnDisclaimerTests(unittest.TestCase):
    STRINGS = {
        "learn.disclaimer_label": {"en": "Important", "nl": "Let op"},
        "learn.disclaimer": {"en": "Check the source.", "nl": "Controleer de bron."},
        "learn.translation_note": {
            "en": "Translated from English.",
            "nl": "Vertaald uit het Engels.",
        },
    }

    def test_learn_article_gets_one_disclaimer_after_verification(self) -> None:
        article = {"path": "learn/example.html", "section": "learn"}
        content = '<h1>Example</h1>\n<p class="verified">Last verified: today</p>\n<p>Body</p>'

        rendered = build_site.render_learn_disclaimer(
            content, article, {"code": "nl"}, self.STRINGS
        )

        self.assertEqual(rendered.count('class="learn-disclaimer"'), 1)
        self.assertIn("Controleer de bron.", rendered)
        self.assertIn("Vertaald uit het Engels.", rendered)
        self.assertLess(rendered.index("learn-disclaimer"), rendered.index("Body"))

    def test_english_disclaimer_has_no_translation_note(self) -> None:
        article = {"path": "learn/example.html", "section": "learn"}
        content = '<p class="verified">Last verified: today</p>'

        rendered = build_site.render_learn_disclaimer(
            content, article, {"code": "en"}, self.STRINGS
        )

        self.assertIn("Check the source.", rendered)
        self.assertNotIn("learn-translation-note", rendered)

    def test_help_article_is_unchanged(self) -> None:
        article = {"path": "help/example.html", "section": "help"}
        content = "<p>Help copy</p>"
        self.assertEqual(
            build_site.render_learn_disclaimer(
                content, article, {"code": "nl"}, self.STRINGS
            ),
            content,
        )


class DateTests(unittest.TestCase):
    def test_english_matches_the_committed_wording(self) -> None:
        locale = locales.load_locales()[locales.default_locale_code()]
        self.assertEqual(locales.render_date("2026-08-02", locale), "August 2, 2026")

    def test_year_leading_locale(self) -> None:
        locale = {"code": "ja", "date_format": "{y}年{m}月{d}日"}
        self.assertEqual(locales.render_date("2026-08-02", locale), "2026年8月2日")


class StalenessTests(unittest.TestCase):
    FRAGMENT = (
        "<p>Add the widget.</p>\n"
        '<figure class="help-shot help-shot-screen"><img src="/assets/article-images/help/'
        'widgets/widget-gallery.webp" alt="Widget gallery" width="1206" height="2622" '
        'loading="lazy" decoding="async" /></figure>\n'
    )

    def test_recapture_does_not_flag_a_translation_stale(self) -> None:
        """sync_help_screenshots rewrites dimensions; that is not a prose change."""
        resized = self.FRAGMENT.replace('width="1206" height="2622"', 'width="1290" height="2796"')
        self.assertEqual(locales.source_hash(self.FRAGMENT), locales.source_hash(resized))

    def test_prose_edit_flags_a_translation_stale(self) -> None:
        edited = self.FRAGMENT.replace("Add the widget.", "Add the widget to your Home Screen.")
        self.assertNotEqual(locales.source_hash(self.FRAGMENT), locales.source_hash(edited))

    def test_figure_collapses_to_its_slot_key(self) -> None:
        self.assertIn("[figure:widget-gallery]", locales.translatable_source(self.FRAGMENT))


if __name__ == "__main__":
    unittest.main()
