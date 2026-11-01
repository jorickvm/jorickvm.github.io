import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_translations as check
from locales import load_locales


class TranslationEntityTests(unittest.TestCase):
    def test_apostrophe_entity_is_not_a_missing_factual_number(self):
        english = "<p>Brazil&#x27;s threshold is 184 days.</p>"
        problems = []
        check.check_structure("nl/example", english,
                              "<p>De drempel in Brazilië is 184 dagen.</p>",
                              load_locales()["nl"], set(), problems)
        self.assertEqual(problems, [])
        check.check_structure("nl/example", english,
                              "<p>De drempel in Brazilië is 183 dagen.</p>",
                              load_locales()["nl"], set(), problems)
        self.assertTrue(any("184" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
