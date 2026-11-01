"""Execute the shipping hero controller with browser events under Node."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

HARNESS = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(process.argv[1], 'utf8');
const start = source.indexOf('  (function heroMotion() {');
const end = source.indexOf('  })();', start) + '  })();'.length;
assert(start >= 0 && end > start, 'shipping hero controller exists');
const hero = source.slice(start, end);

function element(props = {}) {
  const classes = new Set();
  return Object.assign({
    classList: {
      toggle(name, on) { on ? classes.add(name) : classes.delete(name); },
      remove(name) { classes.delete(name); },
      contains(name) { return classes.has(name); }
    },
    style: {
      setProperty(name, value) { this[name] = value; },
      removeProperty(name) { delete this[name]; }
    }
  }, props);
}

function setup({wide = false, reduced = false, height = 900, phoneTop = 530, phoneHeight = 550} = {}) {
  const frames = new Map();
  let frameID = 0;
  const tracker = element();
  const dashboard = element({offsetWidth: 330});
  const phones = element({querySelector: s => s === '.hx-phone-back' ? tracker : dashboard, getBoundingClientRect: () => ({top: phoneTop - window.scrollY, height: phoneHeight})});
  const panel = element({offsetHeight: 793});
  const motion = {matches: reduced, addEventListener(type, fn) { this.change = fn; }};
  const desktop = {matches: wide};
  const events = {};
  const scrollHandlers = [];
  const window = {
    scrollY: 0, innerHeight: height,
    matchMedia: s => s.includes('reduced') ? motion : desktop,
    addEventListener(type, fn) { events[type] = fn; }
  };
  const stage = element({querySelector: () => panel, getBoundingClientRect: () => ({top: 73 - window.scrollY})});
  vm.runInNewContext(hero, {
    page: {querySelector: s => s === '[data-hx-hero-stage]' ? stage : phones},
    document: {querySelector: () => ({offsetHeight: 73})},
    window, hasObserver: true, scrollHandlers,
    getComputedStyle: () => ({paddingBottom: '48px'}),
    requestAnimationFrame: fn => { frames.set(++frameID, fn); return frameID; },
    cancelAnimationFrame: id => frames.delete(id),
  });
  return {
    phones, tracker, stage, motion, events,
    scroll(y) { window.scrollY = y; scrollHandlers.forEach(fn => fn()); },
    tick(now) { const current = [...frames.values()]; frames.clear(); current.forEach(fn => fn(now)); },
    pending() { return frames.size; }
  };
}
"""


class HeroMotionTests(unittest.TestCase):
    def run_controller(self, assertions):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is required to execute the hero controller")
        result = subprocess.run(
            [node, "-e", HARNESS + assertions, str(ROOT / "assets/js/marketing.js")],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_mobile_visible_on_load_waits_for_scroll(self):
        self.run_controller(r"""
const mobile = setup();
const initial = mobile.tracker.style.transform;
mobile.tick(0); mobile.tick(5000);
assert.equal(mobile.tracker.style.transform, initial, 'time must not start the swap');
mobile.events.pageshow(); mobile.events.resize();
mobile.scroll(8); mobile.scroll(24);
assert.equal(mobile.tracker.style.transform, initial, 'keep the initial pose before scrolling');
mobile.scroll(100);
assert.notEqual(mobile.tracker.style.transform, initial, 'scrolling starts the handoff');
assert.equal(mobile.pending(), 0, 'no independent timer should keep moving the phones');
""")

    def test_mobile_retraces_the_same_poses_when_scrolling_up(self):
        self.run_controller(r"""
const mobile = setup();
const initial = mobile.tracker.style.transform;
mobile.scroll(80); const early = mobile.tracker.style.transform;
mobile.scroll(160); const late = mobile.tracker.style.transform;
mobile.scroll(400);
assert(mobile.phones.classList.contains('is-tracker-front'));
mobile.scroll(160); assert.equal(mobile.tracker.style.transform, late);
mobile.scroll(80); assert.equal(mobile.tracker.style.transform, early);
mobile.scroll(0); assert.equal(mobile.tracker.style.transform, initial);
assert(!mobile.phones.classList.contains('is-tracker-front'));
mobile.scroll(400); mobile.events.resize(); mobile.scroll(0);
assert.equal(mobile.tracker.style.transform, initial, 'repeat visits and resize must remain reversible');
""")

    def test_mobile_waits_until_the_phones_enter_view(self):
        self.run_controller(r"""
const mobile = setup({phoneTop: 900, phoneHeight: 500, height: 800});
const initial = mobile.tracker.style.transform;
mobile.scroll(200); mobile.scroll(375);
assert.equal(mobile.tracker.style.transform, initial);
mobile.scroll(420);
assert.notEqual(mobile.tracker.style.transform, initial);
mobile.scroll(600);
assert(mobile.phones.classList.contains('is-tracker-front'));
mobile.scroll(375); assert.equal(mobile.tracker.style.transform, initial);
""")

    def test_desktop_scrubbing_and_reduced_motion_are_preserved(self):
        self.run_controller(r"""
const desktop = setup({wide: true});
assert(desktop.stage.classList.contains('is-pinned'));
desktop.scroll(280);
assert(desktop.phones.classList.contains('is-tracker-front'));
desktop.scroll(0);
assert(!desktop.phones.classList.contains('is-tracker-front'));
const reduced = setup({reduced: true});
reduced.scroll(280);
assert.equal(reduced.tracker.style.transform, undefined);
const mobile = setup();
mobile.scroll(200);
mobile.motion.matches = true; mobile.motion.change();
assert.equal(mobile.tracker.style.transform, undefined);
assert.equal(mobile.pending(), 0);
""")
