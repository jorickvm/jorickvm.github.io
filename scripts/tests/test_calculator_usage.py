import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import build_site


class CalculatorUsageTests(unittest.TestCase):
    def test_client_and_collector_privacy_contract(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "node is required to check the counter privacy contract")
        result = subprocess.run([node, "--test", str(ROOT / "scripts/calculator-usage/usage.test.mjs")],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_placement_and_disabled_endpoint_are_rendered_without_page_urls(self):
        source = '<div data-day-calendar="spt"></div><script defer src="../assets/js/day-calendar.js?v=1"></script>'
        for path, placement in [("learn/substantial-presence-test-calculator.html", "standalone"),
                                ("learn/canadian-snowbird-day-limits.html", "embedded")]:
            with tempfile.TemporaryDirectory() as directory:
                config = Path(directory) / "data/calculator-usage.json"
                config.parent.mkdir()
                config.write_text(json.dumps({"enabled": False}))
                with patch.object(build_site, "SOURCE_ROOT", Path(directory)):
                    markup = build_site.render_calculator_usage(source, path, "../")
            self.assertIn(f'data-cal-placement="{placement}"', markup)
            self.assertIn('data-endpoint=""', markup)
            self.assertLess(markup.index('calculator-usage.js'), markup.index('day-calendar.js'))
            self.assertNotIn(path, markup)
