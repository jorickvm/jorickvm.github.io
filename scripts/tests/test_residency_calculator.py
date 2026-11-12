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


    def test_majority_periods_year_switches_overrides_and_app_offers(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is required to execute the calculator")
        harness = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const window = {};
vm.runInNewContext(JSON.parse(require('node:fs').readFileSync(0, 'utf8')), {window, Set});
const rule = window.AtlasDaysRules.days183;
const D = {
  fromParts: (y,m,d) => Date.UTC(y,m-1,d)/86400000,
  iso: d => new Date(d*86400000).toISOString().slice(0,10),
  parts: d => ({y:new Date(d*86400000).getUTCFullYear()}),
  shiftYears: (d,n) => {const p=new Date(d*86400000);return Date.UTC(p.getUTCFullYear()+n,p.getUTCMonth(),p.getUTCDate())/86400000;}
};
function context(settings={}) {
  return {D,today:D.fromParts(2026,11,12),settings,trips:[],allowed:['AU','IT','BG'],
    offers:{AU:'residence-australia',IT:'residence-italy',BG:'residence-bulgaria'},
    text:(k,a)=>a?`${k}:${a.n}`:k,tone:()=>'',dateRange:()=>''};
}
function linked(q) {return context(rule.fromQuery(new URLSearchParams(q),context()).settings);}
function result(c,days) {
  const b=rule.range(c);c.trips=days?[{country:c.settings.country,start:b.from,end:b.from+days-1}]:[];
  return rule.evaluate(c.trips,c);
}
for (const example of [
  {q:'country=IT&period=calendar&resident=183&majority=1',year:'2024',start:null,id:'residence-italy',offerYear:2024},
  {q:'country=AU&period=tax&start=07-01&resident=183&majority=1',year:null,start:'2023-07-01',id:'residence-australia',offerYear:2023}
]) {
  const c=linked(example.q);
  if(example.year)c.settings.year=example.year;
  if(example.start)c.settings.taxStart=example.start;
  assert.equal(rule.range(c).to-rule.range(c).from+1,366);
  c.settings.goal='reach';
  let r=result(c,183);
  assert.equal(r.meter.limit,184,'leap-period resident trigger');
  assert.equal(r.statusText,'needed:1','183 does not meet a 366-day majority');
  assert.equal(r.controls.find(x=>x.key==='limitInput').value,184,'show the active period number');
  assert.equal(rule.trackerOffer(c.trips,c),`${example.id},goal:reach,days:184,year:${example.offerYear}`);
  assert.equal(result(c,184).statusText,'reachedTarget');
  c.settings.goal='stay';r=result(c,183);
  assert.equal(r.meter.limit,183,'last safe count in the leap period');
  assert.equal(r.statusText,'atLimit');
  assert.equal(result(c,184).statusText,'overBy:1');
  assert.equal(rule.trackerOffer(c.trips,c),`${example.id},goal:stay,days:184,year:${example.offerYear}`,
    'preset days uses the first-resident trigger for both goals');
  if(example.year)c.settings.year='2025';else c.settings.taxStart='2024-07-01';
  c.settings.goal='reach';r=result(c,183);
  assert.equal(r.meter.limit,183,'recompute when the chosen year changes');
  assert.equal(r.statusText,'reachedTarget');
  assert.equal(r.controls.find(x=>x.key==='limitInput').value,183);
  c.settings.goal='stay';assert.equal(result(c,182).meter.limit,182);
  c.settings.limitInput=200;c.settings.goal='reach';
  assert.equal(result(c,183).meter.limit,200,'an explicit number remains a custom target');
  assert.ok(rule.trackerOffer(c.trips,c).startsWith('custom,'),'do not label a custom number as the country rule');
}
// Existing country-rule bookmarks gain the same year-aware behavior.
let c=linked('country=IT&period=calendar&resident=183');c.settings.year='2024';c.settings.goal='reach';
assert.equal(result(c,183).meter.limit,184);
c=linked('country=AU&period=tax&start=07-01&resident=183');c.settings.taxStart='2023-07-01';c.settings.goal='reach';
assert.equal(result(c,183).meter.limit,184);
// Generic counters, explicit fixed counts and changed country/windows retain their own scope.
c=context({country:'IT',periodType:'calendar',year:'2024',goal:'reach'});
assert.equal(result(c,183).meter.limit,183,'a generic country choice is not a linked legal preset');
c=linked('country=IT&period=calendar&resident=183&majority=0');c.settings.year='2024';c.settings.goal='reach';
assert.equal(result(c,183).meter.limit,183);
assert.ok(rule.trackerOffer(c.trips,c).startsWith('custom,'));
c=linked('country=AU&period=tax&start=07-01&resident=183&majority=1');c.settings.periodType='calendar';c.settings.year='2024';
assert.ok(rule.trackerOffer([],c).startsWith('custom,'),'a changed window is not the annual preset');
c=linked('country=IT&period=calendar&resident=183&majority=1');c.settings.country='BG';c.settings.year='2024';c.settings.goal='reach';
assert.equal(result(c,183).meter.limit,183,'majority stays bound to its source country');
c=linked('country=BG&period=rolling&resident=184');
assert.equal(result(c,183).meter.limit,183,'ordinary greater-than-183 safe count is unchanged');
console.log('Year-majority boundaries, year changes, controls, manual overrides and supported app offers passed.');
"""
        result = subprocess.run(
            [node, "-e", harness], text=True, capture_output=True, timeout=30,
            input=json.dumps((ROOT / "assets/js/rules/days-183.js").read_text()),
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_country_links_declare_majority_and_embeds_bind_it_to_the_country(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import build_site
        records = {r["path"]: r for r in json.loads((ROOT / "_site-src/data/articles.json").read_text())["articles"]}
        for slug, period in [("australia", "period=tax&start=07-01"), ("italy", "period=calendar")]:
            record = records[f"learn/{slug}-183-day-tax-residency.html"]
            query = build_site.calculator_link_query(record)
            self.assertIn(period, query)
            self.assertIn("&majority=1", query)
        italy = records["learn/italy-183-day-tax-residency.html"]
        embedded = {**italy, "calculator": {"settings": {}}}
        self.assertEqual(build_site.calculator_preset(embedded)["settings"]["majorityOfYear"], "IT")
        self.assertNotIn("majority=", build_site.calculator_link_query(records["learn/canada-183-day-tax-residency.html"]))


if __name__ == "__main__":
    unittest.main()
