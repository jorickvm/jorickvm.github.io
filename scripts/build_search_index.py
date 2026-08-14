#!/usr/bin/env python3
"""Generate the privacy-preserving Help/Learn client-side search index."""

from __future__ import annotations

import argparse
import json
from html.parser import HTMLParser
from pathlib import Path

from locales import default_locale_code, load_locales, route_for


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


def translated_entries(
    sources: dict[str, dict],
    editorial: dict[str, dict],
    clusters: dict[str, dict],
) -> list[dict[str, object]]:
    """One search entry per translated page, tagged with its language.

    The index stays a single file: 100-odd entries do not justify a second
    fetch, and search.js already filters client-side.

    Everything except the title, description, and synonyms is taken from the
    English record, exactly as the rendered page is: a translation supplies
    prose, so it cannot land in a different category, claim a different
    jurisdiction, or promote itself to a pillar.
    """
    entries: list[dict[str, object]] = []
    default = default_locale_code()
    for code, locale in load_locales().items():
        registry = locale.get("articles")
        if code == default or not registry or not (DATA.parent / str(registry)).exists():
            continue
        data = json.loads((DATA.parent / str(registry)).read_text(encoding="utf-8"))
        for overlay in list(data.get("articles", [])) + list(data.get("hubs", [])):
            source = sources.get(str(overlay["source"]))
            if source is None:
                # A translated hub. Hubs are the search surface, not a result
                # in it, so English has no entry for them either.
                continue
            path = str(overlay["source"])
            section = str(source.get("section", "help"))
            slug = Path(path).stem
            if section == "help":
                category = str(source.get("category", "trips-travel-days"))
                jurisdiction = ""
                pillar = False
            else:
                category = str(editorial[path]["rule_category"])
                jurisdiction = str(editorial[path]["jurisdiction"])
                pillar = clusters[path]["relationship"] == "pillar"
            entries.append(
                {
                    "section": section,
                    "lang": code,
                    "category": category,
                    "title": str(overlay["headline"]),
                    "description": str(overlay["description"]),
                    # The English jurisdiction name is a Latin-script place
                    # name in the index either way; the translated one rides in
                    # through the synonyms.
                    "jurisdiction": jurisdiction,
                    "keywords": sorted(
                        {
                            slug.replace("-", " "),
                            category.replace("-", " "),
                            jurisdiction.lower(),
                            # English aliases stay searchable: a reader who
                            # knows the English term on their paperwork has no
                            # other route to the page.
                            *(str(value).lower() for value in source.get("search_synonyms", [])),
                            *(str(value).lower() for value in overlay.get("search_synonyms", [])),
                            *(value.lower() for value in help_headings(overlay) if section == "help"),
                        }
                        - {""}
                    ),
                    "url": f"/{code}" + route_for(path),
                    "pillar": pillar,
                }
            )
    return entries


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
        title = str(record["title"]).replace(" – AtlasDays Help Center", "").replace(" – AtlasDays", "")
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
    entries.extend(translated_entries({str(r["path"]): r for r in articles}, editorial, clusters))
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
