#!/usr/bin/env python3
"""Generate sitemap.xml and llms.txt from the route manifest and committed HTML."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from audit_site import PageParser, meta_content


ROOT = Path(__file__).resolve().parents[1]
ROUTES = ROOT / "_site-src" / "data" / "routes.json"
SITEMAP = ROOT / "sitemap.xml"
LLMS = ROOT / "llms.txt"
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ET.register_namespace("", NS)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def page_details(path: str) -> tuple[str, str]:
    parser = PageParser()
    parser.feed((ROOT / path).read_text(encoding="utf-8"))
    descriptions = meta_content(parser, name="description")
    return parser.title, descriptions[0] if descriptions else ""


def render_sitemap(routes: list[dict[str, object]]) -> str:
    root = ET.Element(f"{{{NS}}}urlset")
    for route in routes:
        if not route.get("indexable", True):
            continue
        node = ET.SubElement(root, f"{{{NS}}}url")
        ET.SubElement(node, f"{{{NS}}}loc").text = str(route["canonical"])
        if route.get("lastmod"):
            ET.SubElement(node, f"{{{NS}}}lastmod").text = str(route["lastmod"])
        ET.SubElement(node, f"{{{NS}}}priority").text = str(route.get("priority", "0.5"))
    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def section_for(path: str) -> str:
    if path == "index.html":
        return "Start Here"
    if path.startswith("help/"):
        return "Help"
    if path.startswith("learn/"):
        return "Learn"
    return "Site Information"


def render_llms(routes: list[dict[str, object]]) -> str:
    grouped: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for route in routes:
        if not route.get("indexable", True):
            continue
        title, description = page_details(str(route["path"]))
        grouped[section_for(str(route["path"]))].append((title, str(route["canonical"]), description))
    lines = [
        "# AtlasDays", "",
        "> AtlasDays is a private iPhone app and website for tracking visa limits, residency or tax presence days, and travel history.", "",
        "AtlasDays is a record-keeping and day-counting tool, not legal or tax advice. Official government guidance and professional advice remain authoritative for rule interpretation.", "",
    ]
    for section in ("Start Here", "Help", "Learn", "Site Information"):
        lines.extend([f"## {section}", ""])
        for title, url, description in grouped.get(section, []):
            lines.append(f"- [{title}]({url}): {description}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    options = arguments()
    routes = json.loads(ROUTES.read_text(encoding="utf-8"))["routes"]
    expected = {SITEMAP: render_sitemap(routes), LLMS: render_llms(routes)}
    stale = [path for path, value in expected.items() if not path.exists() or path.read_text(encoding="utf-8") != value]
    if options.check:
        if stale:
            print("Stale route output:")
            for path in stale:
                print(f"  {path.relative_to(ROOT)}")
            return 1
        print(f"Checked sitemap and llms.txt for {len(routes)} routes.")
        return 0
    for path, value in expected.items():
        path.write_text(value, encoding="utf-8")
    print(f"Built sitemap and llms.txt for {len(routes)} routes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
