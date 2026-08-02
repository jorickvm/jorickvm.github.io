#!/usr/bin/env python3
"""Generate the privacy-preserving Help/Learn client-side search index."""

from __future__ import annotations

import argparse
import json
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "_site-src" / "data"
OUTPUT = ROOT / "assets" / "search-index.json"

class HeadingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_heading = False
        self.current: list[str] = []
        self.headings: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h1", "h2", "h3"}:
            self.in_heading = True
            self.current = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h1", "h2", "h3"} and self.in_heading:
            value = " ".join(" ".join(self.current).split())
            if value:
                self.headings.append(value)
            self.in_heading = False

    def handle_data(self, data: str) -> None:
        if self.in_heading:
            self.current.append(data)


def help_headings(record: dict[str, object]) -> list[str]:
    parser = HeadingParser()
    parser.feed((ROOT / "_site-src" / str(record["content"])).read_text(encoding="utf-8"))
    return parser.headings


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
            category = str(record.get("category", "trips-travel-days"))
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
                "keywords": sorted(
                    {
                        slug.replace("-", " "),
                        category.replace("-", " "),
                        jurisdiction.lower(),
                        *(str(value).lower() for value in record.get("search_synonyms", [])),
                        *(value.lower() for value in help_headings(record) if section == "help"),
                    }
                    - {""}
                ),
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
