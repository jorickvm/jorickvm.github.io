from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_site  # noqa: E402


class AuditSiteTests(unittest.TestCase):
    def test_dark_default_contract_matches_expected_bootstrap(self) -> None:
        source = (
            "var t=localStorage.getItem('theme');"
            "document.documentElement.setAttribute('data-theme',t==='light'?'light':'dark')"
        )
        self.assertRegex(source, audit_site.THEME_DARK_DEFAULT)

    def test_system_preference_bootstrap_does_not_match_contract(self) -> None:
        source = (
            "var t=localStorage.getItem('theme');"
            "if(t)document.documentElement.setAttribute('data-theme',t)"
        )
        self.assertIsNone(audit_site.THEME_DARK_DEFAULT.search(source))

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


if __name__ == "__main__":
    unittest.main()
