#!/usr/bin/env python3
"""One-time importer for simple root-level content pages."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from audit_site import PageParser, SITE_ROOT
from import_articles import serialize_links, serialize_meta, style_blocks
from import_hubs import extract_main, extract_page_scripts


SOURCE_ROOT = SITE_ROOT / "_site-src"
DATA_PATH = SOURCE_ROOT / "data" / "pages.json"
CONTENT_ROOT = SOURCE_ROOT / "content" / "pages"
VARIANT_ROOT = SITE_ROOT / "assets" / "css" / "page-variants"
PAGE_PATHS = [Path("about.html"), Path("privacy.html"), Path("terms.html"), Path("changelog.html")]
LEGAL_PATHS = {Path("about.html"), Path("privacy.html"), Path("terms.html")}


def extract_changelog(text: str) -> str:
    head = re.search(r'<section class="page-head">.*?</section>', text, re.DOTALL)
    releases = re.search(r'<main class="release-stack">(.*?)</main>', text, re.DOTALL)
    if head is None or releases is None:
        raise SystemExit("Could not extract changelog content")
    return (
        '  <main class="page-shell" id="main-content">\n'
        + head.group(0)
        + '\n\n    <div class="release-stack">'
        + releases.group(1)
        + '</div>\n  </main>\n'
    )


def main() -> int:
    CONTENT_ROOT.mkdir(parents=True, exist_ok=True)
    VARIANT_ROOT.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    for rel in PAGE_PATHS:
        text = (SITE_ROOT / rel).read_text(encoding="utf-8")
        parser = PageParser()
        parser.feed(text)
        content_path = CONTENT_ROOT / rel
        content = extract_changelog(text) if rel == Path("changelog.html") else extract_main(text, rel)
        content_path.write_text(content, encoding="utf-8")
        style_ids: list[str] = ["legal"] if rel in LEGAL_PATHS else []
        if rel not in LEGAL_PATHS:
            for style in style_blocks(text):
                style_id = hashlib.sha256(style.encode("utf-8")).hexdigest()[:12]
                (VARIANT_ROOT / f"{style_id}.css").write_text(style.strip() + "\n", encoding="utf-8")
                style_ids.append(style_id)
        records.append(
            {
                "path": rel.as_posix(),
                "title": parser.title,
                "meta": serialize_meta(parser),
                "links": serialize_links(parser),
                "jsonld": parser.jsonld_blobs,
                "content": content_path.relative_to(SOURCE_ROOT).as_posix(),
                "style_variants": style_ids,
                "current_navigation": "changelog" if rel == Path("changelog.html") else "",
                "page_scripts": extract_page_scripts(text),
            }
        )
    DATA_PATH.write_text(json.dumps({"schema_version": 1, "pages": records}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Imported {len(records)} pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
