#!/usr/bin/env python3
"""Generate sitemap.xml and llms.txt from the route manifest and committed HTML."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from audit_site import PageParser, meta_content
from locales import default_locale_code, load_locales, route_for


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


BASE_SECTIONS = ("Start Here", "Help", "Learn", "Site Information")


def expanded_routes(routes: list[dict[str, object]]) -> list[dict[str, object]]:
    """Add every published translation to the English route manifest.

    The manifest owns English editorial priorities. Localized paths are derived
    from translation registries so publishing a complete locale cannot leave
    its pages out of sitemap.xml or llms.txt.
    """
    expanded = list(routes)
    by_source = {str(route["path"]): route for route in routes}
    known_paths = set(by_source)
    default = default_locale_code()
    for code, locale in load_locales().items():
        registry = locale.get("articles")
        if code == default or locale.get("status") != "published" or not registry:
            continue
        data = json.loads((ROOT / "_site-src" / str(registry)).read_text(encoding="utf-8"))
        for overlay in (
            list(data.get("articles", []))
            + list(data.get("hubs", []))
            + list(data.get("pages", []))
        ):
            source = str(overlay["source"])
            base = by_source.get(source)
            if base is None or not base.get("indexable", True):
                continue
            localized_path = f"{code}/{source}"
            if localized_path in known_paths:
                continue
            known_paths.add(localized_path)
            expanded.append(
                {
                    **base,
                    "path": localized_path,
                    "canonical": "https://atlasdays.app" + f"/{code}" + route_for(source),
                    "lastmod": str(overlay.get("translated_on", base.get("lastmod", ""))),
                }
            )
    return expanded


def split_locale(path: str) -> tuple[str, str]:
    """(locale code, English source path) for a generated file."""
    locales = load_locales()
    default = default_locale_code()
    head, _, rest = path.partition("/")
    if head in locales and head != default and rest:
        return head, rest
    return default, path


def section_for(path: str) -> str:
    """The llms.txt heading a page belongs under.

    Locale-aware so a Japanese page never gets filed as an English one: an LLM
    reading llms.txt would otherwise present a translated page as the English
    answer.
    """
    code, rest = split_locale(path)
    if rest == "index.html":
        base = "Start Here"
    elif rest.startswith("help/"):
        base = "Help"
    elif rest.startswith("learn/"):
        base = "Learn"
    else:
        base = "Site Information"
    if code == default_locale_code():
        return base
    return f"{base} ({load_locales()[code]['native_name']})"


def section_order() -> list[str]:
    """English sections first, then each published translation's own sections."""
    order = list(BASE_SECTIONS)
    default = default_locale_code()
    for code, locale in load_locales().items():
        if code == default or locale.get("status") != "published":
            continue
        order += [f"{base} ({locale['native_name']})" for base in BASE_SECTIONS]
    return order


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
    for section in section_order():
        if section not in grouped and section not in BASE_SECTIONS:
            continue
        lines.extend([f"## {section}", ""])
        for title, url, description in grouped.get(section, []):
            lines.append(f"- [{title}]({url}): {description}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    options = arguments()
    routes = expanded_routes(json.loads(ROUTES.read_text(encoding="utf-8"))["routes"])
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
