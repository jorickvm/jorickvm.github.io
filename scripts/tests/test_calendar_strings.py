import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import calendar_strings
import check_untranslated


def block(data):
    return '<script type="application/json" data-cal-strings>' + json.dumps(data, ensure_ascii=False) + '</script>'


class CalendarStringsTests(unittest.TestCase):
    def test_messages_participate_in_english_leak_check(self):
        self.assertIn('Mark your trips outside the UK.', check_untranslated.visible_runs(block({'empty': 'Mark your trips outside the UK.'})))

    def test_missing_message_and_changed_placeholder_rejected(self):
        source = block({'hint': 'Tap {date} again.'})
        for target in [block({}), block({'hint': 'Tik {day} nogmaals.'})]:
            with self.assertRaises(ValueError):
                calendar_strings.check(source, target, 'nl')

    def test_russian_requires_all_plural_forms(self):
        source = block({'away': {'one': '{n} day away', 'other': '{n} days away'}})
        with self.assertRaises(ValueError):
            calendar_strings.check(source, block({'away': {'one': '{n} день', 'other': '{n} дней'}}), 'ru')
        calendar_strings.check(source, block({'away': {'one': '{n} день', 'few': '{n} дня', 'many': '{n} дней', 'other': '{n} дня'}}), 'ru')

    def test_target_can_add_plurals_but_must_cover_its_language(self):
        source = block({'left': '{n} left'})
        with self.assertRaises(ValueError):
            calendar_strings.check(source, block({'left': {'one': 'Остался {n} день', 'other': 'Осталось {n} дней'}}), 'ru')

    def test_japanese_single_plural_form_and_numbers(self):
        source = block({'away': {'one': '{n} of 180 days', 'other': '{n} of 180 days'}})
        calendar_strings.check(source, block({'away': {'other': '180日中{n}日'}}), 'ja')
        with self.assertRaises(ValueError):
            calendar_strings.check(source, block({'away': {'other': '183日中{n}日'}}), 'ja')
