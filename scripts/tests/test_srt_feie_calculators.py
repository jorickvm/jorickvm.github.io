import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HARNESS = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const input = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const window = {};
for (const source of input.sources) vm.runInNewContext(source, {window, Set});
const day = s => Date.parse(s + 'T00:00:00Z') / 86400000;
const D = {
  fromParts: (y,m,d) => Date.UTC(y,m-1,d)/86400000,
  parts: n => {const d=new Date(n*86400000);return {y:d.getUTCFullYear(),m:d.getUTCMonth(),d:d.getUTCDate()};},
  iso: n => new Date(n*86400000).toISOString().slice(0,10),
  shiftYears: (n,k) => {const p=D.parts(n),y=p.y+k,last=new Date(Date.UTC(y,p.m+1,0)).getUTCDate();return Date.UTC(y,p.m,Math.min(p.d,last))/86400000;}
};
const context = settings => ({D,today:day('2026-11-13'),settings,
  text:(key,args)=>key+(args?':'+args.n:''),tone:()=>'',dateRange:(a,b)=>D.iso(a)+'/'+D.iso(b)});
const trips = rows => rows.map(r=>({...r,start:day(r.start),end:day(r.end)}));
const srt=window.AtlasDaysRules.ukSrt, feie=window.AtlasDaysRules.feie;
"""


class SrtFeieCalculatorTests(unittest.TestCase):
    def run_javascript(self, checks):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is required to execute the calculators")
        payload = {
            "sources": [(ROOT / "assets/js/rules" / name).read_text() for name in ("uk-srt.js", "feie.js")],
            "fixtures": json.loads((ROOT / "scripts/tests/fixtures/srt-feie-counts.json").read_text()),
        }
        result = subprocess.run([node, "-e", HARNESS + checks], input=json.dumps(payload),
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_srt_reference_counts_ties_and_goals(self):
        self.run_javascript(r"""
for (const t of input.fixtures.srt) {
  const c=context({year:String(t.year),prior:t.previous?'yes':'no',family:t.family?'yes':'no',
    accommodation:t.accommodation?'yes':'no',work:t.work?'yes':'no'});
  const r=srt.evaluate(trips(t.trips),c),e=t.expected;
  assert.equal(r.meter.days,e.days,t.id+' days');
  assert.equal(r.meter.limit,e.firstResidentDay-1,t.id+' last safe day');
  assert.equal(r.controls.find(x=>x.key==='ninety').value.startsWith('ninetyYes'),e.ninety,t.id+' 90-day tie');
  if(t.previous)assert.equal(r.controls.find(x=>x.key==='countryTie').value==='yes',e.country,t.id+' country tie');
  c.settings.goal='reach';assert.equal(srt.evaluate(trips(t.trips),c).meter.limit,e.firstResidentDay,t.id+' target');
}
// Both sufficient-ties tables, immediately before and on each first-resident day.
for(const prior of [false,true])for(let ties=0;ties<=4;ties++) {
  const first=(prior?[183,121,91,46,16]:[183,183,121,91,46])[ties];
  for(const n of [first-1,first]) {
    const c=context({year:'2026',prior:prior?'yes':'no',family:ties>0?'yes':'no',
      accommodation:ties>1?'yes':'no',work:ties>2?'yes':'no'});
    const start=day('2026-04-06'),records=[{country:'GB',start,end:start+n},
      {country:'FR',start,end:start+365}];
    if(ties===4)records.push({country:'GB',start:day('2025-04-06'),end:day('2025-07-06')});
    const r=srt.evaluate(records,c);assert.equal(r.meter.limit,first-1);
    assert.equal(r.statusText,n===first?'overBy:1':'atLimit');
  }
}
""")

    def test_feie_reference_windows_exclusions_and_travel_days(self):
        self.run_javascript(r"""
for(const t of input.fixtures.feie) {
  const c=context({checkOn:t.asOf,countView:'qualifying'}),r=feie.evaluate(trips(t.trips),c),b=feie.range(c),e=t.expected;
  assert.equal(r.meter.days,e.days,t.name);assert.equal(r.meter.limit,330);
  assert.equal(D.iso(b.from),e.from,t.name+' first day');assert.equal(D.iso(b.to),e.to,t.name+' last day');
  assert.equal(r.statusText,e.days>=330?'reachedTarget':'needed:'+(330-e.days));
}
""")

    def test_feie_display_modes_allowances_and_boundaries(self):
        self.run_javascript(r"""
for(const asOf of ['2026-11-13','2024-11-13']) {
  const c=context({checkOn:asOf}),b=feie.range(c),allowance=b.to-b.from+1-330;
  c.tone=(days,limit,target)=>target?(days>=limit?'achieved':'normal'):(days>=limit?'critical':'normal');
  assert.equal(allowance,asOf.startsWith('2024')?36:35);
  for(const excluded of [0,12,allowance-1,allowance,allowance+1]) {
    const start=b.from+10;
    const records=excluded?[{country:'US',start,end:start+excluded-3}]:[];
    const original=JSON.stringify(records);
    delete c.settings.countView;
    const budget=feie.evaluate(records,c);
    assert.equal(budget.controls[0].key,'countView');
    assert.equal(budget.controls[0].value,'excluded');
    assert.equal(budget.meter.days,excluded);
    assert.equal(budget.meter.limit,allowance);
    assert.equal(budget.statusText,excluded<allowance?'allowanceLeft:'+(allowance-excluded)
      :excluded===allowance?'allowanceUsed':'allowanceOver:'+(excluded-allowance));
    if(excluded===allowance)assert.equal(budget.meter.tone,'warning','exact allowance still meets the day count');
    if(excluded>allowance)assert.equal(budget.meter.tone,'critical');
    c.settings.countView='qualifying';
    const qualifying=feie.evaluate(records,c);
    assert.equal(qualifying.meter.days,330+allowance-excluded);
    assert.equal(qualifying.meter.limit,330);
    assert.equal(qualifying.statusText,excluded<=allowance?'reachedTarget':'needed:'+(excluded-allowance));
    assert.equal(qualifying.meter.tone,excluded<=allowance?'achieved':'normal');
    assert.equal(budget.meter.days+qualifying.meter.days,b.to-b.from+1);
    assert.equal(JSON.stringify(records),original,'switching views preserves the recorded stays');
    assert.equal(feie.trackerOffer(records,c),'tax-us-feie-physical-presence,goal:reach');
  }
}
for(const t of input.fixtures.feie) {
  const c=context({checkOn:t.asOf}),r=feie.evaluate(trips(t.trips),c),b=feie.range(c);
  assert.equal(r.meter.days,b.to-b.from+1-t.expected.days,t.name+' excluded complement');
  assert.equal(r.meter.limit,b.to-b.from+1-330,t.name+' allowance');
}
""")

    def test_question_state_and_import_preserve_real_records(self):
        self.run_javascript(r"""
const c=context({}),keys=()=>srt.evaluate([],c).controls.map(x=>x.key);
assert.ok(!srt.evaluate([],c).meter,'unanswered questions are not a verdict');
assert.ok(keys().includes('prior')&&!keys().includes('family'));
c.settings.prior='yes';assert.ok(keys().includes('family')&&!keys().includes('accommodation'));
c.settings.family='no';assert.ok(keys().includes('accommodation')&&!keys().includes('work'));
c.settings.accommodation='yes';assert.ok(keys().includes('work'));
c.settings.work='no';assert.ok(srt.evaluate([],c).meter);
c.settings.year='2026';
assert.equal(srt.trackerOffer([],c),'residence-united-kingdom-srt,goal:stay,year:2026,prior:yes,family:no,accommodation:yes,work:no');
assert.equal(srt.trackerOffer([],context({})),'residence-united-kingdom-srt,goal:stay,year:2026');
assert.equal(feie.trackerOffer([],c),'tax-us-feie-physical-presence,goal:reach');
const records=trips([{country:'US',start:'2026-04-01',end:'2026-04-10'},
  {country:'PT',start:'2026-04-10',end:'2026-05-01'},{country:'XW',start:'2026-05-02',end:'2026-05-02'}]);
for(const rule of [srt,feie]) {
  const rows=JSON.parse(JSON.stringify(rule.exportRows(records,c)));
  assert.deepEqual(rows.map(({country,start,end})=>({country,start,end})),records,
    'only original records, including foreign handoffs, are sent to the app');
}
assert.ok(feie.countries(['US']).includes('XW'));
""")
