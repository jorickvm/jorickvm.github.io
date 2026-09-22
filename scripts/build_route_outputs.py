#!/usr/bin/env python3
"""Generate the sitemap set and the llms.txt set from the route manifest and committed HTML.

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
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from audit_site import PageParser, meta_content
from locales import default_locale_code, load_locales, load_ui_strings, route_for


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


SECTIONS = ("Start Here", "Use Cases", "Help", "Learn", "Site Information")
PAGES = ROOT / "_site-src" / "data" / "pages.json"
HUBS = ROOT / "_site-src" / "data" / "hubs.json"
HEADER_PARTIAL = ROOT / "_site-src" / "templates" / "partials" / "site-header.html"


def llms_path(code: str) -> Path:
    """Where a locale's llms.txt is served: the site root for English, else `/<code>/`.

    Mirrors the page routing, so an agent that landed on `/ja/learn/...` finds
    `/ja/llms.txt` by the same rule it found the page.
    """
    return LLMS if code == default_locale_code() else ROOT / code / "llms.txt"


def llms_url(code: str) -> str:
    return SITE_URL + "/" + llms_path(code).relative_to(ROOT).as_posix()


def app_store_url() -> str:
    """The one App Store URL, read from the header partial that every page renders."""
    found = set(re.findall(r'https://apps\.apple\.com/[^"\s]+', HEADER_PARTIAL.read_text(encoding="utf-8")))
    if len(found) != 1:
        raise SystemExit(f"Expected one App Store URL in {HEADER_PARTIAL.name}, found {sorted(found)}")
    return found.pop()


def use_case_sources() -> set[str]:
    pages = json.loads(PAGES.read_text(encoding="utf-8"))["pages"]
    return {str(page["path"]) for page in pages if page.get("current_navigation") == "use-cases"}


def hub_sources() -> set[str]:
    return {str(hub["path"]) for hub in json.loads(HUBS.read_text(encoding="utf-8"))["hubs"]}


def section_for(source: str, use_cases: set[str]) -> str:
    """The llms.txt heading an English source path belongs under."""
    if source == "index.html":
        return "Start Here"
    if source in use_cases:
        return "Use Cases"
    if source.startswith("help/"):
        return "Help"
    if source.startswith("learn/"):
        return "Learn"
    return "Site Information"


def short_title(title: str, locale: dict, strings: dict[str, dict[str, str]]) -> str:
    """A page title without the site suffix every entry would otherwise repeat.

    The file's own `# AtlasDays` heading already names the site. The suffix is
    the locale's separator plus a chrome string, so both come from the registry.
    """
    code = str(locale["code"])
    separator = str(locale.get("title_separator", " – "))
    for key in ("site.title_suffix_help", "site.title_suffix"):
        suffix = separator + strings[key][code]
        if title.endswith(suffix):
            return title[: -len(suffix)]
    return title


def render_llms(code: str, routes: list[dict[str, object]], published: list[dict]) -> str:
    """One locale's llms.txt, in that locale's own language apart from the headings.

    Every sentence is already-reviewed site copy: the summary is the localized
    homepage description and the disclaimer is the Learn disclaimer, so the
    generator writes no prose of its own that would need translating.
    """
    locale = load_locales()[code]
    strings = load_ui_strings()
    use_cases, hubs = use_case_sources(), hub_sources()
    grouped: dict[str, list[tuple[int, float, float, str]]] = defaultdict(list)
    summary = ""
    for index, route in enumerate(routes):
        path = str(route["path"])
        title, description = page_details(path)
        source = split_locale(path)[1]
        if source == "index.html":
            summary = description
        entry = f"- [{short_title(title, locale, strings)}]({route['canonical']}): {description}"
        # Hubs lead their section because they link everything else in it,
        # which is what a reader that truncates the file most needs to see.
        rank = 0 if source in hubs else 1
        grouped[section_for(source, use_cases)].append((rank, -float(route.get("priority", 0.5)), index, entry))
        if source == "index.html":
            store = f"- [{strings['footer.app_store'][code]}]({app_store_url()}): {strings['footer.tagline'][code]}"
            grouped["Start Here"].append((rank, -float(route.get("priority", 0.5)), index + 0.5, store))
    lines = ["# AtlasDays", "", f"> {summary}", "", strings["learn.disclaimer"][code], ""]
    # Languages come before the page lists: they are the only way to reach the
    # other files, and a fetch tool that truncates would never see them at the end.
    lines.extend(["## Other Languages", ""])
    for other in published:
        if other["code"] != code:
            lines.append(f"- [{other['native_name']} ({other['english_name']})]({llms_url(str(other['code']))})")
    lines.append("")
    for section in SECTIONS:
        if section in grouped:
            lines.extend([f"## {section}", ""])
            lines.extend(entry for *_, entry in sorted(grouped[section]))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def llms_files(routes: list[dict[str, object]]) -> dict[Path, str]:
    """Every llms.txt to write: English at the root, each translation under its prefix.

    Split for the same reason the sitemap is: one file carrying all thirteen
    languages was 93% translations, and fetch tools truncate long responses, so
    an agent reading it saw the English head and never reached its own language.
    """
    grouped = routes_by_locale(routes)
    published = [load_locales()[code] for code in grouped]
    return {llms_path(code): render_llms(code, locale_routes, published) for code, locale_routes in grouped.items()}


def orphan_llms(expected: set[Path]) -> list[Path]:
    """Per-locale llms.txt files on disk that no published locale emits."""
    return sorted(path for path in ROOT.glob("*/llms.txt") if path not in expected)


def main() -> int:
    options = arguments()
    routes = expanded_routes(json.loads(ROUTES.read_text(encoding="utf-8"))["routes"])
    expected = {**sitemap_files(routes), **llms_files(routes)}
    orphans = orphan_sitemaps(set(expected)) + orphan_llms(set(expected))
    stale = [path for path, value in expected.items() if not path.exists() or path.read_text(encoding="utf-8") != value]
    if options.check:
        if stale or orphans:
            if stale:
                print("Stale route output:")
                for path in stale:
                    print(f"  {path.relative_to(ROOT)}")
            if orphans:
                print("Route outputs on disk that no locale claims:")
                for path in orphans:
                    print(f"  {path.relative_to(ROOT)}")
            return 1
        print(f"Checked {len(expected)} route outputs (sitemaps and llms.txt) for {len(routes)} routes.")
        return 0
    for path, value in expected.items():
        path.write_text(value, encoding="utf-8")
    for path in orphans:
        path.unlink()
        print(f"Removed {path.relative_to(ROOT)}: no locale claims it.")
    print(f"Built {len(expected)} route outputs (sitemaps and llms.txt) for {len(routes)} routes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
