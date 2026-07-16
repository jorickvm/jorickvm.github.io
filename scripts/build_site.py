#!/usr/bin/env python3
"""Build generated AtlasDays article pages into their public paths."""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

from build_route_outputs import LLMS, ROUTES, SITEMAP, render_llms, render_sitemap


SITE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = SITE_ROOT / "_site-src"
DATA_PATH = SOURCE_ROOT / "data" / "articles.json"
HUB_DATA_PATH = SOURCE_ROOT / "data" / "hubs.json"
PAGE_DATA_PATH = SOURCE_ROOT / "data" / "pages.json"
SOCIAL_DATA_PATH = SOURCE_ROOT / "data" / "social-cards.json"
ARTICLE_TEMPLATE = SOURCE_ROOT / "templates" / "article.html"
HUB_TEMPLATE = SOURCE_ROOT / "templates" / "hub.html"
HEADER_TEMPLATE = SOURCE_ROOT / "templates" / "partials" / "site-header.html"
FOOTER_TEMPLATE = SOURCE_ROOT / "templates" / "partials" / "site-footer.html"
CLUSTER_DATA_PATH = SOURCE_ROOT / "data" / "content-clusters.json"
BUILD_VERSION = "20260714b"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if generated output differs from committed HTML")
    parser.add_argument("--section", choices=("all", "help", "learn"), default="all")
    return parser.parse_args()


def attrs_html(attrs: dict[str, str]) -> str:
    parts: list[str] = []
    for key, value in attrs.items():
        if value == "":
            parts.append(key)
        else:
            parts.append(f'{key}="{html.escape(value, quote=True)}"')
    return " ".join(parts)


def render_metadata(article: dict[str, object], prefix: str = "../") -> str:
    lines = [f"  <title>{html.escape(str(article['title']))}</title>"]
    meta = [dict(attrs) for attrs in article.get("meta", [])]
    if SOCIAL_DATA_PATH.exists():
        social_data = json.loads(SOCIAL_DATA_PATH.read_text(encoding="utf-8"))
        social = next((page for page in social_data.get("pages", []) if page.get("path") == article.get("path")), None)
        if social:
            replaced_properties = {"og:image", "og:image:type", "og:image:width", "og:image:height", "og:image:alt"}
            replaced_names = {"twitter:image", "twitter:image:alt"}
            meta = [
                attrs for attrs in meta
                if attrs.get("property") not in replaced_properties and attrs.get("name") not in replaced_names
            ]
            image_url = "https://atlasdays.app" + str(social["image"])
            meta.extend(
                [
                    {"property": "og:image", "content": image_url},
                    {"property": "og:image:type", "content": "image/png"},
                    {"property": "og:image:width", "content": str(social["width"])},
                    {"property": "og:image:height", "content": str(social["height"])},
                    {"property": "og:image:alt", "content": str(social["alt"])},
                    {"name": "twitter:image", "content": image_url},
                    {"name": "twitter:image:alt", "content": str(social["alt"])},
                ]
            )
    for attrs in meta:
        lines.append(f"  <meta {attrs_html(dict(attrs))} />")
    for attrs in article.get("links", []):
        lines.append(f"  <link {attrs_html(dict(attrs))} />")
    lines.extend(
        [
            f'  <link rel="icon" type="image/png" href="{prefix}assets/brand/favicon_light.png?v=20260325a" media="(prefers-color-scheme: light)" />',
            f'  <link rel="icon" type="image/png" href="{prefix}assets/brand/favicon_dark.png?v=20260325a" media="(prefers-color-scheme: dark)" />',
        ]
    )
    return "\n".join(lines)


def render_structured_data(article: dict[str, object]) -> str:
    lines: list[str] = []
    for raw in article.get("jsonld", []):
        lines.append('  <script type="application/ld+json">')
        for line in str(raw).strip().splitlines():
            lines.append("  " + line)
        lines.append("  </script>")
    return "\n".join(lines)


def render_styles(article: dict[str, object], family: str = "article", prefix: str = "../") -> str:
    lines = [
        f'  <link rel="stylesheet" href="{prefix}assets/css/{family}-variants/{style_id}.css?v={BUILD_VERSION}" />'
        for style_id in article.get("style_variants", [])
    ]
    lines.append(f'  <link rel="stylesheet" href="{prefix}assets/css/site-header.css?v={BUILD_VERSION}" />')
    lines.append(f'  <link rel="stylesheet" href="{prefix}assets/css/site-footer.css?v={BUILD_VERSION}" />')
    return "\n".join(lines)


def render_header(article: dict[str, object], template: str, prefix: str = "../") -> str:
    section = str(article.get("current_navigation", article.get("section", "")))
    return (
        template.replace("{{ASSET_PREFIX}}", prefix)
        .replace("{{HELP_CURRENT}}", ' aria-current="page"' if section == "help" else "")
        .replace("{{LEARN_CURRENT}}", ' aria-current="page"' if section in {"learn", "day-limits"} else "")
        .replace("{{DAY_LIMITS_CURRENT}}", ' aria-current="page"' if section == "day-limits" else "")
        .replace("{{CHANGELOG_CURRENT}}", ' aria-current="page"' if section == "changelog" else "")
    ).rstrip()


def render_cluster_related(article: dict[str, object]) -> str:
    if article.get("section") != "learn" or not CLUSTER_DATA_PATH.exists():
        return ""
    assignments = json.loads(CLUSTER_DATA_PATH.read_text(encoding="utf-8"))["clusters"]
    current = next((item for item in assignments if item["path"] == article["path"]), None)
    if not current:
        return ""
    article_data = json.loads(DATA_PATH.read_text(encoding="utf-8"))["articles"]
    hub_data = json.loads(HUB_DATA_PATH.read_text(encoding="utf-8"))["hubs"] if HUB_DATA_PATH.exists() else []
    titles = {item["path"]: str(item["title"]).replace(" — AtlasDays Help Center", "").replace(" — AtlasDays", "") for item in article_data + hub_data}
    candidates = [item["path"] for item in assignments if item["cluster"] == current["cluster"] and item["path"] != article["path"]]
    pillar = current["pillar"]
    ordered = ([pillar] if pillar != article["path"] else []) + sorted(path for path in candidates if path != pillar)
    links = []
    for path in ordered[:5]:
        title = titles.get(path)
        if not title:
            continue
        href = "/" + str(path).removesuffix(".html")
        links.append(f'        <li><a href="{html.escape(href)}">{html.escape(title)}</a></li>')
    if not links:
        return ""
    identifier = "related-" + Path(str(article["path"])).stem
    return "\n".join(
        [
            f'    <nav class="related generated-related" aria-labelledby="{identifier}">',
            f'      <h2 id="{identifier}">Related in this topic</h2>',
            "      <ul>",
            *links,
            "      </ul>",
            "    </nav>",
        ]
    )


def render_article(
    article: dict[str, object],
    template: str,
    header_template: str,
    footer_template: str,
) -> str:
    content_path = SOURCE_ROOT / str(article["content"])
    content = content_path.read_text(encoding="utf-8").rstrip()
    replacements = {
        "{{METADATA}}": render_metadata(article),
        "{{STRUCTURED_DATA}}": render_structured_data(article),
        "{{STYLESHEETS}}": render_styles(article),
        "{{SITE_HEADER}}": render_header(article, header_template),
        "{{SITE_FOOTER}}": footer_template.replace("{{ASSET_PREFIX}}", "../").rstrip(),
        "{{ARTICLE_CONTENT}}": content,
        "{{CLUSTER_RELATED}}": render_cluster_related(article),
        "{{ASSET_PREFIX}}": "../",
    }
    rendered = template
    for marker, value in replacements.items():
        rendered = rendered.replace(marker, value)
    leftovers = [marker for marker in replacements if marker in rendered]
    if leftovers:
        raise SystemExit(f"Unresolved template markers for {article['path']}: {leftovers}")
    return rendered.rstrip() + "\n"


def render_hub(
    hub: dict[str, object],
    template: str,
    header_template: str,
    footer_template: str,
    *,
    family: str = "hub",
    prefix: str = "../",
) -> str:
    content = (SOURCE_ROOT / str(hub["content"])).read_text(encoding="utf-8").rstrip()
    replacements = {
        "{{METADATA}}": render_metadata(hub, prefix),
        "{{STRUCTURED_DATA}}": render_structured_data(hub),
        "{{STYLESHEETS}}": render_styles(hub, family, prefix),
        "{{SITE_HEADER}}": render_header(hub, header_template, prefix),
        "{{MAIN_CONTENT}}": content,
        "{{SITE_FOOTER}}": footer_template.replace("{{ASSET_PREFIX}}", prefix).rstrip(),
        "{{PAGE_SCRIPTS}}": str(hub.get("page_scripts", "")).rstrip(),
        "{{SEARCH_STYLESHEET}}": (
            f'  <link rel="stylesheet" href="{prefix}assets/css/search.css?v=20260717b" />'
            if family == "hub" else ""
        ),
        "{{SEARCH_SCRIPT}}": (
            f'  <script src="{prefix}assets/js/search.js?v=20260717b"></script>'
            if family == "hub" else ""
        ),
        "{{ASSET_PREFIX}}": prefix,
    }
    rendered = template
    for marker, value in replacements.items():
        rendered = rendered.replace(marker, value)
    return rendered.rstrip() + "\n"


def main() -> int:
    args = parse_args()
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    template = ARTICLE_TEMPLATE.read_text(encoding="utf-8")
    header_template = HEADER_TEMPLATE.read_text(encoding="utf-8")
    footer_template = FOOTER_TEMPLATE.read_text(encoding="utf-8")
    hub_template = HUB_TEMPLATE.read_text(encoding="utf-8")
    changed: list[str] = []
    selected = 0

    for article in data.get("articles", []):
        if args.section != "all" and article.get("section") != args.section:
            continue
        selected += 1
        output_path = SITE_ROOT / str(article["path"])
        rendered = render_article(article, template, header_template, footer_template)
        current = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
        if current == rendered:
            continue
        changed.append(str(article["path"]))
        if not args.check:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding="utf-8")

    if args.section == "all" and HUB_DATA_PATH.exists():
        hub_data = json.loads(HUB_DATA_PATH.read_text(encoding="utf-8"))
        for hub in hub_data.get("hubs", []):
            selected += 1
            output_path = SITE_ROOT / str(hub["path"])
            rendered = render_hub(hub, hub_template, header_template, footer_template)
            current = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
            if current == rendered:
                continue
            changed.append(str(hub["path"]))
            if not args.check:
                output_path.write_text(rendered, encoding="utf-8")

    if args.section == "all" and PAGE_DATA_PATH.exists():
        page_data = json.loads(PAGE_DATA_PATH.read_text(encoding="utf-8"))
        for page in page_data.get("pages", []):
            selected += 1
            output_path = SITE_ROOT / str(page["path"])
            rendered = render_hub(
                page,
                hub_template,
                header_template,
                footer_template,
                family="page",
                prefix="",
            )
            current = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
            if current == rendered:
                continue
            changed.append(str(page["path"]))
            if not args.check:
                output_path.write_text(rendered, encoding="utf-8")

    if args.section == "all" and ROUTES.exists():
        routes = json.loads(ROUTES.read_text(encoding="utf-8"))["routes"]
        for output_path, rendered in ((SITEMAP, render_sitemap(routes)), (LLMS, render_llms(routes))):
            current = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
            if current == rendered:
                continue
            changed.append(output_path.relative_to(SITE_ROOT).as_posix())
            if not args.check:
                output_path.write_text(rendered, encoding="utf-8")

    if args.check and changed:
        print("Generated article output is stale:")
        for path in changed:
            print(f"  {path}")
        return 1
    action = "Checked" if args.check else "Built"
    print(f"{action} {selected} generated pages; {len(changed)} changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
