from __future__ import annotations

import sys
import json
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_site  # noqa: E402


class AuditSiteTests(unittest.TestCase):
    EXPECTED_BOOTSTRAP = (
        "var d=document.documentElement,"
        "q=new URLSearchParams(location.search).get('theme'),t=null;"
        "if(q==='light'||q==='dark'){t=q;try{sessionStorage.setItem('theme',q)}catch(e){}}"
        "else{try{t=sessionStorage.getItem('theme')}catch(e){}"
        "if(!t)try{t=localStorage.getItem('theme')}catch(e){}}"
        "d.setAttribute('data-theme',t==='light'?'light':'dark')"
    )

    def test_dark_default_contract_matches_expected_bootstrap(self) -> None:
        self.assertRegex(self.EXPECTED_BOOTSTRAP, audit_site.THEME_DARK_DEFAULT)

    def test_app_override_contract_matches_expected_bootstrap(self) -> None:
        self.assertRegex(self.EXPECTED_BOOTSTRAP, audit_site.THEME_APP_OVERRIDE)

    def test_system_preference_bootstrap_does_not_match_contract(self) -> None:
        source = (
            "var t=localStorage.getItem('theme');"
            "if(t)document.documentElement.setAttribute('data-theme',t)"
        )
        self.assertIsNone(audit_site.THEME_DARK_DEFAULT.search(source))

    def test_bootstrap_without_app_override_is_rejected(self) -> None:
        source = (
            "var t=localStorage.getItem('theme');"
            "document.documentElement.setAttribute('data-theme',t==='light'?'light':'dark')"
        )
        self.assertRegex(source, audit_site.THEME_DARK_DEFAULT)
        self.assertIsNone(audit_site.THEME_APP_OVERRIDE.search(source))

    def test_route_mapping(self) -> None:
        self.assertEqual(audit_site.route_for_path(audit_site.SITE_ROOT / "index.html"), "/")
        self.assertEqual(
            audit_site.route_for_path(audit_site.SITE_ROOT / "help" / "index.html"),
            "/help/",
        )
        self.assertEqual(
            audit_site.route_for_path(audit_site.SITE_ROOT / "learn" / "example.html"),
            "/learn/example",
        )

    def test_parser_uses_main_content_for_baseline(self) -> None:
        parser = audit_site.PageParser()
        parser.feed(
            "<header>Navigation changes</header>"
            "<main><article><h1>Stable title</h1><p>Stable body.</p></article></main>"
            "<footer>Footer changes</footer>"
        )
        self.assertEqual(parser.h1, ["Stable title"])
        self.assertEqual(parser.content_text, "Stable title Stable body.")

    def test_parser_falls_back_to_article_before_main_migration(self) -> None:
        parser = audit_site.PageParser()
        parser.feed("<header>Navigation</header><article><h1>Title</h1><p>Body.</p></article>")
        self.assertEqual(parser.content_text, "Title Body.")

    def test_legacy_related_block_pattern_matches_only_hand_authored_blocks(self) -> None:
        self.assertIsNotNone(
            audit_site.LEGACY_RELATED_PATTERN.search('<div class="related">\n<h2>Related</h2>')
        )
        self.assertIsNone(
            audit_site.LEGACY_RELATED_PATTERN.search('<nav class="related generated-related">')
        )

    def test_learn_fragments_carry_no_legacy_related_blocks(self) -> None:
        findings: list[audit_site.Finding] = []
        audit_site.audit_learn_fragments(findings)
        self.assertEqual(findings, [])

    def test_generated_pages_are_not_content_hash_compared(self) -> None:
        # build_site.py --check already fails when committed HTML is not what
        # the sources render, so comparing the hash here only forced the
        # baseline to be re-armed alongside every copy edit.
        for path in ("changelog.html", "learn/schengen-90-180-rule.html", "index.html"):
            with self.subTest(path=path):
                self.assertNotIn(path, audit_site.BASELINE_HAND_AUTHORED)

    def test_hand_authored_pages_are_content_hash_compared(self) -> None:
        # Nothing rebuilds these, so the baseline hash is their only guard.
        self.assertEqual(
            audit_site.BASELINE_HAND_AUTHORED,
            {
                "app/changelog/index.html",
                "app/help/index.html",
                "app/privacy/index.html",
                "app/terms/index.html",
                "learn/day-limits.html",
                "learn/how-to-use-atlasdays.html",
                "learn/icloud-sync-travel-tracking.html",
            },
        )

    def test_hand_authored_list_has_not_gone_stale(self) -> None:
        # A renamed or deleted stub would leave a path here guarding nothing.
        for path in audit_site.BASELINE_HAND_AUTHORED:
            with self.subTest(path=path):
                self.assertTrue((audit_site.SITE_ROOT / path).is_file())

    def test_root_content_pages_have_styles_and_single_shared_scripts(self) -> None:
        pages = json.loads((audit_site.SITE_ROOT / "_site-src/data/pages.json").read_text())["pages"]
        by_path = {page["path"]: page for page in pages}
        for path in ("about.html", "privacy.html", "terms.html"):
            with self.subTest(path=path):
                self.assertTrue(by_path[path]["style_variants"])
                source = (audit_site.SITE_ROOT / path).read_text()
                self.assertIn("assets/css/page-variants/legal.css", source)
                self.assertEqual(source.count("assets/js/theme.js"), 1)
                self.assertEqual(source.count("assets/js/navigation.js"), 1)


if __name__ == "__main__":
    unittest.main()
