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

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and attrs.get("type") == "checkbox":
            self.codes.append(attrs["value"])


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
                codes = set(parser.codes)
                self.assertEqual(len(parser.codes), 195)
                self.assertEqual(len(codes), 195)
                self.assertTrue({"VA", "PS"}.issubset(codes))
                self.assertFalse({"TW", "XK", "PR", "HK"}.intersection(codes))
                if baseline is None:
                    baseline = codes
                self.assertEqual(codes, baseline)
                self.assertNotIn("<!-- COUNTRY_CHECKLIST -->", rendered)

    def test_other_articles_are_left_untouched(self):
        content = "<p>A visa day count.</p>"
        self.assertEqual(build_site.render_country_checklist(content, "en"), content)


if __name__ == "__main__":
    unittest.main()
