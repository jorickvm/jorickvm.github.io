#!/usr/bin/env python3
"""Generate the privacy-preserving Help/Learn client-side search index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "_site-src" / "data"
OUTPUT = ROOT / "assets" / "search-index.json"

HELP_CATEGORIES = {
    "getting-started": "setup-trips", "timeline-and-calendar": "setup-trips", "history-and-import": "setup-trips",
    "photo-import": "imports", "csv-import": "imports", "flighty-import": "imports",
    "dashboard-and-map": "trackers-counts", "trackers-and-limits": "trackers-counts",
    "export-and-reports": "reports", "privacy-location-and-sync": "privacy-sync",
    "icloud-sync-and-restore": "privacy-sync", "atlasdays-pro": "pro-widgets", "widgets": "pro-widgets",
}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def description(record: dict[str, object]) -> str:
    return next((str(meta["content"]) for meta in record.get("meta", []) if meta.get("name") == "description"), "")


def route(path: str) -> str:
    clean = path.removesuffix("index.html").removesuffix(".html")
    return "/" + clean


def build() -> dict[str, object]:
    articles = json.loads((DATA / "articles.json").read_text(encoding="utf-8"))["articles"]
    editorial = {item["path"]: item for item in json.loads((DATA / "editorial.json").read_text(encoding="utf-8"))["articles"]}
    clusters = {item["path"]: item for item in json.loads((DATA / "content-clusters.json").read_text(encoding="utf-8"))["clusters"]}
    entries = []
    for record in articles:
        path = str(record["path"])
        section = str(record["section"])
        slug = Path(path).stem
        title = str(record["title"]).replace(" — AtlasDays Help Center", "").replace(" — AtlasDays", "")
        if section == "help":
            category = HELP_CATEGORIES.get(slug, "setup-trips")
            jurisdiction = ""
            pillar = False
        else:
            governance = editorial[path]
            cluster = clusters[path]
            category = str(governance["rule_category"])
            jurisdiction = str(governance["jurisdiction"])
            pillar = cluster["relationship"] == "pillar"
        entries.append(
            {
                "section": section,
                "category": category,
                "title": title,
                "description": description(record),
                "jurisdiction": jurisdiction,
                "keywords": sorted({slug.replace("-", " "), category.replace("-", " "), jurisdiction.lower()} - {""}),
                "url": route(path),
                "pillar": pillar,
            }
        )
    return {"schema_version": 1, "generated_by": "scripts/build_search_index.py", "entries": entries}


def main() -> int:
    options = arguments()
    rendered = json.dumps(build(), ensure_ascii=False, separators=(",", ":")) + "\n"
    if options.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            print("assets/search-index.json is stale")
            return 1
        print(f"Checked {len(build()['entries'])} search entries.")
        return 0
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Built {len(build()['entries'])} search entries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
