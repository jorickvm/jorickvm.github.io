#!/usr/bin/env python3
"""Build generated AtlasDays article pages into their public paths."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import date
from pathlib import Path

from build_route_outputs import LLMS, ROUTES, SITEMAP, render_llms, render_sitemap
from locales import (
    default_locale_code,
    load_locales,
    load_ui_strings,
    localize,
    localized_route,
    meta_hash,
    render_date,
    route_for,
    source_hash,
)


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
BUILD_VERSION = "20260809a"

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


def asset_prefix(path: str) -> str:
    """Relative hop back to the site root from a page's own directory.

    Derived from the output path rather than passed in by the caller, so a page
    at any depth links its assets correctly without a call-site argument.
    """
    return "../" * (len(Path(str(path)).parts) - 1)


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
        # Translated pages have no card of their own yet: generate_social_cards
        # cannot lay out CJK, so they share the English card for their source.
        social_path = article.get("social_source_path", article.get("path"))
        social = next((page for page in social_data.get("pages", []) if page.get("path") == social_path), None)
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


def render_header(
    article: dict[str, object],
    template: str,
    prefix: str = "../",
    switcher: str = "",
    switcher_mobile: str = "",
) -> str:
    section = str(article.get("current_navigation", article.get("section", "")))
    return (
        template.replace("{{ASSET_PREFIX}}", prefix)
        .replace("{{LANGUAGE_SWITCHER}}", switcher)
        .replace("{{LANGUAGE_SWITCHER_MOBILE}}", switcher_mobile)
        .replace("{{HELP_CURRENT}}", ' aria-current="page"' if section == "help" else "")
        .replace("{{LEARN_CURRENT}}", ' aria-current="page"' if section in {"learn", "day-limits"} else "")
        .replace("{{DAY_LIMITS_CURRENT}}", ' aria-current="page"' if section == "day-limits" else "")
        .replace("{{CHANGELOG_CURRENT}}", ' aria-current="page"' if section == "changelog" else "")
        # The use-cases entry is a <details>, not an <a>, so it takes a data
        # attribute rather than aria-current: the element that is "current" is
        # the link inside the panel, and marking the disclosure as the current
        # page would announce the wrong thing.
        .replace("{{USE_CASES_CURRENT}}", ' data-current' if section == "use-cases" else "")
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
            f'      <h2 id="{identifier}">{{{{t:related.heading}}}}</h2>',
            "      <ul>",
            *links,
            "      </ul>",
            "    </nav>",
        ]
    )


def render_help_tail(
    article: dict[str, object],
    locale: dict[str, object],
    strings: dict[str, dict[str, str]],
) -> str:
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
    updated = html.escape(render_date(str(article["last_updated_iso"]), locale))
    # Resolved here rather than left as a marker: the sentence carries the date
    # inline, and every language places it differently.
    updated_line = str(strings["help.updated"][str(locale["code"])]).replace("{date}", updated)
    return "\n".join(
        [
            f'    <nav class="help-next" aria-labelledby="{identifier}">',
            f'      <h2 id="{identifier}">{{{{t:help.continue}}}}</h2>',
            "      <ul>",
            *items,
            "      </ul>",
            "    </nav>",
            '    <aside class="help-contact">',
            "      <h2>{{t:help.still_need}}</h2>",
            "      <p>{{t:help.contact_body}}</p>",
            "    </aside>",
            f'    <p class="help-updated">{updated_line}</p>',
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


# A translation record supplies prose and nothing else. Every structural field
# is derived from the English source, so a translator cannot invent a URL, a
# canonical, or a JSON-LD graph in a language nobody here can proofread, and
# validate_help_next_steps keeps guarding the routes for free.
OVERLAY_FIELDS = {
    "source",
    "headline",
    "description",
    "content",
    "next_steps",
    "screenshot_alt",
    "search_synonyms",
    "source_hash",
    "source_meta_hash",
    "translated_on",
    "translated_by",
    "stale_ack",
}


def load_translations(locales: dict[str, dict]) -> dict[str, dict[str, dict]]:
    """Translation overlays per locale, keyed by the English source path."""
    loaded: dict[str, dict[str, dict]] = {}
    for code, locale in locales.items():
        relative = locale.get("articles")
        if not relative:
            continue
        path = SOURCE_ROOT / str(relative)
        if not path.exists():
            raise SystemExit(f"Locale {code!r} points at a missing registry: {relative}")
        data = json.loads(path.read_text(encoding="utf-8"))
        overlays: dict[str, dict] = {}
        for entry in list(data.get("articles", [])) + list(data.get("hubs", [])):
            unknown = sorted(set(entry) - OVERLAY_FIELDS)
            if unknown:
                raise SystemExit(
                    f"{relative}: {entry.get('source')!r} sets derived field(s) {unknown}. "
                    "Those come from the English record."
                )
            overlays[str(entry["source"])] = entry
        loaded[code] = overlays
    return loaded


def check_translation_freshness(
    code: str,
    overlays: dict[str, dict],
    sources: dict[str, dict],
    today: date,
) -> list[str]:
    """English edits that have not reached their translation yet.

    Blocking every English edit until a retranslation lands is not survivable,
    so `stale_ack` carries the new hash, a reason, and an expiry: a warning
    until that date, an error after it. Same shape as editorial-overdue.
    """
    problems: list[str] = []
    for source_path in sorted(overlays):
        overlay = overlays[source_path]
        source = sources.get(source_path)
        if source is None:
            problems.append(f"{code}: {source_path} has no English source record")
            continue
        fragment = (SOURCE_ROOT / str(source["content"])).read_text(encoding="utf-8")
        expected = {"source_hash": source_hash(fragment), "source_meta_hash": meta_hash(source)}
        acknowledged = overlay.get("stale_ack") or {}
        for field, current in expected.items():
            recorded = str(overlay.get(field, ""))
            if recorded == current:
                continue
            if str(acknowledged.get(field, acknowledged.get("source_hash", ""))) == current:
                expires = str(acknowledged.get("expires", ""))
                try:
                    if date.fromisoformat(expires) >= today:
                        continue
                except ValueError:
                    problems.append(f"{code}: {source_path} stale_ack has an invalid expires {expires!r}")
                    continue
                problems.append(
                    f"{code}: {source_path} stale_ack expired on {expires}; retranslate it"
                )
                continue
            problems.append(
                f"{code}: {source_path} is stale ({field}). English is {current}, "
                f"translation recorded {recorded or 'nothing'}"
            )
    return problems


def localize_url(url: str, locale: dict, available: set[str]) -> str:
    """Re-point an absolute site URL at the locale's copy, when one exists.

    Asset URLs survive untouched because they are never in `available`.
    """
    if not url.startswith(SITE_URL):
        return url
    route = url[len(SITE_URL):] or "/"
    return SITE_URL + localized_route(route, locale, available)


def translate_jsonld(
    raw: str,
    overlay: dict,
    source: dict,
    locale: dict,
    available: set[str],
    strings: dict[str, dict[str, str]],
) -> str:
    """Rebuild a JSON-LD block in the target locale.

    Rewritten from the parsed English graph rather than hand-authored, because
    a mistyped @type in a language Jorick cannot read is invisible.
    """
    code = str(locale["code"])
    own_route = SITE_URL + localized_route(route_for(str(source["path"])), locale, available)
    hub_route = SITE_URL + localized_route("/help/", locale, available)
    graph = json.loads(raw)

    def walk(node: object) -> object:
        if isinstance(node, list):
            return [walk(item) for item in node]
        if not isinstance(node, dict):
            return node
        out: dict[str, object] = {}
        for key, value in node.items():
            if key in {"headline", "name"} and node.get("@type") != "ListItem":
                out[key] = str(overlay["headline"]) if key == "headline" else value
            elif key == "description":
                out[key] = str(overlay["description"])
            elif key in {"url", "item"} and isinstance(value, str):
                out[key] = localize_url(value, locale, available)
            else:
                out[key] = walk(value)
        if out.get("@type") == "ListItem":
            item = str(out.get("item", ""))
            if item == own_route:
                out["name"] = str(overlay["headline"])
            elif item == hub_route:
                out["name"] = str(strings["nav.help"][code])
        if out.get("@type") == "Article":
            out["inLanguage"] = code
        return out

    return json.dumps(walk(graph), indent=2, ensure_ascii=False)


def derive_record(
    overlay: dict,
    source: dict,
    locale: dict,
    locales: dict[str, dict],
    translations: dict[str, dict[str, dict]],
    available: set[str],
    strings: dict[str, dict[str, str]],
    *,
    kind: str,
) -> dict[str, object]:
    """A full page record for `source` in `locale`, from prose plus derivation."""
    code = str(locale["code"])
    source_path = str(source["path"])
    record = dict(source)
    record["path"] = f"{code}/{source_path}"
    # og:image has no localized card yet, so the social lookup must still find
    # the English one by the path it was generated for.
    record["social_source_path"] = source_path
    record["content"] = str(overlay["content"])

    suffix_key = "site.title_suffix_help" if kind == "article" else "site.title_suffix"
    title = f"{overlay['headline']}{locale['title_separator']}{strings[suffix_key][code]}"
    description = str(overlay["description"])
    record["title"] = title

    meta: list[dict[str, str]] = []
    for attrs in source.get("meta", []):
        entry = dict(attrs)
        key = entry.get("property") or entry.get("name")
        content = str(entry.get("content", ""))
        if key in {"description", "og:description", "twitter:description"}:
            content = description
        elif key in {"og:title", "twitter:title"}:
            content = title
        else:
            content = localize_url(content, locale, available)
        entry["content"] = content
        meta.append(entry)
    meta.append({"property": "og:locale", "content": str(locale["og_locale"])})
    if locale.get("status") != "published":
        # A draft locale builds and previews but must not be indexed or appear
        # in the sitemap. noindex is what keeps the audit's sitemap agreement
        # check honest while a new language is still being verified.
        meta.append({"name": "robots", "content": "noindex, nofollow"})
    record["meta"] = meta

    links = [
        {**link, "href": localize_url(str(link.get("href", "")), locale, available)}
        for link in source.get("links", [])
    ]
    record["links"] = links + alternate_links(source_path, locales, translations)

    record["jsonld"] = [
        translate_jsonld(str(raw), overlay, source, locale, available, strings)
        for raw in source.get("jsonld", [])
    ]

    if source.get("next_steps"):
        # URLs come from the already-validated English record, so a translation
        # cannot point at a page that does not exist.
        labels = list(overlay.get("next_steps", []))
        if len(labels) != len(source["next_steps"]):
            raise SystemExit(
                f"{record['path']}: next_steps has {len(labels)} entries, "
                f"English has {len(source['next_steps'])}"
            )
        record["next_steps"] = [
            {
                "url": localized_route(str(step["url"]), locale, available),
                "title": str(label["title"]),
                "description": str(label["description"]),
            }
            for step, label in zip(source["next_steps"], labels)
        ]

    if source.get("screenshot_slots"):
        alts = overlay.get("screenshot_alt", {})
        record["screenshot_slots"] = [
            {**slot, "alt": str(alts.get(str(slot["key"]), slot.get("alt", "")))}
            for slot in source["screenshot_slots"]
        ]

    if overlay.get("search_synonyms"):
        # English aliases stay: they are how a Japanese reader who knows the
        # English term on their paperwork still finds the page.
        record["search_synonyms"] = list(source.get("search_synonyms", [])) + list(
            overlay["search_synonyms"]
        )
    return record


def alternate_links(
    source_path: str,
    locales: dict[str, dict],
    translations: dict[str, dict[str, dict]],
) -> list[dict[str, str]]:
    """The reciprocal hreflang set for one page, in every locale that has it.

    Emitted identically on both sides, because Google discards a set whose
    members do not point back at each other. A page with no translation gets
    nothing, which is what keeps this off the other 93 English pages.
    """
    default_code = default_locale_code()
    members: list[tuple[dict, str]] = []
    for code, locale in locales.items():
        if locale.get("status") != "published":
            continue
        if code != default_code and source_path not in translations.get(code, {}):
            continue
        route = f"/{code}{route_for(source_path)}" if code != default_code else route_for(source_path)
        members.append((locale, route))
    if len(members) < 2:
        return []
    links = [
        {"rel": "alternate", "hreflang": str(locale["hreflang"]), "href": SITE_URL + route}
        for locale, route in members
    ]
    fallback = next((route for locale, route in members if locale.get("x_default")), None)
    if fallback:
        links.append({"rel": "alternate", "hreflang": "x-default", "href": SITE_URL + fallback})
    return links


def render_language_switcher(
    source_path: str,
    locales: dict[str, dict],
    translations: dict[str, dict[str, dict]],
    current: str,
    strings: dict[str, dict[str, str]],
    *,
    mobile: bool = False,
    indent: str = "        ",
) -> str:
    """Static links to this page's other languages.

    Every page already knows its alternates because it emits hreflang for them,
    so the switcher is those same links: crawlable, no flash, and correct with
    JavaScript off.
    """
    default_code = default_locale_code()
    others = []
    for link in alternate_links(source_path, locales, translations):
        code = str(link["hreflang"])
        if code in {"x-default", current}:
            continue
        locale = locales.get(code)
        if locale:
            others.append((locale, str(link["href"])))
    if not others:
        return ""
    label = html.escape(str(strings["a11y.language"][current]))
    rows = "".join(
        f'<a href="{html.escape(url[len(SITE_URL):])}" lang="{locale["code"]}" '
        f'hreflang="{locale["hreflang"]}">{html.escape(str(locale["native_name"]))}</a>'
        for locale, url in others
    )
    css = "mobile-menu-lang" if mobile else "lang-switch"
    # Carries its own newline and indent so an untranslated page renders the
    # header byte-for-byte as it did before the switcher existed.
    return f'\n{indent}<nav class="{css}" aria-label="{label}">{rows}</nav>'


def render_article(
    article: dict[str, object],
    template: str,
    header_template: str,
    footer_template: str,
    locale: dict[str, object],
    strings: dict[str, dict[str, str]],
    locales: dict[str, dict],
    translations: dict[str, dict[str, dict]],
) -> str:
    content_path = SOURCE_ROOT / str(article["content"])
    content = content_path.read_text(encoding="utf-8").rstrip()
    prefix = asset_prefix(str(article["path"]))
    source_path = str(article.get("social_source_path", article["path"]))
    code = str(locale["code"])
    switcher = render_language_switcher(source_path, locales, translations, code, strings)
    switcher_mobile = render_language_switcher(
        source_path, locales, translations, code, strings, mobile=True, indent="          "
    )
    # Only routes this locale actually has may be prefixed; everything else
    # falls back to English. Without this the chrome links a Japanese page to
    # /ja/about and friends, which were never built.
    available = {route_for(path) for path in translations.get(code, {})}
    replacements = {
        "{{HTML_LANG}}": str(locale["html_lang"]),
        "{{HTML_CLASS}}": WASH_SUBTLE,
        "{{METADATA}}": render_metadata(article, prefix),
        "{{STRUCTURED_DATA}}": render_structured_data(article),
        "{{STYLESHEETS}}": render_styles(article, "article", prefix),
        "{{SITE_HEADER}}": render_header(
            article, header_template, prefix, switcher, switcher_mobile
        ),
        "{{SITE_FOOTER}}": footer_template.replace("{{ASSET_PREFIX}}", prefix).rstrip(),
        "{{ARTICLE_CONTENT}}": content,
        "{{CLUSTER_RELATED}}": (
            render_help_tail(article, locale, strings) or render_cluster_related(article)
        ),
        "{{ASSET_PREFIX}}": prefix,
    }
    rendered = template
    for marker, value in replacements.items():
        rendered = rendered.replace(marker, value)
    leftovers = [marker for marker in replacements if marker in rendered]
    if leftovers:
        raise SystemExit(f"Unresolved template markers for {article['path']}: {leftovers}")
    rendered = localize(rendered, locale, strings, available_routes=available, context=str(article["path"]))
    return rendered.rstrip() + "\n"


def render_hub(
    hub: dict[str, object],
    template: str,
    header_template: str,
    footer_template: str,
    locale: dict[str, object],
    strings: dict[str, dict[str, str]],
    locales: dict[str, dict],
    translations: dict[str, dict[str, dict]],
    *,
    family: str = "hub",
) -> str:
    content = (SOURCE_ROOT / str(hub["content"])).read_text(encoding="utf-8").rstrip()
    prefix = asset_prefix(str(hub["path"]))
    source_path = str(hub.get("social_source_path", hub["path"]))
    code = str(locale["code"])
    switcher = render_language_switcher(source_path, locales, translations, code, strings)
    switcher_mobile = render_language_switcher(
        source_path, locales, translations, code, strings, mobile=True, indent="          "
    )
    # Only routes this locale actually has may be prefixed; everything else
    # falls back to English. Without this the chrome links a Japanese page to
    # /ja/about and friends, which were never built.
    available = {route_for(path) for path in translations.get(code, {})}
    replacements = {
        "{{HTML_LANG}}": str(locale["html_lang"]),
        # Hubs are marketing surfaces and take the full wash; the legal and
        # about pages built through this same template are long-form reading
        # and step down with the articles.
        "{{HTML_CLASS}}": WASH_SUBTLE if family == "page" else "",
        "{{METADATA}}": render_metadata(hub, prefix),
        "{{STRUCTURED_DATA}}": render_structured_data(hub),
        "{{STYLESHEETS}}": render_styles(hub, family, prefix),
        "{{SITE_HEADER}}": render_header(hub, header_template, prefix, switcher, switcher_mobile),
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
    rendered = localize(rendered, locale, strings, available_routes=available, context=str(hub["path"]))
    return rendered.rstrip() + "\n"


def main() -> int:
    args = parse_args()
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    validate_help_next_steps(data.get("articles", []))
    locales = load_locales()
    locale = locales[default_locale_code()]
    strings = load_ui_strings()
    translations = load_translations(locales)
    hub_data = json.loads(HUB_DATA_PATH.read_text(encoding="utf-8")) if HUB_DATA_PATH.exists() else {"hubs": []}
    sources = {str(record["path"]): record for record in data.get("articles", [])}
    hub_sources = {str(record["path"]): record for record in hub_data.get("hubs", [])}

    stale = [
        problem
        for code, overlays in translations.items()
        for problem in check_translation_freshness(code, overlays, {**sources, **hub_sources}, date.today())
    ]
    if stale:
        print("Refusing to build: a translation no longer matches its English source.")
        for problem in stale:
            print(f"  {problem}")
        print(
            "\nRetranslate the page and record the new hash, or add a stale_ack with an\n"
            "expiry if the English edit does not change the meaning."
        )
        return 1

    def with_alternates(record: dict[str, object]) -> dict[str, object]:
        """English pages advertise their translations; untranslated ones stay bare."""
        alternates = alternate_links(str(record["path"]), locales, translations)
        if not alternates:
            return record
        return {**record, "links": list(record.get("links", [])) + alternates}

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
            render_article(
                with_alternates(article), template, header_template, footer_template,
                locale, strings, locales, translations,
            ),
        )

    if args.section == "all":
        for hub in hub_data.get("hubs", []):
            queue(
                SITE_ROOT / str(hub["path"]),
                render_hub(
                    with_alternates(hub), hub_template, header_template, footer_template,
                    locale, strings, locales, translations,
                ),
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
                    locale,
                    strings,
                    locales,
                    translations,
                    family="page",
                ),
                guard=True,
            )

    for code, overlays in translations.items():
        if code == default_locale_code() or not overlays:
            continue
        target = locales[code]
        available = {route_for(path) for path in overlays}
        for source_path in sorted(overlays):
            source = sources.get(source_path) or hub_sources[source_path]
            kind = "article" if source_path in sources else "hub"
            if args.section != "all" and source.get("section") != args.section:
                continue
            record = derive_record(
                overlays[source_path], source, target, locales, translations,
                available, strings, kind=kind,
            )
            renderer = render_article if kind == "article" else render_hub
            queue(
                SITE_ROOT / str(record["path"]),
                renderer(
                    record,
                    template if kind == "article" else hub_template,
                    header_template, footer_template,
                    target, strings, locales, translations,
                ),
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
