#!/usr/bin/env python3
"""Audit the committed AtlasDays static site without third-party dependencies.

The default mode blocks regressions that the current site can already satisfy.
Known migration work (semantic landmarks and the article-image catalog) is
reported as warnings until its dedicated phase is complete. Use the strict
flags to promote those warnings to errors.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


SITE_ROOT = Path(__file__).resolve().parents[1]
SITE_ORIGIN = "https://atlasdays.app"
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
IGNORED_DIRS = {".git", "assets", "_site-src"}
THEME_DARK_DEFAULT = re.compile(
    r"document\.documentElement\.setAttribute\("
    r"['\"]data-theme['\"],\s*t===['\"]light['\"]\?['\"]light['\"]:['\"]dark['\"]\)"
)


@dataclass(order=True)
class Finding:
    severity: str
    code: str
    path: str
    detail: str


@dataclass
class PageRecord:
    path: str
    route: str
    page_type: str
    indexable: bool
    title: str
    description: str
    canonical: str
    h1: list[str]
    content_hash: str
    jsonld_types: list[str] = field(default_factory=list)


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str | None], tuple[int, int]]] = []
        self.ids: list[str] = []
        self.title_parts: list[str] = []
        self.h1_parts: list[list[str]] = []
        self._in_title = False
        self._h1_depth = 0
        self._jsonld_depth = 0
        self._jsonld_buffer: list[str] = []
        self.jsonld_blobs: list[str] = []
        self._main_depth = 0
        self._article_depth = 0
        self._content_parts: list[str] = []
        self._fallback_article_parts: list[str] = []
        self.has_main = False
        self.has_article = False
        self.main_count = 0
        self.footer_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        self.tags.append((tag, data, self.getpos()))
        if data.get("id"):
            self.ids.append(str(data["id"]))
        if tag == "title":
            self._in_title = True
        if tag == "h1":
            self._h1_depth += 1
            self.h1_parts.append([])
        if tag == "script" and data.get("type") == "application/ld+json":
            self._jsonld_depth += 1
            self._jsonld_buffer = []
        if tag == "main":
            self.has_main = True
            self.main_count += 1
            self._main_depth += 1
        if tag == "footer":
            self.footer_count += 1
        if tag == "article":
            self.has_article = True
            self._article_depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag == "h1" and self._h1_depth:
            self._h1_depth -= 1
        if tag == "script" and self._jsonld_depth:
            self.jsonld_blobs.append("".join(self._jsonld_buffer))
            self._jsonld_depth -= 1
            self._jsonld_buffer = []
        if tag == "main" and self._main_depth:
            self._main_depth -= 1
        if tag == "article" and self._article_depth:
            self._article_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        if self._h1_depth and self.h1_parts:
            self.h1_parts[-1].append(data)
        if self._jsonld_depth:
            self._jsonld_buffer.append(data)
        clean = " ".join(data.split())
        if not clean:
            return
        if self._main_depth:
            self._content_parts.append(clean)
        elif self._article_depth:
            self._fallback_article_parts.append(clean)

    @property
    def title(self) -> str:
        return " ".join("".join(self.title_parts).split())

    @property
    def h1(self) -> list[str]:
        return [" ".join("".join(parts).split()) for parts in self.h1_parts]

    @property
    def content_text(self) -> str:
        parts = self._content_parts or self._fallback_article_parts
        return " ".join(parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict-semantics", action="store_true")
    parser.add_argument("--strict-images", action="store_true")
    parser.add_argument("--write-baseline", type=Path)
    parser.add_argument("--check-baseline", type=Path)
    parser.add_argument("--json", dest="json_output", action="store_true")
    return parser.parse_args()


def discover_html() -> list[Path]:
    pages: list[Path] = []
    for path in SITE_ROOT.rglob("*.html"):
        rel = path.relative_to(SITE_ROOT)
        if rel.parts and rel.parts[0] in IGNORED_DIRS:
            continue
        pages.append(path)
    return sorted(pages)


def route_for_path(path: Path) -> str:
    rel = path.relative_to(SITE_ROOT)
    if rel == Path("index.html"):
        return "/"
    if rel.name == "index.html":
        return "/" + rel.parent.as_posix().strip("/") + "/"
    return "/" + rel.with_suffix("").as_posix()


def page_type_for(path: Path, indexable: bool, parser: PageParser) -> str:
    rel = path.relative_to(SITE_ROOT)
    if rel == Path("404.html"):
        return "404"
    if not indexable:
        return "redirect"
    if rel == Path("index.html"):
        return "home"
    if rel == Path("changelog.html"):
        return "changelog"
    if rel.as_posix() in {"about.html", "privacy.html", "terms.html"}:
        return "legal"
    if rel.name == "index.html" or rel.as_posix() in {
        "learn/day-limits.html",
        "learn/tax-residency-by-country.html",
        "learn/us-state-tax-residency.html",
    }:
        return "hub"
    if parser.has_article:
        return "article"
    return "page"


def meta_content(parser: PageParser, *, name: str | None = None, prop: str | None = None) -> list[str]:
    values: list[str] = []
    for tag, attrs, _ in parser.tags:
        if tag != "meta":
            continue
        if name is not None and attrs.get("name") != name:
            continue
        if prop is not None and attrs.get("property") != prop:
            continue
        values.append(str(attrs.get("content") or "").strip())
    return values


def link_values(parser: PageParser, rel: str) -> list[str]:
    values: list[str] = []
    for tag, attrs, _ in parser.tags:
        if tag != "link":
            continue
        rels = str(attrs.get("rel") or "").split()
        if rel in rels:
            values.append(str(attrs.get("href") or "").strip())
    return values


def is_indexable(path: Path, parser: PageParser) -> bool:
    if path.name == "404.html":
        return False
    robots = " ".join(meta_content(parser, name="robots")).lower()
    return "noindex" not in robots


def expected_canonical(route: str) -> str:
    return SITE_ORIGIN + route


def resolve_local(source: Path, raw_url: str) -> Path | None:
    split = urlsplit(raw_url)
    if split.scheme or raw_url.startswith(("//", "mailto:", "tel:", "data:", "javascript:")):
        return None
    raw_path = unquote(split.path)
    if not raw_path:
        return source
    path = SITE_ROOT / raw_path.lstrip("/") if raw_path.startswith("/") else source.parent / raw_path
    path = path.resolve()
    candidates = [path]
    if raw_path.endswith("/"):
        candidates = [path / "index.html"]
    elif not path.suffix:
        candidates.extend([Path(str(path) + ".html"), path / "index.html"])
    return next((candidate for candidate in candidates if candidate.exists()), path)


def jsonld_types(value: object) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        kind = value.get("@type")
        if isinstance(kind, str):
            found.append(kind)
        elif isinstance(kind, list):
            found.extend(str(item) for item in kind)
        for child in value.values():
            found.extend(jsonld_types(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(jsonld_types(child))
    return found


def severity(strict: bool) -> str:
    return "error" if strict else "warning"


def audit_pages(args: argparse.Namespace) -> tuple[list[PageRecord], list[Finding], dict[Path, PageParser]]:
    findings: list[Finding] = []
    records: list[PageRecord] = []
    parsed: dict[Path, PageParser] = {}
    pages = discover_html()

    for path in pages:
        rel = path.relative_to(SITE_ROOT).as_posix()
        parser = PageParser()
        try:
            parser.feed(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive parser boundary
            findings.append(Finding("error", "html-parse", rel, str(exc)))
            continue
        parsed[path.resolve()] = parser
        route = route_for_path(path)
        indexable = is_indexable(path, parser)
        descriptions = meta_content(parser, name="description")
        canonicals = link_values(parser, "canonical")
        description = descriptions[0] if descriptions else ""
        canonical = canonicals[0] if canonicals else ""

        if not parser.title:
            findings.append(Finding("error", "missing-title", rel, "Page has no title"))
        if indexable and not description:
            findings.append(Finding("error", "missing-description", rel, "Indexable page has no meta description"))
        if indexable and len(canonicals) != 1:
            findings.append(Finding("error", "canonical-count", rel, f"Expected 1 canonical, found {len(canonicals)}"))
        if indexable and canonical and canonical != expected_canonical(route):
            findings.append(
                Finding("error", "canonical-route", rel, f"Expected {expected_canonical(route)}, found {canonical}")
            )
        if indexable:
            social_checks = (
                ("og:image", meta_content(parser, prop="og:image")),
                ("og:image:width", meta_content(parser, prop="og:image:width")),
                ("og:image:height", meta_content(parser, prop="og:image:height")),
                ("og:image:alt", meta_content(parser, prop="og:image:alt")),
                ("twitter:image", meta_content(parser, name="twitter:image")),
                ("twitter:image:alt", meta_content(parser, name="twitter:image:alt")),
            )
            for field_name, values in social_checks:
                if len(values) != 1 or not values[0]:
                    findings.append(
                        Finding("error", "social-metadata", rel, f"Expected one non-empty {field_name}")
                    )
            og_images = meta_content(parser, prop="og:image")
            if og_images:
                social_path = SITE_ROOT / urlsplit(og_images[0]).path.lstrip("/")
                if not social_path.exists():
                    findings.append(Finding("error", "social-image", rel, og_images[0]))
        if indexable and len(parser.h1) != 1:
            findings.append(Finding("error", "h1-count", rel, f"Expected 1 H1, found {len(parser.h1)}"))
        if indexable:
            stylesheets = [
                str(attrs.get("href") or "")
                for tag, attrs, _ in parser.tags
                if tag == "link" and "stylesheet" in str(attrs.get("rel") or "").split()
            ]
            shared_styles = ("site-header.css", "site-footer.css", "search.css")
            if not any(href and not any(name in href for name in shared_styles) for href in stylesheets):
                findings.append(
                    Finding("error", "missing-content-style", rel, "Page has no page-family or content stylesheet")
                )
        if indexable and parser.main_count != 1:
            findings.append(
                Finding(
                    severity(args.strict_semantics),
                    "missing-main",
                    rel,
                    f"Indexable page needs exactly one main landmark; found {parser.main_count}",
                )
            )
        if indexable and args.strict_semantics:
            has_skip_link = any(
                tag == "a" and "skip-link" in str(attrs.get("class") or "").split()
                for tag, attrs, _ in parser.tags
            )
            if not has_skip_link:
                findings.append(Finding("error", "missing-skip-link", rel, "Indexable page needs a skip link"))
            if parser.footer_count != 1:
                findings.append(
                    Finding("error", "footer-count", rel, f"Expected one footer, found {parser.footer_count}")
                )

        duplicates = [item for item, count in Counter(parser.ids).items() if count > 1]
        if duplicates:
            findings.append(Finding("error", "duplicate-id", rel, ", ".join(sorted(duplicates))))

        script_sources = [
            str(attrs.get("src") or "")
            for tag, attrs, _ in parser.tags
            if tag == "script" and attrs.get("src")
        ]
        for shared_script in ("theme.js", "navigation.js", "search.js"):
            count = sum(shared_script in source for source in script_sources)
            if count > 1:
                findings.append(Finding("error", "duplicate-shared-script", rel, f"{shared_script}: {count}"))

        page_jsonld_types: list[str] = []
        for blob in parser.jsonld_blobs:
            try:
                page_jsonld_types.extend(jsonld_types(json.loads(blob)))
            except json.JSONDecodeError as exc:
                findings.append(Finding("error", "invalid-jsonld", rel, str(exc)))

        source_text = path.read_text(encoding="utf-8")
        if "localStorage.getItem('theme')" in source_text and not THEME_DARK_DEFAULT.search(source_text):
            findings.append(
                Finding("error", "theme-default", rel, "Theme bootstrap must fall back to dark unless light is stored")
            )

        for tag, attrs, position in parser.tags:
            line = position[0]
            if tag == "img":
                if "alt" not in attrs:
                    findings.append(Finding("error", "image-alt", rel, f"Line {line}: missing alt attribute"))
                if not attrs.get("width") or not attrs.get("height"):
                    findings.append(
                        Finding("warning", "image-dimensions", rel, f"Line {line}: {attrs.get('src', '')}")
                    )
            if tag == "button" and not attrs.get("type"):
                findings.append(Finding("error", "button-type", rel, f"Line {line}: button has no type"))
            if tag == "a" and attrs.get("target") == "_blank":
                rel_values = str(attrs.get("rel") or "").split()
                if "noopener" not in rel_values:
                    findings.append(
                        Finding("error", "noopener", rel, f"Line {line}: target=_blank without rel=noopener")
                    )

            attr_name: str | None = None
            if tag in {"a", "link"}:
                attr_name = "href"
            elif tag in {"img", "script", "video", "source"}:
                attr_name = "src"
            if not attr_name or not attrs.get(attr_name):
                continue
            raw_url = str(attrs[attr_name])
            destination = resolve_local(path.resolve(), raw_url)
            if destination is not None and not destination.exists():
                findings.append(Finding("error", "broken-local-ref", rel, f"Line {line}: {raw_url}"))
                continue
            fragment = urlsplit(raw_url).fragment
            if fragment and destination in parsed and fragment not in parsed[destination].ids:
                findings.append(Finding("error", "broken-fragment", rel, f"Line {line}: {raw_url}"))

        content_hash = hashlib.sha256(parser.content_text.encode("utf-8")).hexdigest()
        records.append(
            PageRecord(
                path=rel,
                route=route,
                page_type=page_type_for(path, indexable, parser),
                indexable=indexable,
                title=parser.title,
                description=description,
                canonical=canonical,
                h1=parser.h1,
                content_hash=content_hash,
                jsonld_types=sorted(set(page_jsonld_types)),
            )
        )

    # Fragment targets can point forward to pages parsed later, so verify them again now.
    for path in pages:
        parser = parsed.get(path.resolve())
        if parser is None:
            continue
        rel = path.relative_to(SITE_ROOT).as_posix()
        for tag, attrs, position in parser.tags:
            if tag != "a" or not attrs.get("href"):
                continue
            raw_url = str(attrs["href"])
            fragment = urlsplit(raw_url).fragment
            if not fragment:
                continue
            destination = resolve_local(path.resolve(), raw_url)
            if destination in parsed and fragment not in parsed[destination].ids:
                finding = Finding("error", "broken-fragment", rel, f"Line {position[0]}: {raw_url}")
                if finding not in findings:
                    findings.append(finding)

    return records, findings, parsed


def audit_theme_css(findings: list[Finding]) -> None:
    for path in sorted((SITE_ROOT / "assets" / "css").rglob("*.css")):
        if "@media (prefers-color-scheme:" in path.read_text(encoding="utf-8"):
            findings.append(
                Finding(
                    "error",
                    "system-theme-palette",
                    path.relative_to(SITE_ROOT).as_posix(),
                    "Palette must use the dark base and explicit data-theme=light override",
                )
            )


def audit_governance(records: list[PageRecord], findings: list[Finding]) -> None:
    editorial_path = SITE_ROOT / "_site-src" / "data" / "editorial.json"
    clusters_path = SITE_ROOT / "_site-src" / "data" / "content-clusters.json"
    try:
        editorial = json.loads(editorial_path.read_text(encoding="utf-8"))["articles"]
        clusters = json.loads(clusters_path.read_text(encoding="utf-8"))["clusters"]
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        findings.append(Finding("error", "governance-config", "_site-src/data", str(exc)))
        return
    learn_paths = {
        record.path for record in records
        if record.indexable and record.path.startswith("learn/") and record.page_type == "article"
    }
    editorial_by_path = {str(item.get("path", "")): item for item in editorial}
    clusters_by_path = {str(item.get("path", "")): item for item in clusters}
    for path in sorted(learn_paths):
        if path not in editorial_by_path:
            findings.append(Finding("error", "editorial-missing", path, "No editorial governance record"))
            continue
        item = editorial_by_path[path]
        required = ("jurisdiction", "rule_category", "risk_level", "review_interval_days", "last_fact_verified", "next_review_due", "review_status")
        for field_name in required:
            if not item.get(field_name):
                findings.append(Finding("error", "editorial-field", path, f"Missing {field_name}"))
        if item.get("risk_level") == "high" and not item.get("source_urls"):
            findings.append(Finding("error", "editorial-sources", path, "High-risk article has no structured external source"))
        due = str(item.get("next_review_due") or "")
        try:
            if due and date.fromisoformat(due) < date.today():
                findings.append(Finding("error", "editorial-overdue", path, due))
        except ValueError:
            findings.append(Finding("error", "editorial-date", path, f"Invalid next_review_due: {due}"))
        if path not in clusters_by_path:
            findings.append(Finding("error", "cluster-missing", path, "No content-cluster assignment"))
    for unexpected in sorted(editorial_by_path.keys() - learn_paths):
        findings.append(Finding("error", "editorial-orphan", unexpected, "Record has no Learn article"))
    for unexpected in sorted(clusters_by_path.keys() - learn_paths):
        findings.append(Finding("error", "cluster-orphan", unexpected, "Assignment has no Learn article"))


def audit_sitemap(records: list[PageRecord], findings: list[Finding]) -> None:
    sitemap_path = SITE_ROOT / "sitemap.xml"
    try:
        root = ET.parse(sitemap_path).getroot()
    except (ET.ParseError, OSError) as exc:
        findings.append(Finding("error", "invalid-sitemap", "sitemap.xml", str(exc)))
        return

    urls = [str(node.text or "").strip() for node in root.iter(SITEMAP_NS + "loc")]
    for duplicate, count in Counter(urls).items():
        if count > 1:
            findings.append(Finding("error", "sitemap-duplicate", "sitemap.xml", duplicate))

    indexable_by_canonical = {record.canonical: record for record in records if record.indexable and record.canonical}
    sitemap_set = set(urls)
    for url in urls:
        if url not in indexable_by_canonical:
            findings.append(
                Finding("error", "sitemap-noncanonical", "sitemap.xml", f"No indexable canonical page for {url}")
            )
    for canonical, record in indexable_by_canonical.items():
        if canonical not in sitemap_set:
            findings.append(Finding("error", "sitemap-missing", record.path, canonical))


def audit_image_pipeline(args: argparse.Namespace, findings: list[Finding]) -> None:
    plan_path = SITE_ROOT / "article-image-plan.json"
    catalog_path = SITE_ROOT / "assets/article-images/catalog.json"
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        findings.append(Finding("error", "image-config", "article-image-plan.json", str(exc)))
        return

    catalog_entries: dict[tuple[str, str], dict[str, object]] = {}
    for article in catalog.get("articles", []):
        if not isinstance(article, dict):
            continue
        key = f"{article.get('section', '')}/{article.get('slug', '')}"
        for image in article.get("images", []):
            if isinstance(image, dict):
                catalog_entries[(key, str(image.get("slot", "")))] = image

    finding_severity = severity(args.strict_images)
    for key, config in plan.get("articles", {}).items():
        section, _, slug = str(key).partition("/")
        article_path = SITE_ROOT / section / f"{slug}.html"
        if not article_path.exists():
            findings.append(Finding("error", "image-plan-page", str(key), "Planned article does not exist"))
            continue
        source = article_path.read_text(encoding="utf-8")
        for slot in config.get("slots", []):
            marker = str(slot.get("marker", ""))
            slot_id = str(slot.get("id", ""))
            if f"<!-- ARTICLE_IMAGE:{marker} -->" not in source:
                findings.append(
                    Finding(finding_severity, "image-marker", article_path.relative_to(SITE_ROOT).as_posix(), marker)
                )
            if (key, slot_id) not in catalog_entries:
                findings.append(
                    Finding(finding_severity, "image-catalog", article_path.relative_to(SITE_ROOT).as_posix(), slot_id)
                )

    for (key, slot_id), entry in catalog_entries.items():
        asset = SITE_ROOT / str(entry.get("path", ""))
        if not asset.exists():
            findings.append(Finding(finding_severity, "image-asset", str(key), f"{slot_id}: {asset}"))


def baseline_payload(records: list[PageRecord]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "site_origin": SITE_ORIGIN,
        "html_file_count": len(records),
        "indexable_route_count": sum(record.indexable for record in records),
        "pages": [asdict(record) for record in sorted(records, key=lambda item: item.path)],
    }


def write_baseline(path: Path, records: list[PageRecord]) -> None:
    target = path if path.is_absolute() else SITE_ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(baseline_payload(records), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def check_baseline(path: Path, records: list[PageRecord], findings: list[Finding]) -> None:
    target = path if path.is_absolute() else SITE_ROOT / path
    try:
        expected = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        findings.append(Finding("error", "baseline-read", str(path), str(exc)))
        return
    actual = baseline_payload(records)
    expected_pages = {page["path"]: page for page in expected.get("pages", [])}
    actual_pages = {page["path"]: page for page in actual["pages"]}
    for missing in sorted(expected_pages.keys() - actual_pages.keys()):
        findings.append(Finding("error", "baseline-page-missing", missing, "Page disappeared"))
    for added in sorted(actual_pages.keys() - expected_pages.keys()):
        findings.append(Finding("error", "baseline-page-added", added, "Page was added"))
    compared_fields = ("route", "indexable", "title", "description", "canonical", "h1", "content_hash")
    for page in sorted(expected_pages.keys() & actual_pages.keys()):
        for field_name in compared_fields:
            if expected_pages[page].get(field_name) != actual_pages[page].get(field_name):
                findings.append(
                    Finding(
                        "error",
                        "baseline-drift",
                        page,
                        f"{field_name}: expected {expected_pages[page].get(field_name)!r}, "
                        f"found {actual_pages[page].get(field_name)!r}",
                    )
                )


def print_report(records: list[PageRecord], findings: list[Finding], json_output: bool) -> None:
    errors = sorted(item for item in findings if item.severity == "error")
    warnings = sorted(item for item in findings if item.severity == "warning")
    if json_output:
        print(
            json.dumps(
                {
                    "summary": {
                        "html_files": len(records),
                        "indexable_routes": sum(record.indexable for record in records),
                        "errors": len(errors),
                        "warnings": len(warnings),
                    },
                    "findings": [asdict(item) for item in sorted(findings)],
                },
                indent=2,
            )
        )
        return

    for item in errors + warnings:
        print(f"{item.severity.upper():7} {item.code:24} {item.path}: {item.detail}")
    print()
    print(
        f"Audited {len(records)} HTML files / {sum(record.indexable for record in records)} indexable routes: "
        f"{len(errors)} errors, {len(warnings)} warnings."
    )


def main() -> int:
    args = parse_args()
    records, findings, _ = audit_pages(args)
    audit_sitemap(records, findings)
    audit_image_pipeline(args, findings)
    audit_theme_css(findings)
    audit_governance(records, findings)
    if args.write_baseline:
        write_baseline(args.write_baseline, records)
    if args.check_baseline:
        check_baseline(args.check_baseline, records, findings)
    print_report(records, findings, args.json_output)
    return 1 if any(item.severity == "error" for item in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
