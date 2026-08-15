#!/usr/bin/env python3
"""Locale registry, chrome strings, and per-locale rendering helpers.

The site is generated one locale at a time from the same templates. Everything
that differs between locales is data: `_site-src/data/locales.json` says which
locales exist and how each one formats a route, a date, and a title, and
`_site-src/data/ui-strings.json` holds the chrome copy. Adding a locale is
meant to be those two files plus content, never a change in here.

Templates and partials carry two marker forms, both resolved by `localize`:

    {{t:nav.help}}   a chrome string
    {{r:/help/}}     an internal route, locale-prefixed when that page exists

Both fail loudly on an unknown key. A silently empty nav label is exactly the
defect nobody catches on a page they cannot read.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = SITE_ROOT / "_site-src"
LOCALES_PATH = SOURCE_ROOT / "data" / "locales.json"
UI_STRINGS_PATH = SOURCE_ROOT / "data" / "ui-strings.json"

STRING_MARKER = re.compile(r"\{\{t:([a-z0-9_.]+)\}\}")
ROUTE_MARKER = re.compile(r"\{\{r:(/[\w\-./]*)\}\}")

# sync_help_screenshots.py regenerates each figure from the record in
# articles.json, so its width, height, and crop class move whenever a capture
# is retaken. None of that is prose. The staleness hash therefore sees a
# figure as its slot key alone, and the slot's alt text rides on the meta hash
# with the rest of articles.json.
FIGURE = re.compile(
    r'<figure class="help-shot[^"]*">\s*<img src="[^"]*/([\w\-]+)\.webp"[^>]*/>\s*</figure>'
)
DEFERRED_FIGURE = re.compile(r"<!-- SCREENSHOT_DEFERRED: ([\w\-]+) \|[^>]*-->")


def load_locales() -> dict[str, dict]:
    """Every registered locale, keyed by code, in registry order."""
    data = json.loads(LOCALES_PATH.read_text(encoding="utf-8"))
    return {str(entry["code"]): entry for entry in data["locales"]}


def default_locale_code() -> str:
    return str(json.loads(LOCALES_PATH.read_text(encoding="utf-8"))["default"])


def published_locales(locales: dict[str, dict]) -> list[dict]:
    """Locales that may appear in hreflang, the sitemap, and the switcher.

    A `draft` locale still builds and previews, which is how a new language is
    verified end to end before it becomes discoverable.
    """
    return [entry for entry in locales.values() if entry.get("status") == "published"]


def load_ui_strings() -> dict[str, dict[str, str]]:
    return json.loads(UI_STRINGS_PATH.read_text(encoding="utf-8"))["strings"]


def route_for(path: str) -> str:
    """The public route a generated file is served at."""
    if path.endswith("/index.html"):
        return "/" + path[: -len("index.html")].strip("/") + "/"
    if path == "index.html":
        return "/"
    return "/" + path.removesuffix(".html")


def localized_route(route: str, locale: dict, available: set[str] | None = None) -> str:
    """`route` under `locale`, falling back to the default locale's page.

    Partial coverage is deliberate: a Japanese Help page links to the Japanese
    Help hub but to the English Travel Rules hub, because no Japanese one
    exists yet. Passing `available` is what keeps a link from pointing at a
    page that was never built.
    """
    prefix = str(locale.get("route_prefix", ""))
    if not prefix:
        return route
    if available is not None and route not in available:
        return route
    return f"{prefix}/" if route == "/" else prefix + route


def localize(
    text: str,
    locale: dict,
    strings: dict[str, dict[str, str]],
    *,
    available_routes: set[str] | None = None,
    context: str = "",
) -> str:
    """Resolve every `{{t:}}` and `{{r:}}` marker in a rendered document."""
    code = str(locale["code"])
    where = f" in {context}" if context else ""

    def string_value(match: re.Match[str]) -> str:
        key = match.group(1)
        entry = strings.get(key)
        if entry is None:
            raise SystemExit(f"Unknown UI string key {key!r}{where}")
        value = entry.get(code)
        if value is None:
            raise SystemExit(f"UI string {key!r} has no {code!r} value{where}")
        return value

    def route_value(match: re.Match[str]) -> str:
        return localized_route(match.group(1), locale, available_routes)

    return ROUTE_MARKER.sub(route_value, STRING_MARKER.sub(string_value, text))


def render_date(iso_date: str, locale: dict) -> str:
    """An ISO date in the locale's own order.

    Japanese leads with the year, so a shared `d MMM yyyy` shape is not merely
    unidiomatic there, it is ungrammatical.
    """
    year, month, day = (int(part) for part in str(iso_date).split("-"))
    months = locale.get("month_names") or []
    rendered = str(locale["date_format"])
    if "{month}" in rendered:
        if not months:
            raise SystemExit(f"Locale {locale['code']!r} needs month_names for its date_format")
        rendered = rendered.replace("{month}", str(months[month - 1]))
    return rendered.replace("{y}", str(year)).replace("{m}", str(month)).replace("{d}", str(day))


def translatable_source(text: str) -> str:
    """The part of an English fragment a translation actually depends on.

    Screenshot dimensions and whitespace churn are not translation-relevant, so
    hashing raw bytes would mark every Japanese page stale every time a capture
    is retaken.
    """
    collapsed = FIGURE.sub(lambda match: f"[figure:{match.group(1)}]", text)
    collapsed = DEFERRED_FIGURE.sub(lambda match: f"[figure:{match.group(1)}]", collapsed)
    return " ".join(collapsed.split())


def description_of(record: dict) -> str:
    for attrs in record.get("meta", []):
        if attrs.get("name") == "description":
            return str(attrs.get("content", ""))
    return ""


def meta_hash(source: dict) -> str:
    """Hash of the English metadata a translation mirrors.

    Separate from the fragment hash because the two fail differently: a moved
    paragraph means retranslate the body, a reworded description means redo the
    title and next-step labels only.
    """
    payload = [str(source.get("title", "")), description_of(source)]
    if "source_note" in source:
        payload.append(str(source["source_note"]))
    for step in source.get("next_steps", []):
        payload += [str(step.get("title", "")), str(step.get("description", ""))]
    for slot in source.get("screenshot_slots", []):
        payload += [str(slot.get("key", "")), str(slot.get("alt", ""))]
    return "sha256:" + hashlib.sha256("\x1f".join(payload).encode("utf-8")).hexdigest()


def source_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(translatable_source(text).encode("utf-8")).hexdigest()
