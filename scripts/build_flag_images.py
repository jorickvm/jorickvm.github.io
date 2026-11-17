#!/usr/bin/env python3
"""Build lightweight flag images while retaining their PNG masters."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
FLAGS = ROOT / "assets/flags"
OUTPUT = FLAGS / "web"
MANIFEST = ROOT / "_site-src/data/flag-images.json"
THUMBNAIL_WIDTH = 168
THUMBNAIL_HEIGHT = 126


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def png_size(path):
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Not a PNG: {path.name}")
    return struct.unpack(">II", data[16:24])


def webp_size(path):
    data = path.read_bytes()
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError(f"Not a WebP: {path.name}")
    offset = 12
    while offset + 8 <= len(data):
        kind = data[offset:offset + 4]
        size = int.from_bytes(data[offset + 4:offset + 8], "little")
        body = data[offset + 8:offset + 8 + size]
        if kind == b"VP8L" and len(body) >= 5 and body[0] == 0x2f:
            bits = int.from_bytes(body[1:5], "little")
            return (bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1
        offset += 8 + size + (size % 2)
    raise ValueError(f"Not a lossless WebP: {path.name}")


def record(source, output):
    width, height = webp_size(output)
    original_width, original_height = png_size(source)
    if not (min(original_width, THUMBNAIL_WIDTH) <= width <= original_width
            and min(original_height, THUMBNAIL_HEIGHT) <= height <= original_height):
        raise ValueError(f"Unexpected flag resolution: {output.name}")
    if abs(height - original_height * width / original_width) > 1:
        raise ValueError(f"Flag aspect ratio changed: {output.name}")
    return {"source_sha256": digest(source), "webp_sha256": digest(output),
            "width": width, "height": height, "bytes": output.stat().st_size}


def build(source, encoder):
    with tempfile.TemporaryDirectory() as folder:
        candidates = []
        source_width, source_height = png_size(source)
        thumbnail_width = min(source_width, math.ceil(max(THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT * source_width / source_height)))
        for width in (0, thumbnail_width):
            if width and source_width <= width:
                continue
            target = Path(folder) / f"{width}.webp"
            command = [encoder, "-quiet", "-lossless", "-exact", "-m", "6", "-metadata", "icc"]
            if width:
                command += ["-resize", str(width), "0"]
            subprocess.run(command + [str(source), "-o", str(target)], check=True, capture_output=True)
            candidates.append(target)
        # Flat artwork can be smaller at its original dimensions.
        smallest = min(candidates, key=lambda path: path.stat().st_size)
        output = OUTPUT / f"{source.stem}.webp"
        shutil.copyfile(smallest, output)
    return source.stem, record(source, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify the stored images without encoding")
    args = parser.parse_args()
    sources = sorted(FLAGS.glob("*.png"))
    if args.check:
        manifest = json.loads(MANIFEST.read_text())
        expected = manifest["flags"]
        if (manifest.get("thumbnail_width"), manifest.get("thumbnail_height")) != (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT):
            raise SystemExit("Flag image dimensions changed; rebuild the images")
        if set(expected) != {p.stem for p in sources}:
            raise SystemExit("Flag masters changed; rebuild the images")
        if {p.stem for p in OUTPUT.glob("*.webp")} != set(expected):
            raise SystemExit("Flag web images are missing or unexpected")
        for source in sources:
            output = OUTPUT / f"{source.stem}.webp"
            if not output.exists() or record(source, output) != expected[source.stem]:
                raise SystemExit(f"Flag image is stale: {source.name}")
        print(f"Checked {len(sources)} optimized flag images.")
        return
    encoder = shutil.which("cwebp")
    if not encoder:
        raise SystemExit("cwebp is required to build flag images")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = dict(pool.map(lambda path: build(path, encoder), sources))
    MANIFEST.write_text(json.dumps({"thumbnail_width": THUMBNAIL_WIDTH, "thumbnail_height": THUMBNAIL_HEIGHT, "flags": records}, indent=2) + "\n")
    original = sum(path.stat().st_size for path in sources)
    optimized = sum(row["bytes"] for row in records.values())
    print(f"Built {len(records)} flags: {original:,} to {optimized:,} bytes ({100 * (1 - optimized / original):.1f}% smaller).")


if __name__ == "__main__":
    main()
