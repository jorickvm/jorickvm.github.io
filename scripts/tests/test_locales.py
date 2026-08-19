import json
import shutil
import sys
import tempfile
import unittest
import unittest.mock
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

    def test_untranslated_pages_have_no_overlay_and_no_output(self) -> None:
        """A page served in English only must be absent from the locale entirely.

        Leaving an overlay behind would keep pinning the English hash, which is
        the coupling the exemption exists to remove.
        """
        import json

        for code, entry in self.locales.items():
            registry = entry.get("articles")
            if not registry:
                continue
            data = json.loads((ROOT / "_site-src" / str(registry)).read_text(encoding="utf-8"))
            overlays = {
                str(item["source"])
                for key in ("articles", "hubs", "pages")
                for item in data.get(key, [])
            }
            prefix = str(entry.get("route_prefix", "")).strip("/")
            for source in entry.get("untranslated", []):
                with self.subTest(locale=code, source=source):
                    self.assertNotIn(str(source), overlays)
                    self.assertFalse((ROOT / prefix / str(source)).exists())

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

    def test_dutch_hub_embeds_localized_dynamic_search_copy(self) -> None:
        rendered = (ROOT / "nl" / "learn" / "index.html").read_text(encoding="utf-8")
        self.assertIn("window.AtlasDaysSearchStrings=", rendered)
        self.assertIn("Geen passende regel of gids gevonden.", rendered)
        self.assertIn("{count} resultaten gevonden", rendered)


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
        self.assertIn('hreflang="en"', markup)
        self.assertEqual(markup.count('class="lang-switch-panel"'), 1)


class LearnTrustTests(unittest.TestCase):
    STRINGS = {
        "learn.official_source": {"en": "Official source", "nl": "Officiële bron", "ja": "公式情報源"},
        "learn.official_sources": {"en": "Official sources", "nl": "Officiële bronnen", "ja": "公式情報源"},
        "learn.context_label": {
            "en": "About this article",
            "nl": "Over dit artikel",
            "ja": "この記事について",
        },
        "learn.disclaimer": {
            "en": "Check the source.",
            "nl": "Controleer de bron.",
            "ja": "情報源を確認してください。",
        },
    }
    LOCALES = {
        "en": {"code": "en", "label_colon": ":"},
        "nl": {"code": "nl", "label_colon": ":"},
        "ja": {"code": "ja", "label_colon": "："},
    }

    def test_learn_article_ends_with_source_and_context(self) -> None:
        article = {
            "path": "learn/example.html",
            "section": "learn",
            "sources": [{"url": "https://example.gov/rule"}],
            "source_note": 'The <a href="{{source:0}}">official rule</a> explains the test.',
        }
        content = '<h1>Example</h1>\n<p class="verified">Last verified: today</p>\n<p>Body</p>'

        rendered = build_site.render_learn_trust(
            content, article, self.LOCALES["nl"], self.STRINGS
        )

        self.assertEqual(rendered.count('class="article-trust"'), 1)
        self.assertEqual(rendered.count('class="learn-disclaimer"'), 1)
        self.assertIn("Officiële bron", rendered)
        self.assertIn('href="https://example.gov/rule"', rendered)
        self.assertIn(
            '<p class="learn-disclaimer"><strong>Over dit artikel:</strong> '
            "Controleer de bron.</p>",
            rendered,
        )
        self.assertGreater(rendered.index("article-trust"), rendered.index("Body"))
        # The advice boundary is prose after the citation card, not a row in it.
        self.assertGreater(rendered.index("learn-disclaimer"), rendered.index("</aside>"))

    def test_article_without_source_note_has_no_card_at_all(self) -> None:
        article = {"path": "learn/example.html", "section": "learn"}
        content = '<p class="verified">Last verified: today</p>'

        rendered = build_site.render_learn_trust(
            content, article, self.LOCALES["en"], self.STRINGS
        )

        self.assertNotIn("article-trust", rendered)
        self.assertIn("<strong>About this article:</strong> Check the source.", rendered)

    def test_japanese_takes_the_full_width_colon_and_no_space(self) -> None:
        article = {"path": "learn/example.html", "section": "learn"}
        content = '<p class="verified">Last verified: today</p>'

        rendered = build_site.render_learn_trust(
            content, article, self.LOCALES["ja"], self.STRINGS
        )

        self.assertIn(
            "<strong>この記事について：</strong>情報源を確認してください。", rendered
        )

    def test_learn_article_without_a_verified_date_fails(self) -> None:
        article = {"path": "learn/example.html", "section": "learn"}

        with self.assertRaises(SystemExit):
            build_site.render_learn_trust(
                "<h1>Example</h1>\n<p>Body</p>", article, {"code": "en"}, self.STRINGS
            )

    def test_help_article_is_unchanged(self) -> None:
        article = {"path": "help/example.html", "section": "help"}
        content = "<p>Help copy</p>"
        self.assertEqual(
            build_site.render_learn_trust(
                content, article, {"code": "nl"}, self.STRINGS
            ),
            content,
        )

    def test_existing_legal_basis_row_is_left_as_plain_text(self) -> None:
        """The row names the statute; it does not link to it.

        It used to. The factbox sits above the fold, so that link was the
        earliest way off the page, competing with the download CTA before the
        reader had reached it (Jorick, 2026-08-17).
        """
        article = {
            "path": "learn/example.html",
            "section": "learn",
            "sources": [{"url": "https://example.gov/law"}],
        }
        content = (
            '<div class="factbox"><dl><div><dt>Threshold</dt><dd>90 days</dd></div>'
            '<div class="legal-basis"><dt>Legal basis</dt><dd>Example Act, s. 1</dd></div>'
            '</dl></div>'
        )

        rendered = build_site.render_factbox_legal_basis(content, article)

        self.assertEqual(rendered, content)
        self.assertNotIn("<a ", rendered)
        self.assertIn("Example Act, s. 1", rendered)

    def test_missing_legal_basis_row_is_generated_unlinked(self) -> None:
        article = {
            "path": "learn/example.html",
            "section": "learn",
            "sources": [{"url": "https://example.gov/law"}],
            "legal_basis": "Example Act, s. 1",
        }
        content = (
            '<div class="factbox"><dl>'
            '<div><dt>Threshold</dt><dd>90 days</dd></div>'
            '</dl></div>'
        )

        rendered = build_site.render_factbox_legal_basis(content, article)

        self.assertIn("{{t:learn.legal_basis}}", rendered)
        self.assertIn("<dd>Example Act, s. 1</dd>", rendered)
        self.assertNotIn("<a ", rendered)
        self.assertEqual(rendered.count('class="legal-basis"'), 1)


class NavScriptTests(unittest.TestCase):
    """navigation.js writes two labels at runtime, so it is handed them."""

    STRINGS = {
        "nav.menu_open": {"en": "Open navigation menu", "ja": "ナビゲーションメニューを開く"},
        "nav.menu_close": {"en": "Close navigation menu", "ja": "ナビゲーションメニューを閉じる"},
    }

    def test_payload_carries_this_locale_and_precedes_the_script(self) -> None:
        rendered = build_site.render_nav_script("../", "ja", self.STRINGS)

        self.assertIn("ナビゲーションメニューを開く", rendered)
        self.assertIn("ナビゲーションメニューを閉じる", rendered)
        self.assertNotIn("Open navigation menu", rendered)
        # The labels are useless to the script if it has already run.
        self.assertLess(
            rendered.index("AtlasDaysNavStrings"), rendered.index("navigation.js")
        )

    def test_every_published_locale_has_both_labels(self) -> None:
        strings = locales.load_ui_strings()
        for code, locale in locales.load_locales().items():
            if locale.get("status") != "published":
                continue
            with self.subTest(locale=code):
                # Would raise KeyError in the build, one locale at a time.
                build_site.render_nav_script("../", code, strings)

    def test_a_closing_tag_in_a_label_cannot_end_the_script_block(self) -> None:
        rendered = build_site.render_nav_script(
            "../",
            "en",
            {
                "nav.menu_open": {"en": "</script> menu"},
                "nav.menu_close": {"en": "Close navigation menu"},
            },
        )

        self.assertNotIn("</script> menu", rendered)
        self.assertIn("<\\/script>", rendered)


class RelatedArticleTests(unittest.TestCase):
    def test_localized_article_uses_localized_related_routes_and_titles(self) -> None:
        registry = locales.load_locales()
        translations = build_site.load_translations(registry)
        article = {
            "path": "es/learn/arizona-tax-residency.html",
            "social_source_path": "learn/arizona-tax-residency.html",
            "section": "learn",
        }

        rendered = build_site.render_cluster_related(article, registry["es"], translations)

        self.assertIn('class="related generated-related"', rendered)
        self.assertIn('href="/es/learn/', rendered)
        self.assertIn("Residencia fiscal", rendered)

    def test_flighty_article_has_related_articles(self) -> None:
        registry = locales.load_locales()
        translations = build_site.load_translations(registry)
        article = {
            "path": "learn/flighty-flight-history-day-count.html",
            "section": "learn",
        }

        rendered = build_site.render_cluster_related(article, registry["en"], translations)

        self.assertIn('class="related generated-related"', rendered)
        self.assertIn("Travel History", rendered)


class FaqGraphTests(unittest.TestCase):
    """The FAQ graph is the one place a translation can silently stay English.

    Nothing about a page looks wrong when it happens: the prose is translated,
    every structural check passes, and only a reader of the page source would
    notice. Dutch shipped 57 pages that way.
    """

    GRAPH = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": "Is Australia's test based on the calendar year?",
                    "acceptedAnswer": {"@type": "Answer", "text": "No, the income year."},
                }
            ],
        }
    )
    SOURCE = {"path": "learn/x.html", "content": "content/learn/x.html"}

    def _write(self, english: str, translated: str) -> Path:
        root = Path(tempfile.mkdtemp())
        (root / "content" / "learn").mkdir(parents=True)
        (root / "content" / "nl" / "learn").mkdir(parents=True)
        (root / "content" / "learn" / "x.html").write_text(english, encoding="utf-8")
        (root / "content" / "nl" / "learn" / "x.html").write_text(translated, encoding="utf-8")
        self.addCleanup(shutil.rmtree, root)
        return root

    def _render(self, root: Path, overlay: dict, locale: dict) -> str:
        with unittest.mock.patch.object(build_site, "SOURCE_ROOT", root):
            return build_site.translate_jsonld(
                self.GRAPH, overlay, self.SOURCE, locale, set(), {}
            )

    def test_matching_prose_is_derived_without_an_overlay_entry(self) -> None:
        root = self._write(
            "<h3>Is Australia's test based on the calendar year?</h3><p>No, the income year.</p>",
            "<h3>Gaat de toets uit van het kalenderjaar?</h3><p>Nee, het inkomstenjaar.</p>",
        )
        overlay = {"content": "content/nl/learn/x.html", "headline": "H", "description": "D"}

        rendered = self._render(root, overlay, {"code": "nl"})

        self.assertIn("Gaat de toets uit van het kalenderjaar?", rendered)
        self.assertIn("Nee, het inkomstenjaar.", rendered)

    def test_standalone_graph_copy_must_be_translated_explicitly(self) -> None:
        """The graph is written to stand alone in a rich result, so it is often
        not the same sentence as the page. That cannot be derived, and going
        unnoticed is exactly the bug."""
        root = self._write(
            "<h3>Is the test based on the calendar year?</h3><p>No, the income year.</p>",
            "<h3>Gaat de toets uit van het kalenderjaar?</h3><p>Nee, het inkomstenjaar.</p>",
        )
        overlay = {"content": "content/nl/learn/x.html", "headline": "H", "description": "D"}

        with self.assertRaises(SystemExit) as caught:
            self._render(root, overlay, {"code": "nl"})
        self.assertIn("still English", str(caught.exception))

    def test_a_known_gap_is_allowed_only_while_it_is_real(self) -> None:
        english = "<h3>Is the test based on the calendar year?</h3><p>No, the income year.</p>"
        dutch = "<h3>Gaat de toets uit van het kalenderjaar?</h3><p>Nee, het inkomstenjaar.</p>"
        root = self._write(english, dutch)
        overlay = {"content": "content/nl/learn/x.html", "headline": "H", "description": "D"}
        listed = {"code": "nl", "faq_graph_english": ["learn/x.html"]}

        # Listed, and genuinely still English: allowed, so the build stays green.
        # The answer derives from the matching prose; the standalone question
        # is the part that cannot, and is what remains English here.
        rendered = self._render(root, overlay, listed)
        self.assertIn("Is Australia's test based on the calendar year?", rendered)
        self.assertIn("Nee, het inkomstenjaar.", rendered)

        # Listed, but now fully translated: the entry is stale and must go.
        overlay["jsonld_replacements"] = {
            "Is Australia's test based on the calendar year?": "Gaat de Australische toets uit van het kalenderjaar?",
        }
        with self.assertRaises(SystemExit) as caught:
            self._render(root, overlay, listed)
        self.assertIn("Remove the entry", str(caught.exception))

    def test_a_shape_mismatch_fails_instead_of_guessing(self) -> None:
        root = self._write(
            "<h3>Q1</h3><p>A1</p><h3>Q2</h3><p>A2</p>",
            "<h3>V1</h3><p>A1</p>",
        )
        overlay = {"content": "content/nl/learn/x.html", "headline": "H", "description": "D"}

        with self.assertRaises(SystemExit) as caught:
            self._render(root, overlay, {"code": "nl"})
        self.assertIn("cannot be derived", str(caught.exception))


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

    def test_source_note_changes_metadata_hash_only_when_present(self) -> None:
        source = {"title": "Example", "meta": []}
        before = locales.meta_hash(source)

        self.assertEqual(before, locales.meta_hash({**source}))
        self.assertNotEqual(
            before,
            locales.meta_hash({**source, "source_note": "See the official rule."}),
        )


if __name__ == "__main__":
    unittest.main()
