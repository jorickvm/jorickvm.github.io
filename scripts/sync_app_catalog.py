#!/usr/bin/env python3
"""Snapshot the app's add-tracker catalogue into _site-src/data/app-catalog.json.

The Learn index shows each rule the way the app's preset cards do: the same
sections, filter pills, flags, titles and one-line rule descriptions, in every
language. The app owns that wording. Its test
`AtlasDaysTests/WebsiteCatalogExportTests` writes one JSON file per interface
language (`tools/website-catalog/catalog.<language>.json` in the app checkout;
how to run it is in that file); this script folds them into one committed
snapshot, the way `sync_glossary.py` snapshots terminology. CI cannot reach
the app repo, so the snapshot is what the build reads.

    python3 scripts/sync_app_catalog.py --app-repo ~/Projects/AtlasDays/AtlasDays

Articles name their preset with `app_preset` in `_site-src/data/articles.json`;
the few without one carry their own card in `_site-src/data/learn-cards.json`.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from locales import load_locales

SITE_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = SITE_ROOT / "_site-src" / "data" / "app-catalog.json"
DEFAULT_APP_REPO = Path.home() / "Projects" / "AtlasDays" / "AtlasDays"


def app_file(folder: Path, code: str) -> Path:
    """The export for a site locale: `de` reads catalog.de*.json, `pt` the
    app's pt-BR, `zh-Hant` its zh-Hant(-TW)."""
    matches = sorted(folder.glob(f"catalog.{code}*.json")) or sorted(folder.glob(f"catalog.{code.split('-')[0]}*.json"))
    if not matches:
        raise SystemExit(f"No app catalogue export for {code} in {folder}; run WebsiteCatalogExportTests in that language")
    return matches[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--app-repo", type=Path, default=DEFAULT_APP_REPO)
    parser.add_argument("--preview", action="store_true",
                        help="Fill languages not exported yet with English, for a local preview only; never commit the result.")
    args = parser.parse_args()
    folder = args.app_repo / "tools" / "website-catalog"
    codes = list(load_locales())
    sections: dict[str, dict] = {}
    presets: dict[str, dict] = {}
    for code in codes:
        try:
            source = app_file(folder, code)
        except SystemExit:
            if not args.preview:
                raise
            source = app_file(folder, "en")
        data = json.loads(source.read_text(encoding="utf-8"))
        for order, section in enumerate(data["sections"]):
            family = section["family"]
            entry = sections.setdefault(family, {"family": family, "order": order, "pill": {}, "title": {}})
            entry["pill"][code] = section["pill"]
            entry["title"][code] = section["title"]
            for rank, row in enumerate(section["entries"]):
                # The app orders each section in the reader's language, so the
                # position is kept per locale.
                preset = presets.setdefault(row["id"], {"family": family, "flag": row.get("flag", ""), "rank": {}, "title": {}, "line": {}})
                preset["rank"][code] = rank
                preset["title"][code] = row["title"]
                preset["line"][code] = row["line"]
    snapshot = {
        "generated_by": "scripts/sync_app_catalog.py from the app's WebsiteCatalogExportTests",
        "sections": sorted(sections.values(), key=lambda s: s["order"]),
        "presets": presets,
    }
    CATALOG_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(presets)} presets in {len(sections)} sections for {', '.join(codes)}.")


if __name__ == "__main__":
    main()
