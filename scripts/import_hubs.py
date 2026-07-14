#!/usr/bin/env python3
"""One-time importer for the five Help/Learn hub pages."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from audit_site import PageParser, SITE_ROOT
from import_articles import serialize_links, serialize_meta, style_blocks


SOURCE_ROOT = SITE_ROOT / "_site-src"
DATA_PATH = SOURCE_ROOT / "data" / "hubs.json"
CONTENT_ROOT = SOURCE_ROOT / "content" / "hubs"
VARIANT_ROOT = SITE_ROOT / "assets" / "css" / "hub-variants"
HUB_PATHS = [
    Path("help/index.html"),
    Path("learn/index.html"),
    Path("learn/day-limits.html"),
    Path("learn/tax-residency-by-country.html"),
    Path("learn/us-state-tax-residency.html"),
]


def extract_main(text: str, path: Path) -> str:
    match = re.search(r"<main(?:\s[^>]*)?>.*?</main>", text, re.DOTALL)
    if match is None:
        raise SystemExit(f"Could not extract main from {path}")
    value = match.group(0)
    value = re.sub(r"<main(\s[^>]*)?>", lambda m: f'<main{m.group(1) or ""} id="main-content">' if "id=" not in m.group(0) else m.group(0), value, count=1)
    return value.rstrip() + "\n"


def extract_page_scripts(text: str) -> str:
    main_end = text.find("</main>")
    analytics = text.find("<!-- Cloudflare Web Analytics -->", main_end)
    tail = text[main_end + len("</main>"):analytics if analytics >= 0 else None]
    scripts = re.findall(r"<script(?:\s[^>]*)?>.*?</script>", tail, re.DOTALL)
    cleaned: list[str] = []
    for script in scripts:
        if re.search(r'<script[^>]+src=["\'][^"\']*(?:theme|navigation|search)\.js', script):
            continue
        script = re.sub(r"\s*function toggleTheme\(\) \{.*?\n\s*\}\s*", "\n", script, flags=re.DOTALL)
        if re.sub(r"</?script(?:\s[^>]*)?>", "", script).strip():
            cleaned.append(script.strip())
    return "\n".join(cleaned)


def main() -> int:
    CONTENT_ROOT.mkdir(parents=True, exist_ok=True)
    VARIANT_ROOT.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    for rel in HUB_PATHS:
        path = SITE_ROOT / rel
        text = path.read_text(encoding="utf-8")
        parser = PageParser()
        parser.feed(text)
        content_path = CONTENT_ROOT / ("-".join(rel.with_suffix("").parts) + ".html")
        content_path.write_text(extract_main(text, rel), encoding="utf-8")
        style_ids: list[str] = []
        for style in style_blocks(text):
            style_id = hashlib.sha256(style.encode("utf-8")).hexdigest()[:12]
            (VARIANT_ROOT / f"{style_id}.css").write_text(style.strip() + "\n", encoding="utf-8")
            style_ids.append(style_id)
        current = "help" if rel == Path("help/index.html") else "learn"
        if rel == Path("learn/day-limits.html"):
            current = "day-limits"
        records.append(
            {
                "path": rel.as_posix(),
                "title": parser.title,
                "meta": serialize_meta(parser),
                "links": serialize_links(parser),
                "jsonld": parser.jsonld_blobs,
                "content": content_path.relative_to(SOURCE_ROOT).as_posix(),
                "style_variants": style_ids,
                "current_navigation": current,
                "page_scripts": extract_page_scripts(text),
            }
        )
    DATA_PATH.write_text(json.dumps({"schema_version": 1, "hubs": records}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Imported {len(records)} hubs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
