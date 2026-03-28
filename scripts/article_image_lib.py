#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SITE_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = SITE_ROOT / "assets" / "article-images"
CATALOG_PATH = OUTPUT_ROOT / "catalog.json"
PLAN_PATH = SITE_ROOT / "article-image-plan.json"
ENV_PATH = SITE_ROOT / ".env.local"

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
DESCRIPTION_RE = re.compile(
    r'<meta\s+name="description"\s+content="(.*?)"\s*/?>',
    re.IGNORECASE | re.DOTALL,
)
CANONICAL_RE = re.compile(
    r'<link\s+rel="canonical"\s+href="(.*?)"\s*/?>',
    re.IGNORECASE | re.DOTALL,
)
ARTICLE_RE = re.compile(r"<article\b[^>]*>(.*?)</article>", re.IGNORECASE | re.DOTALL)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
H2_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.IGNORECASE | re.DOTALL)
P_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL)
LI_RE = re.compile(r"<li[^>]*>(.*?)</li>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class SectionContext:
    heading: str
    summary: str
    detail_points: list[str]


@dataclass
class Article:
    section: str
    slug: str
    source_path: Path
    title: str
    description: str
    canonical: str | None
    headline: str
    intro: str
    section_contexts: list[SectionContext]

    @property
    def key(self) -> str:
        return f"{self.section}/{self.slug}"


def load_env_file(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def clean_article_title(value: str) -> str:
    cleaned = re.sub(r"\s+[—-]\s+AtlasDays Help$", "", value)
    cleaned = re.sub(r"\s+[—-]\s+AtlasDays$", "", cleaned)
    cleaned = re.sub(r"\s+[—-]\s+Help$", "", cleaned)
    return cleaned.strip()


def clean_html_text(value: str) -> str:
    text = TAG_RE.sub(" ", value)
    text = html.unescape(text)
    return collapse_whitespace(text)


def extract_article_html(text: str) -> str:
    match = ARTICLE_RE.search(text)
    return match.group(1) if match else text


def is_content_paragraph(value: str) -> bool:
    normalized = collapse_whitespace(value)
    if not normalized:
        return False
    lowered = normalized.lower()
    if lowered.startswith("last verified:") or lowered.startswith("last reviewed:"):
        return False
    if lowered.startswith("atlasdays /"):
        return False
    if lowered.startswith("need travel-rule explainers"):
        return False
    return len(normalized) >= 35


def extract_headline(article_html: str) -> str:
    match = H1_RE.search(article_html)
    return clean_html_text(match.group(1)) if match else ""


def extract_intro_paragraph(article_html: str) -> str:
    for match in P_RE.finditer(article_html):
        paragraph = clean_html_text(match.group(1))
        if is_content_paragraph(paragraph):
            return paragraph
    return ""


def extract_section_contexts(article_html: str) -> list[SectionContext]:
    matches = list(H2_RE.finditer(article_html))
    contexts: list[SectionContext] = []
    for index, match in enumerate(matches):
        heading = clean_html_text(match.group(1))
        if not heading:
            continue
        block_end = matches[index + 1].start() if index + 1 < len(matches) else len(article_html)
        block = article_html[match.end():block_end]
        summary = ""
        detail_points: list[str] = []
        for p_match in P_RE.finditer(block):
            paragraph = clean_html_text(p_match.group(1))
            if is_content_paragraph(paragraph):
                summary = paragraph
                break
        for p_match in P_RE.finditer(block):
            paragraph = clean_html_text(p_match.group(1))
            if not is_content_paragraph(paragraph):
                continue
            if paragraph != summary and paragraph not in detail_points:
                detail_points.append(paragraph)
            if len(detail_points) >= 2:
                break
        for li_match in LI_RE.finditer(block):
            item = clean_html_text(li_match.group(1))
            if len(item) < 20:
                continue
            if not summary:
                summary = item
                continue
            if item not in detail_points:
                detail_points.append(item)
            if len(detail_points) >= 5:
                break
        contexts.append(SectionContext(heading=heading, summary=summary, detail_points=detail_points))
    return contexts


def parse_article(path: Path, section: str) -> Article:
    text = path.read_text(encoding="utf-8")
    title_match = TITLE_RE.search(text)
    desc_match = DESCRIPTION_RE.search(text)
    canonical_match = CANONICAL_RE.search(text)
    if not title_match or not desc_match:
        raise SystemExit(f"Missing title or meta description in {path}")
    article_html = extract_article_html(text)
    title = clean_article_title(collapse_whitespace(title_match.group(1)))
    description = collapse_whitespace(desc_match.group(1))
    return Article(
        section=section,
        slug=path.stem,
        source_path=path,
        title=title,
        description=description,
        canonical=collapse_whitespace(canonical_match.group(1)) if canonical_match else None,
        headline=extract_headline(article_html) or title,
        intro=extract_intro_paragraph(article_html),
        section_contexts=extract_section_contexts(article_html),
    )


def discover_articles(selected_keys: set[str] | None = None) -> dict[str, Article]:
    lookup: dict[str, Article] = {}
    for section in ("help", "learn"):
        for path in sorted((SITE_ROOT / section).glob("*.html")):
            if path.name == "index.html":
                continue
            key = f"{section}/{path.stem}"
            if selected_keys is not None and key not in selected_keys:
                continue
            article = parse_article(path, section)
            lookup[article.key] = article
    return lookup


def load_plan(path: Path = PLAN_PATH) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Missing article image plan: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("articles"), dict):
        raise SystemExit(f"Invalid plan structure in {path}")
    return data


def select_article_keys(
    plan: dict[str, Any],
    section_filter: str,
    slug: str | None,
    limit: int,
) -> list[str]:
    keys = list(plan["articles"].keys())
    if section_filter != "all":
        keys = [key for key in keys if key.startswith(f"{section_filter}/")]
    if slug:
        keys = [key for key in keys if key.split("/", 1)[1] == slug]
    if limit > 0:
        keys = keys[:limit]
    return keys


def normalize_heading(value: str) -> str:
    return clean_html_text(value).casefold()


def find_section_context(article: Article, heading: str) -> SectionContext:
    target = normalize_heading(heading)
    for context in article.section_contexts:
        if normalize_heading(context.heading) == target:
            return context
    raise SystemExit(
        f'Could not find heading "{heading}" in {article.source_path.relative_to(SITE_ROOT)}'
    )


def relative_asset_url(from_article: Path, asset_path: Path) -> str:
    rel = os.path.relpath(asset_path, start=from_article.parent)
    return rel.replace(os.sep, "/")
