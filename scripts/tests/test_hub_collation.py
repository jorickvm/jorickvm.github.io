"""The per-language collation rules, as cases rather than as prose.

Each test is a place name that a plausible simpler implementation puts in the
wrong position, so a regression names the language it broke.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import hub_collation  # noqa: E402


def order(names, code):
    return sorted(names, key=lambda n: hub_collation.sort_key(n, code))


class LatinTests(unittest.TestCase):
    def test_accented_initial_is_not_sorted_after_z(self):
        """A code-point sort put Émirats last and Géorgie after Grèce."""
        names = ["Grèce", "Géorgie", "Émirats arabes unis", "Espace Schengen"]
        self.assertEqual(
            order(names, "fr"),
            ["Émirats arabes unis", "Espace Schengen", "Géorgie", "Grèce"],
        )

    def test_spanish_ch_is_c_then_h(self):
        """Spanish dropped ch as a separate letter in 1994."""
        self.assertEqual(
            order(["Colombia", "Chipre", "Chequia", "Canadá"], "es"),
            ["Canadá", "Chequia", "Chipre", "Colombia"],
        )


class TurkishTests(unittest.TestCase):
    def test_dotless_i_sorts_before_i_not_after_z(self):
        """ı is its own letter between h and i, not an accented i."""
        self.assertEqual(
            order(["Kolombiya", "Kıbrıs", "Kanada", "Kuzey Dakota"], "tr"),
            ["Kanada", "Kıbrıs", "Kolombiya", "Kuzey Dakota"],
        )
        self.assertEqual(
            order(["Singapur", "Sırbistan", "Slovakya"], "tr"),
            ["Sırbistan", "Singapur", "Slovakya"],
        )

    def test_c_cedilla_follows_the_whole_c_block(self):
        self.assertEqual(
            order(["Çekya", "Colorado", "Connecticut", "Endonezya"], "tr"),
            ["Colorado", "Connecticut", "Çekya", "Endonezya"],
        )

    def test_dotted_capital_i_sorts_as_i(self):
        """casefold turns İ into i plus a combining dot that is not a letter."""
        self.assertEqual(
            order(["İtalya", "Idaho", "İrlanda"], "tr"),
            ["Idaho", "İrlanda", "İtalya"],
        )

    def test_retained_foreign_w_keeps_its_latin_place(self):
        self.assertEqual(
            order(["Yeni Zelanda", "New York", "Vermont"], "tr"),
            ["New York", "Vermont", "Yeni Zelanda"],
        )

    def test_turkish_rules_do_not_leak_into_other_languages(self):
        """Turkish is the only locale where ö is not an accented o."""
        self.assertEqual(
            order(["Österreich", "Polen", "Oregon"], "de"),
            ["Oregon", "Österreich", "Polen"],
        )


class CyrillicTests(unittest.TestCase):
    def test_ukrainian_letters_outside_the_a_ya_run(self):
        """і, ї, є and ґ have code points above я."""
        self.assertEqual(
            order(["Японія", "Італія", "Ірландія", "Єгипет"], "uk"),
            ["Єгипет", "Ірландія", "Італія", "Японія"],
        )

    def test_apostrophe_is_not_a_letter(self):
        """В’єтнам is spelled with an apostrophe; collation ignores it."""
        self.assertEqual(
            order(["Вірджинія", "В’єтнам", "Вермонт"], "uk"),
            ["Вермонт", "В’єтнам", "Вірджинія"],
        )

    def test_russian_soft_sign_keeps_its_place(self):
        self.assertEqual(
            order(["Вьетнам", "Виргиния", "Вермонт"], "ru"),
            ["Вермонт", "Виргиния", "Вьетнам"],
        )

    def test_cyrillic_is_ordered_by_script_in_any_locale(self):
        self.assertEqual(order(["Ялта", "Ірпінь"], "de"), ["Ірпінь", "Ялта"])


class JapaneseTests(unittest.TestCase):
    def test_prolonged_sound_mark_is_the_vowel_it_lengthens(self):
        """ー sits at the end of the katakana block, so it sorted last."""
        self.assertEqual(
            order(["オレゴン州", "オーストラリア", "オハイオ州"], "ja"),
            ["オーストラリア", "オハイオ州", "オレゴン州"],
        )
        self.assertEqual(
            order(["ポルトガル", "ポーランド"], "ja"),
            ["ポーランド", "ポルトガル"],
        )

    def test_voicing_is_not_a_primary_difference(self):
        """シ and ジ are one code point apart, which put ジョージア after シンガポール."""
        self.assertEqual(
            order(["シンガポール", "ジョージア", "シェンゲン圏"], "ja"),
            ["シェンゲン圏", "ジョージア", "シンガポール"],
        )

    def test_kanji_names_sort_by_reading_not_by_block(self):
        """台湾, 日本, 米国 and 英国 were dumped below every katakana name."""
        self.assertEqual(
            order(["日本", "タイ", "台湾", "チェコ", "トルコ"], "ja"),
            ["タイ", "台湾", "チェコ", "トルコ", "日本"],
        )
        self.assertEqual(
            order(["ベトナム", "米国", "ブルガリア"], "ja"),
            ["ブルガリア", "米国", "ベトナム"],
        )

    def test_small_kana_are_their_full_forms(self):
        self.assertEqual(
            order(["ニュージャージー州", "ニュージーランド"], "ja"),
            ["ニュージーランド", "ニュージャージー州"],
        )

    def test_a_name_and_the_same_name_qualified_stay_adjacent(self):
        self.assertEqual(
            order(["ジョージア州", "ジョージア"], "ja"),
            ["ジョージア", "ジョージア州"],
        )

    def test_a_kanji_name_with_no_reading_is_reported_not_guessed(self):
        self.assertEqual(hub_collation.unresolved(["台湾", "日本"], "ja"), [])
        self.assertEqual(hub_collation.unresolved(["神奈川"], "ja"), ["神奈川"])
        # Only Japanese can fail this way; every other branch orders whatever
        # letters it is handed.
        self.assertEqual(hub_collation.unresolved(["神奈川"], "de"), [])


class MixedScriptTests(unittest.TestCase):
    def test_an_untranslated_english_row_still_compares(self):
        """A hub emits English for a row awaiting translation; it must sort."""
        for code in ("de", "tr", "ru", "uk", "ja"):
            with self.subTest(code=code):
                names = ["Vietnam", "Кипр", "オーストラリア", "Çekya"]
                self.assertEqual(len(order(names, code)), len(names))


if __name__ == "__main__":
    unittest.main()
