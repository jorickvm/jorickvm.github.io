#!/usr/bin/env python3
"""Keep Help screenshot slots in sync with captured WebP files.

Each help record in _site-src/data/articles.json declares its slots in
"screenshot_slots". In the content fragment a slot is either a rendered
figure (its WebP exists at assets/article-images/help/<slug>/<key>.webp) or a
deferred marker:

    <!-- SCREENSHOT_DEFERRED: key | scenario -->

Capturing a screenshot stays "save the file, rerun this script": the write
mode swaps markers to figures (and refreshes a figure whose file changed
shape), then build_site.py re-renders the pages. --check fails when any
fragment disagrees with the files on disk; CI runs it so a landed capture
cannot be forgotten half-published.

The figure markup and the width rule are carried over verbatim from the
retired rebuild_help_center.py: intrinsic size is read from the WebP header,
and a capture wider than the phone frame width in screenshots.json renders
with the landscape class instead of the portrait width cap.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from locales import default_locale_code, load_locales

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "_site-src"
DATA = SOURCE / "data"
CONTENT = SOURCE / "content" / "help"


def phone_capture_width() -> int:
    try:
        manifest = json.loads((DATA / "screenshots.json").read_text())
        return int(manifest["device"]["target_width"])
    except (OSError, ValueError, KeyError, TypeError):
        return 1320


PHONE_WIDTH = phone_capture_width()


def webp_dimensions(path: Path) -> tuple[int, int] | None:
    try:
        data = path.read_bytes()[:32]
    except OSError:
        return None
    if len(data) < 30 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None
    chunk = data[12:16]
    if chunk == b"VP8X":
        width = int.from_bytes(data[24:27], "little") + 1
        height = int.from_bytes(data[27:30], "little") + 1
        return width, height
    if chunk == b"VP8 ":
        width = int.from_bytes(data[26:28], "little") & 0x3FFF
        height = int.from_bytes(data[28:30], "little") & 0x3FFF
        return width, height
    return None


def image_relpath(slug: str, key: str, code: str | None = None) -> str:
    return (
        f"assets/article-images/{code}/help/{slug}/{key}.webp"
        if code
        else f"assets/article-images/help/{slug}/{key}.webp"
    )


def resolve_image(slug: str, key: str, code: str | None) -> tuple[str, bool]:
    """The locale's own capture when it exists, otherwise the English one.

    Per file rather than per page, so a language can recapture its screens
    gradually instead of all at once.
    """
    if code:
        localized = image_relpath(slug, key, code)
        if (ROOT / localized).exists():
            return localized, True
    english = image_relpath(slug, key)
    return english, (ROOT / english).exists()


def figure_markup(slug: str, slot: dict[str, str], alt_text: str, code: str | None = None) -> str:
    relpath, _ = resolve_image(slug, str(slot["key"]), code)
    alt = str(alt_text).replace('"', "&quot;")
    size = webp_dimensions(ROOT / relpath)
    dimensions = f' width="{size[0]}" height="{size[1]}"' if size else ""
    tablet = " help-shot-landscape" if size and size[0] > PHONE_WIDTH else ""
    return (
        f'<figure class="help-shot help-shot-{slot["crop"]}{tablet}">'
        f'<img src="/{relpath}" alt="{alt}"{dimensions} loading="lazy" decoding="async" />'
        f"</figure>"
    )


def deferred_marker(slot: dict[str, str]) -> str:
    return f"<!-- SCREENSHOT_DEFERRED: {slot['key']} | {slot['scenario']} -->"


def slot_pattern(slug: str, slot: dict[str, str], code: str | None = None) -> re.Pattern[str]:
    """Match whichever form the slot currently takes in the fragment.

    Both image paths are accepted so a fragment can move between the English
    fallback and a locale capture without a hand edit.
    """
    sources = [re.escape("/" + image_relpath(slug, str(slot["key"])))]
    if code:
        sources.insert(0, re.escape("/" + image_relpath(slug, str(slot["key"]), code)))
    figure = (
        r'<figure class="help-shot[^"]*">'
        + r'<img src="(?:'
        + "|".join(sources)
        + r')"[^>]*/></figure>'
    )
    marker = re.escape(f"<!-- SCREENSHOT_DEFERRED: {slot['key']} | ") + r"[^>]*-->"
    return re.compile(f"(?:{figure})|(?:{marker})")


def load_translations() -> dict[str, dict[str, dict]]:
    """Overlay records per locale, keyed by English source path."""
    loaded: dict[str, dict[str, dict]] = {}
    default = default_locale_code()
    for code, locale in load_locales().items():
        registry = locale.get("articles")
        if code == default or not registry or not (SOURCE / str(registry)).exists():
            continue
        data = json.loads((SOURCE / str(registry)).read_text(encoding="utf-8"))
        loaded[code] = {str(entry["source"]): entry for entry in data.get("articles", [])}
    return loaded


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail instead of rewriting stale fragments")
    args = parser.parse_args()

    articles = json.loads((DATA / "articles.json").read_text(encoding="utf-8"))["articles"]
    translations = load_translations()
    errors: list[str] = []
    stale: list[str] = []
    checked = 0
    for article in articles:
        slots = article.get("screenshot_slots")
        if article.get("section") != "help" or not slots:
            continue
        source_path = str(article["path"])
        slug = Path(source_path).stem
        # The English fragment, then every translation of it. A translated
        # fragment is generated output too: leaving it out let a recapture
        # update the English dimensions and silently strand the translation.
        targets: list[tuple[str | None, Path, dict[str, str]]] = [(None, CONTENT / f"{slug}.html", {})]
        for code, overlays in translations.items():
            overlay = overlays.get(source_path)
            if overlay:
                targets.append((code, SOURCE / str(overlay["content"]), overlay.get("screenshot_alt", {})))

        for code, fragment_path, alts in targets:
            label = slug if code is None else f"{code}/{slug}"
            if not fragment_path.exists():
                errors.append(f"{label}: fragment missing at {fragment_path.relative_to(ROOT)}")
                continue
            text = fragment_path.read_text(encoding="utf-8")
            rebuilt = text
            for slot in slots:
                checked += 1
                alt_text = alts.get(str(slot["key"]), slot.get("alt", ""))
                _, exists = resolve_image(slug, str(slot["key"]), code)
                expected = (
                    figure_markup(slug, slot, alt_text, code) if exists else deferred_marker(slot)
                )
                matches = slot_pattern(slug, slot, code).findall(rebuilt)
                if len(matches) != 1:
                    errors.append(f"{label}: slot {slot['key']!r} appears {len(matches)} times in the fragment")
                    continue
                if matches[0] != expected:
                    rebuilt = rebuilt.replace(matches[0], expected)
            if rebuilt != text:
                if args.check:
                    stale.append(fragment_path.relative_to(ROOT).as_posix())
                else:
                    fragment_path.write_text(rebuilt, encoding="utf-8")
                    print(f"Updated {fragment_path.relative_to(ROOT)}")

    if errors:
        print("Help screenshot slots are inconsistent:\n  " + "\n  ".join(errors))
        return 1
    if stale:
        print(
            "Fragments out of sync with captured screenshots; run scripts/sync_help_screenshots.py"
            " and scripts/build_site.py:\n  " + "\n  ".join(stale)
        )
        return 1
    print(f"Checked {checked} screenshot slots." if args.check else f"All {checked} screenshot slots in sync.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
