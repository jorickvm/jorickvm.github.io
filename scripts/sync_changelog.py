#!/usr/bin/env python3
"""Copy the release cards out of the AtlasDays repo's changelog into this site's page.

The two repos own different halves of the same page. The app repo owns the
**content**: `Docs/CHANGELOG.md` is written there at release time and its
`changelog.html` is the rendered result, so the release cards are authored once,
next to the code they describe. This repo owns the **page source**: shared design
tokens, the site header and footer, social card metadata, and the `?theme=`
bootstrap that lets the app open `/app/changelog/` in its own appearance.

The release workflow used to `cp` the whole file across, which silently reverted
every one of those site-side things on each release. This replaces only the
contents of `<div class="release-stack">`, so a release updates the cards and
nothing else.

The card markup itself is identical in both repos (`release-card`,
`release-card-head`, `release-kicker`, `v-label`, `release-date`,
`release-section`, `release-summary`), and it has to stay that way. The styles
live here; the app repo's inline copy exists so that file is viewable on its
own. If a card ever grows a new class, add it to this repo's stylesheet in the
same change.

    python3 scripts/sync_changelog.py ../AtlasDays/AtlasDays/changelog.html
    python3 scripts/sync_changelog.py <source> --check   # non-zero if stale
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parents[1]
TARGET = SITE_ROOT / "_site-src" / "content" / "pages" / "changelog.html"
STACK_OPEN = '<div class="release-stack">'
CARD_PATTERN = re.compile(r'<article class="release-card.*?</article>', re.S)


def release_cards(html: str) -> list[str]:
    cards = CARD_PATTERN.findall(html)
    if not cards:
        raise SystemExit("No release cards found in the source changelog.")
    return cards


def stack_bounds(html: str) -> tuple[int, int]:
    """Character range of the release-stack's inner content.

    Found by scanning rather than by one regex: a card contains its own
    `<div>`s, so a non-greedy match to the first `</div>` stops inside the first
    card, and a greedy one runs past the stack into the footer.
    """
    open_at = html.find(STACK_OPEN)
    if open_at == -1:
        raise SystemExit(f"{TARGET.name} has no {STACK_OPEN} wrapper.")
    inner_start = open_at + len(STACK_OPEN)
    last_card_end = html.rfind("</article>")
    if last_card_end == -1 or last_card_end < inner_start:
        raise SystemExit(f"{TARGET.name} has no release cards to replace.")
    close_at = html.find("</div>", last_card_end)
    if close_at == -1:
        raise SystemExit(f"{TARGET.name} has an unclosed release-stack.")
    return inner_start, close_at


def rendered(source_html: str, target_html: str) -> str:
    cards = release_cards(source_html)
    # Re-indent to this page's nesting; the app repo's file sits at a different
    # depth, so a straight copy stair-steps the whole stack.
    body = "\n" + "\n".join(
        "\n".join(
            ("      " + line.strip()) if line.strip() else ""
            for line in card.splitlines()
        )
        for card in cards
    ) + "\n    "
    start, end = stack_bounds(target_html)
    return target_html[:start] + body + target_html[end:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="changelog.html from the AtlasDays repo")
    parser.add_argument("--check", action="store_true",
                        help="Report whether the page is up to date, and change nothing.")
    args = parser.parse_args()

    if not args.source.is_file():
        raise SystemExit(f"Source changelog not found: {args.source}")

    target_html = TARGET.read_text(encoding="utf-8")
    updated = rendered(args.source.read_text(encoding="utf-8"), target_html)

    if updated == target_html:
        print(f"{TARGET.name} is up to date.")
        return 0
    if args.check:
        print(f"{TARGET.name} is out of date. Run scripts/sync_changelog.py to update it.",
              file=sys.stderr)
        return 1
    TARGET.write_text(updated, encoding="utf-8")
    print(f"Updated {TARGET.name} with {len(release_cards(args.source.read_text(encoding='utf-8')))} release cards.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
