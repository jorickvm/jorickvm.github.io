#!/usr/bin/env python3
"""Verify every Learn slug the AtlasDays app links to exists in learn/.

The iOS app's tracker editor links each curated preset to its Learn article
via the slug map in `TrackerLearnLinks.swift` (app repo). Those URLs are
shipped in App Store builds and cannot be taken back, so a slug rename or an
article merge on this site silently 404s inside the app. This script reads
the app's map and fails when any slug no longer resolves to
`learn/<slug>.html`.

Those URLs are also the language hook. Each generated page carries a map of
its own translations and redirects when it is opened with `?lang=<code>`, so
the app keeps one URL per preset and appends its interface language, exactly
as it already does for the /app/ alias pages. A slug with no translation has
no entry in its map and stays English, which is why this check still only
has to prove the English article exists.

Local-only guard: the app repo is private, so CI cannot run this. It is
deliberately NOT wired into site-audit.yml. Run it before renaming, merging,
or deleting any Learn article, and as part of the pre-release habit:

    python3 scripts/check_app_learn_links.py

Exits 0 with a skip message when the app repo is absent (e.g. a machine
that only has the website checkout).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_APP_FILE = (
    Path.home()
    / "Projects/AtlasDays/AtlasDays/AtlasDays/Trackers/TrackerLearnLinks.swift"
)

# The slug map is the dictionary literal assigned to slugsByPresetID; only
# parse inside it (the same quoted-pair shape appears elsewhere in the file,
# e.g. in a ternary inside the matcher).
MAP_RE = re.compile(
    r"slugsByPresetID:\s*\[String:\s*String\]\s*=\s*\[(.*?)\n    \]",
    re.DOTALL,
)
# One map entry per line: "preset-id": "article-slug",
ENTRY_RE = re.compile(r'"([a-z0-9-]+)"\s*:\s*"([a-z0-9-]+)"\s*,')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--app-file",
        type=Path,
        default=DEFAULT_APP_FILE,
        help="Path to TrackerLearnLinks.swift (default: the main app checkout)",
    )
    args = parser.parse_args()

    if not args.app_file.exists():
        print(f"skip: app repo not found at {args.app_file}")
        return 0

    source = args.app_file.read_text(encoding="utf-8")
    map_block = MAP_RE.search(source)
    if not map_block:
        print(f"error: slugsByPresetID dictionary not found in {args.app_file}")
        return 1
    entries = ENTRY_RE.findall(map_block.group(1))
    if not entries:
        print(f"error: no map entries parsed from {args.app_file}")
        return 1

    missing = [
        (preset_id, slug)
        for preset_id, slug in entries
        if not (ROOT / "learn" / f"{slug}.html").exists()
    ]
    if missing:
        print(f"error: {len(missing)} app-linked slugs have no article:")
        for preset_id, slug in missing:
            print(f"  {preset_id} -> learn/{slug}.html")
        return 1

    linked = {slug for _, slug in entries}
    unlinked = sorted(
        p.stem
        for p in (ROOT / "learn").glob("*.html")
        if p.stem not in linked and p.stem != "index"
    )
    print(f"OK: all {len(entries)} app-linked slugs resolve to learn/ articles.")
    if unlinked:
        print(f"note: {len(unlinked)} learn articles have no app link (informational).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
