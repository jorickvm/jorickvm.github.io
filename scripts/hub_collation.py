#!/usr/bin/env python3
"""Alphabetical order for place names, in the reader's own language.

A hub presented as alphabetical that is not alphabetical in the reader's
language reads as broken, so every hub that lists places sorts on the names it
actually displays. This module is the single answer to "where does this name
belong", shared by the generated residency tables
(scripts/build_residency_hub.py) and the hand-authored library tiles
(scripts/build_hub_tile_order.py) so the two hubs cannot disagree.

Collation is per language, not per script, because the same Latin letters are
ordered differently by different languages. `sort_key(name, code)` takes the
locale code for that reason. Every branch returns a (primary, secondary) pair
of plain strings, so a hub whose rows mix scripts -- as one does whenever a row
is still awaiting translation and is emitted in English -- still compares
without a type error.
"""
import unicodedata

# Punctuation that collation ignores. Ukrainian is the case that forced this:
# the apostrophe in the Ukrainian for Vietnam is a spelling device, not a
# letter, and treating it as one sorted that row to the bottom of the В block
# instead of after Вермонт. U+2019 is the character the copy actually uses.
IGNORABLE = dict.fromkeys(map(ord, "’ʼ'­"))

# Cyrillic order as a superset of the Russian and Ukrainian alphabets: ґ sits
# after г, є after е, і and ї after и, and Russian's ё, ъ, ы, э keep their own
# places. Neither language uses the other's extra letters, so one table orders
# both correctly.
CYRILLIC_ALPHABET = "абвгґдеёєжзиіїйклмнопрстуфхцчшщъыьэюя"

# Turkish is a Latin alphabet that folding diacritics gets wrong, which is the
# whole reason this module dispatches on language rather than script. ç ğ ı ö ş
# ü are letters in their own right, not accented c g i o s u: ı sorts before i,
# and ç after c. Fold them and Kıbrıs lands after Kuzey Dakota and Sırbistan
# after Slovenya. q, w and x are not Turkish letters; they appear only in
# retained foreign names (Hawaii, New York) and take their Latin-alphabet
# places, which is where a reader scanning for "New" looks.
TURKISH_ALPHABET = "abcçdefgğhıijklmnoöpqrsştuüvwxyz"

# casefold maps İ to i followed by U+0307; the dot is not a Turkish letter.
COMBINING_DOT_ABOVE = "̇"


def _ranked(alphabet: str) -> dict[str, str]:
    """Letter -> a single char ordering it, in a contiguous ascending range.

    Mapping into characters rather than integers keeps the key a plain string,
    so it compares against the other branches' keys.
    """
    return {ch: chr(0x100 + i) for i, ch in enumerate(alphabet)}


CYRILLIC_ORDER = _ranked(CYRILLIC_ALPHABET)
TURKISH_ORDER = _ranked(TURKISH_ALPHABET)

# --- Japanese ---------------------------------------------------------------
#
# Japanese needs a reading, not a code point. The katakana block is close
# enough to gojūon order to look plausible and is wrong in three ways that all
# show up in these hubs: the prolonged sound mark sits at the end of the block,
# so オーストラリア sorted below オレゴン州; voicing is a code point apart, so
# ジョージア sorted below シンガポール; and a name written in kanji shares no
# block with kana at all, so 台湾, 日本, 米国 and 英国 were dumped under every
# katakana name.
#
# The fix is ordinary Japanese practice: compare on the reading, where the
# prolonged sound mark is the vowel it lengthens, small kana are their full
# forms, and kanji are their readings. Those differences come back as the
# secondary key, so no two distinct names compare equal.

GOJUON = (
    "アイウエオカキクケコサシスセソタチツテトナニヌネノ"
    "ハヒフヘホマミムメモヤユヨラリルレロワヲン"
)
# The vowel each gojūon kana ends in, for expanding the prolonged sound mark.
# Written out rather than derived by modulo because the ヤ, ワ and ン rows are
# not five kana wide.
GOJUON_VOWELS = "aiueo" * 7 + "auo" + "aiueo" + "ao" + "-"
VOWEL_KANA = {"a": "ア", "i": "イ", "u": "ウ", "e": "エ", "o": "オ"}
SMALL_KANA = dict(zip("ァィゥェォッャュョヮヵヶ", "アイウエオツヤユヨワカケ"))
KATAKANA_ORDER = {ch: chr(0x100 + i) for i, ch in enumerate(GOJUON)}
PROLONGED = "ー"

# Readings for the names these hubs write with kanji. Substituted longest key
# first, so 州 does not have to be repeated for each of the twenty-one US
# states. A name still holding a non-kana character after this is reported by
# the callers rather than sorted on a guess: adding a Japanese place name
# written in kanji should fail loudly and be one line here.
JAPANESE_READINGS = {
    "首長国連邦": "シュチョウコクレンポウ",
    "台湾": "タイワン",
    "日本": "ニホン",
    "米国": "ベイコク",
    "英国": "エイコク",
    "圏": "ケン",
    "州": "シュウ",
}


def japanese_reading(name: str) -> str:
    """`name` with its kanji replaced by katakana, and hiragana raised to it."""
    for kanji, kana in sorted(JAPANESE_READINGS.items(), key=lambda kv: -len(kv[0])):
        name = name.replace(kanji, kana)
    # Hiragana and katakana write the same syllables; compare them as one.
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in name)


def is_kana(text: str) -> bool:
    """True if every letter is kana, i.e. the reading is fully resolved."""
    return all(
        not c.strip() or unicodedata.name(c, "").startswith(("KATAKANA", "HIRAGANA"))
        for c in text
    )


def japanese_key(name: str) -> tuple[str, str]:
    """Primary: the reading at gojūon level. Secondary: the reading itself.

    A character with no gojūon position -- a Latin letter in a row still
    awaiting translation, or a kanji with no reading above -- is kept as
    itself. Because the gojūon range starts at U+0100, that sorts ASCII before
    the kana and any other script after them, which groups the odd row out
    instead of scattering it.
    """
    reading = japanese_reading(name)
    primary, previous = [], None
    for char in unicodedata.normalize("NFC", reading):
        if char == PROLONGED and previous is not None:
            vowel = GOJUON_VOWELS[ord(KATAKANA_ORDER[previous]) - 0x100]
            char = VOWEL_KANA.get(vowel, previous)
        elif char in SMALL_KANA:
            char = SMALL_KANA[char]
        else:
            # Strip voicing: ガ and カ are one letter at the primary level.
            base = unicodedata.normalize("NFD", char)[0]
            if base in KATAKANA_ORDER:
                char = base
        if char in KATAKANA_ORDER:
            primary.append(KATAKANA_ORDER[char])
            previous = char
        else:
            primary.append(char)
    return ("".join(primary), reading)


# --- Latin and Cyrillic -----------------------------------------------------


def sort_key(name: str, code: str) -> tuple[str, str]:
    """Where `name` belongs in a list read by a speaker of `code`.

    A plain `.lower()` is a code-point sort, so an accented initial lands after
    z: French put Émirats arabes unis last and Géorgie after Grèce. Folding
    diacritics for the comparison puts each name where a reader of that
    language looks for it -- for the languages that treat them as accents.
    Turkish and Japanese do not, and take the branches above.

    Cyrillic is detected by script rather than by locale code because the one
    table serves both languages that use it, and because it must keep ordering
    a Cyrillic name correctly wherever it appears.
    """
    if code == "ja":
        return japanese_key(name)
    name = name.casefold().translate(IGNORABLE)
    letters = [c for c in name if c.isalpha()]
    is_latin = all(c.isascii() or "LATIN" in unicodedata.name(c, "") for c in letters)
    if letters and all("CYRILLIC" in unicodedata.name(c, "") for c in letters):
        return ("".join(CYRILLIC_ORDER.get(c, c) for c in name), name)
    if code == "tr" and is_latin:
        turkish = name.replace(COMBINING_DOT_ABOVE, "")
        return ("".join(TURKISH_ORDER.get(c, c) for c in turkish), name)
    if not is_latin:
        return (name, name)
    folded = unicodedata.normalize("NFD", name)
    return ("".join(c for c in folded if not unicodedata.combining(c)), name)


def unresolved(names, code: str) -> list[str]:
    """Names this module cannot order on merit, for the callers to report.

    Only Japanese can fail this way today: every other branch orders whatever
    letters it is given, while a Japanese name written in kanji has no order
    until someone supplies its reading.
    """
    if code != "ja":
        return []
    return sorted({n for n in names if not is_kana(japanese_reading(n))})
