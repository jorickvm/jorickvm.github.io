#!/usr/bin/env python3
"""Build smaller copies of the marketing screenshots for phones and low-density screens."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "_site-src/content"
IMAGES = "assets/home"
OUTPUT = ROOT / IMAGES / "web"
MANIFEST = ROOT / "_site-src/data/responsive-images.json"
# A phone screenshot is drawn at most 300 CSS pixels wide, so 720 covers a
# 2x laptop and a 3x phone, and 480 covers everything below that.
WIDTHS = (480, 720)
QUALITY = 82
REFERENCE = re.compile(r'<img\b[^>]*?\bsrc="[^"]*?(' + IMAGES + r'/[^"?]+\.webp)')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def webp_size(path):
    data = path.read_bytes()
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError(f"Not a WebP: {path.name}")
    offset = 12
    while offset + 8 <= len(data):
        kind = data[offset:offset + 4]
        size = int.from_bytes(data[offset + 4:offset + 8], "little")
        body = data[offset + 8:offset + 8 + size]
        if kind == b"VP8X":
            return int.from_bytes(body[4:7], "little") + 1, int.from_bytes(body[7:10], "little") + 1
        if kind == b"VP8 ":
            return int.from_bytes(body[6:8], "little") & 0x3fff, int.from_bytes(body[8:10], "little") & 0x3fff
        if kind == b"VP8L":
            bits = int.from_bytes(body[1:5], "little")
            return (bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1
        offset += 8 + size + (size % 2)
    raise ValueError(f"No image data in {path.name}")


def variant_path(source, width):
    """Site path of the copy of `source` that is `width` pixels wide."""
    return f"{IMAGES}/web/{width}/{source[len(IMAGES) + 1:]}"


def referenced_sources():
    """Every marketing screenshot a page fragment shows, in any language."""
    sources = set()
    for fragment in CONTENT.rglob("*.html"):
        sources.update(REFERENCE.findall(fragment.read_text(encoding="utf-8")))
    return sorted(source for source in sources if not source.startswith(f"{IMAGES}/web/"))


def record(source):
    width, height = webp_size(ROOT / source)
    variants = {}
    for target in WIDTHS:
        if target >= width:
            continue
        output = ROOT / variant_path(source, target)
        built_width, built_height = webp_size(output)
        if built_width != target or abs(built_height - height * target / width) > 1:
            raise ValueError(f"Unexpected size for {output.relative_to(ROOT)}")
        variants[str(target)] = {"sha256": digest(output), "bytes": output.stat().st_size}
    return {"source_sha256": digest(ROOT / source), "width": width, "height": height, "variants": variants}


def build(source, encoder):
    width, _ = webp_size(ROOT / source)
    for target in WIDTHS:
        if target >= width:
            continue
        output = ROOT / variant_path(source, target)
        output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [encoder, "-quiet", "-q", str(QUALITY), "-m", "6", "-sharp_yuv", "-resize", str(target), "0",
             str(ROOT / source), "-o", str(output)],
            check=True, capture_output=True,
        )
    return source, record(source)


def expected_outputs(sources):
    outputs = set()
    for source in sources:
        width, _ = webp_size(ROOT / source)
        outputs.update(variant_path(source, target) for target in WIDTHS if target < width)
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify the stored images without encoding")
    args = parser.parse_args()
    sources = referenced_sources()
    if args.check:
        manifest = json.loads(MANIFEST.read_text())
        if (manifest.get("widths"), manifest.get("quality")) != (list(WIDTHS), QUALITY):
            raise SystemExit("Screenshot sizes changed; rebuild the images")
        expected = manifest["images"]
        if set(expected) != set(sources):
            raise SystemExit("Marketing screenshots changed; run scripts/build_responsive_images.py")
        on_disk = {path.relative_to(ROOT).as_posix() for path in OUTPUT.rglob("*.webp")}
        if on_disk != expected_outputs(sources):
            raise SystemExit("Resized screenshots are missing or unexpected")
        for source in sources:
            if record(source) != expected[source]:
                raise SystemExit(f"Resized screenshot is stale: {source}")
        print(f"Checked {len(sources)} screenshots and {len(on_disk)} resized copies.")
        return
    encoder = shutil.which("cwebp")
    if not encoder:
        raise SystemExit("cwebp is required to build the resized screenshots")
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = dict(pool.map(lambda source: build(source, encoder), sources))
    MANIFEST.write_text(json.dumps({"widths": list(WIDTHS), "quality": QUALITY, "images": records}, indent=2) + "\n")
    original = sum((ROOT / source).stat().st_size for source in sources)
    smallest = sum(min(variant["bytes"] for variant in row["variants"].values()) for row in records.values())
    print(f"Built resized copies of {len(records)} screenshots: {original:,} bytes at full size, "
          f"{smallest:,} at {WIDTHS[0]} pixels.")


if __name__ == "__main__":
    main()
