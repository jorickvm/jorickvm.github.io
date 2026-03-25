#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys

from article_image_lib import (
    H2_RE,
    SITE_ROOT,
    clean_html_text,
    discover_articles,
    load_plan,
    select_article_keys,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Insert or verify article image placement markers in Help/Learn HTML files."
    )
    parser.add_argument("--section", choices=("all", "learn", "help"), default="all")
    parser.add_argument("--slug")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--check", action="store_true", help="Verify markers without rewriting files.")
    return parser.parse_args()


def marker_comment(marker: str) -> str:
    return f"<!-- ARTICLE_IMAGE:{marker} -->"


def strip_marker(text: str, marker: str) -> tuple[str, bool]:
    comment = marker_comment(marker)
    if comment not in text:
        return text, False
    updated = text.replace(f"\n    {comment}", "", 1)
    if updated == text:
        updated = text.replace(comment, "", 1)
    return updated, updated != text


def ensure_hero_marker(text: str, marker: str) -> tuple[str, bool]:
    if marker_comment(marker) in text:
        return text, False
    verified_match = list(re.finditer(r'<p class="verified">.*?</p>', text, re.DOTALL))
    if verified_match:
        target = verified_match[-1]
    else:
        subtitle_match = re.search(r'<p class="subtitle">.*?</p>', text, re.DOTALL)
        if subtitle_match is None:
            raise SystemExit("Could not find subtitle or verified paragraph for hero marker insertion.")
        target = subtitle_match
    insertion = f"{target.group(0)}\n\n    {marker_comment(marker)}"
    return text[: target.start()] + insertion + text[target.end():], True


def ensure_body_marker(text: str, marker: str, anchor_heading: str) -> tuple[str, bool]:
    text, removed = strip_marker(text, marker)
    for match in H2_RE.finditer(text):
        heading = clean_html_text(match.group(1))
        if heading.casefold() != anchor_heading.casefold():
            continue
        insert_at = match.end()
        marker_text = f"\n    {marker_comment(marker)}"
        if text[insert_at:insert_at + len(marker_text)] == marker_text:
            return text, removed
        return text[:insert_at] + marker_text + text[insert_at:], True
    raise SystemExit(f'Could not find h2 heading "{anchor_heading}" while inserting marker {marker}')


def main() -> int:
    args = parse_args()
    plan = load_plan()
    articles = discover_articles()
    selected_keys = select_article_keys(plan, args.section, args.slug, args.limit)
    if not selected_keys:
        print("No matching articles found.")
        return 0

    changed_files = 0
    for key in selected_keys:
        article = articles.get(key)
        if article is None:
            raise SystemExit(f"Plan references missing article: {key}")
        text = article.source_path.read_text(encoding="utf-8")
        original = text
        for slot in plan["articles"][key]["slots"]:
            marker = slot["marker"]
            if slot["id"] == "hero":
                text, _ = ensure_hero_marker(text, marker)
            else:
                anchor = slot.get("anchor_heading")
                if not isinstance(anchor, str) or not anchor.strip():
                    raise SystemExit(f'Missing anchor_heading for {key} slot {slot["id"]}')
                text, _ = ensure_body_marker(text, marker, anchor.strip())
        if text != original:
            changed_files += 1
            if not args.check:
                article.source_path.write_text(text, encoding="utf-8")
                print(f"Updated {article.source_path.relative_to(SITE_ROOT)}")
        elif args.check:
            print(f"OK {article.source_path.relative_to(SITE_ROOT)}")

    if args.check:
        print(f"\nVerified {len(selected_keys)} article files.")
    else:
        print(f"\nUpdated {changed_files} article files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
