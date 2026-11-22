import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class StateCalculatorTests(unittest.TestCase):
    def test_state_counts_queries_and_app_handoff(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is required to execute the calculator")
        harness = r"""
const assert=require('node:assert/strict'),vm=require('node:vm');
const input=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
const window={};vm.runInNewContext(input.rule,{window,Set});
const rule=window.AtlasDaysRules.days183;
const D={fromParts:(y,m,d)=>Date.UTC(y,m-1,d)/86400000,
  iso:n=>new Date(n*86400000).toISOString().slice(0,10),
  parts:n=>({y:new Date(n*86400000).getUTCFullYear()})};
const day=(m,d)=>D.fromParts(2026,m,d);
const allowed=rule.countries(['US','GE','CA','PR'],{});
assert.equal(allowed.filter(c=>c.startsWith('US-')).length,51);
assert.ok(allowed.includes('US-DC'));
assert.ok(!rule.countries(['US','GE'],{country:'GE'}).some(c=>c.startsWith('US-')),
  'country-specific embeds keep their country-only picker');
const catalogue={rule,allowed:rule.countries(input.countries,{}),catalogue:null,recent:[],locale:'en',ALIASES:{},
  englishNames:new Intl.DisplayNames(['en'],{type:'region'}),
  placeName:code=>new Intl.DisplayNames(['en'],{type:'region'}).of(code),text:key=>input.labels[key]||''};
vm.createContext(catalogue);
vm.runInContext(input.engine.match(/function nameForPlace\(code\) \{[^\n]+\}/)[0],catalogue);
vm.runInContext(input.engine.match(/function fold\(s\) \{[^\n]+\}/)[0],catalogue);
const pickerFrom=input.engine.indexOf('function places()'),pickerTo=input.engine.indexOf('function flagImg(',pickerFrom);
vm.runInContext(input.engine.slice(pickerFrom,pickerTo),catalogue);
assert.equal(catalogue.matches('').length,input.countries.length+51);
assert.deepEqual(Array.from(catalogue.matches('NY').slice(0,2),p=>p.code),['US','US-NY']);
assert.equal(catalogue.matches('NY')[0].contextOnly,true);
assert.deepEqual(Array.from(catalogue.matches('District of Columbia'),p=>p.code),['US','US-DC']);
function assertGrouped(rows) {
  const parent=rows.findIndex(p=>p.code==='US');
  const states=rows.filter(p=>p.code.startsWith('US-'));
  assert.equal(states.length,51);
  assert.deepEqual(Array.from(rows.slice(parent+1,parent+52),p=>p.code),Array.from(states,p=>p.code));
  assert.equal(new Set(rows.map(p=>p.code)).size,rows.length);
  assert.deepEqual(Array.from(states,p=>p.name),Array.from(states,p=>p.name).sort((a,b)=>a.localeCompare(b,'en')));
}
assertGrouped(catalogue.matches(''));
assertGrouped(catalogue.matches('United States'));
assert.equal(catalogue.matches('CA')[0].code,'CA','Canada retains exact-code priority');
catalogue.recent=['US-NY','CA'];assertGrouped(catalogue.matches(''));
assert.equal(catalogue.matches('')[0].code,'US','a recent state promotes its country group');
assert.equal(catalogue.places().find(p=>p.code==='US-GA').name,'Georgia (US)');
const trips=[{country:'US-NY',start:day(1,1),end:day(1,10)},
  {country:'US-CA',start:day(1,10),end:day(1,20)},
  {country:'US',start:day(1,20),end:day(1,25)},
  {country:'GE',start:day(1,1),end:day(1,5)},
  {country:'US-GA',start:day(1,1),end:day(1,7)},
  {country:'PR',start:day(2,1),end:day(2,10)}];
function context(country,settings={}) {return {D,today:day(11,13),allowed,trips,
  settings:{year:'2026',country,...settings},offers:{},text:(k,a)=>a?String(a.n):k,tone:()=>'',dateRange:()=>''};}
for(const [country,days] of [['US-NY',10],['US-CA',11],['US',25],['GE',5],['US-GA',7],['PR',10]]) {
  const c=context(country);assert.equal(rule.evaluate(trips,c).meter.days,days,country);
}
let c=context('US-NY');
assert.equal(rule.trackerOffer(trips,c),'custom,place:US-NY,days:183,unit:days,window:year,year:2026,goal:stay');
assert.equal(rule.newTripCountry(c),'US-NY');
assert.equal(rule.fromQuery(new URLSearchParams('country=US-XX'),c),null);
const linked=rule.fromQuery(new URLSearchParams('country=US-NY&period=calendar&resident=184'),c);
assert.equal(linked.settings.country,'US-NY');assert.equal(linked.link,'183-us-ny');
c=context('US-NY',linked.settings);assert.equal(rule.evaluate(trips,c).meter.limit,183);
c.settings.goal='reach';assert.equal(rule.evaluate(trips,c).meter.limit,184);
const rows=JSON.parse(JSON.stringify(rule.exportRows(trips,c)));
assert.deepEqual(rows.map(({country,start,end})=>({country,start,end})),trips);
const from=input.engine.indexOf('function importFragment('),to=input.engine.indexOf('function loadQr(',from);
const encoder={D};vm.createContext(encoder);vm.runInContext(input.engine.slice(from,to),encoder);
const offer=rule.trackerOffer(trips,context('US-NY'));
const fragment=encoder.importFragment(rows,'183',offer),fields=Object.fromEntries(fragment.split('&').map(p=>{const i=p.indexOf('=');return [p.slice(0,i),p.slice(i+1)];}));
assert.equal(fields.v,'2');assert.ok(fields.s.includes('US-NY:0:9'));assert.equal(fields.p,offer);
assert.ok(encoder.importFragment(rows.filter(r=>!r.country.startsWith('US-')),'183',offer).startsWith('v=1&'),
  'country-only payloads remain compatible');
assert.ok(encoder.importFragment([],'183',offer).startsWith('v=2&'),'tracker-only links remain version 2');
const begin=input.landing.indexOf('function rows(q)'),end=input.landing.indexOf('function preset(q)',begin);
const decoder={frag:fragment};vm.createContext(decoder);vm.runInContext(input.landing.slice(begin,end),decoder);
const decoded=JSON.parse(JSON.stringify(decoder.rows(fields)));
assert.deepEqual(decoded.map(r=>r[0]),trips.map(r=>r.country));
assert.equal(decoded[0][1],'2026-01-01');assert.equal(decoded[0][2],'2026-01-10');
"""
        result = subprocess.run([node, "-e", harness], input=json.dumps({
            "rule": (ROOT / "assets/js/rules/days-183.js").read_text(),
            "engine": (ROOT / "assets/js/day-calendar.js").read_text(),
            "landing": (ROOT / "assets/js/app-import.js").read_text(),
            "labels": json.loads(re.search(r"data-cal-strings>(.*?)</script>",
                                           (ROOT / "_site-src/content/learn/183-day-rule-calculator.html").read_text(), re.S)[1]),
            "countries": re.search(r'var PLACES = "([^"]+)"\.split',
                                   (ROOT / "assets/js/day-calendar.js").read_text())[1].split(),
        }), text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_all_state_labels_have_flag_assets(self):
        markup = (ROOT / "_site-src/content/learn/183-day-rule-calculator.html").read_text()
        labels = json.loads(re.search(r"data-cal-strings>(.*?)</script>", markup, re.S)[1])
        states = {key.removeprefix("stateUS") for key in labels if key.startswith("stateUS")}
        self.assertEqual(len(states), 51)
        self.assertIn("DC", states)
        for code in states:
            self.assertTrue((ROOT / "assets/flags" / f"us-{code.lower()}.png").is_file(), code)
