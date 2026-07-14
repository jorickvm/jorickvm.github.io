#!/usr/bin/env python3
"""Generate deterministic, article-specific Open Graph cards and a manifest."""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "_site-src" / "data"
OUTPUT = ROOT / "assets" / "social"
MANIFEST = DATA / "social-cards.json"
WIDTH = 1200
HEIGHT = 630


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate the manifest and generated files without rendering")
    return parser.parse_args()


def description_for(record: dict[str, object]) -> str:
    for meta in record.get("meta", []):
        if meta.get("name") == "description":
            return str(meta.get("content", ""))
    return "Private travel-day tracking for iPhone."


def records() -> list[dict[str, str]]:
    result = [
        {
            "path": "index.html",
            "section": "Product",
            "title": "AtlasDays — Track Travel Days, Visa Limits & Residency",
            "description": "Private travel-day tracking for visa limits, residency thresholds, and a reliable long-term trip history.",
        }
    ]
    for filename, key in (("articles.json", "articles"), ("hubs.json", "hubs"), ("pages.json", "pages")):
        payload = json.loads((DATA / filename).read_text(encoding="utf-8"))
        for item in payload[key]:
            section = str(item.get("section") or item.get("current_navigation") or "AtlasDays")
            result.append(
                {
                    "path": str(item["path"]),
                    "section": section.replace("-", " ").title(),
                    "title": str(item["title"]).replace(" — AtlasDays Help Center", "").replace(" — AtlasDays", ""),
                    "description": description_for(item),
                }
            )
    return sorted(result, key=lambda item: item["path"])


def output_path(page_path: str) -> Path:
    if page_path == "index.html":
        return OUTPUT / "home.png"
    relative = Path(page_path).with_suffix(".png")
    return OUTPUT / relative


def wrap(value: str, width: int, max_lines: int) -> list[str]:
    lines = textwrap.wrap(value, width=width, break_long_words=False, break_on_hyphens=False)
    if len(lines) <= max_lines:
        return lines
    lines = lines[:max_lines]
    lines[-1] = lines[-1].rstrip(" .,") + "…"
    return lines


def text_lines(lines: list[str], x: int, y: int, spacing: int, css_class: str) -> str:
    return "\n".join(
        f'<text x="{x}" y="{y + index * spacing}" class="{css_class}">{html.escape(line)}</text>'
        for index, line in enumerate(lines)
    )


def svg_for(record: dict[str, str]) -> str:
    title = wrap(record["title"], 35, 3)
    description = wrap(record["description"], 68, 1 if len(title) >= 3 else 2)
    title_y = 250 if len(title) == 1 else 235
    description_y = title_y + len(title) * 68 + 26
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#07111f"/>
      <stop offset="0.58" stop-color="#101d31"/>
      <stop offset="1" stop-color="#07101c"/>
    </linearGradient>
    <radialGradient id="glow" cx="50%" cy="50%" r="50%">
      <stop offset="0" stop-color="#50a7ff" stop-opacity=".32"/>
      <stop offset="1" stop-color="#50a7ff" stop-opacity="0"/>
    </radialGradient>
    <filter id="soft"><feGaussianBlur stdDeviation="18"/></filter>
    <style>
      text {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
      .brand {{ fill:#f6f9ff; font-size:34px; font-weight:750; letter-spacing:-1px; }}
      .section {{ fill:#69b7ff; font-size:22px; font-weight:750; letter-spacing:3px; text-transform:uppercase; }}
      .title {{ fill:#f8fbff; font-size:56px; font-weight:780; letter-spacing:-1.8px; }}
      .description {{ fill:#b8c5d7; font-size:25px; font-weight:450; }}
      .domain {{ fill:#d9e4f3; font-size:22px; font-weight:650; }}
    </style>
  </defs>
  <rect width="1200" height="630" fill="url(#bg)"/>
  <circle cx="1040" cy="115" r="250" fill="url(#glow)"/>
  <circle cx="1080" cy="510" r="230" fill="#5b8cff" opacity=".08" filter="url(#soft)"/>
  <path d="M870 128 C980 95 1010 210 1100 180 S1160 255 1102 315 S978 320 920 410 S1005 520 1148 486" fill="none" stroke="#60b5ff" stroke-width="5" stroke-linecap="round" opacity=".58"/>
  <circle cx="870" cy="128" r="10" fill="#8ed0ff"/>
  <circle cx="1102" cy="315" r="10" fill="#f3b85f"/>
  <circle cx="1148" cy="486" r="10" fill="#8ed0ff"/>
  <rect x="58" y="54" width="1084" height="522" rx="36" fill="none" stroke="#92bce8" stroke-opacity=".2"/>
  <text x="92" y="116" class="brand">AtlasDays</text>
  <rect x="92" y="141" width="58" height="4" rx="2" fill="#58adff"/>
  <text x="92" y="174" class="section">{html.escape(record['section'])}</text>
  {text_lines(title, 92, title_y, 68, 'title')}
  {text_lines(description, 92, description_y, 38, 'description')}
  <text x="92" y="535" class="domain">atlasdays.app</text>
</svg>'''


def expected_manifest() -> dict[str, object]:
    pages = []
    for record in records():
        path = output_path(record["path"])
        pages.append(
            {
                "path": record["path"],
                "image": "/" + path.relative_to(ROOT).as_posix(),
                "alt": f"AtlasDays share card for {record['title']}",
                "width": WIDTH,
                "height": HEIGHT,
            }
        )
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
    converter = shutil.which("rsvg-convert")
    if not converter:
        raise SystemExit("rsvg-convert is required to render social cards")
    for record in records():
        destination = output_path(record["path"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", suffix=".svg", encoding="utf-8") as source:
            source.write(svg_for(record))
            source.flush()
            subprocess.run(
                [converter, "--format=png", f"--width={WIDTH}", f"--height={HEIGHT}", "--output", str(destination), source.name],
                check=True,
            )
    MANIFEST.write_text(json.dumps(expected_manifest(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Generated {len(records())} social cards.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
