#!/usr/bin/env python3
"""Regenerate the tax-residency hub tables from articles.json.

Hub rows come from the learn records in _site-src/data/articles.json that
carry a "residency" object ("group" picks the hub). The hub fragments keep
hand-written chrome (hero, search box, CTA) and two machine-generated regions
marked by HTML comments:

    <!-- HUB_TABLE_START --> ... <!-- HUB_TABLE_END -->
    <!-- HUB_COUNT_START -->N<!-- HUB_COUNT_END -->

This script fills those regions in the _site-src fragment, not in the rendered
page. build_site.py renders the page from that fragment, so writing the page
here would be undone by the next site build -- which is exactly how the hub
once lost ten countries. Adding a country means adding the article record
(with its "residency" object) to articles.json, then:

    python3 scripts/build_residency_hub.py && python3 scripts/build_site.py

With --check, verifies the fragments match what the data would generate and
that every residency-tagged record has its rendered page on disk.
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "_site-src" / "data" / "articles.json"
FRAGMENTS = ROOT / "_site-src" / "content" / "hubs"
HUBS = [
    ("countries", FRAGMENTS / "learn-tax-residency-by-country.html"),
    ("us_states", FRAGMENTS / "learn-us-state-tax-residency.html"),
]


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_table(entries: list[dict]) -> str:
    rows = []
    for e in sorted(entries, key=lambda x: str(x["name"]).lower()):
        name = esc(str(e["name"]))
        href = "/learn/" + str(e["slug"])
        rows.append(
            f'        <tr class="hub-row" data-name="{name.lower()}" data-href="{href}">\n'
            f'          <td class="hub-td-country"><img class="hub-row-flag" '
            f'src="../assets/flags/{e["code"]}.png" alt="" width="30" height="22" loading="lazy" /> '
            f'<a href="{href}">{name}</a></td>\n'
            f'          <td>{esc(str(e["threshold"]))}</td>\n'
            f'          <td>{esc(str(e["windowLabel"]))}</td>\n'
            f'          <td class="hub-td-go"><span aria-hidden="true">&rarr;</span></td>\n'
            f'        </tr>'
        )
    return "\n".join(rows)


def replace_region(html: str, start: str, end: str, body: str) -> str:
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    return pattern.sub(f"{start}\n{body}\n{end}", html)


def load_entries() -> dict[str, list[dict]]:
    articles = json.loads(DATA.read_text(encoding="utf-8"))["articles"]
    groups: dict[str, list[dict]] = {}
    errors = []
    for article in articles:
        residency = article.get("residency")
        if not residency:
            continue
        path = str(article["path"])
        if not (ROOT / path).exists():
            errors.append(f"{path}: residency-tagged record has no rendered page on disk")
        entry = dict(residency)
        entry["slug"] = Path(path).stem
        groups.setdefault(str(residency["group"]), []).append(entry)
    if errors:
        raise SystemExit("Invalid residency records:\n  " + "\n  ".join(errors))
    return groups


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if fragments do not match the data")
    args = parser.parse_args()

    groups = load_entries()
    stale = []
    for key, hub_path in HUBS:
        entries = groups.get(key, [])
        if not entries:
            raise SystemExit(f"No residency entries for group {key!r} in {DATA.relative_to(ROOT)}")
        html = hub_path.read_text(encoding="utf-8")
        rebuilt = replace_region(html, "<!-- HUB_TABLE_START -->", "<!-- HUB_TABLE_END -->", build_table(entries))
        rebuilt = re.sub(
            r"<!-- HUB_COUNT_START -->.*?<!-- HUB_COUNT_END -->",
            f"<!-- HUB_COUNT_START -->{len(entries)}<!-- HUB_COUNT_END -->",
            rebuilt,
            flags=re.DOTALL,
        )
        if args.check:
            if rebuilt != html:
                stale.append(hub_path.relative_to(ROOT).as_posix())
        elif rebuilt != html:
            hub_path.write_text(rebuilt, encoding="utf-8")
            print(f"Wrote {hub_path.relative_to(ROOT)} with {len(entries)} entries.")
        else:
            print(f"{hub_path.relative_to(ROOT)} already current ({len(entries)} entries).")

    if stale:
        print("Hub fragments are stale; run scripts/build_residency_hub.py:\n  " + "\n  ".join(stale))
        return 1
    if args.check:
        total = sum(len(v) for v in groups.values())
        print(f"Checked {len(HUBS)} hub fragments against {total} residency records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
