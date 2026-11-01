"""Tests for terminology extraction in sync_glossary.py.

Under-enforcement passes every other gate, so these pin two cases: the table
extractor stops at the end of the last language section, and a table that lists
only its divergences still enforces the terms it inherits.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import sync_glossary  # noqa: E402


GUIDELINES = """
#### Accepted Traditional Chinese terminology

| Source | Accepted translation | Literal | `zh-Hant` | Reason |
| --- | --- | --- | --- | --- |
| Tracker | 追蹤器 | "Tracker." | | Because. |
| Ongoing | 停留中 | "Staying." | | Because. |
| Per Stay | 每次入境 | "Per entry." | | Because. |

#### Accepted Simplified Chinese terminology

| Source | Accepted translation | Literal | `zh-Hant` | Reason |
| --- | --- | --- | --- | --- |
| Tracker | 追踪器 | "Tracker." | 追蹤器 | Script only. |

## Decision Log Template

| Source | Accepted translation | Literal | Context | Reason |
| --- | --- | --- | --- | --- |
| Example term | Example translation | "Literal" | Settings row | Fits one line. |
"""


class TableBoundaryTests(unittest.TestCase):
    def test_a_shallower_heading_ends_the_table(self):
        """A `##` heading ends the last language section.

        Otherwise the rows of the section that follows (here a template's
        example row) would be published as enforced terms.
        """
        rows = sync_glossary.terminology_rows(GUIDELINES, "Simplified Chinese")
        self.assertEqual([row[0] for row in rows], ["Tracker"])

    def test_a_sibling_heading_still_ends_the_table(self):
        rows = sync_glossary.terminology_rows(GUIDELINES, "Traditional Chinese")
        self.assertEqual([row[0] for row in rows], ["Tracker", "Ongoing", "Per Stay"])


class InheritanceTests(unittest.TestCase):
    """A divergences-only table has to enforce the rows it does not list."""

    def own(self):
        return [{"en": source} for source, _, _ in
                sync_glossary.terminology_rows(GUIDELINES, "Simplified Chinese")]

    def test_an_absent_row_is_taken_from_the_shipped_catalog(self):
        extra = sync_glossary.inherited_terms(
            GUIDELINES, "zh-Hans", {"Ongoing": "停留中"}, self.own()
        )
        self.assertEqual([e["en"] for e in extra], ["Ongoing"])
        self.assertEqual(extra[0]["accepted"], ["停留中"])
        self.assertEqual(extra[0]["inherited_from"], "Traditional Chinese")

    def test_a_row_the_app_does_not_ship_is_skipped_not_guessed(self):
        """Never fall back to the base language's value.

        `每次入境` is Traditional. Carrying it across would be a script
        conversion, which is the one thing a terminology gate must not do: an
        invented accepted form fails copy that is correct.
        """
        extra = sync_glossary.inherited_terms(GUIDELINES, "zh-Hans", {}, self.own())
        self.assertEqual(extra, [])

    def test_a_row_the_language_lists_itself_is_not_overwritten(self):
        extra = sync_glossary.inherited_terms(
            GUIDELINES, "zh-Hans", {"Tracker": "追踪器"}, self.own()
        )
        self.assertEqual(extra, [])

    def test_a_language_with_its_own_complete_table_inherits_nothing(self):
        extra = sync_glossary.inherited_terms(
            GUIDELINES, "ko", {"Ongoing": "체류 중"}, self.own()
        )
        self.assertEqual(extra, [])


if __name__ == "__main__":
    unittest.main()
