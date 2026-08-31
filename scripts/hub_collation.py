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


# --- Traditional Chinese ----------------------------------------------------
#
# Han characters carry no order at all. A code point sort is not merely
# imperfect the way the katakana block is, it is meaningless to a reader: the
# 58 site place names come out as 加拿大 喬治亞 希臘 德國 愛爾蘭 捷克 日本 法國
# 泰國 澳洲 義大利 葡萄牙 西班牙 賽普勒斯, which is an ordering by the historical
# accident of block assignment.
#
# Taiwan indexes on the reading, in 注音 (Bopomofo) order, which is what
# dictionaries, atlas indexes and library catalogues use and what every reader
# was taught in school. Stroke count is the other Taiwan convention, but it
# belongs to name rosters and ballots, where a phonetic order would look like a
# ranking; pinyin is the mainland convention and orders differently (ㄐㄑㄒ sit
# after ㄍㄎㄏ, while j/q/x interleave alphabetically), so it would be the wrong
# signal for a Taiwan-first locale.
#
# This is the Japanese branch's shape: a reading table, a primary key at the
# symbol level, and a name with an unreadable character reported by unresolved()
# rather than sorted on a guess. Adding a place name is one line here.

# 注音符號 in dictionary order: initials, then medials, then finals.
BOPOMOFO = "ㄅㄆㄇㄈㄉㄊㄋㄌㄍㄎㄏㄐㄑㄒㄓㄔㄕㄖㄗㄘㄙㄧㄨㄩㄚㄛㄜㄝㄞㄟㄠㄡㄢㄣㄤㄥㄦ"
BOPOMOFO_ORDER = _ranked(BOPOMOFO)
# Second through fifth tone. First tone is unmarked, so it sorts first for free.
TONES = "ˊˇˋ˙"

# Readings for every Han character these hubs write, from the Taiwan MOE
# standard. Countries are the CLDR zh-Hant names, which is what the app
# displays; US states are the app's own CountrySubdivisions table.
CHINESE_READINGS = {
    "乃": "ㄋㄞˇ", "亞": "ㄧㄚˋ", "亥": "ㄏㄞˋ", "他": "ㄊㄚ", "伐": "ㄈㄚ",
    "伯": "ㄅㄛˊ", "佛": "ㄈㄛˊ", "來": "ㄌㄞˊ", "俄": "ㄜˊ", "保": "ㄅㄠˇ",
    "倫": "ㄌㄨㄣˊ", "克": "ㄎㄜˋ", "內": "ㄋㄟˋ", "公": "ㄍㄨㄥ", "其": "ㄑㄧˊ",
    "利": "ㄌㄧˋ", "加": "ㄐㄧㄚ", "勒": "ㄌㄜˋ", "北": "ㄅㄟˇ", "區": "ㄑㄩ",
    "南": "ㄋㄢˊ", "印": "ㄧㄣˋ", "台": "ㄊㄞˊ", "合": "ㄏㄜˊ", "吉": "ㄐㄧˊ",
    "哥": "ㄍㄜ", "喬": "ㄑㄧㄠˊ", "因": "ㄧㄣ", "國": "ㄍㄨㄛˊ", "土": "ㄊㄨˇ",
    "坡": "ㄆㄛ", "塞": "ㄙㄞ", "夏": "ㄒㄧㄚˋ", "夕": "ㄒㄧˊ", "多": "ㄉㄨㄛ",
    "大": "ㄉㄚˋ", "夷": "ㄧˊ", "奧": "ㄠˋ", "威": "ㄨㄟ", "宛": "ㄨㄢˇ",
    "尼": "ㄋㄧˊ", "岡": "ㄍㄤ", "島": "ㄉㄠˇ", "州": "ㄓㄡ", "巴": "ㄅㄚ",
    "布": "ㄅㄨˋ", "希": "ㄒㄧ", "康": "ㄎㄤ", "德": "ㄉㄜˊ", "愛": "ㄞˋ",
    "拉": "ㄌㄚ", "拿": "ㄋㄚˊ", "捷": "ㄐㄧㄝˊ", "摩": "ㄇㄛˊ", "斯": "ㄙ",
    "新": "ㄒㄧㄣ", "日": "ㄖˋ", "明": "ㄇㄧㄥˊ", "普": "ㄆㄨˇ", "本": "ㄅㄣˇ",
    "根": "ㄍㄣ", "桑": "ㄙㄤ", "模": "ㄇㄛˊ", "比": "ㄅㄧˇ", "沙": "ㄕㄚ",
    "治": "ㄓˋ", "法": "ㄈㄚˇ", "波": "ㄅㄛ", "泰": "ㄊㄞˋ", "洛": "ㄌㄨㄛˋ",
    "洲": "ㄓㄡ", "澤": "ㄗㄜˊ", "澳": "ㄠˋ", "灣": "ㄨㄢ", "爾": "ㄦˇ",
    "牙": "ㄧㄚˊ", "特": "ㄊㄜˋ", "狄": "ㄉㄧˊ", "瓦": "ㄨㄚˇ", "申": "ㄕㄣ",
    "福": "ㄈㄨˊ", "科": "ㄎㄜ", "立": "ㄌㄧˋ", "約": "ㄩㄝ", "紐": "ㄋㄧㄡˇ",
    "維": "ㄨㄟˊ", "緬": "ㄇㄧㄢˇ", "羅": "ㄌㄨㄛˊ", "美": "ㄇㄟˇ", "義": "ㄧˋ",
    "耳": "ㄦˇ", "聯": "ㄌㄧㄢˊ", "臘": "ㄌㄚˋ", "英": "ㄧㄥ", "荷": "ㄏㄜˊ",
    "萄": "ㄊㄠˊ", "葡": "ㄆㄨˊ", "蒙": "ㄇㄥˊ", "薩": "ㄙㄚˋ", "蘇": "ㄙㄨ",
    "蘭": "ㄌㄢˊ", "西": "ㄒㄧ", "諸": "ㄓㄨ", "賓": "ㄅㄧㄣ", "賽": "ㄙㄞˋ",
    "越": "ㄩㄝˋ", "達": "ㄉㄚˊ", "那": "ㄋㄚˋ", "里": "ㄌㄧˇ", "阿": "ㄚ",
    "陶": "ㄊㄠˊ", "馬": "ㄇㄚˇ", "麻": "ㄇㄚˊ",
}


def chinese_reading(name: str) -> str:
    """`name` with each Han character replaced by its 注音 reading."""
    return "".join(CHINESE_READINGS.get(c, c) for c in name)


def is_bopomofo(text: str) -> bool:
    """True if the reading is fully resolved, i.e. holds no Han character."""
    return not any("\u4e00" <= c <= "\u9fff" for c in text)


def chinese_key(name: str) -> tuple[str, str]:
    """Primary: the reading with tones stripped. Secondary: the reading.

    A character with no entry above is kept as itself, and because the 注音
    range starts at U+0100 that puts a row still awaiting translation ahead of
    every Chinese one instead of scattering it through them.
    """
    reading = chinese_reading(name)
    primary = "".join(
        BOPOMOFO_ORDER.get(c, c) for c in reading if c not in TONES
    )
    return (primary, reading)


# --- Simplified Chinese -----------------------------------------------------
#
# Pinyin, and the reasoning is the mirror image of the Traditional branch's.
# That branch chose 注音 and recorded why pinyin was wrong for Taiwan: ㄐㄑㄒ
# follow ㄍㄎㄏ, while j/q/x interleave alphabetically, so the two orders
# genuinely differ. For a mainland locale the same fact makes pinyin the right
# answer, because it is the order a mainland reader has been taught to scan and
# the one every mainland index uses.
#
# None of the Traditional table transfers. Its 113 entries are 注音 readings,
# which is a different alphabet, and the characters themselves are Traditional.
# This table is built from the Simplified names the hubs actually carry.
#
# Syllables are kept apart rather than concatenated, because pinyin collation is
# syllable by syllable: run them together and 西安 (xi an) would sort as though
# it were spelled "xian". The separator is a space, which sorts before every
# letter, so a shorter first syllable wins exactly as it should.
PINYIN_READINGS = {
    "\u4e9a": "ya4", "\u4ea5": "hai4", "\u4ed6": "ta1", "\u4f10": "fa2", "\u4f26": "lun2",
    "\u4f2f": "bo2", "\u4f50": "zuo3", "\u4f5b": "fo2", "\u4fc4": "e2", "\u4fdd": "bao3",
    "\u514b": "ke4", "\u5170": "lan2", "\u5176": "qi2", "\u5185": "nei4", "\u5188": "gang1",
    "\u5229": "li4", "\u52a0": "jia1", "\u52d2": "le4", "\u5317": "bei3", "\u533a": "qu1",
    "\u5357": "nan2", "\u5370": "yin4", "\u53f0": "tai2", "\u5408": "he2", "\u5409": "ji2",
    "\u54e5": "ge1", "\u56e0": "yin1", "\u56fd": "guo2", "\u571f": "tu3", "\u5761": "po1",
    "\u585e": "sai1", "\u590f": "xia4", "\u5915": "xi1", "\u591a": "duo1", "\u5927": "da4",
    "\u5937": "yi2", "\u5a01": "wei1", "\u5b9b": "wan3", "\u5bbe": "bin1", "\u5c14": "er3",
    "\u5c3c": "ni2", "\u5c71": "shan1", "\u5c9b": "dao3", "\u5dde": "zhou1", "\u5df4": "ba1",
    "\u5e03": "bu4", "\u5e0c": "xi1", "\u5ea6": "du4", "\u5eb7": "kang1", "\u5f17": "fu2",
    "\u5f97": "de2", "\u610f": "yi4", "\u62c9": "la1", "\u62ff": "na2", "\u6377": "jie2",
    "\u6469": "mo2", "\u6587": "wen2", "\u65af": "si1", "\u65b0": "xin1", "\u65e5": "ri4",
    "\u660e": "ming2", "\u672c": "ben3", "\u6765": "lai2", "\u6839": "gen1", "\u683c": "ge2",
    "\u6851": "sang1", "\u6bd4": "bi3", "\u6bdb": "mao2", "\u6c42": "qiu2", "\u6c99": "sha1",
    "\u6cbb": "zhi4", "\u6cd5": "fa3", "\u6ce2": "bo1", "\u6cf0": "tai4", "\u6cfd": "ze2",
    "\u6d1b": "luo4", "\u6d66": "pu3", "\u6d85": "nie4", "\u6e7e": "wan1", "\u6fb3": "ao4",
    "\u7231": "ai4", "\u7259": "ya2", "\u7279": "te4", "\u72c4": "di2", "\u74e6": "wa3",
    "\u7533": "shen1", "\u798f": "fu2", "\u79d1": "ke1", "\u7acb": "li4", "\u7ea6": "yue1",
    "\u7ebd": "niu3", "\u7ef4": "wei2", "\u7f05": "mian3", "\u7f57": "luo2", "\u7f8e": "mei3",
    "\u8033": "er3", "\u8054": "lian2", "\u814a": "la4", "\u82cf": "su1", "\u82f1": "ying1",
    "\u8377": "he2", "\u8404": "tao2", "\u8428": "sa4", "\u8461": "pu2", "\u8499": "meng2",
    "\u897f": "xi1", "\u8bf8": "zhu1", "\u8d8a": "yue4", "\u8def": "lu4", "\u8fbe": "da2",
    "\u90a3": "na4", "\u914b": "qiu2", "\u91cc": "li3", "\u957f": "zhang3", "\u963f": "a1",
    "\u9676": "tao2", "\u9a6c": "ma3", "\u9c81": "lu3", "\u9ed1": "hei1",
}

HAN = ("\u4e00", "\u9fff")


def pinyin_syllables(name: str) -> list[str]:
    """`name` as one toned syllable per character, unreadable ones kept as-is."""
    return [PINYIN_READINGS.get(c, c) for c in name]


def is_pinyin(syllables) -> bool:
    """True if every character resolved, i.e. no Han character survives."""
    return not any(HAN[0] <= c <= HAN[1] for s in syllables for c in s)


def simplified_key(name: str) -> tuple[str, str]:
    """Primary: the reading, tone included, one syllable at a time.

    Keeping the tone digit inside the syllable is what makes a tie at the first
    syllable break on tone before the second syllable is consulted, which is
    what a mainland reader expects and what the platform's own zh-Hans collation
    does: 哥伦比亚 (ge1) before 格鲁吉亚 (ge2), 台湾 (tai2) before 泰国 (tai4).
    Comparing the toneless spelling across the whole name instead put both pairs
    the other way round.

    The digits are doing double duty as the syllable separator. A digit sorts
    below every letter, so a shorter syllable still wins its comparison: jia1
    before jian1, exactly as pinyin order requires.

    A character with no entry above is kept as itself, and because Han sits far
    above the Latin range that puts a row still awaiting a reading at the end of
    the list rather than scattered plausibly through it.
    """
    syllables = pinyin_syllables(name)
    return (" ".join(syllables), name)


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
    if code == "zh-Hant":
        return chinese_key(name)
    if code == "zh-Hans":
        return simplified_key(name)
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

    Japanese and both Chinese locales can fail this way: every other branch
    orders whatever letters it is given, while a name written in kanji or Han
    characters has no order until someone supplies its reading. Chinese fails
    for every unlisted character rather than only for the unusual ones, which
    is the honest behaviour -- there is no Chinese equivalent of kana.
    """
    if code == "ja":
        return sorted({n for n in names if not is_kana(japanese_reading(n))})
    if code == "zh-Hant":
        return sorted({n for n in names if not is_bopomofo(chinese_reading(n))})
    if code == "zh-Hans":
        return sorted({n for n in names if not is_pinyin(pinyin_syllables(n))})
    return []
