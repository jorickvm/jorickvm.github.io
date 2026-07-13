#!/usr/bin/env python3
"""Regenerate the tax-residency hub page from scripts/residency_data.json.

The hub page keeps hand-written chrome (header, hero, search box, CTA) and two
machine-generated regions marked by HTML comments:

    <!-- HUB_TABLE_START --> ... <!-- HUB_TABLE_END -->
    <!-- HUB_COUNT_START -->N<!-- HUB_COUNT_END -->

This script fills those regions in place, so the emitted HTML is static and
crawlable (search is progressive-enhancement JS layered on top). Adding a country
is a one-line edit in residency_data.json followed by:

    python3 scripts/build_residency_hub.py

It also prints the sitemap <url> blocks and llms.txt lines for any entries, so the
shared files can be kept in sync.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "scripts" / "residency_data.json"
HUBS = [
    ("countries", ROOT / "learn" / "tax-residency-by-country.html"),
    ("us_states", ROOT / "learn" / "us-state-tax-residency.html"),
]


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_table(countries: list) -> str:
    rows = []
    for c in sorted(countries, key=lambda x: x["name"].lower()):
        name = esc(c["name"])
        href = f"/learn/{c['slug']}"
        rows.append(
            f'        <tr class="hub-row" data-name="{name.lower()}" data-href="{href}">\n'
            f'          <td class="hub-td-country"><img class="hub-row-flag" '
            f'src="../assets/flags/{c["code"]}.png" alt="" width="30" height="22" loading="lazy" /> '
            f'<a href="{href}">{name}</a></td>\n'
            f'          <td>{esc(c["threshold"])}</td>\n'
            f'          <td>{esc(c["windowLabel"])}</td>\n'
            f'          <td class="hub-td-go"><span aria-hidden="true">&rarr;</span></td>\n'
            f'        </tr>'
        )
    return "\n".join(rows)


def replace_region(html: str, start: str, end: str, body: str) -> str:
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    return pattern.sub(f"{start}\n{body}\n{end}", html)


def main() -> None:
    data = json.loads(DATA.read_text())

    for key, hub_path in HUBS:
        rows = data.get(key, [])
        if not rows or not hub_path.exists():
            print(f"Skipped {hub_path.name} ({len(rows)} entries, exists={hub_path.exists()}).")
            continue
        html = hub_path.read_text()
        html = replace_region(html, "<!-- HUB_TABLE_START -->", "<!-- HUB_TABLE_END -->", build_table(rows))
        html = re.sub(
            r"<!-- HUB_COUNT_START -->.*?<!-- HUB_COUNT_END -->",
            f"<!-- HUB_COUNT_START -->{len(rows)}<!-- HUB_COUNT_END -->",
            html,
            flags=re.DOTALL,
        )
        hub_path.write_text(html)
        print(f"Wrote {hub_path.relative_to(ROOT)} with {len(rows)} entries.")

    print("\n--- sitemap <url> blocks ---")
    for key, _ in HUBS:
        for c in data.get(key, []):
            print(
                f"  <url>\n    <loc>https://atlasdays.app/learn/{c['slug']}</loc>\n"
                f"    <lastmod>2026-07-13</lastmod>\n    <priority>0.8</priority>\n  </url>"
            )


if __name__ == "__main__":
    main()
