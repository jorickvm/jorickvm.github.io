import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_site

HELP = {"section": "help"}
STRINGS = {"help.screenshots_english": {"en": "English note", "nl": "Dutch note"}}
ENGLISH_SHOT = '    <figure class="help-shot help-shot-screen"><img src="/assets/article-images/help/a/one.webp" alt="" /></figure>'
DUTCH_SHOT = '    <figure class="help-shot help-shot-screen"><img src="/assets/article-images/nl/help/a/two.webp" alt="" /></figure>'
NOTE = '    <p class="help-shot-note">Dutch note</p>'


def render(content, article=HELP, code="nl", strings=STRINGS):
    return build_site.render_english_screenshot_note(content, article, code, strings)


class HelpScreenshotNoteTests(unittest.TestCase):
    def test_note_sits_once_above_the_first_english_capture(self):
        content = "\n".join(["    <p>Intro</p>", DUTCH_SHOT, ENGLISH_SHOT, ENGLISH_SHOT])
        self.assertEqual(
            render(content),
            "\n".join(["    <p>Intro</p>", DUTCH_SHOT, NOTE, ENGLISH_SHOT, ENGLISH_SHOT]),
        )

    def test_page_with_only_its_own_captures_has_no_note(self):
        content = "\n".join(["    <p>Intro</p>", DUTCH_SHOT])
        self.assertEqual(render(content), content)

    def test_english_page_has_no_note(self):
        self.assertEqual(render(ENGLISH_SHOT, code="en"), ENGLISH_SHOT)

    def test_other_sections_have_no_note(self):
        self.assertEqual(render(ENGLISH_SHOT, article={"section": "learn"}), ENGLISH_SHOT)

    def test_language_without_the_string_has_no_note(self):
        self.assertEqual(render(ENGLISH_SHOT, code="de"), ENGLISH_SHOT)


if __name__ == "__main__":
    unittest.main()
