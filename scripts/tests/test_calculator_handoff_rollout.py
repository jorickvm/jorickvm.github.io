import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import build_site


class CalculatorHandoffRolloutTests(unittest.TestCase):
    def test_release_switch_only_affects_trackers_requiring_3_0_3(self):
        cases = [
            ("dayCount", None, True),
            *(("dayCount", "day-count-" + code, True) for code in ("nl", "de", "mx", "be", "jp")),
            *(("days183", preset, True) for preset in ("residence-cambodia", "residence-barbados",
                                                       "residence-united-arab-emirates-90-days")),
            ("days183", "residence-united-arab-emirates", False),
            ("schengen", "visa-turkiye-short-stay", False),
            ("presence", "citizenship-new-zealand-presence", False),
            ("ukIlr", "citizenship-uk-naturalisation-combined", False),
        ]
        with tempfile.TemporaryDirectory() as directory, patch.object(build_site, "SOURCE_ROOT", Path(directory)):
            config = Path(directory) / "data/calculator-handoffs.json"
            config.parent.mkdir()
            for enabled in (False, True):
                config.write_text(json.dumps({"enable_3_0_3_trackers": enabled}))
                for rule, preset, affected in cases:
                    with self.subTest(enabled=enabled, rule=rule, preset=preset):
                        html = (f'<div data-day-calendar="{rule}"><div class="cal-dialog-foot"></div></div>'
                                '<script src="/assets/js/day-calendar.js?v=old"></script>')
                        result = build_site.render_calculator_handoff(html, {"app_preset": preset})
                        self.assertEqual('data-cal-handoff="trips-only"' in result, affected and not enabled)
                        self.assertEqual("data-cal-tracker-version" in result, affected and enabled)
                        if affected:
                            self.assertNotIn("?v=old", result)
                        else:
                            self.assertEqual(result, html)
