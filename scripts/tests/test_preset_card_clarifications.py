import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_site
import locales
import check_translations


class PresetCardClarificationTests(unittest.TestCase):
    def setUp(self):
        self.preset = {
            "family": "usState", "flag": "US-CA", "rank": {"en": 7, "ja": 12},
            "title": {"en": "California", "ja": "カリフォルニア州"},
            "line": {"en": "Catalogue wording", "ja": "元の説明"},
        }
        self.clarifications = {
            "us-state-ca": {
                "source_line": "Catalogue wording",
                "line": {"en": "A planning estimate & a separate legal rule.", "ja": "日数の目安と法定基準は異なります。"},
            }
        }

    def test_clarified_line_uses_the_requested_locale_without_mutating_the_catalogue(self):
        original = copy.deepcopy(self.preset)
        self.assertEqual(build_site.preset_card_line("us-state-ca", self.preset, "ja", self.clarifications),
                         self.clarifications["us-state-ca"]["line"]["ja"])
        self.assertEqual(self.preset, original)
        self.assertEqual(build_site.preset_card_line("other-preset", self.preset, "en", self.clarifications),
                         self.preset["line"]["en"])

    def test_catalogue_change_requires_review_instead_of_silently_retaining_the_clarification(self):
        self.preset["line"]["en"] = "Updated catalogue wording"
        with self.assertRaisesRegex(SystemExit, "catalogue line changed"):
            build_site.preset_card_line("us-state-ca", self.preset, "ja", self.clarifications)

    def test_missing_localized_clarification_never_falls_back_to_english(self):
        del self.clarifications["us-state-ca"]["line"]["ja"]
        with self.assertRaisesRegex(SystemExit, "no ja line"):
            build_site.preset_card_line("us-state-ca", self.preset, "ja", self.clarifications)

    def test_render_keeps_the_preset_identity_order_and_destination(self):
        path = "learn/california-tax-residency.html"
        data = {"catalog": {"presets": {"us-state-ca": self.preset}}, "own": {},
                "records": {path: {"app_preset": "us-state-ca"}}, "clarifications": self.clarifications}
        with patch.dict(build_site._card_data, data, clear=True):
            family, rank, markup = build_site.rule_card(path, "en", locales.load_locales()["en"],
                                                      {"/learn/california-tax-residency"})
        self.assertEqual((family, rank), ("usState", 7))
        self.assertIn('href="/learn/california-tax-residency"', markup)
        self.assertIn('/assets/flags/us-ca.png', markup)
        self.assertIn('<strong>California</strong>', markup)
        self.assertIn('A planning estimate &amp; a separate legal rule.', markup)
        self.assertNotIn('Catalogue wording', markup)

    def test_clarification_data_keeps_every_threshold_number(self):
        cards = {"line_clarifications": {"example": {"line": {
            "en": "270 days is an estimate. More than 9 months.",
            "ja": "270日は目安です。法定の月数を確認してください。",
        }}}}
        problems = []
        check_translations.check_card_clarifications(
            cards, {"en": {"status": "published"}, "ja": {"status": "published"}}, problems,
        )
        self.assertTrue(any("drops number(s)" in p and "9" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
