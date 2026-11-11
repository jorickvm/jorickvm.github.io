import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_site

ROOT = Path(__file__).resolve().parents[2]


class AppImportRoutingTests(unittest.TestCase):
    def test_import_uses_published_locale_routes_and_preserves_the_payload(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is required to execute the import controller")
        locales = build_site.load_locales()
        markup = build_site.render_locale_routing(
            "app/import/index.html", locales, build_site.load_translations(locales),
            "en", build_site.load_ui_strings(), "../../",
        )
        head = markup.split("<script>", 1)[1].split("</script>", 1)[0]
        harness = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const payload = 'v=2&c=schengen&b=2026-03-01&s=FR:0:9&p=schengen-90-180';
async function run(options) {
  const trace = [], saved = new Map();
  if (options.resume) saved.set('atlasdays-import', payload);
  const context = {
    URLSearchParams, Intl,
    navigator: {languages: options.languages || [], language: options.language || 'en-US'},
    document: {documentElement: {lang: options.pageLanguage || 'en'}, readyState: 'loading',
      currentScript: {getAttribute() { return ''; }}, addEventListener() {}},
    location: {pathname: '/app/import/', search: options.search || '?notrack',
      hash: options.resume ? '' : '#' + payload,
      replace(url) { trace.push(['redirect', url]); }},
    sessionStorage: {
      setItem(key, value) { if (options.blockStorage) throw Error('blocked'); saved.set(key, value); trace.push(['saved', key]); },
      getItem(key) { if (options.blockStorage) throw Error('blocked'); return saved.get(key); }
    },
    history: {replaceState(state, title, url) { context.location.hash = ''; trace.push(['stripped', url]); }},
    fetch(path) { trace.push(['fetch', path]); return Promise.resolve({ok: false}); }
  };
  context.window = context;
  vm.createContext(context);
  vm.runInContext(input.head, context);
  if (options.noMap) delete context.AtlasDaysPageLocales;
  if (options.noMatcher) delete context.AtlasDaysMatchLocale;
  vm.runInContext(input.source, context);
  await new Promise(setImmediate);
  assert.equal(trace.filter(x => x[0] === 'fetch').length, 0, 'do not probe guessed language URLs');
  return {trace, saved, redirects: trace.filter(x => x[0] === 'redirect').map(x => x[1])};
}
(async function () {
  for (const [tag, expected] of [['zh-CN','zh-Hans'], ['zh-SG','zh-Hans'], ['zh-TW','zh-Hant'],
      ['zh-HK','zh-Hant'], ['zh-Hant-HK','zh-Hant'], ['zh','zh-Hans'], ['pt-BR','pt'], ['fr-CA','fr']]) {
    const r = await run({languages: [tag]});
    assert.deepEqual(r.redirects, ['/' + expected + '/app/import/?notrack'], tag);
    assert.equal(r.saved.get('atlasdays-import'), payload);
    assert(r.trace.findIndex(x => x[0] === 'saved') < r.trace.findIndex(x => x[0] === 'stripped'));
    assert(r.trace.findIndex(x => x[0] === 'stripped') < r.trace.findIndex(x => x[0] === 'redirect'));
    assert(!r.redirects[0].includes(payload), 'the retained stays do not move into the query or redirect URL');
  }
  assert.deepEqual((await run({languages:['en-GB','fr-FR']})).redirects, []);
  assert.deepEqual((await run({languages:['xx','zh-TW']})).redirects, ['/zh-Hant/app/import/?notrack']);
  assert.deepEqual((await run({languages:[], language:'pt-BR'})).redirects, ['/pt/app/import/?notrack']);
  assert.deepEqual((await run({languages:['fr'], search:'?lang=en&notrack'})).redirects, []);
  assert.deepEqual((await run({languages:['en'], search:'?lang=fr&notrack'})).redirects,
    ['/fr/app/import/?lang=fr&notrack#' + payload], 'explicit language routing keeps its original fragment');
  assert.deepEqual((await run({languages:['fr'], pageLanguage:'ja'})).redirects, []);
  assert.deepEqual((await run({languages:['xx']})).redirects, []);
  assert.deepEqual((await run({languages:['fr'], noMap:true})).redirects, []);
  assert.deepEqual((await run({languages:['fr'], noMatcher:true})).redirects, []);
  assert.deepEqual((await run({languages:['fr'], blockStorage:true})).redirects, [], 'do not lose an import when storage is unavailable');
  const resumed = await run({languages:['fr'], resume:true});
  assert.deepEqual(resumed.redirects, ['/fr/app/import/?notrack']);
  assert.equal(resumed.saved.get('atlasdays-import'), payload);
  console.log('Import language preferences, script tags, explicit choices and retained payloads passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
"""
        result = subprocess.run(
            [node, "-e", harness], input=json.dumps({
                "head": head, "source": (ROOT / "assets/js/app-import.js").read_text(),
            }), text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_import_script_changes_get_a_new_cache_key(self):
        markup = '<script src="../../assets/js/app-import.js?v=old"></script>'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "assets/js/app-import.js"
            script.parent.mkdir(parents=True)
            with patch.object(build_site, "SITE_ROOT", root):
                script.write_text("first")
                first = build_site.version_import_script(markup)
                self.assertNotEqual(first, markup)
                script.write_text("second")
                second = build_site.version_import_script(markup)
                self.assertNotEqual(first, second)
                self.assertEqual(second.count("app-import.js?v="), 1)
                self.assertEqual(build_site.version_import_script("<p>Example</p>"), "<p>Example</p>")


if __name__ == "__main__":
    unittest.main()
