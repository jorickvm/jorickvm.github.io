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

function setup({wide = false, reduced = false} = {}) {
  let callback;
  const frames = new Map();
  let frameID = 0;
  const tracker = element();
  const dashboard = element({offsetWidth: 330});
  const phones = element({querySelector: s => s === '.hx-phone-back' ? tracker : dashboard});
  const panel = element({offsetHeight: 793});
  const motion = {matches: reduced, addEventListener(type, fn) { this.change = fn; }};
  const desktop = {matches: wide};
  const events = {};
  const scrollHandlers = [];
  const window = {
    scrollY: 0, innerHeight: 900,
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
    IntersectionObserver: class {
      constructor(fn) { callback = fn; }
      observe() {}
      disconnect() {}
    }
  });
  return {
    phones, tracker, stage, motion, events,
    intersect(ratio) { callback([{isIntersecting: ratio > 0, intersectionRatio: ratio}]); },
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
mobile.intersect(0.8);
assert.equal(mobile.pending(), 0, 'visibility on initial load must not start the swap');
mobile.events.pageshow(); mobile.intersect(0.8);
mobile.events.resize(); mobile.intersect(0.8);
assert.equal(mobile.pending(), 0, 'restoring or resizing at the top must not start it');
mobile.scroll(8);
assert.equal(mobile.pending(), 0, 'ignore tiny scroll offsets');
mobile.scroll(40);
assert.equal(mobile.pending(), 1, 'scrolling with the phones visible starts one animation');
mobile.tick(0); mobile.tick(1400);
assert(mobile.phones.classList.contains('is-tracker-front'));
mobile.scroll(100); mobile.events.resize();
assert.equal(mobile.pending(), 0, 'the mobile swap must not repeat');
""")

    def test_mobile_scroll_still_waits_for_visibility(self):
        self.run_controller(r"""
const mobile = setup();
mobile.intersect(0.2); mobile.scroll(80);
assert.equal(mobile.pending(), 0);
mobile.intersect(0.6);
assert.equal(mobile.pending(), 1);
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
assert.equal(reduced.pending(), 0);
assert.equal(reduced.tracker.style.transform, undefined);
const mobile = setup();
mobile.intersect(0.8); mobile.scroll(40);
mobile.motion.matches = true; mobile.motion.change();
assert.equal(mobile.pending(), 0, 'turning on reduced motion cancels the swap');
assert.equal(mobile.tracker.style.transform, undefined);
""")
