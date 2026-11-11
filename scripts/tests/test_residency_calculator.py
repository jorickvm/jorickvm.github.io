import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class ResidencyCalculatorTests(unittest.TestCase):
    def test_cyprus_border_days_and_other_country_counts(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is required to execute the calculator")
        harness = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const source = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const window = {};
vm.runInNewContext(source, {window, Set});
const rule = window.AtlasDaysRules.days183;
const D = {
  fromParts: (y, m, d) => Date.UTC(y, m - 1, d) / 86400000,
  iso: d => new Date(d * 86400000).toISOString().slice(0, 10),
  parts: d => ({y: new Date(d * 86400000).getUTCFullYear()})
};
const day = (m, d, y = 2026) => D.fromParts(y, m, d);
const trip = (start, end, country = 'CY') => ({start, end, country});
function context(settings, trips) {
  return {D, today: day(11, 12), settings: {year: '2026', ...settings}, trips,
    allowed: ['CY', 'GR'], offers: {CY: 'residence-cyprus'},
    text: (key, args) => args ? String(args.n) : key, tone: () => '', dateRange: () => ''};
}
function linked(country) {
  return rule.fromQuery(new URLSearchParams('country=' + country + '&period=calendar&resident=184'),
    context({}, [])).settings;
}
function count(trips, settings = linked('CY')) {
  return rule.evaluate(trips, context(settings, trips)).meter.days;
}
const visit = [trip(day(1, 1), day(1, 5))];
assert.equal(count(visit), 4, 'arrival in, departure out');
assert.equal(rule.tripLabel(visit[0], context(linked('CY'), visit)), '4');
assert.equal(count([trip(day(1, 3), day(1, 3))]), 1, 'same-day visit counts');
const split = [trip(day(1, 1), day(1, 3)), trip(day(1, 3), day(1, 5))];
assert.equal(count(split), 4, 'split records alone describe one continuous stay');
const excursion = [...split, trip(day(1, 3), day(1, 3), 'GR')];
assert.equal(count(excursion), 3, 'departure and return on the same day is outside');
assert.equal(rule.tripLabel(split[1], context(linked('CY'), excursion)), '1');
assert.equal(count([...visit, ...visit, trip(day(1, 3), day(1, 7))]), 6, 'merge duplicates and overlaps');
assert.equal(count([trip(day(12, 30, 2025), day(1, 1))]), 0, 'departure on first day of year');
assert.equal(count([trip(day(12, 30, 2025), day(1, 2, 2027))]), 365, 'clip after resolving border days');
assert.equal(count([trip(day(1, 5), day(1, 4))]), 0, 'ignore reversed interval');
assert.equal(count([trip(day(1, 1), day(7, 3))]), 183);
assert.equal(count([trip(day(1, 1), day(7, 4))]), 184);
assert.equal(count([trip(day(1, 1), day(1, 5), 'GR')], linked('GR')), 5, 'other linked countries stay inclusive');
assert.equal(count([trip(day(1, 1), day(1, 5), 'GR')], {...linked('CY'), country: 'GR'}), 5,
  'changing the selected country does not apply Cyprus days to it');
const c = context(linked('CY'), visit);
assert.equal(rule.trackerOffer(visit, c), 'residence-cyprus,goal:stay,year:2026');
c.settings.limitInput = 100;
assert.equal(rule.trackerOffer(visit, c), '', 'do not offer an inclusive custom tracker for Cyprus');
console.log('Cyprus border-day cases, period boundaries, thresholds and import offer passed.');
"""
        result = subprocess.run(
            [node, "-e", harness], text=True, capture_output=True, timeout=30,
            input=json.dumps((ROOT / "assets/js/rules/days-183.js").read_text()),
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
