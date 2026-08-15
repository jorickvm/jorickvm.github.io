#!/usr/bin/env python3
"""Regenerate the tax-residency hub tables from articles.json.

Hub rows come from the learn records in _site-src/data/articles.json that
carry a "residency" object ("group" picks the hub). The hub fragments keep
hand-written chrome (hero, search box, CTA) and two machine-generated regions
marked by HTML comments:

    <!-- HUB_TABLE_START --> ... <!-- HUB_TABLE_END -->
    <!-- HUB_COUNT_START -->N<!-- HUB_COUNT_END -->

This script fills those regions in the _site-src fragment, not in the rendered
page. build_site.py renders the page from that fragment, so writing the page
here would be undone by the next site build -- which is exactly how the hub
once lost ten countries. Adding a country means adding the article record
(with its "residency" object) to articles.json, then:

    python3 scripts/build_residency_hub.py && python3 scripts/build_site.py

Every locale gets the same treatment. The fragment list is derived from
locales.json rather than hardcoded, so a new language is covered the moment its
hub fragment exists and nobody has to remember this script. A translated hub
keeps its own place names and cell wording: the row set, order, links, flags
and count are regenerated from the data, while the translated strings are
carried across by slug. A row with no translation yet is emitted in English and
reported, so adding a country fails the check in every locale that has not
caught up instead of drifting quietly.

With --check, verifies the fragments match what the data would generate and
that every residency-tagged record has its rendered page on disk.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from locales import default_locale_code, load_locales  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "_site-src" / "data" / "articles.json"
SOURCE_ROOT = ROOT / "_site-src"
HUB_FILES = [
    ("countries", "learn-tax-residency-by-country.html"),
    ("us_states", "learn-us-state-tax-residency.html"),
]

# Whitespace-tolerant on purpose: a hand-derived translated table will not match
# this script's exact formatting, and a regex that quietly fails to match reads
# every row as untranslated and overwrites the translation with English.
ROW = re.compile(
    r'<tr class="hub-row" data-name="(?P<data_name>[^"]*)" data-href="[^"]*?/(?P<slug>[^/"]+)">.*?'
    r'<a href="[^"]*">(?P<name>[^<]*)</a>\s*</td>\s*'
    r'<td>(?P<threshold>[^<]*)</td>\s*<td>(?P<window>[^<]*)</td>',
    re.DOTALL,
)


def hub_targets(filename: str):
    """(locale, fragment path) for every locale whose hub fragment exists."""
    for code, locale in load_locales().items():
        path = SOURCE_ROOT / str(locale.get("content_prefix", "content")) / "hubs" / filename
        if path.exists():
            yield code, locale, path


def existing_rows(html: str) -> dict[str, dict]:
    """Translated cells already in a fragment, keyed by article slug."""
    return {m.group("slug"): m.groupdict() for m in ROW.finditer(html)}


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_table(entries: list[dict], locale: dict, existing: dict[str, dict]) -> tuple[str, list[str]]:
    """The table body for one locale, plus the slugs still awaiting translation.

    Sort order follows the locale's own names, because a table presented as
    alphabetical that is not alphabetical in the reader's language reads as
    broken.
    """
    code = str(locale["code"])
    is_default = code == default_locale_code()
    prefix = "" if is_default else str(locale.get("route_prefix", ""))
    # English keeps the relative asset path it has always used; a translated
    # fragment renders one directory deeper, so it needs a root-absolute one.
    flag_base = "../assets/flags/" if is_default else "/assets/flags/"

    prepared, untranslated = [], []
    for e in entries:
        slug = str(e["slug"])
        prior = existing.get(slug)
        if is_default or prior is None:
            if not is_default:
                untranslated.append(slug)
            name = esc(str(e["name"]))
            data_name, threshold, window = name.lower(), esc(str(e["threshold"])), esc(str(e["windowLabel"]))
        else:
            name, data_name = prior["name"], prior["data_name"]
            threshold, window = prior["threshold"], prior["window"]
        prepared.append((name, data_name, threshold, window, str(e["code"]), slug))

    rows = []
    for name, data_name, threshold, window, flag, slug in sorted(prepared, key=lambda r: r[0].lower()):
        href = f"{prefix}/learn/{slug}"
        rows.append(
            f'        <tr class="hub-row" data-name="{data_name}" data-href="{href}">\n'
            f'          <td class="hub-td-country"><img class="hub-row-flag" '
            f'src="{flag_base}{flag}.png" alt="" width="30" height="22" loading="lazy" /> '
            f'<a href="{href}">{name}</a></td>\n'
            f'          <td>{threshold}</td>\n'
            f'          <td>{window}</td>\n'
            f'          <td class="hub-td-go"><span aria-hidden="true">&rarr;</span></td>\n'
            f'        </tr>'
        )
    return "\n".join(rows), untranslated


def replace_region(html: str, start: str, end: str, body: str) -> str:
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    return pattern.sub(f"{start}\n{body}\n{end}", html)


def load_entries() -> dict[str, list[dict]]:
    articles = json.loads(DATA.read_text(encoding="utf-8"))["articles"]
    groups: dict[str, list[dict]] = {}
    errors = []
    for article in articles:
        residency = article.get("residency")
        if not residency:
            continue
        path = str(article["path"])
        if not (ROOT / path).exists():
            errors.append(f"{path}: residency-tagged record has no rendered page on disk")
        entry = dict(residency)
        entry["slug"] = Path(path).stem
        groups.setdefault(str(residency["group"]), []).append(entry)
    if errors:
        raise SystemExit("Invalid residency records:\n  " + "\n  ".join(errors))
    return groups


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if fragments do not match the data")
    args = parser.parse_args()

    groups = load_entries()
    stale, missing_translation, seen = [], [], 0
    for key, filename in HUB_FILES:
        entries = groups.get(key, [])
        if not entries:
            raise SystemExit(f"No residency entries for group {key!r} in {DATA.relative_to(ROOT)}")
        for code, locale, hub_path in hub_targets(filename):
            seen += 1
            html = hub_path.read_text(encoding="utf-8")
            body, untranslated = build_table(entries, locale, existing_rows(html))
            rebuilt = replace_region(html, "<!-- HUB_TABLE_START -->", "<!-- HUB_TABLE_END -->", body)
            rebuilt = re.sub(
                r"<!-- HUB_COUNT_START -->.*?<!-- HUB_COUNT_END -->",
                f"<!-- HUB_COUNT_START -->{len(entries)}<!-- HUB_COUNT_END -->",
                rebuilt,
                flags=re.DOTALL,
            )
            rel = hub_path.relative_to(ROOT).as_posix()
            for slug in untranslated:
                missing_translation.append(f"{rel}: {slug} has no {code} row yet, English used")
            if args.check:
                if rebuilt != html:
                    stale.append(rel)
            elif rebuilt != html:
                hub_path.write_text(rebuilt, encoding="utf-8")
                print(f"Wrote {rel} with {len(entries)} entries.")
            else:
                print(f"{rel} already current ({len(entries)} entries).")

    if stale:
        print("Hub fragments are stale; run scripts/build_residency_hub.py:\n  " + "\n  ".join(stale))
        return 1
    if missing_translation:
        # Deliberately an error, not a warning. A hub row is the one place a
        # missing translation looks like finished work: the table still renders,
        # the link still resolves, and only a reader of that language can see
        # that one row is in English.
        print("Hub rows still need translating:\n  " + "\n  ".join(missing_translation))
        return 1
    if args.check:
        total = sum(len(v) for v in groups.values())
        print(f"Checked {seen} hub fragments across every locale against {total} residency records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
