#!/usr/bin/env python3
"""Sitemap splitting: the index, the per-locale children, and orphan cleanup."""

from __future__ import annotations

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_route_outputs as outputs


NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def route(path: str, canonical: str, lastmod: str = "2026-01-01", **extra: object) -> dict[str, object]:
    return {"path": path, "canonical": canonical, "lastmod": lastmod, **extra}


class RoutesByLocaleTests(unittest.TestCase):
    def test_groups_by_path_prefix_with_default_first(self) -> None:
        grouped = outputs.routes_by_locale(
            [
                route("ja/help/create-a-tracker.html", "https://atlasdays.app/ja/help/create-a-tracker"),
                route("index.html", "https://atlasdays.app/"),
                route("nl/index.html", "https://atlasdays.app/nl/"),
            ]
        )
        self.assertEqual(list(grouped), ["en", "ja", "nl"])
        self.assertEqual(len(grouped["en"]), 1)

    def test_skips_non_indexable_routes(self) -> None:
        grouped = outputs.routes_by_locale(
            [
                route("index.html", "https://atlasdays.app/"),
                route("draft.html", "https://atlasdays.app/draft", indexable=False),
            ]
        )
        self.assertEqual(len(grouped["en"]), 1)

    def test_locale_without_pages_gets_no_group(self) -> None:
        """A draft locale must not receive an empty sitemap of its own."""
        grouped = outputs.routes_by_locale([route("index.html", "https://atlasdays.app/")])
        self.assertEqual(list(grouped), ["en"])


class SitemapIndexTests(unittest.TestCase):
    def test_index_lists_each_child_with_its_newest_date(self) -> None:
        rendered = outputs.render_sitemap_index(
            {
                "en": [route("index.html", "https://atlasdays.app/", "2026-01-01")],
                "uk": [
                    route("uk/index.html", "https://atlasdays.app/uk/", "2026-08-17"),
                    route("uk/about.html", "https://atlasdays.app/uk/about", "2026-08-18"),
                ],
            }
        )
        root = ET.fromstring(rendered)
        self.assertEqual(root.tag, NS + "sitemapindex")
        entries = [
            (entry.findtext(NS + "loc"), entry.findtext(NS + "lastmod"))
            for entry in root.iter(NS + "sitemap")
        ]
        self.assertEqual(
            entries,
            [
                ("https://atlasdays.app/sitemap-en.xml", "2026-01-01"),
                ("https://atlasdays.app/sitemap-uk.xml", "2026-08-18"),
            ],
        )

    def test_index_carries_no_page_urls(self) -> None:
        """The index must not double-list pages that live in a child."""
        rendered = outputs.render_sitemap_index(
            {"en": [route("index.html", "https://atlasdays.app/")]}
        )
        self.assertNotIn("https://atlasdays.app/</loc>", rendered)


class SitemapFilesTests(unittest.TestCase):
    def test_every_url_lands_in_exactly_one_child(self) -> None:
        routes = [
            route("index.html", "https://atlasdays.app/"),
            route("ja/index.html", "https://atlasdays.app/ja/"),
            route("ja/about.html", "https://atlasdays.app/ja/about"),
        ]
        files = outputs.sitemap_files(routes)
        self.assertIn(outputs.SITEMAP, files)

        found: list[str] = []
        for path, text in files.items():
            if path == outputs.SITEMAP:
                continue
            found += [node.text or "" for node in ET.fromstring(text).iter(NS + "loc")]
        self.assertEqual(sorted(found), sorted(str(item["canonical"]) for item in routes))
        self.assertEqual(len(found), len(set(found)))

    def test_child_filenames_match_the_index(self) -> None:
        files = outputs.sitemap_files(
            [
                route("index.html", "https://atlasdays.app/"),
                route("ja/index.html", "https://atlasdays.app/ja/"),
            ]
        )
        declared = {
            (entry.findtext(NS + "loc") or "").rsplit("/", 1)[-1]
            for entry in ET.fromstring(files[outputs.SITEMAP]).iter(NS + "sitemap")
        }
        on_disk = {path.name for path in files if path != outputs.SITEMAP}
        self.assertEqual(declared, on_disk)


class OrphanSitemapTests(unittest.TestCase):
    def test_reports_a_sitemap_no_locale_claims(self) -> None:
        expected = {outputs.SITEMAP, outputs.ROOT / "sitemap-en.xml"}
        retired = outputs.ROOT / "sitemap-zz.xml"
        retired.write_text("<urlset/>", encoding="utf-8")
        try:
            self.assertIn(retired, outputs.orphan_sitemaps(expected))
        finally:
            retired.unlink()

    def test_accepts_the_committed_set(self) -> None:
        routes = outputs.expanded_routes(
            __import__("json").loads(outputs.ROUTES.read_text(encoding="utf-8"))["routes"]
        )
        self.assertEqual(outputs.orphan_sitemaps(set(outputs.sitemap_files(routes))), [])


if __name__ == "__main__":
    unittest.main()
