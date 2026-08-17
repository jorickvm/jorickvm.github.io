#!/usr/bin/env python3
"""Generate the sitemap set and llms.txt from the route manifest and committed HTML.

sitemap.xml is a sitemap index over one `sitemap-<code>.xml` per published
locale. The split is for measurement, not ranking: Search Console reports
discovery and indexing per submitted sitemap, so a locale nobody is indexing
shows up as a number instead of a hunch. robots.txt and any existing Search
Console registration keep pointing at sitemap.xml, which now resolves to the
index and leads a crawler to the rest.
"""

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
SITE_URL = "https://atlasdays.app"
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


def sitemap_name(code: str) -> str:
    return f"sitemap-{code}.xml"


def routes_by_locale(routes: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    """Indexable routes grouped by locale, default locale first, then registry order.

    Grouping is by generated path rather than by the locale registry, so a
    locale gets a sitemap only once it actually has pages: `expanded_routes`
    never emits a draft locale, and a draft one must not get an empty file.
    """
    default = default_locale_code()
    grouped: dict[str, list[dict[str, object]]] = {}
    for route in routes:
        if not route.get("indexable", True):
            continue
        grouped.setdefault(split_locale(str(route["path"]))[0], []).append(route)
    order = [default] + [code for code in load_locales() if code != default]
    return {code: grouped[code] for code in order if code in grouped}


def render_sitemap_index(grouped: dict[str, list[dict[str, object]]]) -> str:
    root = ET.Element(f"{{{NS}}}sitemapindex")
    for code, routes in grouped.items():
        node = ET.SubElement(root, f"{{{NS}}}sitemap")
        ET.SubElement(node, f"{{{NS}}}loc").text = f"{SITE_URL}/{sitemap_name(code)}"
        lastmods = [str(route["lastmod"]) for route in routes if route.get("lastmod")]
        if lastmods:
            # Newest page in the locale: it tells a crawler which children are
            # worth refetching, which is the only reason an index carries dates.
            ET.SubElement(node, f"{{{NS}}}lastmod").text = max(lastmods)
    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def sitemap_files(routes: list[dict[str, object]]) -> dict[Path, str]:
    """Every sitemap document to write: the index, then one urlset per locale."""
    grouped = routes_by_locale(routes)
    files = {SITEMAP: render_sitemap_index(grouped)}
    for code, locale_routes in grouped.items():
        files[ROOT / sitemap_name(code)] = render_sitemap(locale_routes)
    return files


def orphan_sitemaps(expected: set[Path]) -> list[Path]:
    """Per-locale sitemaps on disk that the registry no longer emits.

    Retiring a locale would otherwise leave its sitemap served and crawlable,
    pointing at pages that are now noindex or gone.
    """
    return sorted(path for path in ROOT.glob("sitemap-*.xml") if path not in expected)


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
                    "canonical": SITE_URL + f"/{code}" + route_for(source),
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
    expected = {**sitemap_files(routes), LLMS: render_llms(routes)}
    orphans = orphan_sitemaps(set(expected))
    stale = [path for path, value in expected.items() if not path.exists() or path.read_text(encoding="utf-8") != value]
    if options.check:
        if stale or orphans:
            if stale:
                print("Stale route output:")
                for path in stale:
                    print(f"  {path.relative_to(ROOT)}")
            if orphans:
                print("Sitemaps on disk that no locale claims:")
                for path in orphans:
                    print(f"  {path.relative_to(ROOT)}")
            return 1
        print(f"Checked {len(expected) - 1} sitemaps and llms.txt for {len(routes)} routes.")
        return 0
    for path, value in expected.items():
        path.write_text(value, encoding="utf-8")
    for path in orphans:
        path.unlink()
        print(f"Removed {path.relative_to(ROOT)}: no locale claims it.")
    print(f"Built {len(expected) - 1} sitemaps and llms.txt for {len(routes)} routes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
