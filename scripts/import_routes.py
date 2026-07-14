#!/usr/bin/env python3
"""Import current sitemap scheduling data into the structured route manifest."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "_site-src" / "data" / "routes.json"
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def public_path(url: str) -> str:
    route = urlsplit(url).path
    if route == "/":
        return "index.html"
    direct = ROOT / (route.lstrip("/") + ".html")
    if direct.exists():
        return direct.relative_to(ROOT).as_posix()
    return (ROOT / route.lstrip("/") / "index.html").relative_to(ROOT).as_posix()


def main() -> int:
    root = ET.parse(ROOT / "sitemap.xml").getroot()
    routes = []
    for node in root.findall(NS + "url"):
        loc = str(node.findtext(NS + "loc") or "")
        routes.append(
            {
                "path": public_path(loc),
                "canonical": loc,
                "lastmod": str(node.findtext(NS + "lastmod") or ""),
                "priority": str(node.findtext(NS + "priority") or "0.5"),
                "indexable": True,
            }
        )
    OUTPUT.write_text(json.dumps({"schema_version": 1, "routes": routes}, indent=2) + "\n", encoding="utf-8")
    print(f"Imported {len(routes)} routes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
