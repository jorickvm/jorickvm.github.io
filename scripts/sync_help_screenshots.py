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

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "_site-src" / "data"
CONTENT = ROOT / "_site-src" / "content" / "help"


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


def figure_markup(slug: str, slot: dict[str, str]) -> str:
    relpath = f"assets/article-images/help/{slug}/{slot['key']}.webp"
    alt = str(slot["alt"]).replace('"', "&quot;")
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


def slot_pattern(slug: str, slot: dict[str, str]) -> re.Pattern[str]:
    """Match whichever form the slot currently takes in the fragment."""
    figure = (
        r'<figure class="help-shot[^"]*">'
        + r"<img src=\""
        + re.escape(f"/assets/article-images/help/{slug}/{slot['key']}.webp")
        + r'"[^>]*/></figure>'
    )
    marker = re.escape(f"<!-- SCREENSHOT_DEFERRED: {slot['key']} | ") + r"[^>]*-->"
    return re.compile(f"(?:{figure})|(?:{marker})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail instead of rewriting stale fragments")
    args = parser.parse_args()

    articles = json.loads((DATA / "articles.json").read_text(encoding="utf-8"))["articles"]
    errors: list[str] = []
    stale: list[str] = []
    for article in articles:
        slots = article.get("screenshot_slots")
        if article.get("section") != "help" or not slots:
            continue
        slug = Path(str(article["path"])).stem
        fragment_path = CONTENT / f"{slug}.html"
        if not fragment_path.exists():
            errors.append(f"{slug}: fragment missing at {fragment_path.relative_to(ROOT)}")
            continue
        text = fragment_path.read_text(encoding="utf-8")
        rebuilt = text
        for slot in slots:
            expected = (
                figure_markup(slug, slot)
                if (ROOT / f"assets/article-images/help/{slug}/{slot['key']}.webp").exists()
                else deferred_marker(slot)
            )
            matches = slot_pattern(slug, slot).findall(rebuilt)
            if len(matches) != 1:
                errors.append(f"{slug}: slot {slot['key']!r} appears {len(matches)} times in the fragment")
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
    total = sum(len(a.get("screenshot_slots", [])) for a in articles if a.get("section") == "help")
    print(f"Checked {total} screenshot slots." if args.check else f"All {total} screenshot slots in sync.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
