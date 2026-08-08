#!/usr/bin/env python3
"""Build generated AtlasDays article pages into their public paths."""

from __future__ import annotations

import argparse
import html
import json
import re
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
BUILD_VERSION = "20260808c"

# Root class that drops the background wash from the app's `.medium` step to
# `.subtle`, for pages carrying long-form text. See assets/css/tokens.css.
WASH_SUBTLE = ' class="wash-subtle"'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if generated output differs from committed HTML")
    parser.add_argument("--section", choices=("all", "help", "learn"), default="all")
    parser.add_argument(
        "--allow-delisting",
        action="store_true",
        help="Permit a rebuild to drop links to pages that still exist on disk",
    )
    return parser.parse_args()


SITE_URL = "https://atlasdays.app"


def linked_paths(text: str) -> set[str]:
    """Repo-relative paths for every internal link in a generated file.

    Covers absolute canonicals in sitemap.xml and llms.txt as well as the
    root-relative hrefs used by hub rows.
    """
    paths: set[str] = set()
    for route in re.findall(rf"{re.escape(SITE_URL)}(/[\w\-./]*)", text):
        paths.add(route)
    for route in re.findall(r'(?:href|data-href)="(/[\w\-./]*)"', text):
        paths.add(route)
    normalised = set()
    for route in paths:
        trimmed = route.strip("/")
        if not trimmed:
            trimmed = "index"
        normalised.add(trimmed if trimmed.endswith(".html") else f"{trimmed}.html")
    return normalised


def delisted_live_pages(current: str, rendered: str) -> list[str]:
    """Pages the rebuild would stop linking to that are still published.

    A page vanishing from the sitemap, llms.txt, or a hub while its HTML is
    still committed means the build data lost track of it, not that it was
    retired. That is silent de-indexing, so the caller must refuse to write.
    """
    dropped = linked_paths(current) - linked_paths(rendered)
    return sorted(path for path in dropped if (SITE_ROOT / path).exists())


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
    asset_version = str(article.get("asset_version", BUILD_VERSION))
    # tokens.css first: it owns the palette, wash, and card surface for every
    # page, and the variant stylesheets that follow carry layout only.
    lines = [f'  <link rel="stylesheet" href="{prefix}assets/css/tokens.css?v={asset_version}" />']
    lines += [
        f'  <link rel="stylesheet" href="{prefix}assets/css/{family}-variants/{style_id}.css?v={asset_version}" />'
        for style_id in article.get("style_variants", [])
    ]
    lines.append(f'  <link rel="stylesheet" href="{prefix}assets/css/site-header.css?v={asset_version}" />')
    lines.append(f'  <link rel="stylesheet" href="{prefix}assets/css/site-footer.css?v={asset_version}" />')
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
    titles = {item["path"]: str(item["title"]).replace(" – AtlasDays Help Center", "").replace(" – AtlasDays", "") for item in article_data + hub_data}
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


def render_help_tail(article: dict[str, object]) -> str:
    if article.get("section") != "help":
        return ""
    items = []
    for step in article.get("next_steps", []):
        items.append(
            "\n".join(
                [
                    f'        <li><a href="{html.escape(str(step["url"]))}">',
                    f'          <strong>{html.escape(str(step["title"]))}</strong>',
                    f'          <span>{html.escape(str(step["description"]))}</span>',
                    "        </a></li>",
                ]
            )
        )
    identifier = "next-" + Path(str(article["path"])).stem
    updated = html.escape(str(article.get("last_updated", "August 2, 2026")))
    return "\n".join(
        [
            f'    <nav class="help-next" aria-labelledby="{identifier}">',
            f'      <h2 id="{identifier}">Continue with</h2>',
            "      <ul>",
            *items,
            "      </ul>",
            "    </nav>",
            '    <aside class="help-contact">',
            "      <h2>Still need help?</h2>",
            '      <p><a href="mailto:support@atlasdays.app">Contact AtlasDays Support</a> with the relevant dates, what you expected, and what happened.</p>',
            "    </aside>",
            f'    <p class="help-updated">Last updated {updated}</p>',
        ]
    )


def validate_help_next_steps(articles: list[dict[str, object]]) -> None:
    help_articles = [article for article in articles if article.get("section") == "help"]
    routes = {"/" + str(article["path"]).removesuffix(".html") for article in help_articles}
    errors = []
    for article in help_articles:
        current = "/" + str(article["path"]).removesuffix(".html")
        steps = article.get("next_steps", [])
        if not 2 <= len(steps) <= 3:
            errors.append(f"{article['path']}: expected 2 or 3 next_steps")
            continue
        urls = [str(step.get("url", "")) for step in steps]
        if len(urls) != len(set(urls)):
            errors.append(f"{article['path']}: duplicate next_steps")
        if current in urls:
            errors.append(f"{article['path']}: next_steps contains a self-link")
        for url in urls:
            if url not in routes:
                errors.append(f"{article['path']}: missing next-step route {url}")
        for step in steps:
            if not step.get("title") or not step.get("description"):
                errors.append(f"{article['path']}: incomplete next-step metadata")
    if errors:
        raise SystemExit("Invalid Help next-step metadata:\n  " + "\n  ".join(errors))


def render_article(
    article: dict[str, object],
    template: str,
    header_template: str,
    footer_template: str,
) -> str:
    content_path = SOURCE_ROOT / str(article["content"])
    content = content_path.read_text(encoding="utf-8").rstrip()
    replacements = {
        "{{HTML_CLASS}}": WASH_SUBTLE,
        "{{METADATA}}": render_metadata(article),
        "{{STRUCTURED_DATA}}": render_structured_data(article),
        "{{STYLESHEETS}}": render_styles(article),
        "{{SITE_HEADER}}": render_header(article, header_template),
        "{{SITE_FOOTER}}": footer_template.replace("{{ASSET_PREFIX}}", "../").rstrip(),
        "{{ARTICLE_CONTENT}}": content,
        "{{CLUSTER_RELATED}}": render_help_tail(article) or render_cluster_related(article),
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
        # Hubs are marketing surfaces and take the full wash; the legal and
        # about pages built through this same template are long-form reading
        # and step down with the articles.
        "{{HTML_CLASS}}": WASH_SUBTLE if family == "page" else "",
        "{{METADATA}}": render_metadata(hub, prefix),
        "{{STRUCTURED_DATA}}": render_structured_data(hub),
        "{{STYLESHEETS}}": render_styles(hub, family, prefix),
        "{{SITE_HEADER}}": render_header(hub, header_template, prefix),
        "{{MAIN_CONTENT}}": content,
        "{{SITE_FOOTER}}": footer_template.replace("{{ASSET_PREFIX}}", prefix).rstrip(),
        "{{PAGE_SCRIPTS}}": str(hub.get("page_scripts", "")).rstrip(),
        "{{SEARCH_STYLESHEET}}": (
            f'  <link rel="stylesheet" href="{prefix}assets/css/search.css?v=20260722a" />'
            if family == "hub" else ""
        ),
        "{{SEARCH_SCRIPT}}": (
            f'  <script src="{prefix}assets/js/search.js?v=20260802b"></script>'
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
    validate_help_next_steps(data.get("articles", []))
    template = ARTICLE_TEMPLATE.read_text(encoding="utf-8")
    header_template = HEADER_TEMPLATE.read_text(encoding="utf-8")
    footer_template = FOOTER_TEMPLATE.read_text(encoding="utf-8")
    hub_template = HUB_TEMPLATE.read_text(encoding="utf-8")
    changed: list[str] = []
    selected = 0
    # (output_path, rendered) queued until every de-listing check has passed, so
    # an aborted build leaves the working tree untouched rather than half-written.
    pending: list[tuple[Path, str]] = []
    delistings: list[tuple[str, list[str]]] = []

    def queue(output_path: Path, rendered: str, *, guard: bool = False) -> None:
        nonlocal selected
        selected += 1
        current = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
        if current == rendered:
            return
        relative = output_path.relative_to(SITE_ROOT).as_posix()
        changed.append(relative)
        if guard and current:
            dropped = delisted_live_pages(current, rendered)
            if dropped:
                delistings.append((relative, dropped))
        pending.append((output_path, rendered))

    for article in data.get("articles", []):
        if args.section != "all" and article.get("section") != args.section:
            continue
        queue(
            SITE_ROOT / str(article["path"]),
            render_article(article, template, header_template, footer_template),
        )

    if args.section == "all" and HUB_DATA_PATH.exists():
        hub_data = json.loads(HUB_DATA_PATH.read_text(encoding="utf-8"))
        for hub in hub_data.get("hubs", []):
            queue(
                SITE_ROOT / str(hub["path"]),
                render_hub(hub, hub_template, header_template, footer_template),
                guard=True,
            )

    if args.section == "all" and PAGE_DATA_PATH.exists():
        page_data = json.loads(PAGE_DATA_PATH.read_text(encoding="utf-8"))
        for page in page_data.get("pages", []):
            queue(
                SITE_ROOT / str(page["path"]),
                render_hub(
                    page,
                    hub_template,
                    header_template,
                    footer_template,
                    family="page",
                    prefix="",
                ),
                guard=True,
            )

    if args.section == "all" and ROUTES.exists():
        routes = json.loads(ROUTES.read_text(encoding="utf-8"))["routes"]
        queue(SITEMAP, render_sitemap(routes), guard=True)
        queue(LLMS, render_llms(routes), guard=True)

    if delistings and not args.allow_delisting:
        print("Refusing to build: this would unlink pages that are still published.")
        for relative, dropped in delistings:
            print(f"  {relative} would stop linking to:")
            for path in dropped:
                print(f"    {path}")
        print(
            "\nThese pages exist but are missing from the build data, so a rebuild\n"
            "drops them from search engines and site navigation. Register them in\n"
            "_site-src/data/ first, or pass --allow-delisting if the removal is intended."
        )
        return 1

    if not args.check:
        for output_path, rendered in pending:
            output_path.parent.mkdir(parents=True, exist_ok=True)
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
