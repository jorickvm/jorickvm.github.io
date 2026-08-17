#!/usr/bin/env python3
"""Build the manifest that assigns one generic Open Graph card site-wide."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "_site-src" / "data"
OUTPUT = ROOT / "assets" / "social"
MANIFEST = DATA / "social-cards.json"
WIDTH = 1200
HEIGHT = 630
GENERIC_IMAGE = OUTPUT / "site-v1.png"
GENERIC_ALT = "AtlasDays private travel-day tracking app with a globe and tracker screens"


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate the manifest and generic social image")
    return parser.parse_args()


def is_noindex(record: dict[str, object]) -> bool:
    for meta in record.get("meta", []):
        if meta.get("name") == "robots" and "noindex" in str(meta.get("content", "")):
            return True
    return False


def records() -> list[str]:
    result = ["index.html"]
    seen = set(result)
    for filename, key in (("articles.json", "articles"), ("hubs.json", "hubs"), ("pages.json", "pages")):
        payload = json.loads((DATA / filename).read_text(encoding="utf-8"))
        for item in payload[key]:
            path = str(item["path"])
            # A card only exists to be unfurled from a shared link, and
            # build_site.py gives an og:image to every page listed here. Pages
            # that are noindex are not shared: 404.html and support.html joined
            # pages.json for localization, and a share card for "Page not found"
            # or for a redirect stub is not a thing anyone wants unfurled.
            if path in seen or is_noindex(item):
                continue
            seen.add(path)
            result.append(path)
    return sorted(result)


def expected_manifest() -> dict[str, object]:
    image = "/" + GENERIC_IMAGE.relative_to(ROOT).as_posix()
    pages = [
        {
            "path": path,
            "image": image,
            "alt": GENERIC_ALT,
            "width": WIDTH,
            "height": HEIGHT,
        }
        for path in records()
    ]
    return {"schema_version": 1, "generated_by": "scripts/generate_social_cards.py", "pages": pages}


def check() -> int:
    expected = expected_manifest()
    current = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else None
    failures = []
    if current != expected:
        failures.append("social-cards.json is stale")
    for page in expected["pages"]:
        path = ROOT / str(page["image"]).lstrip("/")
        if not path.exists():
            failures.append(f"missing {path.relative_to(ROOT)}")
        elif path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            failures.append(f"not a PNG: {path.relative_to(ROOT)}")
    if failures:
        print("Social-card validation failed:")
        for failure in failures:
            print(f"  {failure}")
        return 1
    print(f"Checked {len(expected['pages'])} social cards.")
    return 0


def main() -> int:
    args = arguments()
    if args.check:
        return check()
    MANIFEST.write_text(json.dumps(expected_manifest(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Registered the generic social card for {len(records())} pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
