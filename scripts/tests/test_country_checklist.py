import json
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_site


class Options(HTMLParser):
    def __init__(self):
        super().__init__()
        self.codes = []
        self.kinds = {}
        self.continents = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "button" and "data-country-code" in attrs:
            code = attrs["data-country-code"]
            self.codes.append(code)
            self.kinds[code] = attrs["data-country-kind"]
            self.continents[code] = attrs["data-continent"]


class CountryChecklistTests(unittest.TestCase):
    def test_each_published_language_uses_the_same_sovereign_state_baseline(self):
        root = Path(__file__).resolve().parents[2]
        locales = json.loads((root / "_site-src/data/locales.json").read_text())["locales"]
        baseline = None
        for locale in locales:
            if locale.get("status") != "published":
                continue
            code = locale["code"]
            with self.subTest(locale=code):
                rendered = build_site.render_country_checklist("<!-- COUNTRY_CHECKLIST -->", code)
                parser = Options()
                parser.feed(rendered)
                codes = {c for c in parser.codes if parser.kinds[c] == "country"}
                self.assertEqual(len(codes), 195)
                self.assertEqual(len(parser.codes), len(set(parser.codes)))
                self.assertEqual(parser.kinds["HK"], "territory")
                self.assertEqual(parser.kinds["PR"], "territory")
                self.assertEqual(parser.kinds["TW"], "other")
                self.assertEqual(parser.kinds["XK"], "other")
                self.assertNotIn("XA", parser.codes)
                self.assertNotIn("XW", parser.codes)
                for place in parser.codes:
                    self.assertTrue(parser.continents[place])
                    self.assertTrue((root / f"assets/flags/{place.lower()}.png").is_file())
                self.assertTrue({"VA", "PS"}.issubset(codes))
                self.assertFalse({"TW", "XK", "PR", "HK"}.intersection(codes))
                if baseline is None:
                    baseline = codes
                self.assertEqual(codes, baseline)
                self.assertNotIn("<!-- COUNTRY_CHECKLIST -->", rendered)

    def test_country_import_uses_the_travel_history_product_page_only_where_available(self):
        root = Path(__file__).resolve().parents[2]
        pages = json.loads((root / "_site-src/data/product-pages.json").read_text())
        travel = pages["pages"]["travel-history"]
        locales = json.loads((root / "_site-src/data/locales.json").read_text())["locales"]
        for locale in locales:
            code = locale["code"]
            if locale.get("status") != "published":
                continue
            with self.subTest(locale=code):
                pairs = dict(p.split("=", 1) for p in build_site.product_page_presets(code, pages).split(",") if p)
                if code in travel.get("missing_locales", []):
                    self.assertNotIn("countries", pairs)
                else:
                    self.assertEqual(pairs["countries"], travel["ppid"])

    def test_other_articles_are_left_untouched(self):
        content = "<p>A visa day count.</p>"
        self.assertEqual(build_site.render_country_checklist(content, "en"), content)


if __name__ == "__main__":
    unittest.main()
