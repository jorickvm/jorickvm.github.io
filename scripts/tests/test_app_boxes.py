import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_site

CONTENT = build_site.SOURCE_ROOT / 'content'
BOX = re.compile(r'<div class="cta-box[^"]*"[^>]*>')


def app_boxes(text):
    """Each closing app box in a fragment: a cta-box that links the App Store."""
    for match in BOX.finditer(text):
        depth = 0
        for tag in re.finditer(r'<(/?)div\b', text[match.start():]):
            depth += -1 if tag.group(1) else 1
            if depth == 0:
                box = text[match.start():match.start() + tag.end()]
                if build_site.APP_STORE_URL in box:
                    yield box
                break


class AppBoxTests(unittest.TestCase):
    def test_every_app_box_has_the_icon_and_the_apple_button(self):
        for path in sorted(CONTENT.rglob('*.html')):
            text = path.read_text(encoding='utf-8')
            for box in app_boxes(text):
                with self.subTest(path=str(path.relative_to(CONTENT))):
                    self.assertIn('class="cta-logo"', box)
                    button = re.search(r'<a class="cta-btn"[^>]*>\s*(<svg)?', box)
                    self.assertIsNotNone(button, 'the box needs a cta-btn')
                    self.assertIsNotNone(button.group(1), 'the button starts with the Apple logo')
                    self.assertNotIn('cta-micro', box)


if __name__ == '__main__':
    unittest.main()
