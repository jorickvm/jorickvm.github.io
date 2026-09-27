import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_site


class GeneratedRedirectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'data').mkdir()
        (self.root / 'data/redirects.json').write_text(json.dumps({'learn/old.html': 'learn/new.html'}))
        self.locales = {
            'en': {'html_lang': 'en', 'route_prefix': '', 'title_separator': ' – ', 'status': 'published'},
            'fr': {'html_lang': 'fr', 'route_prefix': '/fr', 'title_separator': ' – ', 'label_colon': '\u00a0:', 'status': 'published'},
        }
        self.sources = {'learn/new.html': {'title': 'New & improved – AtlasDays', 'meta': [{'name': 'description', 'content': 'A "quoted" description'}]}}
        self.overlays = {'fr': {'learn/new.html': {'headline': 'Nouveau titre', 'description': 'Description française'}}}
        self.strings = {'help.continue': {'en': 'Continue with', 'fr': 'Continuer avec'}}

    def outputs(self):
        with patch.object(build_site, 'SOURCE_ROOT', self.root), patch.object(build_site, 'SITE_ROOT', self.root), patch.object(build_site, 'default_locale_code', return_value='en'):
            return dict(build_site.redirect_outputs(self.locales, self.overlays, self.sources, self.strings))

    def test_english_metadata_shape_and_localized_canonical(self):
        outputs = self.outputs()
        english = outputs[self.root / 'learn/old.html']
        french = outputs[self.root / 'fr/learn/old.html']
        self.assertIn('New &amp; improved', english)
        self.assertIn('A &quot;quoted&quot; description', english)
        self.assertIn('https://atlasdays.app/fr/learn/new', french)
        self.assertIn('0;url=/fr/learn/new', french)
        self.assertIn('noindex,follow', french)
        self.assertIn('Continuer avec\u00a0:', french)

    def test_published_translation_cannot_silently_fall_back_to_english(self):
        self.overlays = {}
        with self.assertRaisesRegex(ValueError, 'fr: redirect target has no translation'):
            self.outputs()

    def test_new_draft_can_build_before_its_learn_translations_exist(self):
        self.locales['fr']['status'] = 'draft'
        self.overlays = {}
        self.assertEqual(set(self.outputs()), {self.root / 'learn/old.html'})
