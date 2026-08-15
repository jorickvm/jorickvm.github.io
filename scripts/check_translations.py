#!/usr/bin/env python3
"""Gate translated pages on the things a non-speaker cannot check by reading.

Four families, in rough order of how much damage they prevent:

1. Terminology, against the glossary snapshot taken from the app's own shipped
   strings. An article that names a button differently from the app is worse
   than no article.
2. Structural parity with the English source. A translation that quietly drops
   a step from a numbered procedure looks completely normal on the page.
3. Typography. Japanese punctuation rules, plus the house em-dash ban, which
   until now was convention rather than something a machine enforced.
4. Chrome strings, so a marker cannot resolve to an empty nav label.

Run it before build_site.py: there is no point rendering a page that will not
pass.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from locales import (
    default_locale_code,
    load_locales,
    load_ui_strings,
    localized_route,
    meta_hash,
    route_for,
    source_hash,
)

SITE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = SITE_ROOT / "_site-src"
GLOSSARY_PATH = SOURCE_ROOT / "data" / "glossary.json"
ARTICLES_PATH = SOURCE_ROOT / "data" / "articles.json"
HUBS_PATH = SOURCE_ROOT / "data" / "hubs.json"
PAGES_PATH = SOURCE_ROOT / "data" / "pages.json"

EM_DASH = "—"
EN_DASH = "–"
HALFWIDTH_KATAKANA = re.compile(r"[ｦ-ﾟ]")
# A Japanese counter must sit tight against its digit: "3日", never "3 日".
# Horizontal space only, and never across a line break: a count badge in its
# own element ("<span>5</span>" followed by the next list item) is not a
# spaced counter, and matching \s+ made the hub fail on exactly that.
SPACED_COUNTER = re.compile(r"\d[ \u3000]{1,2}[々぀-ヿ一-鿿]")
ASCII_ELLIPSIS = re.compile(r"(?<!\.)\.\.\.(?!\.)")
HEADING = re.compile(r"<h2\b")
LIST_ITEM = re.compile(r"<li\b")
ORDERED_LIST = re.compile(r"<ol\b")
IF_NEEDED = re.compile(r'<section class="if-needed"')
FIGURE_SLOT = re.compile(r'<img src="[^"]*/([\w\-]+)\.webp"')
DEFERRED_SLOT = re.compile(r"<!-- SCREENSHOT_DEFERRED: ([\w\-]+) \|")
# The fragment is part of the link. Without it here, an anchored href like
# /help/#support was invisible to this check in every locale, and a Spanish
# homepage shipped two links into the English Help Center that nothing caught.
INTERNAL_HREF = re.compile(r'href="(/[\w\-./]*(?:#[\w\-]+)?)"')
TAGS = re.compile(r"<[^>]+>")
# Figures carry pixel dimensions, which are not facts about the article.
FIGURES = re.compile(r"<figure.*?</figure>", re.DOTALL)
NUMBER = re.compile(r"\d+")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Kept for symmetry; the script always checks")
    return parser.parse_args()


def visible_text(fragment: str) -> str:
    """Prose only, so a rule never fires on markup or a URL."""
    without_comments = re.sub(r"<!--.*?-->", "\n", fragment, flags=re.DOTALL)
    # Newline rather than space, so text in two different elements never reads
    # as one sentence to the typography rules below.
    return TAGS.sub("\n", without_comments)


def check_house_typography(label: str, text: str, problems: list[str]) -> None:
    """The em-dash ban applies to every locale, including English."""
    if EM_DASH in text:
        problems.append(f"{label}: em dash (U+2014) in reader-facing copy; use an en dash or reword")


def check_japanese_typography(label: str, text: str, problems: list[str]) -> None:
    """Japanese has its own marks, and neither ASCII dash is one of them.

    The house rule says to replace an em dash with an en dash. That rule was
    written for English and misfires here: Japanese has no en dash, and the
    mark it actually uses for the em dash's parenthetical role is an em dash.
    The guidelines already require full-width Japanese punctuation in prose, so
    the resolution is to use neither dash and split the sentence or use
    corner brackets.
    """
    if EN_DASH in text:
        problems.append(
            f"{label}: en dash (U+2013) is not Japanese punctuation; "
            "split the sentence with 。 or use （…） / 「…」"
        )
    if ASCII_ELLIPSIS.search(text):
        problems.append(f"{label}: ASCII '...' should be the full-width ellipsis '…'")
    if HALFWIDTH_KATAKANA.search(text):
        problems.append(f"{label}: half-width katakana")
    match = SPACED_COUNTER.search(text)
    if match:
        problems.append(f"{label}: space between a digit and its counter near {match.group(0)!r}")


def check_terminology(
    label: str,
    english: str,
    translated: str,
    glossary: dict[str, object],
    problems: list[str],
    *,
    app_terms: bool = True,
) -> None:
    """Hold a translation to the app's own vocabulary, where that vocabulary rules.

    `app_terms` is off for Learn. The term tables name buttons, sheets, and
    settings, and they are authoritative because a Help article is a set of
    instructions about those screens: calling a button something the app does
    not is worse than not writing the article. A Learn article explains a
    country's day-count rule and mostly never mentions the interface, so the
    same table starts matching ordinary prose instead. `Custom` is the clearest
    case: its generated plural `Customs` is border control in four articles,
    and enforcing the tracker preset's wording there would corrupt the
    sentence to satisfy a check. Brand and format names still have to survive
    in every section, so those two rules always run.
    """
    terms = list(glossary.get("terms", [])) if app_terms else []
    triggered = [
        term for term in terms
        if any(re.search(rf"\b{re.escape(form)}\b", english) for form in term["match"])
    ]

    # Accepted terms of every glossary entry, not just the triggered ones: a
    # word rejected for one concept is often the right word for another. The
    # table rejects 重複 for Overlap because it is reserved for Duplicate, and
    # rejects 時系列 for Timeline because it belongs to Chronological.
    every_accepted = {value for term in terms for value in term["accepted"]}

    for term in triggered:
        if any(value in translated for value in term["accepted"]):
            # The concept was translated correctly, so a rejected word on the
            # same page is almost always doing a different job: 履歴 inside
            # 旅行履歴 ("travel history") is not Timeline mistranslated, and the
            # guidelines themselves keep 滞在 for physical presence. Flagging
            # those buries the real signal, which is the accepted term being
            # absent entirely. That is what the branch below catches.
            continue
        problems.append(
            f"{label}: English uses {term['en']!r} but the translation has none of "
            f"{term['accepted']} (the app ships {term.get('app_string', term['accepted'][0])!r})"
        )
        for bad in term["forbidden"]:
            if bad not in translated:
                continue
            # A rejected form that only appears inside an accepted term is not
            # a defect: 税務上の居住 contains 居住, 海外滞在日数 contains 滞在.
            if any(bad in value and bad != value for value in every_accepted):
                continue
            problems.append(
                f"{label}: it uses {bad!r}, a rejected translation of {term['en']!r}; "
                f"use {term['accepted']}"
            )

    for name in glossary.get("verbatim", []):
        if re.search(rf"\b{re.escape(name)}\b", english) and name not in translated:
            problems.append(f"{label}: brand or format name {name!r} must survive untranslated")
    for bad in glossary.get("forbidden_always", []):
        if bad in translated:
            problems.append(f"{label}: {bad!r} - the brand stays in Latin script")


def slots(fragment: str) -> set[str]:
    return set(FIGURE_SLOT.findall(fragment)) | set(DEFERRED_SLOT.findall(fragment))


def check_structure(
    label: str,
    english: str,
    translated: str,
    locale: dict,
    available: set[str],
    problems: list[str],
) -> None:
    """Shape must survive translation, because a missing step is invisible."""
    for name, pattern in (
        ("<h2> sections", HEADING),
        ("<ol> lists", ORDERED_LIST),
        ("<li> items", LIST_ITEM),
        ("troubleshooting blocks", IF_NEEDED),
    ):
        expected = len(pattern.findall(english))
        actual = len(pattern.findall(translated))
        if expected != actual:
            problems.append(f"{label}: {expected} {name} in English, {actual} in the translation")

    if slots(english) != slots(translated):
        problems.append(
            f"{label}: screenshot slots differ - English {sorted(slots(english))}, "
            f"translation {sorted(slots(translated))}"
        )

    # Every number in the English must survive. Day counts, window lengths, and
    # visa thresholds are the highest-consequence content on the site, and a
    # dropped digit is invisible to a reader who cannot compare the two. The
    # test is one-directional on purpose: Japanese legitimately adds numbers,
    # writing "6月1日、6月2日、6月3日" where English writes "June 1 to June 3".
    english_numbers = Counter(NUMBER.findall(visible_text(FIGURES.sub(" ", english))))
    lost = english_numbers - Counter(NUMBER.findall(visible_text(FIGURES.sub(" ", translated))))
    if lost:
        problems.append(
            f"{label}: the translation drops number(s) present in English: {dict(lost)}"
        )

    def localize_href(href: str) -> str:
        """Localize the path and put the fragment back on the end."""
        path, sep, fragment = href.partition("#")
        return localized_route(path, locale, available) + sep + fragment

    expected_links = {localize_href(href) for href in INTERNAL_HREF.findall(english)}
    actual_links = set(INTERNAL_HREF.findall(translated))
    missing = expected_links - actual_links
    invented = actual_links - expected_links
    if missing:
        problems.append(f"{label}: translation drops internal links {sorted(missing)}")
    if invented:
        problems.append(f"{label}: translation invents internal links {sorted(invented)}")


def main() -> int:
    parse_args()
    problems: list[str] = []
    locales = load_locales()
    default = default_locale_code()
    strings = load_ui_strings()

    chrome_complete = {
        code
        for code, locale in locales.items()
        if locale.get("status") == "published" or locale.get("coverage") == "complete"
    }
    for key in sorted(strings):
        for code in sorted(chrome_complete):
            if not strings[key].get(code):
                problems.append(f"ui-strings.json: {key} has no {code} value")
        for code, value in strings[key].items():
            if key != "help.contact_body" and ('"' in value or "<" in value):
                problems.append(f"ui-strings.json: {key}:{code} contains markup or a quote")

    sources: dict[str, dict] = {}
    for path, key in (
        (ARTICLES_PATH, "articles"),
        (HUBS_PATH, "hubs"),
        (PAGES_PATH, "pages"),
    ):
        if path.exists():
            for record in json.loads(path.read_text(encoding="utf-8"))[key]:
                sources[str(record["path"])] = record

    for record in sources.values():
        fragment = (SOURCE_ROOT / str(record["content"])).read_text(encoding="utf-8")
        check_house_typography(str(record["path"]), visible_text(fragment), problems)

    glossaries: dict[str, dict] = {}
    if GLOSSARY_PATH.exists():
        glossaries = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))["locales"]

    checked = 0
    for code, locale in locales.items():
        if code == default or not locale.get("articles"):
            continue
        registry = SOURCE_ROOT / str(locale["articles"])
        if not registry.exists():
            continue
        data = json.loads(registry.read_text(encoding="utf-8"))
        overlays = (
            list(data.get("articles", []))
            + list(data.get("hubs", []))
            + list(data.get("pages", []))
        )
        # Pages this locale deliberately serves in English. Listing one is a
        # decision, not an escape hatch for work in progress: the completeness
        # check still covers every other page, and a stale entry here is an
        # error rather than a silent exemption.
        untranslated = {str(path) for path in locale.get("untranslated", [])}
        for source_path in sorted(untranslated - set(sources)):
            problems.append(
                f"{code}: untranslated lists {source_path}, which is not an English source"
            )
        if locale.get("coverage") == "complete":
            translated_sources = {str(entry["source"]) for entry in overlays}
            missing = sorted(set(sources) - translated_sources - untranslated)
            for source_path in missing:
                problems.append(f"{code}: complete locale is missing {source_path}")
        for source_path in sorted(untranslated & {str(entry["source"]) for entry in overlays}):
            problems.append(
                f"{code}: {source_path} is listed as untranslated but still has an overlay"
            )
        available = {route_for(str(entry["source"])) for entry in overlays}
        glossary = glossaries.get(code, {})
        for overlay in overlays:
            source_path = str(overlay["source"])
            source = sources.get(source_path)
            if source is None:
                problems.append(f"{code}: {source_path} has no English source record")
                continue
            english = (SOURCE_ROOT / str(source["content"])).read_text(encoding="utf-8")
            translated_path = SOURCE_ROOT / str(overlay["content"])
            if not translated_path.exists():
                problems.append(f"{code}: missing fragment {overlay['content']}")
                continue
            translated = translated_path.read_text(encoding="utf-8")
            label = f"{code}/{source_path}"
            # Checked here as well as in build_site.py, on purpose. A single
            # gate can be walked past by hand-editing the recorded hash; two
            # independent ones cannot, and this is the gate CI runs first.
            for field, current in (
                ("source_hash", source_hash(english)),
                ("source_meta_hash", meta_hash(source)),
            ):
                if str(overlay.get(field, "")) != current and not overlay.get("stale_ack"):
                    problems.append(
                        f"{label}: {field} is stale; the English source changed since this "
                        "was translated"
                    )
            prose = visible_text(translated)
            check_house_typography(label, prose, problems)
            if code == "ja":
                check_japanese_typography(label, prose, problems)
            if glossary:
                check_terminology(
                    label,
                    visible_text(english),
                    prose,
                    glossary,
                    problems,
                    app_terms=source_path.startswith("help/"),
                )
            check_structure(label, english, translated, locale, available, problems)
            checked += 1

    if problems:
        print("Translation checks failed:")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print(f"Checked {len(sources)} English fragments and {checked} translated pages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
