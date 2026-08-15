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

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "_site-src"
DATA = SOURCE_ROOT / "data"

TAG = re.compile(r"<[^>]+>")
STRIPPED = re.compile(r"<script.*?</script>|<svg.*?</svg>|<!--.*?-->|<pre.*?</pre>|<code.*?</code>", re.DOTALL)
RENDERED_ATTRS = re.compile(r'(?:placeholder|aria-label|title|alt)="([^"]{4,})"')

# Text that is correctly identical in every language.
ALLOW = (
    # Brand, product and platform names.
    "AtlasDays", "App Store", "iPhone", "iPad", "iCloud", "Apple", "Flighty",
    "CSV", "PDF", "Excel", "iOS", "Stage Manager", "Schengen",
    # Official names of tests, statutes, forms and documents. The guidelines
    # require these to survive untranslated.
    "Substantial Presence Test", "Statutory Residence Test", "Publication",
    "Form ", "Appendix ", "Standard Visitor", "Visitor Visa", "ESTA", "eTA",
    "Visa Waiver", "Nonresident Statement", "visitor record", "income year",
    "Income year", "resides test", "domicile test", "superannuation test",
    "exempt individual", "actual resident", "Closer Connection",
    "Introduction to residency", "Travelers' Century Club", "ISO ",
    "Circular ", "Finance Act", "Tax Law", "Rev. Stat", "Gen. Laws",
    "Cent. Code", "Admin. Rules", "Code §", "Stat. §", "R&TC", "M.R.S.",
    "N.J.S.A.", "V.S.A.", "P.S. §", "Tax-General", "subd.", "O.C.G.A.",
    "Tax Act", "Income Tax", "Act No", "Law No",
    # CSV column names and cell values, which are literals in the file the
    # importer reads. The guidelines say to gloss these, never translate them.
    "Start Date", "End Date", "Tourism, Business", "Country,State",
    # Terms of art a translator deliberately kept, recorded in section 8 of
    # TRANSLATION_GUIDELINES-web.md. Adding to this group needs that entry too.
    "deemed resident", "safe harbors",
    # Comparison operators rendered as literal glyphs in hub legends.
    "≥ ", "> ", "&gt; ",
)

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


def visible_text(markup: str) -> set[str]:
    """Every rendered run of two or more words, prose and attributes alike."""
    body = STRIPPED.sub(" ", markup)
    found = {html.unescape(" ".join(chunk.split())) for chunk in TAG.split(body)}
    for match in RENDERED_ATTRS.finditer(body):
        found.add(html.unescape(" ".join(match.group(1).split())))
    return {text for text in found if len(text.split()) >= 2}


def is_allowed(text: str) -> bool:
    if any(token in text for token in ALLOW):
        return True
    if PROPER_NOUN.match(text) or BREADCRUMB_TAIL.match(text) or NUMBERED_HEADING.match(text):
        return True
    return not re.search(r"[A-Za-z]", text)


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
            shared = visible_text((SOURCE_ROOT / str(source["content"])).read_text(encoding="utf-8"))
            shared &= visible_text(translated.read_text(encoding="utf-8"))
            for text in sorted(t for t in shared if not is_allowed(t)):
                problems.append(f"{code}/{overlay['source']}: still English: {text[:90]!r}")

    if problems:
        print("Untranslated reader-facing text:")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print(f"Checked {checked} translated fragments for text left in English.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
