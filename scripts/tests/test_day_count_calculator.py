import json
import shutil
import subprocess
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

class DayCountCalculatorTests(unittest.TestCase):
    def test_counts_and_personal_goals_do_not_infer_legal_rules(self):
        node = shutil.which('node')
        if not node: self.skipTest('node required')
        source = [(ROOT / 'assets/js/rules' / n).read_text() for n in ['days-183.js','day-count.js']]
        harness = r'''
const assert=require('node:assert/strict'),vm=require('node:vm');
const window={};for(const source of JSON.parse(require('node:fs').readFileSync(0,'utf8')))vm.runInNewContext(source,{window,Set});
const D={fromParts:(y,m,d)=>Date.UTC(y,m-1,d)/86400000,iso:d=>new Date(d*86400000).toISOString().slice(0,10),parts:d=>({y:new Date(d*86400000).getUTCFullYear()}),shiftYears:(d,n)=>{const v=new Date(d*86400000),y=v.getUTCFullYear()+n,m=v.getUTCMonth(),day=v.getUTCDate();return Date.UTC(y,m,Math.min(day,new Date(Date.UTC(y,m+1,0)).getUTCDate()))/86400000;}};
const rule=window.AtlasDaysRules.dayCount,today=D.fromParts(2026,11,19);
function ctx(settings={}){return {D,today,settings,trips:[],allowed:['NL','CY','US','US-NY'],text:(k,a)=>a?`${k}:${a.n}`:k,tone:()=> 'personal',dateRange:()=> 'period',offers:{NL:'fake-law'},offer:'fake-law'};}
const t=(a,b,c='NL')=>({start:D.fromParts(...a),end:D.fromParts(...b),country:c});
let c=ctx({country:'NL',year:'2026'}),trips=[t([2026,6,1],[2026,6,10]),t([2026,6,8],[2026,6,12])];c.trips=trips;
let r=rule.evaluate(trips,c);assert.equal(r.meter.days,12);assert.equal(r.meter.limit,null);assert.equal(r.statusText,'');assert.equal(r.meter.tone,'normal');assert(!r.controls.some(x=>x.key==='limitInput'));assert.equal(rule.trackerOffer(trips,c),'');
c.settings.goal='stay';r=rule.evaluate(trips,c);assert.equal(r.meter.limit,null);assert.equal(r.controls.find(x=>x.key==='limitInput').value,'');
for(const value of ['',0,-1,30.5,367,'not a number']){c.settings.limitInput=value;assert.equal(rule.evaluate(trips,c).meter.limit,null);}
c.settings.limitInput=30;r=rule.evaluate(trips,c);assert.equal(r.meter.limit,30);assert.equal(r.statusText,'remaining:18');assert.equal(rule.trackerOffer(trips,c),'');
c.settings.goal='reach';assert.equal(rule.evaluate(trips,c).statusText,'needed:18');c.settings.limitInput=12;assert.equal(rule.evaluate(trips,c).statusText,'reachedTarget');
c.settings.goal='count';assert.equal(rule.evaluate(trips,c).meter.limit,null);
// No Cyprus, overnight, full-day, majority or linked-resident policy leaks into a personal record.
c=ctx({country:'CY',year:'2026',presence:'cyprus',nights:true,overnight:'CY',residentAt:184,linkedCountry:'CY'});trips=[t([2026,1,1],[2026,1,5],'CY')];c.trips=trips;assert.equal(rule.evaluate(trips,c).meter.days,5);assert.equal(rule.tripLabel(trips[0],c),'tripDays:5');
c=ctx({country:'NL',year:'2024'});assert.equal(rule.evaluate([t([2024,2,28],[2024,3,1])],c).meter.days,3);
c=ctx({country:'NL',year:'2026'});assert.equal(rule.evaluate([t([2025,12,30],[2026,1,2])],c).meter.days,2);
c=ctx({country:'NL',year:'2026',periodType:'tax'});assert.equal(D.iso(rule.range(c).from),'2026-01-01');
c=ctx({country:'NL',periodType:'rolling',checkOn:'2026-03-01'});assert.equal(D.iso(rule.range(c).from),'2025-03-02');
c=ctx({country:'US',year:'2026'});assert.equal(rule.evaluate([t([2026,6,1],[2026,6,5],'US-NY'),t([2026,6,3],[2026,6,6],'US')],c).meter.days,6);
let q=rule.fromQuery(new URLSearchParams('country=CY&resident=184&overnight=1&goal=count'),ctx());assert.equal(q.settings.presence,undefined);assert.equal(q.settings.residentAt,undefined);assert.equal(q.settings.overnight,undefined);
// Shared 183-day behaviour remains intact.
c=ctx({country:'NL',year:'2026'});assert.equal(window.AtlasDaysRules.days183.evaluate([],c).meter.limit,183);
console.log('No-limit, optional goals, exclusions, boundaries, leap days, state overlap, queries and old-rule regression passed');
'''
        for tz in ['UTC','America/New_York','Pacific/Auckland']:
            import os
            r=subprocess.run([node,'-e',harness],input=json.dumps(source),text=True,capture_output=True,env={**os.environ,'TZ':tz},timeout=30)
            self.assertEqual(r.returncode,0,r.stderr)
