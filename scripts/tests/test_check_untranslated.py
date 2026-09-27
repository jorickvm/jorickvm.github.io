from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import check_untranslated as check  # noqa: E402


class CheckUntranslatedTests(unittest.TestCase):
    def test_csv_example_checks_notes_but_not_machine_country_values(self):
        markup = '<p>United States</p><div class="data-table data-table-code"><table><tr><td>Japan</td><td></td><td>2019</td><td></td><td>Personal</td><td>Osaka, month unknown</td></tr></table></div>'
        runs = check.visible_runs(markup)
        self.assertIn('United States', runs)
        self.assertIn('Osaka, month unknown', runs)
        self.assertNotIn('Japan', runs)
        self.assertNotIn('Personal', runs)


    def test_brand_name_does_not_exempt_an_english_sentence(self) -> None:
        self.assertFalse(
            check.is_allowed("Get AtlasDays on the App Store")
        )

    def test_brand_product_name_can_remain_unchanged(self) -> None:
        self.assertTrue(check.is_allowed("AtlasDays Pro"))

    def test_partial_english_run_inside_translated_text_is_found(self) -> None:
        english = {
            "Presumption is a rebuttable presumption based on days alone."
        }
        translated = {
            "Presunción: Presumption is a rebuttable presumption based on days alone."
        }
        self.assertEqual(
            check.partial_english(english, translated),
            {"Presumption is a rebuttable presumption based on days alone."},
        )


if __name__ == "__main__":
    unittest.main()
