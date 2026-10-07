#!/usr/bin/env python3
"""Find reader-facing text a translation left in English.

Nothing else detects this. Coverage proves a page exists, structural parity
proves it has the same shape, the number check proves no threshold was dropped,
the terminology tables only fire when a glossary term appears, and the link
check only compares hrefs. A fragment that is 100% English passes every one of
them, because none of them ever asks whether the words changed.

That gap shipped: the Spanish Learn hub went live with its filter pills, group
headings, place-type badges, empty state and legend still in English, because
the hub was derived by translating a hand-picked set of selectors rather than
by enumerating every text node. Dutch had been done by hand and was fine, so
there was nothing to compare against either.

The check is deliberately crude: any run of two or more words that is byte
identical in the English source and the translation is suspicious. Most matches
are legitimate, so ALLOW below carries the things that must stay identical.
Keeping that list short is the point. If you find yourself adding a whole
sentence to it, the sentence probably wanted translating.

    python3 scripts/check_untranslated.py           # report and exit non-zero
    python3 scripts/check_untranslated.py --check    # same, for CI symmetry
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from locales import default_locale_code, load_locales  # noqa: E402

from calendar_strings import prose as cal_prose

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "_site-src"
DATA = SOURCE_ROOT / "data"

TAG = re.compile(r"<[^>]+>")
STRIPPED = re.compile(r"<script.*?</script>|<svg.*?</svg>|<!--.*?-->|<pre.*?</pre>|<code.*?</code>|<div\b[^>]*\blang=\"en\"[^>]*>.*?</div>", re.DOTALL)
# A <div lang="en"> is English on purpose (a quoted original, such as an App
# Store review shown beside its translation), so it is not "left in English".
RENDERED_ATTRS = re.compile(r'(?:placeholder|aria-label|title|alt)="([^"]{4,})"')
WORD = re.compile(r"[A-Za-z][A-Za-z'’.-]*")
PARTIAL_RUN_WORDS = 6

# Brand, product and platform names may stay identical, but their presence
# must not exempt the rest of a sentence. That used to let an English CTA pass
# merely because it also contained "AtlasDays" or "App Store".
BRAND_ALLOW = (
    "AtlasDays", "App Store", "iPhone", "iPad", "iCloud", "Apple", "Flighty",
    "CSV", "PDF", "Excel", "iOS", "Stage Manager", "Schengen",
)

# Text that is correctly identical in every language.
ALLOW = (
    # Official names of tests, statutes, forms and documents. The guidelines
    # require these to survive untranslated.
    "Substantial Presence Test", "Statutory Residence Test", "Publication",
    "Form ", "Appendix ", "Standard Visitor", "Visitor Visa", "ESTA", "eTA",
    # Statute citations and an authority's official name survive as printed
    # (added 2026-09 with the residence-permit and citizenship pages).
    "INA ", " CFR ", "Resident Return", "Refugees and Citizenship Canada",
    "Immigration and Refugee Protection Act", "Citizenship Act", "Migration Regulations",
    "Staatsangehörigkeitsgesetz", "Bureau of Immigration",
    "Visa Waiver", "Nonresident Statement", "visitor record", "income year",
    "Income year", "resides test", "domicile test", "superannuation test",
    "exempt individual", "actual resident", "Closer Connection",
    "Introduction to residency", "Travelers' Century Club", "ISO ",
    "Circular ", "Finance Act", "Tax Law", "Rev. Stat", "Gen. Laws",
    "Cent. Code", "Admin. Rules", "Code §", "Stat. §", "R&TC", "M.R.S.",
    "N.J.S.A.", "V.S.A.", "P.S. §", "Tax-General", "subd.", "O.C.G.A.",
    "Tax Act", "Income Tax", "Act No", "Law No", "Consolidation Act",
    "Naturalisation as a British citizen by discretion",
    "US Customs and Border Protection",
    "Internal Revenue Code", "Treasury Regulation", "Immigration and Nationality Act",
    "Department of the Treasury Internal Revenue Service Center Austin TX",
    # Names of the country lists the counting articles compare. The list is the
    # identifier, so translating it would break the comparison it belongs to.
    "UN 195", "UN 193",
    # CSV column names and cell values, which are literals in the file the
    # importer reads. The guidelines say to gloss these, never translate them.
    "Start Date", "End Date", "Tourism, Business", "Country,State",
    # Terms of art a translator deliberately kept, recorded in that language's
    # translation-web/<code>.md. Adding to this group needs that entry too.
    "deemed resident", "safe harbors",
    # Comparison operators rendered as literal glyphs in hub legends.
    "≥ ", "> ", "&gt; ",
)

# Single-word labels are normally too noisy for this check, but these English
# exonyms have established Spanish forms in the translation guidelines. Keep
# this list locale-specific: a name that needs translating in Spanish may be
# spelled identically in Dutch or German.
MUST_TRANSLATE = {
    "es": {
        "Canada", "Cyprus", "Czech Republic", "Georgia", "Greece", "Hawaii",
        "Ireland", "Italy", "Japan", "Malaysia", "Mauritius", "New Jersey",
        "New York", "New Zealand", "North Dakota", "Oregon", "Pennsylvania",
        "Poland", "Romania", "Schengen Area", "Singapore", "Thailand",
        "Türkiye", "United Arab Emirates",
    },
    # Japanese writes every place name in kana, so the whole set belongs here
    # rather than the handful Spanish needed. The residency hub tables are why:
    # a cell is a bare place name, which is one word, and the general check only
    # looks at runs of two or more. Without this, an untranslated hub row would
    # render, resolve, and be visible only to a reader of the language.
    "ja": {
        "Arizona", "Australia", "Bulgaria", "California", "Canada", "Colombia",
        "Colorado", "Connecticut", "Cyprus", "Czech Republic", "Estonia",
        "Georgia", "Greece", "Hawaii", "Idaho", "Indonesia", "Ireland", "Italy",
        "Japan", "Maine", "Malaysia", "Malta", "Maryland", "Massachusetts",
        "Mauritius", "Minnesota", "Montenegro", "Nebraska", "New Jersey",
        "New York", "New Zealand", "North Dakota", "Ohio", "Oregon",
        "Pennsylvania", "Poland", "Portugal", "Rhode Island", "Romania",
        "Schengen", "Schengen Area", "Serbia", "Singapore", "Thailand",
        "Türkiye", "United Arab Emirates", "United Kingdom", "United States",
        "Vermont", "Vietnam", "Virginia",
    },
}

# Cyrillic locales have exactly the property the Japanese entry above describes:
# every place name is written in their own script, so a bare hub cell left in
# English is a single Latin word that the two-word rule cannot see. Russian went
# to production without this protection; it is added here alongside Ukrainian
# rather than left for the next pass to rediscover.
MUST_TRANSLATE["uk"] = set(MUST_TRANSLATE["ja"])
MUST_TRANSLATE["ru"] = set(MUST_TRANSLATE["ja"])

# Korean has the identical property: every place name is written in Hangul, so
# a single Latin word left in a hub cell renders, resolves, and is visible only
# to a reader of the language. Added with the locale rather than after it, so
# the gate protects the hubs while they are being written.
MUST_TRANSLATE["ko"] = set(MUST_TRANSLATE["ja"])

# Traditional Chinese writes every place name in Han characters, so the same
# rule applies again: a bare `Cyprus` left in a hub cell is one Latin word that
# the two-or-more-word rule cannot see. Added with the locale, before the hubs
# exist, so the gate is protecting them while they are written rather than
# after.
MUST_TRANSLATE["zh-Hant"] = set(MUST_TRANSLATE["ja"])

# Simplified Chinese has the same property as Traditional, and the set is keyed
# on the *English* source names, so aliasing carries no Chinese strings between
# the two scripts. Verified rather than assumed: the two Chinese locales share
# no vocabulary, and every place name in this list is spelled differently in
# zh-Hans than in zh-Hant.
MUST_TRANSLATE["zh-Hans"] = set(MUST_TRANSLATE["ja"])

# Numbered legal headings whose noun is spelled the same in the target
# language: Dutch "10. Contact" and "5. Privacy" are correct Dutch.
NUMBERED_HEADING = re.compile(r"^\d+\.\s+[A-Z][\w'-]*$")

# Place names spelled the same in the target language are not defects. Rather
# than list every one, allow a string that is entirely capitalised words, which
# covers "Rhode Island" and "New Jersey" without swallowing sentences: an
# untranslated UI string almost always contains a lowercase word.
PROPER_NOUN = re.compile(r"^(?:[A-Z][\w'&.-]*\s+){1,3}[A-Z][\w'&.-]*$")
# A breadcrumb tail is "/ Arizona": one place name, which may be a single word.
BREADCRUMB_TAIL = re.compile(r"^/\s*(?:[A-Z][\w'&.-]*\s*){1,4}$")


def without_csv_schema_cells(markup: str) -> str:
    """CSV example schema values stay English; free-text Notes still translate."""
    def table(match):
        def row(match):
            column = 0
            def cell(match):
                nonlocal column
                column += 1
                return match.group(1) + ("" if column <= 5 else match.group(2)) + match.group(3)
            return re.sub(r"(<td\b[^>]*>)(.*?)(</td>)", cell, match.group(0), flags=re.DOTALL)
        return re.sub(r"<tr\b[^>]*>.*?</tr>", row, match.group(0), flags=re.DOTALL)
    return re.sub(r'<div\b[^>]*class="[^"]*\bdata-table-code\b[^"]*"[^>]*>.*?</div>', table, markup, flags=re.DOTALL)


def without_declared_english_hub_names(markup: str, locale: dict, records: dict) -> str:
    """Only generated country names may fall back to explicitly deferred English.

    Keep checking the threshold/window cells and all surrounding prose. A
    declaration must identify a real residency record and its exact name/link.
    """
    allowed = {}
    for path in locale.get("untranslated", []):
        record = records.get(path, {})
        name = record.get("residency", {}).get("name")
        if name:
            allowed["/" + path.removesuffix(".html")] = name

    def row(match):
        def link(match):
            href, text = html.unescape(match.group(2)), html.unescape(match.group(3))
            if allowed.get(href) == text:
                return match.group(1) + match.group(4)
            return match.group(0)
        return re.sub(r'(<a href="([^"]+)">)([^<]*)(</a>)', link, match.group(0))

    return re.sub(r'<tr class="hub-row"[^>]*>.*?</tr>', row, markup, flags=re.DOTALL)


def visible_runs(markup: str) -> set[str]:
    """Every non-empty rendered text run, prose and attributes alike."""
    body = STRIPPED.sub(" ", without_csv_schema_cells(markup))
    found = {html.unescape(" ".join(chunk.split())) for chunk in TAG.split(body)}
    found.update(cal_prose(markup))
    for match in RENDERED_ATTRS.finditer(body):
        found.add(html.unescape(" ".join(match.group(1).split())))
    return {text for text in found if text}


def visible_text(markup: str) -> set[str]:
    """Rendered runs long enough for the general untranslated-text check."""
    return {text for text in visible_runs(markup) if len(text.split()) >= 2}


# These complete text runs are also correct native Dutch. Do not allow a
# province token to exempt a surrounding untranslated sentence.
# Formal source-panel titles and statute identifiers are reference labels.
# Help: Flighty's own menu path, which Flighty shows in English, and the
# languages page's list of interface languages, each named in itself.
HELP_EXACT_ALLOW = {"Settings → Account Data",
                    "English US English UK Nederlands Espa ol Deutsch Fran ais T rk e Portugu s Brasil"}
EXACT_ALLOW = HELP_EXACT_ALLOW | {"§ 10 StAG", "§ 12b StAG","Request for International Movement Records", "travel movements requests", "Entry/Exit System", "Boletín Oficial del Estado", "8 U.S.C. 1187(a)(7)", "8 U.S.C. 1202(g)", "IMM 5257 Schedule 1", "How to Calculate Physical Presence (CIT 0407)", "How to Calculate Physical Presence CIT", "deeming rule","Destination Thailand Visa (DTV)", "Electronic Travel Authorisation (ETA)", "Long Residence UK Ancestry Hong Kong BN O", "UK Immigration Rules Part Suitability SUI"}

LOCALE_ALLOW = {
    "pt": {"Alberta (AHCIP)", "Québec (RAMQ)", "Malta: Nomad Residence Permit", ". Portugal:"},
    "tr": {"virtusopus · Türkiye", "Ontario (OHIP)", "Alberta (AHCIP)", "Québec (RAMQ)", "Malta: Nomad Residence Permit"},
    "de": {". Portugal:"},
    "es": {". Indonesia:", ". Portugal:", "Malta: Nomad Residence Permit", "Ontario (OHIP)", "Alberta (AHCIP)"},
    "fr": {"Basecampoversummit · Canada", "Ontario (OHIP)", "Alberta (AHCIP)", "Québec (RAMQ)"},
    "nl": {"Basecampoversummit · Canada", ". Portugal:", "Québec (RAMQ)", "Alberta (AHCIP)", "British Columbia (MSP)", "Ontario (OHIP)", "in Québec.", "Malta: Nomad Residence Permit", "Thailand: Destination Thailand Visa (DTV)", "India, e-Tourist Visa", "Entry/Exit System (EES)"},
}


def is_allowed(text: str, code: str = "") -> bool:
    if re.fullmatch(r"[A-Z]{3}\s+[0-9][0-9,.\u00a0\u202f ]*", text):
        return True
    if text in EXACT_ALLOW or text in LOCALE_ALLOW.get(code, set()):
        return True
    residual = text
    found_brand = False
    for token in sorted(BRAND_ALLOW, key=len, reverse=True):
        if token in residual:
            found_brand = True
            residual = residual.replace(token, " ")
    if found_brand and len(WORD.findall(residual)) <= 1:
        return True
    if any(token in text for token in ALLOW):
        return True
    if PROPER_NOUN.match(text) or BREADCRUMB_TAIL.match(text) or NUMBERED_HEADING.match(text):
        return True
    return not re.search(r"[A-Za-z]", text)


def partial_english(english_runs: set[str], translated_runs: set[str]) -> set[str]:
    """Long English word runs embedded inside otherwise translated nodes."""
    translated_index: dict[str, list[list[str]]] = {}
    for text in translated_runs:
        words = WORD.findall(text)
        if len(words) < PARTIAL_RUN_WORDS:
            continue
        for word in set(words):
            translated_index.setdefault(word, []).append(words)

    found: set[str] = set()
    for text in english_runs:
        english_words = WORD.findall(text)
        if len(english_words) < PARTIAL_RUN_WORDS:
            continue
        best: list[str] = []
        for start, first in enumerate(english_words):
            for translated_words in translated_index.get(first, []):
                for translated_start, word in enumerate(translated_words):
                    if word != first:
                        continue
                    length = 0
                    while (
                        start + length < len(english_words)
                        and translated_start + length < len(translated_words)
                        and english_words[start + length] == translated_words[translated_start + length]
                    ):
                        length += 1
                    if length >= PARTIAL_RUN_WORDS and length > len(best):
                        best = english_words[start : start + length]
        phrase = " ".join(best)
        if phrase and not is_allowed(phrase):
            found.add(phrase)
    return found


def sources() -> dict[str, dict]:
    found: dict[str, dict] = {}
    for name, key in (("pages.json", "pages"), ("hubs.json", "hubs"), ("articles.json", "articles")):
        path = DATA / name
        if path.exists():
            for record in json.loads(path.read_text(encoding="utf-8"))[key]:
                found[str(record["path"])] = record
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Kept for symmetry; the script always checks")
    parser.parse_args()

    english = sources()
    default = default_locale_code()
    problems: list[str] = []
    checked = 0

    for code, locale in load_locales().items():
        registry = locale.get("articles")
        if code == default or not registry:
            continue
        path = SOURCE_ROOT / str(registry)
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for overlay in [o for key in ("articles", "hubs", "pages") for o in data.get(key, [])]:
            source = english.get(str(overlay["source"]))
            translated = SOURCE_ROOT / str(overlay["content"])
            if source is None or not translated.exists():
                continue
            checked += 1
            english_runs = visible_runs(
                (SOURCE_ROOT / str(source["content"])).read_text(encoding="utf-8")
            )
            translated_runs = visible_runs(without_declared_english_hub_names(
                translated.read_text(encoding="utf-8"), locale, english
            ))
            required = MUST_TRANSLATE.get(code, set())
            for text in sorted(english_runs & translated_runs & required):
                problems.append(f"{code}/{overlay['source']}: still English: {text[:90]!r}")
            shared = {text for text in english_runs & translated_runs if len(text.split()) >= 2}
            for text in sorted(t for t in shared if not is_allowed(t, code)):
                problems.append(f"{code}/{overlay['source']}: still English: {text[:90]!r}")
            for text in sorted(partial_english(english_runs, translated_runs)):
                if text not in shared:
                    problems.append(
                        f"{code}/{overlay['source']}: English run inside translated text: "
                        f"{text[:90]!r}"
                    )

    if problems:
        print("Untranslated reader-facing text:")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print(f"Checked {checked} translated fragments for text left in English.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
