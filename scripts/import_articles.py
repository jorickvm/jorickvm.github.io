#!/usr/bin/env python3
"""One-time importer for moving current articles into the static generator."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from audit_site import PageParser, SITE_ROOT, discover_html, is_indexable


SOURCE_ROOT = SITE_ROOT / "_site-src"
CONTENT_ROOT = SOURCE_ROOT / "content"
DATA_PATH = SOURCE_ROOT / "data" / "articles.json"
VARIANT_ROOT = SITE_ROOT / "assets" / "css" / "article-variants"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Replace an existing imported manifest and fragments")
    return parser.parse_args()


def article_inner(text: str, path: Path) -> str:
    match = re.search(r"<article(?:\s[^>]*)?>(.*?)</article>", text, re.DOTALL)
    if match is None:
        raise SystemExit(f"Could not extract article from {path.relative_to(SITE_ROOT)}")
    value = match.group(1)
    if value.startswith("\n"):
        value = value[1:]
    if value.endswith("\n  "):
        value = value[:-3]
    return value.rstrip() + "\n"


def style_blocks(text: str) -> list[str]:
    return re.findall(r"<style(?:\s[^>]*)?>(.*?)</style>", text, re.DOTALL)


def hash_style(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def serialize_meta(parser: PageParser) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for tag, attrs, _ in parser.tags:
        if tag != "meta":
            continue
        if "charset" in attrs or attrs.get("name") == "viewport":
            continue
        records.append({key: str(value or "") for key, value in attrs.items()})
    return records


def serialize_links(parser: PageParser) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for tag, attrs, _ in parser.tags:
        if tag != "link":
            continue
        rels = str(attrs.get("rel") or "").split()
        if "canonical" in rels:
            records.append({key: str(value or "") for key, value in attrs.items()})
    return records


def main() -> int:
    args = parse_args()
    if DATA_PATH.exists() and not args.force:
        raise SystemExit(f"{DATA_PATH.relative_to(SITE_ROOT)} already exists; pass --force to re-import")

    CONTENT_ROOT.mkdir(parents=True, exist_ok=True)
    VARIANT_ROOT.mkdir(parents=True, exist_ok=True)
    if args.force:
        for generated in VARIANT_ROOT.glob("*.css"):
            generated.unlink()
    articles: list[dict[str, object]] = []
    variants: dict[str, str] = {}

    for path in discover_html():
        if path.parent.name not in {"help", "learn"}:
            continue
        text = path.read_text(encoding="utf-8")
        parser = PageParser()
        parser.feed(text)
        if not parser.has_article or not is_indexable(path, parser):
            continue

        rel = path.relative_to(SITE_ROOT)
        if rel.name == "index.html" or rel.as_posix() in {
            "learn/day-limits.html",
            "learn/tax-residency-by-country.html",
            "learn/us-state-tax-residency.html",
        }:
            continue
        content_path = CONTENT_ROOT / rel
        content_path.parent.mkdir(parents=True, exist_ok=True)
        content_path.write_text(article_inner(text, path), encoding="utf-8")

        style_ids: list[str] = []
        for style in style_blocks(text):
            style_id = hash_style(style)
            variants.setdefault(style_id, style.strip() + "\n")
            style_ids.append(style_id)

        articles.append(
            {
                "path": rel.as_posix(),
                "section": rel.parts[0],
                "title": parser.title,
                "meta": serialize_meta(parser),
                "links": serialize_links(parser),
                "jsonld": parser.jsonld_blobs,
                "content": content_path.relative_to(SOURCE_ROOT).as_posix(),
                "style_variants": style_ids,
            }
        )

    for style_id, value in variants.items():
        (VARIANT_ROOT / f"{style_id}.css").write_text(value, encoding="utf-8")

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_from": "committed article HTML",
                "articles": sorted(articles, key=lambda article: str(article["path"])),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Imported {len(articles)} articles and {len(variants)} style variants.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
