import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

class VisaDeadlineTests(unittest.TestCase):
    def test_calendar_boundaries_explicit_deadlines_and_invalid_input(self):
        node = shutil.which('node')
        self.assertIsNotNone(node)
        checks = r'''
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const window={};vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window});const D=window.AtlasDaysVisaDeadline;
const calc=x=>D.calculate({arrival:'2026-01-01',today:'2026-01-01',mode:'days',amount:'90',endConvention:'same',...x});
assert.equal(calc({}).deadline,'2026-03-31');assert.equal(calc({arrival:'2024-01-01'}).deadline,'2024-03-30');
assert.equal(calc({amount:1}).deadline,'2026-01-01');assert.equal(calc({amount:1}).totalDays,1);
assert.equal(calc({arrival:'2026-01-31',mode:'months',amount:1}).deadline,'2026-02-28');
assert.equal(calc({arrival:'2024-01-31',mode:'months',amount:1}).deadline,'2024-02-29');
assert.equal(calc({arrival:'2026-01-31',mode:'months',amount:1,endConvention:'before'}).deadline,'2026-02-27');
assert.equal(calc({arrival:'2024-02-29',mode:'years',amount:1}).deadline,'2025-02-28');
assert.equal(calc({arrival:'2026-05-01',mode:'months',amount:6}).deadline,'2026-11-01');
assert.equal(calc({arrival:'2026-05-01',mode:'days',amount:180}).deadline,'2026-10-27');
assert.equal(calc({mode:'official',deadline:'2026-02-10',amount:1}).deadline,'2026-02-10');
assert.equal(calc({mode:'official',deadline:'2026-01-01'}).daysUntil,0);
assert.equal(calc({mode:'official',deadline:'2026-01-01',today:'2026-01-02'}).daysUntil,-1);
assert.equal(calc({mode:'official',deadline:'2026-01-01',departure:'2026-01-02'}).departureMargin,-1);
assert.equal(calc({mode:'official',deadline:'2026-01-01',departure:'2026-01-01'}).departureMargin,0);
assert.equal(calc({mode:'official',deadline:'2026-01-02',departure:'2026-01-01'}).departureMargin,1);
assert.equal(calc({today:'2025-12-31'}).daysUsed,0);assert.equal(calc({today:'2025-12-31'}).started,false);
assert.equal(calc({mode:'official',deadline:'2025-12-31'}).error,'order');
assert.equal(calc({mode:'official',deadline:'2026-02-30'}).error,'deadline');
assert.equal(calc({arrival:'2026-02-29'}).error,'arrival');
assert.equal(calc({departure:'2025-12-31'}).error,'departure');
for(const amount of ['','0','-1','1.5','NaN','Infinity','3661'])assert.equal(calc({amount}).error,'amount');
assert.equal(calc({mode:'months',amount:121}).error,'amount');assert.equal(calc({mode:'years',amount:11}).error,'amount');
assert.equal(calc({mode:'months',amount:1,endConvention:'invalid'}).error,'convention');
assert.equal(calc({arrival:'2100-12-31',amount:2}).error,'range');
assert.equal(D.parse('2026-1-01'),null);assert.equal(D.parse('2026-04-31'),null);
'''
        for timezone in ('UTC', 'America/New_York', 'Pacific/Auckland'):
            import os
            result = subprocess.run([node, '-e', checks, str(ROOT/'assets/js/rules/visa-deadline.js')],
                                    env={**os.environ, 'TZ': timezone}, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, timezone+'\n'+result.stderr)
