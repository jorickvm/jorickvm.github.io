#!/usr/bin/env python3
"""Put the library hub's place tiles in the locale's own alphabetical order.

_site-src/content/<code>/hubs/learn-index.html is hand-authored per locale, not
generated, so its tiles were translated in place and kept the English running
order: every locale displayed translated names in English alphabetical
positions, with Chipre between Colorado and Chequia in Spanish and Tsjechië
after Cyprus in Dutch. That is the defect
TRANSLATION_GUIDELINES-web.md section 7 records for the residency tables, which
build_residency_hub.py fixes by sorting on the locale's own names; because this
hub is written by hand rather than generated, the fix never reached it.

This script only reorders whole <div class="hub-tile"> blocks inside
<div class="hub-places">. It never edits a tile, so the link set, the
hub-key spans and the tile count come out unchanged and check_translations.py
sees the same document. The general-guides tiles under <div class="hub-topics">
are left alone: that section is ordered editorially, not alphabetically.

Ordering lives in hub_collation, shared with build_residency_hub.py, so a name
lands in the same place in both hubs.

    python3 scripts/build_hub_tile_order.py            # reorder in place
    python3 scripts/build_hub_tile_order.py --check    # fail if out of order

With --check this is a guard rather than a build step: the fragment is
hand-edited, so nothing else would notice the order regressing when a place is
added.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hub_collation import sort_key, unresolved  # noqa: E402
from locales import load_locales  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = ROOT / "_site-src"
HUB_FILE = "learn-index.html"

# Anchored on the exact indentation the fragments use, so a nested <div> inside
# a tile cannot be mistaken for the end of one. A file that does not match this
# shape is reported rather than rewritten -- see tiles_of.
PLACES = re.compile(
    r'(?<=<div class="hub-places">\n).*?(?=^        </div>\n)',
    re.DOTALL | re.MULTILINE,
)
TILE = re.compile(
    r'^          <div class="hub-tile".*?^          </div>\n',
    re.DOTALL | re.MULTILINE,
)
NAME = re.compile(r'<span class="hub-tile-name">([^<]*)</span>')


def hub_targets():
    """(locale code, fragment path) for every locale that has this hub."""
    for code, locale in load_locales().items():
        path = SOURCE_ROOT / str(locale.get("content_prefix", "content")) / "hubs" / HUB_FILE
        if path.exists():
            yield code, path


def tiles_of(path: Path) -> tuple[str, re.Match, list[str]]:
    """The fragment, its hub-places span, and the tile blocks filling it.

    The tiles must account for every character of the section. Reordering a
    partial parse would silently drop whatever the regex failed to claim, so a
    fragment whose markup has drifted from this shape stops the script instead.
    """
    html = path.read_text(encoding="utf-8")
    section = PLACES.search(html)
    if not section:
        raise SystemExit(f"{path}: no <div class=\"hub-places\"> section")
    tiles = TILE.findall(section.group(0))
    if "".join(tiles) != section.group(0):
        raise SystemExit(f"{path}: hub-places holds markup that is not a hub-tile block")
    return html, section, tiles


def name_of(tile: str) -> str:
    match = NAME.search(tile)
    if not match:
        raise SystemExit(f"A hub tile has no hub-tile-name span:\n{tile}")
    return match.group(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if tiles are out of order")
    args = parser.parse_args()

    out_of_order, seen = [], 0
    for code, path in hub_targets():
        seen += 1
        html, section, tiles = tiles_of(path)
        names = [name_of(t) for t in tiles]
        blocked = unresolved(names, code)
        if blocked:
            # A Japanese name written in kanji has no order until someone
            # supplies its reading, and guessing one silently mis-sorts the
            # hub. One line in hub_collation.JAPANESE_READINGS fixes it.
            raise SystemExit(
                f"No {code} reading for: {', '.join(blocked)}\n"
                "  Add it to JAPANESE_READINGS in scripts/hub_collation.py."
            )
        ordered = sorted(tiles, key=lambda t: sort_key(name_of(t), code))
        rel = path.relative_to(ROOT).as_posix()
        if ordered == tiles:
            print(f"{rel} already in {code} order ({len(tiles)} places).")
            continue
        moved = sum(1 for a, b in zip(names, [name_of(t) for t in ordered]) if a != b)
        if args.check:
            out_of_order.append(f"{rel}: {moved} of {len(tiles)} places sit in the wrong place")
            continue
        rebuilt = html[: section.start()] + "".join(ordered) + html[section.end() :]
        path.write_text(rebuilt, encoding="utf-8")
        print(f"Wrote {rel} with {len(tiles)} places in {code} order ({moved} moved).")

    if out_of_order:
        print(
            "Library hub tiles are not in the locale's alphabetical order; run "
            "scripts/build_hub_tile_order.py:\n  " + "\n  ".join(out_of_order)
        )
        return 1
    if args.check:
        print(f"Checked place-tile order in {seen} library hub fragments.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
