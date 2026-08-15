#!/usr/bin/env python3
"""Snapshot AtlasDays product terminology into _site-src/data/glossary.json.

The authoritative terminology lives in the app repo: the shipped translations
in `Localizable.xcstrings` and the accepted-terminology tables in
`Docs/reference/translation-guidelines.md`. CI here cannot reach that repo, so
this writes a committed snapshot and records where every row came from.

Why the app catalog is the source rather than a hand-written glossary: a help
article is a set of instructions about the app's own screens. If an article
names a button in Japanese and the app calls it something else, the article is
worse than useless, and that mismatch is invisible to anyone who cannot read
Japanese. Deriving the glossary from the strings the app actually ships is the
only version of this check that stays true.

    python3 scripts/sync_glossary.py --app-repo ~/Projects/AtlasDays/AtlasDays
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from locales import default_locale_code, load_locales

SITE_ROOT = Path(__file__).resolve().parents[1]
GLOSSARY_PATH = SITE_ROOT / "_site-src" / "data" / "glossary.json"
DEFAULT_APP_REPO = Path.home() / "Projects" / "AtlasDays" / "AtlasDays"

# Brand, platform, and format names the guidelines keep unchanged in every
# language. A translated help page must still contain them verbatim.
VERBATIM = [
    "AtlasDays",
    "AtlasDays Pro",
    "Apple",
    "iOS",
    "iPhone",
    "iPad",
    "iCloud",
    "App Store",
    "SwiftData",
    "CSV",
    "PDF",
    "Flighty",
    "ESTA",
]

# Transliterations of the brand. It stays in Latin script in every language, so
# any of these appearing at all is a defect.
FORBIDDEN_ALWAYS = {
    "ja": ["アトラスデイズ", "アトラス・デイズ", "アトラスデイス"],
}

TABLE_HEADING = re.compile(r"^####\s+Accepted (\w+) terminology\s*$")
BACKTICKED = re.compile(r"`([^`]+)`")


def translated_locale_codes() -> list[str]:
    """Every non-English locale, in locales.json order.

    The default used to be a hardcoded `["ja"]`, from when Japanese was the only
    translation. Because a run rewrites the whole snapshot, a bare invocation
    after Dutch shipped would have quietly deleted Dutch terminology and left
    `check_translations.py` enforcing nothing on `/nl/help/`. Deriving it means
    adding a language stays a data change.
    """
    default = default_locale_code()
    return [code for code in load_locales() if code != default]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-repo", type=Path, default=DEFAULT_APP_REPO)
    parser.add_argument("--locale", action="append", default=None, help="Locale code; repeatable.")
    parser.add_argument("--check", action="store_true", help="Fail if the snapshot is stale")
    return parser.parse_args()


def catalog_values(app_repo: Path, code: str) -> dict[str, str]:
    """English catalog key -> shipped translation, across every app catalog."""
    values: dict[str, str] = {}
    for relative in (
        "AtlasDays/Localizable.xcstrings",
        "AtlasDaysWidgets/Localizable.xcstrings",
        "AtlasDays/InfoPlist.xcstrings",
    ):
        path = app_repo / relative
        if not path.exists():
            continue
        for key, entry in json.loads(path.read_text(encoding="utf-8"))["strings"].items():
            unit = entry.get("localizations", {}).get(code, {}).get("stringUnit", {})
            if unit.get("state") == "translated" and unit.get("value"):
                values.setdefault(key, str(unit["value"]))
    return values


def terminology_rows(guidelines: str, language: str) -> list[tuple[str, str, str]]:
    """(source term, accepted, rejected) from a language's accepted-terminology table."""
    rows: list[tuple[str, str, str]] = []
    collecting = False
    for line in guidelines.splitlines():
        heading = TABLE_HEADING.match(line)
        if heading:
            collecting = heading.group(1).lower() == language.lower()
            continue
        if collecting and line.startswith("###"):
            break
        if not collecting or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4 or cells[0] in {"Source", "---"} or set(cells[0]) <= {"-", " "}:
            continue
        rows.append((cells[0], cells[1], cells[3]))
    return rows


def match_forms(term: str) -> list[str]:
    """English spellings of a term that should trigger the rule."""
    forms = {term}
    if " " not in term and term[-1:].isalpha():
        forms.add(term + "s" if not term.endswith("s") else term)
    return sorted(forms, key=len, reverse=True)


def build_locale(app_repo: Path, code: str, language: str) -> dict[str, object]:
    guidelines = (app_repo / "Docs" / "reference" / "translation-guidelines.md").read_text(encoding="utf-8")
    catalog = catalog_values(app_repo, code)
    terms: list[dict[str, object]] = []
    for source, accepted_cell, rejected_cell in terminology_rows(guidelines, language):
        accepted = [part.strip() for part in accepted_cell.split(" / ") if part.strip()]
        accepted = [part for part in accepted if part and not part.startswith("%")]
        if not accepted:
            continue
        rejected = [
            token.strip()
            for token in BACKTICKED.findall(rejected_cell)
            if token.strip() and not token.strip().startswith("%")
        ]
        entry: dict[str, object] = {
            "en": source,
            "match": match_forms(source),
            "accepted": accepted,
            "forbidden": rejected,
        }
        shipped = catalog.get(source)
        if shipped:
            entry["app_string"] = shipped
            if shipped not in accepted:
                # The table and the shipped app disagree. The app wins, because
                # it is what the reader sees on screen.
                entry["accepted"] = [shipped] + accepted
                entry["app_disagrees_with_table"] = True
        terms.append(entry)
    return {
        "terms": terms,
        "verbatim": [name for name in VERBATIM if name],
        "forbidden_always": FORBIDDEN_ALWAYS.get(code, []),
        "catalog_size": len(catalog),
    }


def build(app_repo: Path, codes: list[str]) -> dict[str, object]:
    names = {"ja": "Japanese", "nl": "Dutch", "de": "German", "es": "Spanish",
             "fr": "French", "ru": "Russian", "uk": "Ukrainian"}
    return {
        "schema_version": 1,
        "_comment": [
            "GENERATED by scripts/sync_glossary.py. Do not hand-edit.",
            "The app repo is authoritative: Docs/reference/translation-guidelines.md",
            "for the accepted terms and rejected alternatives, Localizable.xcstrings",
            "for the strings the app actually ships. Re-run the script when either",
            "changes, or a help article can drift from the app's own wording.",
        ],
        "generated_from": {
            "guidelines": "Docs/reference/translation-guidelines.md (accepted terminology tables)",
            "catalogs": [
                "AtlasDays/Localizable.xcstrings",
                "AtlasDaysWidgets/Localizable.xcstrings",
                "AtlasDays/InfoPlist.xcstrings",
            ],
        },
        "locales": {code: build_locale(app_repo, code, names.get(code, code)) for code in codes},
    }


def main() -> int:
    args = parse_args()
    app_repo = args.app_repo.expanduser()
    if not app_repo.exists():
        print(f"App repo not found: {app_repo}")
        return 1
    codes = args.locale or translated_locale_codes()
    payload = json.dumps(build(app_repo, codes), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        current = GLOSSARY_PATH.read_text(encoding="utf-8") if GLOSSARY_PATH.exists() else ""
        if current != payload:
            print("glossary.json is stale; re-run scripts/sync_glossary.py")
            return 1
        print(f"Checked glossary for {', '.join(codes)}.")
        return 0
    GLOSSARY_PATH.write_text(payload, encoding="utf-8")
    total = sum(len(entry["terms"]) for entry in build(app_repo, codes)["locales"].values())
    print(f"Wrote glossary for {', '.join(codes)}: {total} terms.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
