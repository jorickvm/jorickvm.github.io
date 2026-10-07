#!/usr/bin/env python3
"""Build generated AtlasDays article pages into their public paths."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path

from build_route_outputs import ROUTES, expanded_routes, llms_files, sitemap_files
from locales import (
    default_locale_code,
    description_of,
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
STANDALONE_TEMPLATE = SOURCE_ROOT / "templates" / "standalone.html"
HEADER_TEMPLATE = SOURCE_ROOT / "templates" / "partials" / "site-header.html"
FOOTER_TEMPLATE = SOURCE_ROOT / "templates" / "partials" / "site-footer.html"
REDIRECT_TEMPLATE = SOURCE_ROOT / "templates" / "redirect.html"
CLUSTER_DATA_PATH = SOURCE_ROOT / "data" / "content-clusters.json"
BUILD_VERSION = "20260928f"
VARIANT_VERSIONS = {("article", "help20260802"): "20260928f", ("hub", "92c3adc0daf3"): "20260928f", ("article", "49dd6e3e3ea5"): "20261005a", ("article", "88b8694b8f2d"): "20261005a"}
SITE_HEADER_VERSION = "20260930a"
SITE_FOOTER_VERSION = "20261006a"
ARTICLE_COMPONENTS_VERSION = "20261006a"
RULE_CARDS_VERSION = "20261006b"
NAVIGATION_VERSION = "20261005a"

# Root class that drops the background wash from the app's `.medium` step to
# `.subtle`, for pages carrying long-form text. See assets/css/tokens.css.
WASH_SUBTLE = ' class="wash-subtle"'


def redirect_outputs(locales, translations, sources, strings):
    """Merged Learn routes remain generated and covered by --check in each locale."""
    registry = json.loads((SOURCE_ROOT / "data/redirects.json").read_text(encoding="utf-8"))
    template = REDIRECT_TEMPLATE.read_text(encoding="utf-8")
    for code, locale in locales.items():
        for old, target in registry.items():
            record = sources[target] if code == default_locale_code() else translations.get(code, {}).get(target)
            if not record:
                if locale.get("status") == "draft":
                    continue
                raise ValueError(f"{code}: redirect target has no translation: {target}")
            prefix = locale.get("route_prefix", "")
            href = prefix + "/" + target.removesuffix(".html")
            headline = record.get("headline") or str(record["title"]).removesuffix(" – AtlasDays")
            title = html.escape(headline)
            description = record.get("description") or description_of(record)
            message = html.escape(strings["help.continue"][code])
            colon = html.escape(locale.get("label_colon", ":"))
            replacements = {
                "{{HTML_LANG}}": html.escape(locale["html_lang"]),
                "{{TITLE}}": title + html.escape(locale["title_separator"]) + "AtlasDays",
                "{{HEADLINE}}": title,
                "{{DESCRIPTION}}": html.escape(description, quote=True),
                "{{TARGET}}": html.escape(href, quote=True),
                "{{CONTINUE}}": message,
                "{{COLON}}": colon,
            }
            rendered = template
            for marker, value in replacements.items():
                rendered = rendered.replace(marker, value)
            yield SITE_ROOT / (prefix.lstrip("/") + "/" + old).lstrip("/"), rendered


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

# Sources carry the plain App Store URL; the build swaps every clickable link to
# it for an App Store Connect campaign link, so downloads from the site show up
# under Sources > Campaigns. Done here rather than in the fragments because the
# URL sits in every English fragment, and editing those would mark every
# translation stale. Only `href` is rewritten: the smart-banner app-argument,
# JSON-LD, and llms.txt keep the canonical URL. One campaign (`ct=web`) for the
# whole site until traffic is high enough to split it past Apple's threshold.
APP_STORE_URL = "https://apps.apple.com/app/atlasdays-track-country-days/id6760133544"
APP_STORE_CAMPAIGN_URL = "https://apps.apple.com/app/apple-store/id6760133544?pt=128618782&amp;ct=web&amp;mt=8"


def with_campaign_links(rendered: str) -> str:
    return rendered.replace(f'href="{APP_STORE_URL}"', f'href="{APP_STORE_CAMPAIGN_URL}"')


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

    404.html is the exception, because it is the one page not served from where
    it lives: Pages returns it for any missing URL, at any depth, with the
    requested path still in the address bar. A hop computed from the file's own
    location then resolves against the visitor's URL instead, so a miss at
    /learn/typo would look for /learn/assets/css/tokens.css and render the page
    unstyled. Root-absolute links resolve the same from every depth.
    """
    if Path(str(path)).name == "404.html":
        return "/"
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
                    {"property": "og:image:alt", "content": str(article.get("social_alt", social["alt"]))},
                    {"name": "twitter:image", "content": image_url},
                    {"name": "twitter:image:alt", "content": str(article.get("social_alt", social["alt"]))},
                ]
            )
    for attrs in meta:
        lines.append(f"  <meta {attrs_html(dict(attrs))} />")
    for attrs in article.get("links", []):
        lines.append(f"  <link {attrs_html(dict(attrs))} />")
    lines.append(
        f'  <link rel="icon" type="image/png" sizes="192x192" href="{prefix}assets/brand/favicon.png" />'
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
    if article.get("stylesheets"):
        return "\n".join(
            f'  <link rel="stylesheet" href="{prefix}{path}" />'
            for path in article["stylesheets"]
        )
    # tokens.css first: it owns the palette, wash, and card surface for every
    # page, and the variant stylesheets that follow carry layout only.
    lines = [f'  <link rel="stylesheet" href="{prefix}assets/css/tokens.css?v={asset_version}" />']
    lines += [
        f'  <link rel="stylesheet" href="{prefix}assets/css/{family}-variants/{style_id}.css?v={VARIANT_VERSIONS.get((family, str(style_id)), asset_version)}" />'
        for style_id in article.get("style_variants", [])
    ]
    lines.append(
        f'  <link rel="stylesheet" href="{prefix}assets/css/site-header.css?v={SITE_HEADER_VERSION}" />'
    )
    if family == "article":
        lines.append(
            f'  <link rel="stylesheet" href="{prefix}assets/css/article-components.css?v={ARTICLE_COMPONENTS_VERSION}" />'
        )
        if article.get("section") == "learn":
            lines.append(f'  <link rel="stylesheet" href="{prefix}assets/css/rule-cards.css?v={RULE_CARDS_VERSION}" />')
    lines.append(f'  <link rel="stylesheet" href="{prefix}assets/css/site-footer.css?v={SITE_FOOTER_VERSION}" />')
    return "\n".join(lines)


def render_header(
    article: dict[str, object],
    template: str,
    prefix: str = "../",
    switcher: str = "",
) -> str:
    section = str(article.get("current_navigation", article.get("section", "")))
    return (
        template.replace("{{ASSET_PREFIX}}", prefix)
        .replace("{{LANGUAGE_SWITCHER}}", switcher)
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


def render_nav_script(prefix: str, code: str, strings: dict[str, dict[str, str]]) -> str:
    """navigation.js plus the two labels it cannot read from the DOM.

    The drawer's summary carries a translated aria-label from the header
    partial, and the script rewrites it on open/close so a screen reader is not
    told to "open" a menu that is already open. Those two labels used to be
    English literals in the script, which is one file served to every locale:
    a Japanese reader's accessible name flipped to English on the first tap.
    Same shape as the search strings, for the same reason.
    """
    copy = json.dumps(
        {
            "menuOpen": strings["nav.menu_open"][code],
            "menuClose": strings["nav.menu_close"][code],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    return (
        f"  <script>window.AtlasDaysNavStrings={copy};</script>\n"
        f'  <script src="{prefix}assets/js/navigation.js?v={NAVIGATION_VERSION}"></script>'
    )


RELATED_LIMIT = 6
REGIONS_PATH = SOURCE_ROOT / "data" / "regions.json"
EDITORIAL_DATA_PATH = SOURCE_ROOT / "data" / "editorial.json"
CALCULATOR_PAGES = ("learn/183-day-rule-calculator.html", "learn/schengen-calculator.html", "learn/uk-ilr-absence-calculator.html")
# The guide that explains how each kind of rule counts.
TOPIC_GUIDES = {
    "tax": "learn/183-day-tax-residency-rule.html",
    "usState": "learn/183-day-tax-residency-rule.html",
    "visa": "learn/what-counts-as-a-day-for-visa-purposes.html",
    "residence": "learn/residence-permit-citizenship-absence-rules.html",
    "citizenship": "learn/residence-permit-citizenship-absence-rules.html",
}
FAMILY_ORDER = ("visa", "tax", "usState", "residence", "citizenship")
GLOBE_ICON = (
    '<span class="rule-icon"><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="8.5"/>'
    '<path d="M3.5 12h17M12 3.5c2.5 2.6 3.5 5.4 3.5 8.5s-1 5.9-3.5 8.5c-2.5-2.6-3.5-5.4-3.5-8.5s1-5.9 3.5-8.5Z"/></svg></span>'
)
RELATED_ICON = (
    '<span class="rule-icon"><svg viewBox="0 0 24 24" fill="none" aria-hidden="true">'
    '<path d="M6 4.5h9l3 3v12H6z"/><path d="M9 11h6M9 14.5h6"/></svg></span>'
)
_related: dict[str, object] = {}


def _hub_sections(name: str) -> list[list[str]]:
    """The article paths a hub fragment lists, section by section, in page order."""
    text = (SOURCE_ROOT / "content" / "hubs" / name).read_text(encoding="utf-8")
    return [
        [f"learn/{slug}.html" for slug in re.findall(r'href="/learn/([^"#/]+)', section)]
        for section in re.split(r"<section\b", text)[1:]
    ]


def _related_index() -> dict[str, object]:
    """Family, country and region of every Learn article, read once."""
    if _related:
        return _related
    records = json.loads(DATA_PATH.read_text(encoding="utf-8"))["articles"]
    presets = json.loads(APP_CATALOG_PATH.read_text(encoding="utf-8"))["presets"]
    own = json.loads(LEARN_CARDS_PATH.read_text(encoding="utf-8"))["cards"]
    editorial = {e["path"]: e for e in json.loads(EDITORIAL_DATA_PATH.read_text(encoding="utf-8"))["articles"]}
    clusters = {c["path"]: c for c in json.loads(CLUSTER_DATA_PATH.read_text(encoding="utf-8"))["clusters"]}
    regions = json.loads(REGIONS_PATH.read_text(encoding="utf-8"))["regions"]
    region_of = {code: name for name, codes in regions.items() for code in codes}
    # Each region lists its countries roughly in geographic order.
    place_of = {code: place for codes in regions.values() for place, code in enumerate(codes)}
    info: dict[str, dict[str, object]] = {}
    for record in records:
        path = str(record["path"])
        if record.get("section") != "learn":
            continue
        family = flag = rank = None
        if record.get("app_preset"):
            preset = presets[record["app_preset"]]
            family, flag, rank = preset["family"], preset["flag"], preset["rank"]["en"]
        elif path in own:
            family, flag = own[path]["family"], own[path]["flag"]
        info[path] = {
            "family": family,
            "flag": flag,
            "jurisdiction": str(editorial.get(path, {}).get("jurisdiction", "")),
            "embedded": record.get("calculator") is not None,
            "pillar": clusters.get(path, {}).get("pillar"),
            "cluster": clusters.get(path, {}).get("cluster"),
            # The app's catalogue order, which puts the most used rules first.
            "rank": rank,
        }
    # A country is its flag; an article flagged EU for a national rule (Spain's
    # EU long-term residence) and a guide without a flag take the country its
    # jurisdiction names.
    country_of = {"Schengen Area": "EU"}
    for item in info.values():
        if item["flag"] and item["flag"] != "EU" and item["jurisdiction"] != "Multiple jurisdictions":
            country_of.setdefault(item["jurisdiction"], item["flag"])
    for item in info.values():
        item["country"] = country_of.get(item["jurisdiction"]) or item["flag"]
        item["region"] = region_of.get(str(item["country"]))
        item["place"] = place_of.get(str(item["country"]), 0)
    _related.update(info=info, guides=_hub_sections("learn-guides.html"), calculators=_hub_sections("learn-calculators.html"))
    return _related


def related_paths(path: str) -> list[str]:
    """The Learn pages most related to one, best first.

    Rule articles: the same country's other rules (the same kind of rule
    first), the calculator for the rule, the guide that explains how it
    counts, the country's guides and calculators, the topic overview, then the
    same kind of rule in the same region (regions.json, nearest first), and
    elsewhere only to reach four. Guides: the same country's pages, their section of the guides
    page, then their topic cluster when it is small. Calculator pages: their
    section of the calculators page, the country's pages, the topic guide.
    """
    index = _related_index()
    info: dict[str, dict[str, object]] = index["info"]  # type: ignore[assignment]
    me = info.get(path)
    if not me:
        return []
    out: list[str] = []

    def add(candidate: object) -> None:
        if candidate and candidate != path and candidate not in out:
            out.append(str(candidate))

    family, country = me["family"], me["country"]

    def ranked(paths: list[str]) -> list[str]:
        return sorted(paths, key=lambda p: (
            info[p]["family"] != family,
            FAMILY_ORDER.index(info[p]["family"]) if info[p]["family"] in FAMILY_ORDER else len(FAMILY_ORDER),
            p,
        ))

    cluster_size = Counter(i["cluster"] for i in info.values())

    def by_app_order(paths: object) -> list[str]:
        return sorted(paths, key=lambda p: (info[p]["rank"] is None, info[p]["rank"] or 0, p))  # type: ignore[arg-type, union-attr]
    same_country = ranked([p for p, i in info.items() if p != path and country and i["country"] == country and i["family"]])
    # The country's calculator first, then its guides.
    country_pages = sorted(
        (p for p, i in info.items() if p != path and country and i["country"] == country and not i["family"]),
        key=lambda p: (p not in CALCULATOR_PAGES, p),
    )
    if path in CALCULATOR_PAGES:
        for section in index["calculators"]:  # type: ignore[union-attr]
            if path in section:
                for candidate in section:
                    add(candidate)
        for candidate in same_country + country_pages:
            add(candidate)
        if path == "learn/183-day-rule-calculator.html":
            add(TOPIC_GUIDES["tax"])
            add(me["pillar"])
        elif path == "learn/schengen-calculator.html":
            add("learn/schengen-rolling-window-walkthrough.html")
    elif not family:
        for candidate in same_country + country_pages:
            add(candidate)
        for section in index["guides"]:  # type: ignore[union-attr]
            if path in section:
                for candidate in section:
                    add(candidate)
        if cluster_size[me["cluster"]] <= 10:
            add(me["pillar"])
            for candidate in sorted(p for p, i in info.items() if i["cluster"] == me["cluster"]):
                add(candidate)
    else:
        for candidate in same_country[:3]:
            add(candidate)
        if not me["embedded"]:
            if family in ("tax", "usState"):
                add("learn/183-day-rule-calculator.html")
            elif country == "EU":
                add("learn/schengen-calculator.html")
            elif country == "GB" and family in ("residence", "citizenship"):
                add("learn/uk-ilr-absence-calculator.html")
        add("learn/schengen-rolling-window-walkthrough.html" if country == "EU" else TOPIC_GUIDES.get(str(family)))
        for candidate in country_pages:
            add(candidate)
        add(me["pillar"])
        neighbours = [p for p, i in info.items() if i["family"] == family and me["region"] and i["region"] == me["region"]]
        for candidate in sorted(by_app_order(neighbours), key=lambda p: abs(info[p]["place"] - me["place"])):  # type: ignore[operator]
            add(candidate)
        for candidate in by_app_order(p for p, i in info.items() if i["family"] == family):
            if len(out) >= 4:
                break
            add(candidate)
    return out[:RELATED_LIMIT]


def related_card(path: str, locale: dict[str, object], available: set[str], title: str) -> str:
    """A related page as a card with the article's own title and nothing under
    it: a guide or calculator keeps the icon or flag its hub page gives it, a
    rule article shows its flag, anything else a page icon."""
    slug = Path(path).stem
    for hub in ("learn-guides.html", "learn-calculators.html"):
        fragment = SOURCE_ROOT / str(locale.get("content_prefix", "content")) / "hubs" / hub
        if fragment.exists():
            found = re.search(r'<a class="rule-card[^"]*" href="[^"#]*/learn/' + re.escape(slug) + r'">.*?</a>', fragment.read_text(encoding="utf-8"), re.S)
            if found:
                return re.sub(r"<strong>.*?</strong>(<span>.*?</span>)?", lambda _: f"<strong>{html.escape(title)}</strong>", found.group(0), count=1, flags=re.S)
    href = html.escape(localized_route(route_for(path), locale, available), quote=True)
    flag = _related_index()["info"].get(path, {}).get("flag")  # type: ignore[union-attr]
    image = (
        f'<img class="rule-flag" src="/assets/flags/{str(flag).lower()}.png" alt="" width="36" height="25" loading="lazy" />'
        if flag else RELATED_ICON
    )
    return f'<a class="rule-card" href="{href}">{image}<span class="rule-text"><strong>{html.escape(title)}</strong></span></a>'


def english_h1(record: dict[str, object]) -> str:
    """The English page's visible title: the <h1> of its fragment, else its
    <title> without the site suffix."""
    content = record.get("content")
    if content and (SOURCE_ROOT / str(content)).exists():
        found = re.search(r"<h1[^>]*>(.*?)</h1>", (SOURCE_ROOT / str(content)).read_text(encoding="utf-8"), re.S)
        if found:
            return html.unescape(re.sub(r"<[^>]+>", "", found.group(1))).strip()
    return str(record["title"]).replace(" – AtlasDays Help Center", "").replace(" – AtlasDays", "")


TITLE_WIDTH = 65


def title_width(title: str) -> int:
    """Roughly what a title occupies in a search result: a CJK or Hangul
    character takes the room of two Latin ones."""
    return sum(2 if unicodedata.east_asian_width(char) in "WF" else 1 for char in title)


def title_budget(source: dict[str, object]) -> int:
    """How long a translated title may be: what Google shows, or the English
    title's own length when that is longer."""
    return max(TITLE_WIDTH, len(str(source.get("title", ""))))


def render_cluster_related(
    article: dict[str, object],
    locale: dict[str, object],
    translations: dict[str, dict[str, dict]],
) -> str:
    if article.get("section") != "learn":
        return ""
    source_path = str(article.get("social_source_path", article["path"]))
    article_data = json.loads(DATA_PATH.read_text(encoding="utf-8"))["articles"]
    hub_data = json.loads(HUB_DATA_PATH.read_text(encoding="utf-8"))["hubs"] if HUB_DATA_PATH.exists() else []
    titles = {item["path"]: english_h1(item) for item in article_data + hub_data}
    ordered = related_paths(source_path)
    code = str(locale["code"])
    available = {route_for(path) for path in translations.get(code, {})}
    if code != "en":
        # A page this locale has not translated yet (published English first,
        # or listed under `untranslated`) is not offered here in English.
        ordered = [path for path in ordered if path in translations.get(code, {})]
    cards = []
    for path in ordered:
        overlay = translations.get(code, {}).get(path)
        title = str(overlay["headline"]) if overlay else titles.get(path, "")
        if title:
            cards.append("        " + related_card(path, locale, available, title))
    if not cards:
        return ""
    identifier = "related-" + Path(source_path).stem
    return "\n".join(
        [
            f'    <nav class="related generated-related" aria-labelledby="{identifier}">',
            f'      <h2 id="{identifier}">{{{{t:related.heading}}}}</h2>',
            '      <div class="rule-cards">',
            *cards,
            "      </div>",
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
    "page_title",
    "description",
    "content",
    "next_steps",
    "screenshot_alt",
    "search_synonyms",
    "jsonld_replacements",
    "social_alt",
    "source_hash",
    "source_meta_hash",
    "translated_on",
    "translated_by",
    "stale_ack",
    "source_note",
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
            # Registering the locale comes first and writing its registry comes
            # later, so a draft locale legitimately points at a file that does
            # not exist yet; `check_translations.py` has always tolerated that.
            # Only a published locale must have one, because that is the point
            # at which readers can reach the pages.
            if locale.get("status") != "published":
                continue
            raise SystemExit(f"Locale {code!r} points at a missing registry: {relative}")
        data = json.loads(path.read_text(encoding="utf-8"))
        overlays: dict[str, dict] = {}
        for entry in (
            list(data.get("articles", []))
            + list(data.get("hubs", []))
            + list(data.get("pages", []))
        ):
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


FAQ_PAIR = re.compile(r"<h3\b[^>]*>((?:(?!</h3>).)*)</h3>\s*<p\b[^>]*>(.*?)</p>", re.DOTALL)
MARKUP = re.compile(r"<[^>]+>")


def faq_pairs(fragment: str) -> list[tuple[str, str]]:
    """Every `<h3>` question and the `<p>` answer under it, in document order."""
    return [
        (" ".join(MARKUP.sub("", q).split()), " ".join(MARKUP.sub("", a).split()))
        for q, a in FAQ_PAIR.findall(fragment)
    ]


def faq_strings(graph: object) -> list[str]:
    """Every question and answer in a `FAQPage` graph, in order."""
    if not isinstance(graph, dict) or graph.get("@type") != "FAQPage":
        return []
    out: list[str] = []
    for question in graph.get("mainEntity", []):
        if not isinstance(question, dict):
            continue
        out.append(str(question.get("name", "")))
        answer = question.get("acceptedAnswer")
        if isinstance(answer, dict):
            out.append(str(answer.get("text", "")))
    return [text for text in out if text]


def derived_faq_replacements(overlay: dict, source: dict, label: str) -> dict[str, str]:
    """Localized FAQ strings lifted out of the translated fragment.

    The visible FAQ and the `FAQPage` graph are the same content. Asking a
    translator to supply it twice, once as prose and once in the overlay, is how
    the two drift: Dutch shipped 57 Learn pages whose visible FAQ was Dutch and
    whose structured data was still English, because nothing fails when the
    second copy is simply absent. Deriving it means the translation is written
    once, in the fragment, and the graph follows it for free.

    Positional, because the question text is exactly what changed. That is only
    safe while the two fragments have the same shape, so a mismatch raises
    instead of emitting a graph that is half translated.
    """
    english = faq_pairs((SOURCE_ROOT / str(source["content"])).read_text(encoding="utf-8"))
    if not english:
        return {}
    translated = faq_pairs((SOURCE_ROOT / str(overlay["content"])).read_text(encoding="utf-8"))
    if len(translated) != len(english):
        raise SystemExit(
            f"{label}: {len(english)} question-and-answer blocks in English, "
            f"{len(translated)} in the translation; the FAQ graph cannot be derived"
        )
    pairs: dict[str, str] = {}
    for (en_q, en_a), (loc_q, loc_a) in zip(english, translated):
        pairs[en_q] = loc_q
        pairs[en_a] = loc_a
    return pairs


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
    # Every hub a breadcrumb can point at, not just Help. Japanese was Help-only
    # when this was written, so hardcoding /help/ was invisible until Dutch
    # shipped Learn and 80 pages published a "Travel Rules" crumb inside
    # otherwise-Dutch structured data. The name is localized even when the URL
    # still resolves to English, because it has to match the visible breadcrumb.
    hub_routes = {
        SITE_URL + localized_route(route, locale, available): key
        for route, key in (
            ("/help/", "nav.help"),
            ("/learn/", "nav.learn"),
            ("/learn/guides", "nav.guides"),
            ("/learn/calculators", "nav.calculators"),
        )
    }
    graph = json.loads(raw)
    label = f"{code}/{source['path']}"
    # The English headline is the page title without its " – AtlasDays" suffix;
    # each JSON-LD block is rewritten on its own, so it cannot come from the graph.
    english_headline = str(source.get("title", "")).rsplit(" – ", 1)[0]
    # Derived first, so an explicit `jsonld_replacements` entry still wins: the
    # homepage sets strings that are not FAQ prose, and any article can override
    # a derived pair without giving up the derivation for the rest.
    replacements = {
        **derived_faq_replacements(overlay, source, label),
        **{
            str(key): str(value)
            for key, value in dict(overlay.get("jsonld_replacements", {})).items()
        },
    }

    def walk(node: object) -> object:
        if isinstance(node, list):
            return [walk(item) for item in node]
        if not isinstance(node, dict):
            return node
        out: dict[str, object] = {}
        for key, value in node.items():
            if key in {"headline", "name"} and node.get("@type") != "ListItem":
                # A name that is the page's own English headline (a calculator's
                # WebApplication) takes the translated headline, like `headline`.
                # The brand is a name, never a headline to translate: the
                # homepage title leads with it, so it can look like one.
                out[key] = (
                    str(overlay["headline"])
                    if key == "headline" or (str(value) == english_headline and str(value) != "AtlasDays")
                    else replacements.get(str(value), value)
                )
            elif key == "description":
                out[key] = replacements.get(str(value), str(overlay["description"]))
            elif key == "text" and isinstance(value, str):
                out[key] = replacements.get(value, value)
            elif key in {"url", "item"} and isinstance(value, str):
                out[key] = localize_url(value, locale, available)
            else:
                out[key] = walk(value)
        if out.get("@type") == "ListItem":
            item = str(out.get("item", ""))
            if item == own_route:
                out["name"] = str(overlay["headline"])
            elif item in hub_routes:
                out["name"] = str(strings[hub_routes[item]][code])
        if out.get("@type") == "Article":
            out["inLanguage"] = code
        return out

    rendered = walk(graph)
    # The gate that makes any of this trustworthy, because the failure it
    # catches is silent: an unreplaced key leaves English in the graph, and the
    # page still builds and still reads correctly to anyone looking at it.
    #
    # It cannot be a plain hard failure yet. Dutch shipped 52 Learn pages whose
    # FAQ graph is still English, and those need real translation rather than a
    # code change, so they are enumerated in `faq_graph_english` and checked in
    # both directions: a page not on the list may not strand English, and a page
    # on the list must actually still strand some, so the list shrinks as the
    # debt is paid and can never quietly grow. Same contract as `untranslated`.
    if code != default_locale_code() and faq_strings(graph):
        english = set(faq_strings(graph))
        stranded = [
            text
            for text in faq_strings(rendered)
            if text in english and replacements.get(text) != text
        ]
        known = str(source["path"]) in set(locale.get("faq_graph_english", []))
        if stranded and not known:
            raise SystemExit(
                f"{label}: FAQ structured data is still English after translation: "
                f"{stranded[0]!r}. Add the localized question and answer to this "
                "overlay's jsonld_replacements."
            )
        if known and not stranded:
            raise SystemExit(
                f"{label}: listed in faq_graph_english for {code}, but its FAQ graph "
                "is fully translated. Remove the entry."
            )
    return json.dumps(rendered, indent=2, ensure_ascii=False)


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
    if "source_note" in overlay:
        record["source_note"] = str(overlay["source_note"])

    # The suffix follows the section, not the template. Japanese was the only
    # translated locale for a while and it only had Help, so "article" and
    # "Help Center" were the same thing; a Dutch Learn article is an article
    # that is not Help.
    suffix_key = (
        "site.title_suffix_help"
        if kind == "article" and str(source.get("section", "")) == "help"
        else "site.title_suffix"
    )
    # Search words first, the brand only where it fits (Jorick, 2026-10-06):
    # Google shows the site name on its own line, so the " – AtlasDays" suffix
    # is added only while the title stays within what Google shows, never at
    # the cost of a search word. A title that already names AtlasDays (the
    # homepage leads with it) is left as written.
    suffix = f"{locale['title_separator']}{strings[suffix_key][code]}"
    title = str(overlay.get("page_title") or overlay["headline"])
    if "AtlasDays" not in title and title_width(title + suffix) <= title_budget(source):
        title += suffix
    description = str(overlay["description"])
    record["title"] = title
    record["social_alt"] = str(
        overlay.get("social_alt")
        or strings["social.card_alt"][code].format(title=str(overlay["headline"]))
    )

    meta: list[dict[str, str]] = []
    for attrs in source.get("meta", []):
        entry = dict(attrs)
        key = entry.get("property") or entry.get("name")
        content = str(entry.get("content", ""))
        if key in {"description", "og:description", "twitter:description"}:
            content = description
        elif key in {"og:title", "twitter:title"}:
            content = title
        elif str(entry.get("http-equiv", "")).lower() == "refresh":
            content = re.sub(
                r"(?i)(url=)(/[^; ]*)",
                lambda match: match.group(1) + localized_route(match.group(2), locale, available),
                content,
            )
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
    # A draft locale emits no alternate set at all. `alternate_links` lists only
    # published locales, so a draft page would otherwise advertise en and nl
    # while omitting itself, and the published pages would not point back: a
    # one-way hreflang cluster, which is a worse signal than none. noindex plus
    # no alternates is what "invisible until verified" actually means.
    record["links"] = links + (
        alternate_links(source_path, locales, translations)
        if source.get("locale_alternates") is not False and locale.get("status") == "published"
        else []
    )

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
    indent: str = "        ",
) -> str:
    """A compact menu of this page's available languages.

    Every page already knows its alternates because it emits hreflang for them,
    so the menu is built from those same links: crawlable, no flash, and correct
    with JavaScript off. One disclosure stays the same width as the site grows
    from two languages to many.
    """
    available = []
    for link in alternate_links(source_path, locales, translations):
        code = str(link["hreflang"])
        if code == "x-default":
            continue
        locale = locales.get(code)
        if locale:
            available.append((locale, str(link["href"])))
    available.sort(
        key=lambda item: (
            str(
                item[0].get("language_menu_english_name")
                or item[0].get("english_name", item[0]["native_name"])
            ).casefold(),
            str(item[0]["code"]),
        )
    )
    if len(available) < 2:
        return ""
    label = html.escape(str(strings["a11y.language"][current]))
    current_locale = locales[current]
    rows = []
    for locale, url in available:
        name = html.escape(str(locale["native_name"]))
        english_name = html.escape(
            str(
                locale.get("language_menu_english_name")
                or locale.get("english_name", locale["native_name"])
            )
        )
        code = str(locale["code"])
        secondary_name = (
            f'<span class="lang-switch-english" lang="en">{english_name}</span>'
            if english_name.casefold() != name.casefold()
            else ""
        )
        names = (
            f'<span class="lang-switch-label"><span class="lang-switch-native">{name}</span>'
            f'{secondary_name}</span>'
        )
        check = (
            '<svg class="lang-switch-check" width="15" height="15" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true">'
            '<path d="m5 12 4 4L19 6"/></svg>'
        )
        if code == current:
            rows.append(
                f'<span class="lang-switch-option is-current" lang="{code}" '
                f'aria-current="true">{check}{names}</span>'
            )
        else:
            rows.append(
                f'<a class="lang-switch-option" href="{html.escape(url[len(SITE_URL):])}" '
                f'lang="{code}" hreflang="{locale["hreflang"]}">'
                f'<span class="lang-switch-check" aria-hidden="true"></span>{names}</a>'
            )
    current_name = html.escape(str(current_locale["native_name"]))
    globe = (
        '<svg class="lang-switch-globe" width="16" height="16" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="1.9" aria-hidden="true">'
        '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/></svg>'
    )
    caret = (
        '<svg class="lang-switch-caret" width="12" height="12" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">'
        '<path d="m6 9 6 6 6-6"/></svg>'
    )
    # Carries its own leading newline and indentation so a page without
    # alternates renders its surrounding header exactly as before.
    return (
        f'\n{indent}<details class="lang-switch">'
        f'<summary aria-label="{label}" title="{label}">{globe}'
        f'<span class="lang-switch-current">{current_name}</span>{caret}</summary>'
        f'<nav class="lang-switch-panel" aria-label="{label}">{"".join(rows)}</nav>'
        '</details>'
    )


SOURCE_MARKER = re.compile(r"\{\{source:(\d+)\}\}")
FACTBOX_PATTERN = re.compile(
    r'(<div class="factbox">\s*<dl>)(.*?)(</dl>\s*</div>)', re.DOTALL
)
LEGAL_BASIS_PATTERN = re.compile(
    r'(<div class="legal-basis">\s*<dt>.*?</dt>\s*<dd>)(.*?)(</dd>\s*</div>)',
    re.DOTALL,
)


def official_source_urls(article: dict[str, object]) -> list[str]:
    urls: list[str] = []
    for source in article.get("sources", []):
        if not isinstance(source, dict) or not source.get("url"):
            raise SystemExit(f"Invalid official source metadata: {article['path']}")
        urls.append(str(source["url"]))
    return urls


def hydrate_source_note(note: str, article: dict[str, object]) -> str:
    urls = official_source_urls(article)

    def replace(match: re.Match[str]) -> str:
        index = int(match.group(1))
        if index >= len(urls):
            raise SystemExit(
                f"Official source marker {index} is out of range: {article['path']}"
            )
        return html.escape(urls[index], quote=True)

    rendered = SOURCE_MARKER.sub(replace, note)
    if "{{source:" in rendered:
        raise SystemExit(f"Unresolved official source marker: {article['path']}")
    return rendered


def render_factbox_legal_basis(
    content: str,
    article: dict[str, object],
) -> str:
    """Add the source-owned legal-basis row when the fragment lacks one.

    The row is deliberately not a link. It used to carry one to the statute it
    names, which made the factbox the earliest outbound link on the page, above
    the fold and well before the download CTA: the citation a reader is most
    likely to click is the one that sends them away before they have read the
    article. Jorick's call (2026-08-17). The statute text stays, because naming
    it is the point, and 50 of the 56 pages that show this row already link the
    same URL further down in prose or in the Official source card, with the
    remaining six linking four or more other official sources. Nothing loses
    its citation trail; it just stops competing with the CTA from row one.
    """
    if article.get("section") != "learn" or 'class="factbox"' not in content:
        return content
    if LEGAL_BASIS_PATTERN.search(content):
        return content
    citation = article.get("legal_basis")
    if not citation:
        return content

    def update_factbox(match: re.Match[str]) -> str:
        body = match.group(2).rstrip() + (
            '\n        <div class="legal-basis"><dt>{{t:learn.legal_basis}}</dt>'
            f'<dd>{html.escape(str(citation))}</dd></div>\n      '
        )
        return match.group(1) + body + match.group(3)

    return FACTBOX_PATTERN.sub(update_factbox, content, count=1)


def render_learn_trust(
    content: str,
    article: dict[str, object],
    locale: dict[str, object],
    strings: dict[str, dict[str, str]],
) -> str:
    """Close Learn with the source citation, then the advice boundary as prose.

    The citation is a card because it is a claim about provenance the reader
    may want to follow. The advice boundary is not: it is the same sentence on
    every Learn page, and boxing it gave a standing disclaimer the same visual
    weight as this article's actual sources. Below the card, as a bold lead-in
    on a plain paragraph, it reads as a footer instead of as a second finding.
    """
    if article.get("section") != "learn":
        return content
    code = str(locale["code"])
    body = html.escape(str(strings["learn.disclaimer"][code]))
    if not re.search(r'<p class="verified">.*?</p>', content, flags=re.DOTALL):
        raise SystemExit(f"Learn article has no verified marker: {article['path']}")
    note = str(article.get("source_note", "")).strip()
    source_block = ""
    if note:
        source_count = len({match.group(1) for match in SOURCE_MARKER.finditer(note)})
        label_key = "learn.official_sources" if source_count > 1 else "learn.official_source"
        label = html.escape(str(strings[label_key][code]))
        source_block = (
            '\n\n    <aside class="article-trust">'
            '\n      <section class="article-trust-item article-source" aria-labelledby="official-source-heading">'
            '\n        <span class="article-trust-icon" aria-hidden="true">'
            '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">'
            '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21.5z"/>'
            '<path d="M4 5.5v16M8 7h8M8 11h7"/></svg></span>'
            f'\n        <div><h2 id="official-source-heading">{label}</h2>'
            f'\n          <p class="source-line">{hydrate_source_note(note, article)}</p></div>'
            '\n      </section>'
            '\n    </aside>'
        )
    # The colon is locale typography, not translated copy: Japanese takes the
    # full-width colon and French a nonbreaking space before it, so it comes
    # from locales.json rather than being appended as ":" in code.
    colon = str(locale["label_colon"])
    context_label = html.escape(str(strings["learn.context_label"][code]) + colon)
    # A full-width colon already carries its own trailing space in the glyph,
    # so Japanese takes no space after it. Every half-width colon does.
    gap = "" if colon == "：" else " "
    return content.rstrip() + source_block + (
        f'\n\n    <p class="learn-disclaimer"><strong>{context_label}</strong>{gap}{body}</p>\n'
    )


def render_locale_routing(
    source_path: str,
    locales: dict[str, dict],
    translations: dict[str, dict[str, dict]],
    current: str,
    strings: dict[str, dict[str, str]],
    prefix: str,
) -> str:
    """This page's other languages, as data the page can route on.

    The AtlasDays app deep-links into Learn articles with URLs frozen into
    App Store builds, so the app cannot be taught new per-language links: it
    appends `?lang=<its interface language>` to the one URL it already has and
    the page decides. The map is generated, so a locale that has not
    translated this article simply has no entry and the reader stays on
    English. A 404 is not reachable from here.

    Only published locales appear, which is the same rule hreflang and the
    switcher use. A draft locale is not somewhere to send a reader.

    The redirect fires on an explicit `?lang=` and nothing else, on every page
    including the homepage. Redirecting on `navigator.language` would take a
    reader who searched in English off the page they chose, and Google advises
    against it. That case gets the offer banner in locale-route.js instead,
    which suggests and never moves.
    """
    entries: dict[str, dict[str, str]] = {}
    for link in alternate_links(source_path, locales, translations):
        code = str(link["hreflang"])
        if code in {"x-default", current}:
            continue
        locale = locales.get(code)
        if not locale:
            continue
        entries[code] = {
            "url": str(link["href"])[len(SITE_URL):],
            "label": str(strings["locale.offer"][code]),
            "dismiss": str(strings["locale.dismiss"][code]),
        }
    if not entries:
        return ""
    payload = json.dumps(entries, ensure_ascii=False, separators=(",", ":"))
    return (
        # Script-aware resolution, inlined because it runs before paint. A plain
        # split('-')[0] was correct while every locale code was two letters and
        # breaks both ways once one carries a script subtag: zh-Hant misses its
        # own tag, and a bare `zh` -- which Intl maximizes to Hans -- would hit
        # it.
        f"\n  <script>window.AtlasDaysPageLocales={payload};"
        # Exposed rather than kept private because locale-route.js needs exactly
        # the same answer over exactly the same map, and a second copy of this
        # is how zh-Hant ended up unreachable from the browser-language offer
        # while the ?lang= path worked. Inlined because the redirect below runs
        # before paint; locale-route.js is deferred, so it always sees this.
        "window.AtlasDaysMatchLocale=function(tag,m){"
        "var w=String(tag||'').trim().replace(/_/g,'-').toLowerCase(),c;if(!w)return '';"
        "for(c in m)if(c.toLowerCase()===w)return c;"
        "var s=function(t){try{return new Intl.Locale(t).maximize().script||''}"
        "catch(err){return null}},b=w.split('-')[0],x=s(w);"
        "for(c in m){if(c.toLowerCase().split('-')[0]!==b)continue;"
        "if(x===null){if(c.indexOf('-')<0)return c;continue}"
        "if(s(c)===x)return c}"
        "return ''};"
        "(function(){var q=new URLSearchParams(location.search).get('lang');if(!q)return;"
        "var m=window.AtlasDaysPageLocales,e=m[window.AtlasDaysMatchLocale(q,m)];"
        "if(e&&e.url!==location.pathname)location.replace(e.url+location.search+location.hash)})()</script>"
        f'\n  <script defer src="{prefix}assets/js/locale-route.js?v=20260830c"></script>'
    )


def optional_block(value: object) -> str:
    text = str(value or "").rstrip()
    return "\n" + text if text else ""


# A country article can embed the 183-day calculator, preset to its own rule.
# The article's record says `"calculator": {}` (optionally with `settings`,
# e.g. {"nights": true} for a country that counts midnights); the preset comes
# from its `residency` data, so the rule is written down once. The article
# itself decides where: its fragment carries a heading, an intro sentence and
# `<div class="calculator-slot" data-calculator></div>`, so placement and
# context are written, and translated, per article (Jorick, 2026-10-04). The markup, strings and dialog are copied from the
# same locale's calculator page, so an embed is translated wherever that page
# is, and the page's own scripts and styles are reused at their current stamps.
CALCULATOR_PAGE = "learn/183-day-rule-calculator.html"
_calculator_assets: dict[str, object] = {}


# The rule plug-ins an article can embed (article record: "calculator":
# {"rule": ..., "settings": ..., "lock": [...], "link": ...}; the 183-day rule
# needs only {}, its preset comes from the record's residency). An embed on a
# rule with its own calculator page borrows that page's labels in each
# locale; the others borrow the shared ones from the 183-day page and bring
# the rest in a <script type="application/json" data-cal-strings> inside the
# article's calculator slot.
CALCULATOR_RULES = {
    "days183": {"script": "days-183.js", "page": "learn/183-day-rule-calculator.html"},
    "schengen": {"script": "schengen.js", "page": "learn/schengen-calculator.html"},
    "ukIlr": {"script": "uk-ilr.js", "page": "learn/uk-ilr-absence-calculator.html"},
    "presence": {"script": "presence.js", "version": "20261007d"},
    "spt": {"script": "spt.js", "version": "20261006a"},
}
SHARED_CALCULATOR_STRINGS = {
    "hintEnd", "hintSelected", "pending", "empty", "deleteTrip", "country", "addCountry", "noMatch",
    "goal", "goalStay", "goalReach", "year", "starts", "tripDays", "remaining", "atLimit", "needed",
    "reachedTarget", "overBy",
}


def calculator_assets(rule: str = "days183") -> dict[str, str]:
    """The 183-day page's styles and scripts, with the rule's own script."""
    if not _calculator_assets:
        records = json.loads(DATA_PATH.read_text(encoding="utf-8"))["articles"]
        _calculator_assets["records"] = {str(record["path"]): record for record in records}
    records = _calculator_assets["records"]
    page = records[CALCULATOR_PAGE]
    scripts = str(page.get("page_scripts", ""))
    if rule != "days183":
        spec = CALCULATOR_RULES[rule]
        version = spec.get("version")
        if not version:
            own = re.search(re.escape(spec["script"]) + r"\?v=(\w+)", str(records[spec["page"]].get("page_scripts", "")))
            version = own.group(1)
        scripts = re.sub(r"rules/days-183\.js\?v=\w+", f"rules/{spec['script']}?v={version}", scripts)
    return {"head_extra": str(page.get("head_extra", "")), "page_scripts": scripts}


def calculator_rule(article: dict[str, object]) -> str:
    return str(dict(article.get("calculator") or {}).get("rule", "days183"))


def calculator_preset(article: dict[str, object]) -> dict[str, object]:
    residency = dict(article.get("residency") or {})
    match = re.match(r"\s*(>|≥)\s*(\d+)", str(residency.get("threshold", "")))
    window = {"calendar": "calendar", "rolling": "rolling"}.get(str(residency.get("window", "")))
    if not match or not window or not residency.get("code"):
        raise SystemExit(f"{article['path']}: calculator needs residency code, a > or ≥ threshold, and a calendar or rolling window")
    number = int(match.group(2))
    settings = {
        "country": str(residency["code"]).upper(),
        "goal": "stay",
        "periodType": window,
        "limit": number,
        "residentAt": number + 1 if match.group(1) == ">" else number,
    }
    settings.update(dict(dict(article["calculator"]).get("settings", {})))
    # A country that counts only days with an overnight stay (Portugal): the
    # rule needs the country the setting belongs to.
    if settings.get("overnight") is True:
        settings["overnight"] = settings["country"]
    return {"settings": settings, "lock": ["country", "goal", "periodType", "limitInput"], "link": f"183-{residency['code']}"}


def calculator_link_query(article: dict[str, object]) -> str:
    """The query that opens the 183-day calculator set to an article's rule.

    A country article's link to the calculator carries its country, window and
    exact threshold, so the reader lands on a calculator already set up, and an
    import from it reports `183-<code>` (assets/js/rules/days-183.js fromQuery).
    Empty when the record's rule is not one the calculator models.
    """
    residency = dict(article.get("residency") or {})
    code = str(residency.get("code", ""))
    # "> 183 days", "≥ 183 days", or a bare "183 days …", which means 183 or more.
    match = re.match(r"\s*(>|≥)?\s*(\d+) days", str(residency.get("threshold", "")))
    if not match or not re.fullmatch(r"[a-z]{2}", code):
        return ""
    window = str(residency.get("window", ""))
    params = {"calendar": "period=calendar", "rolling": "period=rolling"}.get(window)
    if window == "income":
        start = str(residency.get("taxYearStart", ""))
        if not re.fullmatch(r"\d\d-\d\d", start):
            raise SystemExit(f"{article['path']}: an income-year rule needs residency.taxYearStart (MM-DD) for its calculator link")
        params = f"period=tax&start={start}"
    if not params:
        return ""
    number = int(match.group(2))
    resident = number + 1 if match.group(1) == ">" else number
    limit = "" if number == 183 else f"&limit={number}"
    overnight = "&overnight=1" if dict(dict(article.get("calculator") or {}).get("settings", {})).get("overnight") else ""
    return f"?country={code.upper()}&{params}&resident={resident}{limit}{overnight}"


def link_calculator_to_rule(content: str, article: dict[str, object]) -> str:
    query = calculator_link_query(article)
    if not query:
        return content
    pattern = re.compile(r'href="((?:/[A-Za-z-]+)?/learn/183-day-rule-calculator)"')
    return pattern.sub(lambda m: f'href="{m.group(1)}{html.escape(query, quote=True)}"', content)


def mark_calculator_callout(content: str, article: dict[str, object]) -> str:
    """Give the paragraph that links a calculator the `calc-callout` class.

    A plain <p> in a Learn article that links the 183-day, Schengen or ILR
    calculator is the reader's way to count their own dates, so it is set off
    as the article's one blue callout (assets/css/article-components.css).
    """
    if article.get("section") != "learn":
        return content
    pattern = re.compile(r'<p>(?=(?:(?!</p>).)*href="(?:/[A-Za-z-]+)?/learn/(?:183-day-rule|schengen|uk-ilr-absence)-calculator[?"])', re.S)
    return pattern.sub('<p class="calc-callout">', content, count=1)


# The inline list (phones and tablets) only earns its place above a long
# article; the sidebar on wide screens sits in empty margin, so every Learn
# article with sections gets it.
TOC_MIN_SECTIONS = 7
TOC_SIDE_MIN_SECTIONS = 2

# Marks the section being read in the wide-screen sidebar.
TOC_SIDE_SCRIPT = (
    "<script>(function(){var a=[].slice.call(document.currentScript.previousElementSibling.querySelectorAll('a'));"
    # The headings come after this script, so they are looked up on each pass.
    "function on(){var y=innerHeight*0.3,c=0;a.forEach(function(l,i){var e=document.getElementById(l.hash.slice(1));if(e&&e.getBoundingClientRect().top<y)c=i});"
    "a.forEach(function(l,i){if(i===c)l.setAttribute('aria-current','true');else l.removeAttribute('aria-current')})}"
    "addEventListener('scroll',on,{passive:true});on()})();</script>"
)
# Opens the inline list on tablets; it stays a one-line <details> on phones.
TOC_SCRIPT = (
    "<script>(function(){var t=document.currentScript.previousElementSibling;"
    "if(matchMedia('(min-width: 760px)').matches)t.open=true})();</script>"
)


def render_toc(content: str, article: dict[str, object]) -> str:
    """"On this page" for a Learn article.

    Sections are the <h2>s outside the closing app box and the build's source
    panel; each gets an id from its text if it has none. Wide screens get a
    sticky sidebar from the top of the page on every article (.toc-side);
    phones and tablets get the list after the summary on long articles only,
    a one-line <details> on phones and an open list on tablets (.toc). CSS
    shows one or the other (assets/css/article-components.css).
    """
    if article.get("section") != "learn":
        return content
    cta = content.find('<div class="cta-box"')
    heading = re.compile(r"<h2(?P<attrs>[^>]*)>(?P<text>.*?)</h2>", re.S)
    # The closing app box and the build's source panel are furniture, not sections.
    found = [
        m for m in heading.finditer(content)
        if (cta < 0 or not _inside_cta(content, cta, m.start())) and 'id="official-source-heading"' not in m.group("attrs")
    ]
    if len(found) < TOC_SIDE_MIN_SECTIONS:
        return content
    used: set[str] = set()
    items, out, last = [], [], 0
    for index, m in enumerate(found, 1):
        attrs, text = m.group("attrs"), m.group("text")
        existing = re.search(r'\bid="([^"]+)"', attrs)
        if existing:
            ident = existing.group(1)
        else:
            plain = re.sub(r"<[^>]+>", "", html.unescape(text))
            ident = re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-") or f"section-{index}"
            while ident in used:
                ident += "-2"
            out.append(content[last:m.start()] + f'<h2 id="{ident}"{attrs}>{text}</h2>')
            last = m.end()
        used.add(ident)
        items.append(f'        <li><a href="#{ident}">{re.sub(r"<[^>]+>", "", text).strip()}</a></li>')
    content = "".join(out) + content[last:]
    if len(found) >= TOC_MIN_SECTIONS:
        first = heading.search(content)
        block = "\n".join([
            '<details class="toc">',
            "      <summary>{{t:toc.heading}}</summary>",
            "      <ul>",
            *items,
            "      </ul>",
            "    </details>",
            "    " + TOC_SCRIPT,
            "    ",
        ])
        content = content[:first.start()] + block + content[first.start():]
    side = "\n".join([
        '<nav class="toc-side" aria-label="{{t:toc.heading}}">',
        '      <p class="toc-title">{{t:toc.heading}}</p>',
        "      <ul>",
        *items,
        "      </ul>",
        "    </nav>",
        "    " + TOC_SIDE_SCRIPT,
        "    ",
    ])
    top = content.find('<nav class="breadcrumb">')
    top = top if top >= 0 else len(content) - len(content.lstrip())
    return content[:top] + side + content[top:]


def _inside_cta(content: str, cta: int, position: int) -> bool:
    """Whether a position falls inside the closing app box (a nested <div>)."""
    depth = 0
    for tag in re.finditer(r"<(/?)div\b", content[cta:]):
        depth += -1 if tag.group(1) else 1
        if depth == 0:
            return cta <= position < cta + tag.end()
    return position >= cta


def render_embedded_calculator(content: str, article: dict[str, object], code: str) -> str:
    if article.get("calculator") is None:
        return content
    rule = calculator_rule(article)
    folder = "learn" if code == default_locale_code() else f"{code}/learn"
    page = (SOURCE_ROOT / "content" / folder / Path(CALCULATOR_PAGE).name).read_text(encoding="utf-8")
    start = page.index('<div class="daycal"')
    privacy = re.search(r'<p class="cal-private">.*?</p>', page, re.S)
    block = page[start:privacy.start()].rstrip() + "\n    " + privacy.group(0)
    slot = re.compile(r'<div class="calculator-slot" data-calculator>(.*?)</div>', re.S)
    slots = slot.findall(content)
    if len(slots) != 1:
        # _devtest/preview_build.py previews English before the translations
        # have their slot; a real build never skips one.
        if not slots and code != default_locale_code() and os.environ.get("ATLASDAYS_PREVIEW_BUILD"):
            return content
        raise SystemExit(f"{article['path']} ({code}): needs exactly one calculator slot where the calculator goes")
    if rule == "days183":
        preset = calculator_preset(article)
    else:
        calc = dict(article["calculator"])
        preset = {"settings": calc.get("settings", {}), "lock": calc.get("lock", []), "link": calc["link"]}
        # Labels: the rule's own page (or the shared 183-day ones), then the article's.
        cal_strings = re.compile(r'(<script type="application/json" data-cal-strings>)(.*?)(</script>)', re.S)
        own_page = CALCULATOR_RULES[rule].get("page")
        if own_page:
            source = (SOURCE_ROOT / "content" / folder / Path(own_page).name).read_text(encoding="utf-8")
            labels = json.loads(cal_strings.search(source).group(2))
        else:
            labels = {key: value for key, value in json.loads(cal_strings.search(page).group(2)).items() if key in SHARED_CALCULATOR_STRINGS}
        mine = cal_strings.search(slots[0])
        if not mine:
            raise SystemExit(f"{article['path']} ({code}): a {rule} calculator brings its labels in the slot's data-cal-strings")
        labels.update(json.loads(mine.group(2)))
        text = json.dumps(labels, ensure_ascii=False, indent=2)
        block = cal_strings.sub(lambda m: m.group(1) + "\n" + text + "\n      " + m.group(3), block, count=1)
        block = block.replace('data-day-calendar="days183"', f'data-day-calendar="{rule}"', 1)
    encoded = html.escape(json.dumps(preset, ensure_ascii=False, separators=(",", ":")), quote=True)
    block = block.replace('id="days-183"', f'id="embed-{rule}"', 1).replace("days-183-import-title", f"embed-{rule}-import-title")
    block = block.replace(f'data-day-calendar="{rule}"', f'data-day-calendar="{rule}" data-cal-preset="{encoded}"', 1)
    return slot.sub(lambda m: block, content, count=1)


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
    content = render_factbox_legal_basis(content, article)
    content = render_learn_trust(content, article, locale, strings)
    content = render_embedded_calculator(content, article, code)
    content = link_calculator_to_rule(content, article)
    content = mark_calculator_callout(content, article)
    content = render_toc(content, article)
    switcher = render_language_switcher(source_path, locales, translations, code, strings)
    # Only routes this locale actually has may be prefixed; everything else
    # falls back to English. Without this the chrome links a Japanese page to
    # /ja/about and friends, which were never built.
    available = {route_for(path) for path in translations.get(code, {})}
    replacements = {
        "{{HTML_LANG}}": str(locale["html_lang"]),
        "{{HTML_CLASS}}": WASH_SUBTLE,
        "{{LOCALE_ROUTING}}": render_locale_routing(
            source_path, locales, translations, code, strings, prefix
        ),
        "{{METADATA}}": render_metadata(article, prefix),
        "{{STRUCTURED_DATA}}": render_structured_data(article),
        "{{STYLESHEETS}}": render_styles(article, "article", prefix),
        "{{SITE_HEADER}}": render_header(article, header_template, prefix, switcher),
        "{{NAV_SCRIPT}}": render_nav_script(prefix, code, strings),
        "{{SITE_FOOTER}}": footer_template.replace("{{ASSET_PREFIX}}", prefix).rstrip(),
        "{{ARTICLE_CONTENT}}": content,
        # Optional per-article assets, for the few pages with an interactive
        # component (the UK absence calculator). Inline markers, so every other
        # page renders byte-for-byte as before.
        "{{HEAD_EXTRA}}": optional_block(article.get("head_extra") or (calculator_assets(calculator_rule(article))["head_extra"] if article.get("calculator") is not None else "")),
        "{{PAGE_SCRIPTS}}": optional_block(article.get("page_scripts") or (calculator_assets(calculator_rule(article))["page_scripts"] if article.get("calculator") is not None else "")),
        "{{CLUSTER_RELATED}}": (
            render_help_tail(article, locale, strings)
            or render_cluster_related(article, locale, translations)
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


APP_CATALOG_PATH = SOURCE_ROOT / "data" / "app-catalog.json"
LEARN_CARDS_PATH = SOURCE_ROOT / "data" / "learn-cards.json"


def rule_card(path: str, code: str, locale: dict[str, object], available: set[str], preset_id: str | None = None) -> tuple[str, float, str] | None:
    """One rule article as the app's preset card, in this locale: (family,
    rank in the app's order, markup), or None when it has no card.

    The card text is the app's (app-catalog.json, synced from the app by
    scripts/sync_app_catalog.py) for articles with an `app_preset`; the few
    without one have a card in learn-cards.json, ranked by its English title
    among the app's rows. Used by the Learn index and the use-case pages.
    """
    if not _card_data:
        _card_data["catalog"] = json.loads(APP_CATALOG_PATH.read_text(encoding="utf-8"))
        _card_data["own"] = json.loads(LEARN_CARDS_PATH.read_text(encoding="utf-8"))["cards"]
        _card_data["records"] = {str(r["path"]): r for r in json.loads(DATA_PATH.read_text(encoding="utf-8"))["articles"]}
    catalog, own = _card_data["catalog"], _card_data["own"]
    record = _card_data["records"].get(path, {})
    default = default_locale_code()
    preset_id = preset_id or record.get("app_preset")
    if preset_id:
        preset = catalog["presets"][preset_id]
        family, flag, rank = preset["family"], preset["flag"], float(preset["rank"][code])
        title, line = preset["title"][code], preset["line"][code]
    elif path in own:
        card = own[path]
        family, flag = card["family"], card["flag"]
        title, line = card["title"].get(code), card["line"].get(code)
        if (not title or not line) and os.environ.get("ATLASDAYS_PREVIEW_BUILD"):
            title, line = card["title"][default], card["line"][default]
        if not title or not line:
            raise SystemExit(f"learn-cards.json: {path} has no {code} title or line")
        english = card["title"][default]
        ranks = [p["rank"][code] for p in catalog["presets"].values() if p["family"] == family and p["title"][default] < english]
        rank = (max(ranks) if ranks else -1) + 0.5
    else:
        return None
    href = html.escape(localized_route(route_for(path), locale, available), quote=True)
    # A rule for any country gets the globe icon, not the AtlasDays logo.
    image = (
        f'<img class="rule-flag" src="/assets/flags/{flag.lower()}.png" alt="" width="36" height="25" loading="lazy" />'
        if flag else GLOBE_ICON
    )
    pill = "tax" if family == "usState" else family
    markup = (
        f'          <a class="rule-card" href="{href}" data-filter-item data-groups="{pill}">'
        f'{image}'
        f'<span class="rule-text"><strong>{html.escape(title)}</strong><span>{html.escape(line)}</span></span></a>'
    )
    return family, rank, markup


_card_data: dict[str, object] = {}


def render_rule_cards(content: str, code: str, locale: dict[str, object], available: set[str]) -> str:
    """`<!-- RULE_CARDS: learn/a.html learn/b.html -->` becomes those articles'
    cards, in the order given (the use-case pages pick their own; they list
    only rules the app offers as presets)."""
    def cards(match: re.Match) -> str:
        rows = []
        for token in match.group(1).split():
            # path@preset: that preset's card, linking to that article (the
            # EU long-term resident preset has no article of its own).
            path, _, preset = token.partition("@")
            card = rule_card(path, code, locale, available, preset or None)
            if card is None:
                raise SystemExit(f"RULE_CARDS: {path} has no card (no app_preset, not in learn-cards.json)")
            rows.append(card[2])
        return "\n".join(rows)
    return re.sub(r"<!-- RULE_CARDS: ([^>]*?) -->", cards, content)


def render_learn_rules(content: str, code: str, locale: dict[str, object], available: set[str]) -> str:
    """The Learn index's rules as the app's preset cards.

    `<!-- LEARN_CHIPS -->` becomes the app's filter pills and
    `<!-- LEARN_RULES -->` one section per app family with every rule
    article's card (rule_card), in the order the app shows them.
    """
    if "<!-- LEARN_RULES -->" not in content:
        return content
    catalog = json.loads(APP_CATALOG_PATH.read_text(encoding="utf-8"))
    records = json.loads(DATA_PATH.read_text(encoding="utf-8"))["articles"]
    cards: dict[str, list[tuple[float, str]]] = {}
    for record in records:
        card = rule_card(str(record["path"]), code, locale, available)
        if card:
            cards.setdefault(card[0], []).append((card[1], card[2]))
    sections = []
    for section in catalog["sections"]:
        family = section["family"]
        if family not in cards:
            continue
        rows = "\n".join(markup for _, markup in sorted(cards[family], key=lambda item: item[0]))
        sections.append(
            f'      <section class="hub-section rule-section" id="rules-{family.lower()}" data-filter-section>\n'
            f'        <p class="hub-label">{html.escape(section["title"][code])}</p>\n'
            f'        <div class="rule-cards">\n{rows}\n        </div>\n      </section>'
        )
    chips = "\n".join(
        f'        <button type="button" data-filter-chip="{section["family"]}" aria-pressed="false">{html.escape(section["pill"][code])}</button>'
        for section in catalog["sections"] if section["family"] != "usState" and section["family"] in cards
    )
    return content.replace("<!-- LEARN_RULES -->", "\n".join(sections)).replace("<!-- LEARN_CHIPS -->", chips)


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
    header = render_header(hub, header_template, prefix, switcher)
    nav_script = render_nav_script(prefix, code, strings)
    search_copy = json.dumps(
        {
            "resultOne": strings["search.result_one"][code],
            "resultMany": strings["search.result_many"][code],
            "emptyHelp": strings["search.empty_help"][code],
            "emptyLearn": strings["search.empty_learn"][code],
            "unavailable": strings["search.unavailable"][code],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    # Only routes this locale actually has may be prefixed; everything else
    # falls back to English. Without this the chrome links a Japanese page to
    # /ja/about and friends, which were never built.
    available = {route_for(path) for path in translations.get(code, {})}
    content = render_learn_rules(content, code, locale, available)
    content = render_rule_cards(content, code, locale, available)
    replacements = {
        "{{HTML_LANG}}": str(locale["html_lang"]),
        # Hubs are marketing surfaces and take the full wash; the legal and
        # about pages built through this same template are long-form reading
        # and step down with the articles. A page record can opt back into
        # the full wash with "wash": "full" (the use-case pages, which share
        # the homepage's marketing layout).
        "{{HTML_CLASS}}": WASH_SUBTLE if family == "page" and hub.get("wash") != "full" else "",
        "{{LOCALE_ROUTING}}": render_locale_routing(
            source_path, locales, translations, code, strings, prefix
        ),
        "{{METADATA}}": render_metadata(hub, prefix),
        "{{STRUCTURED_DATA}}": render_structured_data(hub),
        "{{STYLESHEETS}}": render_styles(hub, family, prefix),
        "{{HEAD_EXTRA}}": str(hub.get("head_extra", "")).rstrip(),
        "{{SITE_HEADER}}": header,
        "{{NAV_SCRIPT}}": nav_script,
        "{{LANGUAGE_SWITCHER}}": switcher,
        "{{MAIN_CONTENT}}": content,
        "{{SITE_FOOTER}}": footer_template.replace("{{ASSET_PREFIX}}", prefix).rstrip(),
        "{{PAGE_SCRIPTS}}": str(hub.get("page_scripts", "")).rstrip(),
        "{{SEARCH_STYLESHEET}}": (
            f'  <link rel="stylesheet" href="{prefix}assets/css/search.css?v=20261006b" />\n'
            f'  <link rel="stylesheet" href="{prefix}assets/css/rule-cards.css?v={RULE_CARDS_VERSION}" />'
            if family == "hub" else ""
        ),
        "{{SEARCH_SCRIPT}}": (
            f"  <script>window.AtlasDaysSearchStrings={search_copy};</script>\n"
            f'  <script src="{prefix}assets/js/search.js?v=20261006b"></script>'
            if family == "hub" else ""
        ),
        "{{ASSET_PREFIX}}": prefix,
    }
    rendered = template
    for marker, value in replacements.items():
        rendered = rendered.replace(marker, value)
    # The standalone template is a bare shell: its page fragment carries the
    # header slot itself, not the template. MAIN_CONTENT is substituted after
    # the header and switcher slots above, so resolve both once more now that
    # the fragment is in place.
    rendered = rendered.replace("{{SITE_HEADER}}", header)
    rendered = rendered.replace("{{NAV_SCRIPT}}", nav_script)
    rendered = rendered.replace("{{LANGUAGE_SWITCHER}}", switcher)
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
    page_data = json.loads(PAGE_DATA_PATH.read_text(encoding="utf-8")) if PAGE_DATA_PATH.exists() else {"pages": []}
    sources = {str(record["path"]): record for record in data.get("articles", [])}
    hub_sources = {str(record["path"]): record for record in hub_data.get("hubs", [])}
    page_sources = {str(record["path"]): record for record in page_data.get("pages", [])}

    stale = [
        problem
        for code, overlays in translations.items()
        for problem in check_translation_freshness(
            code, overlays, {**sources, **hub_sources, **page_sources}, date.today()
        )
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
        if record.get("locale_alternates") is False:
            return record
        alternates = alternate_links(str(record["path"]), locales, translations)
        if not alternates:
            return record
        return {**record, "links": list(record.get("links", [])) + alternates}

    template = ARTICLE_TEMPLATE.read_text(encoding="utf-8")
    header_template = HEADER_TEMPLATE.read_text(encoding="utf-8")
    footer_template = FOOTER_TEMPLATE.read_text(encoding="utf-8")
    hub_template = HUB_TEMPLATE.read_text(encoding="utf-8")
    standalone_template = STANDALONE_TEMPLATE.read_text(encoding="utf-8")
    changed: list[str] = []
    selected = 0
    # (output_path, rendered) queued until every de-listing check has passed, so
    # an aborted build leaves the working tree untouched rather than half-written.
    pending: list[tuple[Path, str]] = []
    delistings: list[tuple[str, list[str]]] = []

    def queue(output_path: Path, rendered: str, *, guard: bool = False) -> None:
        nonlocal selected
        selected += 1
        if output_path.suffix == ".html":
            rendered = with_campaign_links(rendered)
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
        for page in page_data.get("pages", []):
            page_template = standalone_template if page.get("template") == "standalone" else hub_template
            page_family = "standalone" if page.get("template") == "standalone" else "page"
            queue(
                SITE_ROOT / str(page["path"]),
                render_hub(
                    with_alternates(page),
                    page_template,
                    header_template,
                    footer_template,
                    locale,
                    strings,
                    locales,
                    translations,
                    family=page_family,
                ),
                guard=True,
            )

    for code, overlays in translations.items():
        if code == default_locale_code() or not overlays:
            continue
        target = locales[code]
        available = {route_for(path) for path in overlays}
        for source_path in sorted(overlays):
            source = sources.get(source_path) or hub_sources.get(source_path) or page_sources[source_path]
            kind = (
                "article" if source_path in sources
                else "hub" if source_path in hub_sources
                else "page"
            )
            if args.section != "all" and source.get("section") != args.section:
                continue
            record = derive_record(
                overlays[source_path], source, target, locales, translations,
                available, strings, kind=kind,
            )
            renderer = render_article if kind == "article" else render_hub
            localized_template = (
                standalone_template
                if kind == "page" and source.get("template") == "standalone"
                else hub_template
            )
            localized_family = (
                "standalone"
                if kind == "page" and source.get("template") == "standalone"
                else "page"
            )
            queue(
                SITE_ROOT / str(record["path"]),
                renderer(
                    record,
                    template if kind == "article" else localized_template,
                    header_template, footer_template,
                    target, strings, locales, translations,
                    **({"family": localized_family} if kind == "page" else {}),
                ),
            )

    if args.section in {"all", "learn"}:
        for output_path, rendered in redirect_outputs(locales, translations, sources, strings):
            queue(output_path, rendered)

    if args.section == "all" and ROUTES.exists():
        routes = expanded_routes(json.loads(ROUTES.read_text(encoding="utf-8"))["routes"])
        # Each set's delisting guard runs over the set as one document. Per
        # file it would misfire in both directions: sitemap.xml is an index
        # carrying no page URLs at all, and moving a page between locale
        # files is not a delisting. Losing it from every file in the set is.
        for label, outputs in (("sitemap.xml", sitemap_files(routes)), ("llms.txt", llms_files(routes))):
            previous = "\n".join(
                path.read_text(encoding="utf-8") for path in outputs if path.exists()
            )
            dropped = delisted_live_pages(previous, "\n".join(outputs.values())) if previous else []
            if dropped:
                delistings.append((label, dropped))
            for path, rendered in outputs.items():
                queue(path, rendered)

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
