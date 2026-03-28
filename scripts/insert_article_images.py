#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from article_image_lib import (
    CATALOG_PATH,
    SITE_ROOT,
    discover_articles,
    load_plan,
    relative_asset_url,
    select_article_keys,
)


STYLE_START = "<!-- ARTICLE_IMAGE_STYLES_START -->"
STYLE_END = "<!-- ARTICLE_IMAGE_STYLES_END -->"
RENDER_START = "<!-- ARTICLE_IMAGE_RENDER_START:{slot} -->"
RENDER_END = "<!-- ARTICLE_IMAGE_RENDER_END:{slot} -->"
STYLE_BLOCK = """<!-- ARTICLE_IMAGE_STYLES_START -->
  <style id="atlasdays-article-image-styles">
    .atlasdays-article-image {
      margin: 26px 0 30px;
      padding: 10px;
      border-radius: 28px;
      border: 1px solid var(--line, rgba(255,255,255,0.10));
      background:
        linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02)),
        radial-gradient(circle at top left, rgba(22,146,255,0.12), transparent 58%);
      box-shadow: 0 18px 42px rgba(0,0,0,0.12);
    }
    .atlasdays-article-image img {
      display: block;
      width: 100%;
      height: auto;
      border-radius: 22px;
      border: 1px solid rgba(255,255,255,0.06);
      background: rgba(214, 232, 248, 0.42);
      box-shadow: 0 18px 42px rgba(0,0,0,0.18);
    }
    .atlasdays-article-image.is-hero {
      margin-top: 22px;
      margin-bottom: 34px;
    }
    .atlasdays-article-image figcaption {
      margin-top: 10px;
      color: var(--muted-2, var(--muted));
      font-size: 0.92rem;
      line-height: 1.55;
    }
    @media (prefers-color-scheme: light) {
      .atlasdays-article-image {
        border-color: rgba(22,146,255,0.14);
        background:
          linear-gradient(180deg, rgba(22,146,255,0.10), rgba(22,146,255,0.03)),
          linear-gradient(180deg, rgba(232,242,252,0.88), rgba(244,248,253,0.92));
        box-shadow: 0 14px 30px rgba(15, 28, 48, 0.08);
      }
      .atlasdays-article-image img {
        border-color: rgba(22,146,255,0.10);
        background: rgba(226, 238, 248, 0.82);
        box-shadow: 0 14px 28px rgba(15, 28, 48, 0.10);
      }
    }
    html[data-theme="light"] .atlasdays-article-image {
      border-color: rgba(22,146,255,0.14);
      background:
        linear-gradient(180deg, rgba(22,146,255,0.10), rgba(22,146,255,0.03)),
        linear-gradient(180deg, rgba(232,242,252,0.88), rgba(244,248,253,0.92));
      box-shadow: 0 14px 30px rgba(15, 28, 48, 0.08);
    }
    html[data-theme="light"] .atlasdays-article-image img {
      border-color: rgba(22,146,255,0.10);
      background: rgba(226, 238, 248, 0.82);
      box-shadow: 0 14px 28px rgba(15, 28, 48, 0.10);
    }
    @media (max-width: 640px) {
      .atlasdays-article-image {
        margin: 22px 0 26px;
        padding: 8px;
        border-radius: 24px;
      }
      .atlasdays-article-image img {
        border-radius: 18px;
      }
      .atlasdays-article-image.is-hero {
        margin-top: 18px;
        margin-bottom: 28px;
      }
      .atlasdays-article-image figcaption {
        font-size: 0.9rem;
      }
    }
  </style>
  <!-- ARTICLE_IMAGE_STYLES_END -->"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Insert generated article images into Help/Learn HTML files using explicit placement markers."
    )
    parser.add_argument("--section", choices=("all", "learn", "help"), default="all")
    parser.add_argument("--slug")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--captions", action="store_true", help="Render visible figure captions.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Fail if any expected asset is missing.")
    return parser.parse_args()


def load_catalog() -> dict[tuple[str, str], dict]:
    if not CATALOG_PATH.exists():
        raise SystemExit(f"Missing catalog: {CATALOG_PATH}. Run generate_article_images.py first.")
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    lookup: dict[tuple[str, str], dict] = {}
    for article in data.get("articles", []):
        article_key = f"{article['section']}/{article['slug']}"
        for image in article.get("images", []):
          lookup[(article_key, image["slot"])] = image
    return lookup


def ensure_style_block(text: str) -> str:
    style_pattern = re.compile(
        re.escape(STYLE_START) + r".*?" + re.escape(STYLE_END),
        re.DOTALL,
    )
    if style_pattern.search(text):
        return style_pattern.sub(STYLE_BLOCK, text)
    if "</head>" not in text:
        raise SystemExit("Could not find </head> while inserting article image styles.")
    return text.replace("</head>", STYLE_BLOCK + "\n</head>", 1)


def render_figure(rel_url: str, alt: str, slot_id: str, caption: str | None, captions: bool) -> str:
    is_hero = slot_id == "hero"
    classes = "atlasdays-article-image is-hero" if is_hero else "atlasdays-article-image is-body"
    attrs = [
        f'src="{rel_url}"',
        f'alt="{alt}"',
        'width="1536"',
        'height="1024"',
        'decoding="async"',
        'sizes="(max-width: 760px) calc(100vw - 40px), 720px"',
    ]
    if is_hero:
        attrs.append('loading="eager"')
        attrs.append('fetchpriority="high"')
    else:
        attrs.append('loading="lazy"')
    lines = [
        f'    <figure class="{classes}" data-article-image-slot="{slot_id}">',
        f'      <img {" ".join(attrs)} />',
    ]
    if captions and caption:
        lines.append(f"      <figcaption>{caption}</figcaption>")
    lines.append("    </figure>")
    return "\n".join(lines)


def upsert_render_block(text: str, marker: str, slot_id: str, figure_html: str | None) -> str:
    marker_comment = f"<!-- ARTICLE_IMAGE:{marker} -->"
    if marker_comment not in text:
        raise SystemExit(f"Missing marker {marker_comment}")
    start = RENDER_START.format(slot=slot_id)
    end = RENDER_END.format(slot=slot_id)
    block_pattern = re.compile(
        re.escape(start) + r".*?" + re.escape(end),
        re.DOTALL,
    )
    replacement = ""
    if figure_html is not None:
        replacement = f"{start}\n{figure_html}\n    {end}"
    if block_pattern.search(text):
        if replacement:
            return block_pattern.sub(replacement, text)
        return block_pattern.sub("", text)
    if not replacement:
        return text
    return text.replace(marker_comment, f"{marker_comment}\n    {replacement}", 1)


def main() -> int:
    args = parse_args()
    plan = load_plan()
    catalog = load_catalog()
    selected_keys = select_article_keys(plan, args.section, args.slug, args.limit)
    if not selected_keys:
        print("No matching articles found.")
        return 0
    articles = discover_articles(set(selected_keys))

    inserted = 0
    removed = 0
    for key in selected_keys:
        article = articles.get(key)
        if article is None:
            raise SystemExit(f"Plan references missing article: {key}")
        text = article.source_path.read_text(encoding="utf-8")
        original = text
        has_real_asset = False
        for slot in plan["articles"][key]["slots"]:
            catalog_entry = catalog.get((key, slot["id"]))
            if catalog_entry is None:
                raise SystemExit(f"Missing catalog entry for {key} slot {slot['id']}")
            asset_path = SITE_ROOT / catalog_entry["path"]
            figure_html = None
            if asset_path.exists():
                has_real_asset = True
                rel_url = relative_asset_url(article.source_path, asset_path)
                figure_html = render_figure(
                    rel_url=rel_url,
                    alt=str(catalog_entry.get("alt", "")),
                    slot_id=slot["id"],
                    caption=str(catalog_entry.get("caption", "")),
                    captions=args.captions,
                )
            elif args.strict:
                raise SystemExit(f"Missing generated asset for {key} slot {slot['id']}: {asset_path}")
            before = text
            text = upsert_render_block(text, slot["marker"], slot["id"], figure_html)
            if text != before:
                if figure_html is None:
                    removed += 1
                else:
                    inserted += 1
        if has_real_asset or STYLE_START in text:
            if has_real_asset:
                text = ensure_style_block(text)
            elif STYLE_START in text and STYLE_END in text:
                style_pattern = re.compile(
                    re.escape(STYLE_START) + r".*?" + re.escape(STYLE_END) + r"\n?",
                    re.DOTALL,
                )
                text = style_pattern.sub("", text)
        if text != original and not args.dry_run:
            article.source_path.write_text(text, encoding="utf-8")
            print(f"Updated {article.source_path.relative_to(SITE_ROOT)}")
        elif args.dry_run:
            print(f"Checked {article.source_path.relative_to(SITE_ROOT)}")

    action = "Checked" if args.dry_run else "Updated"
    print(f"\n{action} {len(selected_keys)} article files. Inserted/updated {inserted} image blocks; removed {removed}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
