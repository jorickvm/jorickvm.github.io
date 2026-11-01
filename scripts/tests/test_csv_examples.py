import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_translations import csv_schema_values

EXAMPLE = '<div class="data-table data-table-code"><table><tr><th>Country</th><th>State</th><th>Start Date</th><th>End Date</th><th>Purpose</th><th>Notes</th></tr><tr><td>United Kingdom</td><td></td><td>2026-09-01</td><td>2026-09-10</td><td>Personal</td><td>London, family</td></tr></table></div>'

class CsvExampleTests(unittest.TestCase):
    def test_notes_can_translate_without_changing_import_values(self):
        self.assertEqual(csv_schema_values(EXAMPLE), csv_schema_values(EXAMPLE.replace('London, family', 'Londres, famille')))

    def test_translated_country_header_or_purpose_changes_import_contract(self):
        for old, new in [('United Kingdom', 'Royaume-Uni'), ('Country', 'Pays'), ('Personal', 'Personnel')]:
            with self.subTest(old=old):
                self.assertNotEqual(csv_schema_values(EXAMPLE), csv_schema_values(EXAMPLE.replace(old, new)))
