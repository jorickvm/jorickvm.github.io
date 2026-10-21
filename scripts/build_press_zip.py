#!/usr/bin/env python3
"""Bundle the press kit downloads into assets/press/kit/atlasdays-press-kit.zip.

The zip holds the full-size files the press page links to one by one: the app
icons, the iPhone screenshots (framed and plain screen), the framed iPhone Duo
images and the unfold video. Entries carry a fixed timestamp, so rebuilding
without a changed file gives a byte-identical zip. Run it after replacing any
of those files.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "assets" / "press" / "kit"
OUT = KIT / "atlasdays-press-kit.zip"
FOLDER = "AtlasDays-press-kit"
STAMP = (2026, 1, 1, 0, 0, 0)


def entries() -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    for path in sorted(KIT.glob("atlasdays-icon*.png")):
        if not path.stem.endswith("-256"):
            files.append((path, f"icon/{path.name}"))
    for path in sorted(KIT.glob("iphone-*.png")):
        folder = "screen" if path.stem.endswith("-screen") else "framed"
        files.append((path, f"iphone/{folder}/{path.name}"))
    for path in sorted(KIT.glob("duo-*.png")):
        files.append((path, f"iphone-duo/{path.name}"))
    video = ROOT / "assets" / "press" / "iphone-duo" / "unfold.mp4"
    files.append((video, "iphone-duo/atlasdays-iphone-duo-unfold.mp4"))
    return files


def main() -> int:
    with zipfile.ZipFile(OUT, "w") as archive:
        for path, name in entries():
            info = zipfile.ZipInfo(f"{FOLDER}/{name}", STAMP)
            info.external_attr = 0o644 << 16
            # Images and video are already compressed; deflating them gains nothing.
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, path.read_bytes())
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(entries())} files, {OUT.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
