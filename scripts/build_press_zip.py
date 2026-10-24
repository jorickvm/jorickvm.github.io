#!/usr/bin/env python3
"""Bundle the press kit downloads into assets/press/kit/atlasdays-press-kit.zip.

The zip holds the full-size files the press page links to one by one: the app
icons, the iPhone screenshots (framed and plain screen), the framed iPhone Duo
images, the unfold video, and a Markdown press sheet generated from the page
source. Entries carry a fixed timestamp, so rebuilding without a changed file
gives a byte-identical zip. Run it after editing the press copy or media.
"""

from __future__ import annotations

import argparse
import io
import re
import xml.etree.ElementTree as ET
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "assets" / "press" / "kit"
OUT = KIT / "atlasdays-press-kit.zip"
SHEET = KIT / "README.md"
SOURCE = ROOT / "_site-src" / "content" / "pages" / "press.html"
PAGE_URL = "https://atlasdays.app/press/"
FOLDER = "AtlasDays-press-kit"
STAMP = (2026, 1, 1, 0, 0, 0)


class PressParser(HTMLParser):
    """Build a small tree from the authored fragment, including HTML entities."""

    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tree = ET.TreeBuilder()
        self.tree.start("document", {})

    def handle_starttag(self, tag, attrs):
        self.tree.start(tag, {key: value or "" for key, value in attrs})
        if tag in self.VOID:
            self.tree.end(tag)

    def handle_endtag(self, tag):
        if tag not in self.VOID:
            self.tree.end(tag)

    def handle_data(self, data):
        self.tree.data(data)


def press_markdown() -> str:
    """Export the standalone press sheet from the approved page sections."""
    parser = PressParser()
    parser.feed(SOURCE.read_text(encoding="utf-8"))
    parser.close()
    parser.tree.end("document")
    document = parser.tree.close()
    sections = {"Fact sheet", "Descriptions", "Key features", "Background", "Contact"}
    selected = []
    include = False
    for node in document.find("main"):
        if node.tag == "h2":
            include = "".join(node.itertext()).strip() in sections
        if include:
            selected.append(node)

    def render(node: ET.Element) -> str:
        tag = node.tag
        classes = node.get("class", "").split()
        if tag in {"button", "img"} or node.get("aria-hidden") == "true" or "press-actions" in classes:
            return ""
        content = re.sub(r"\s+", " ", node.text or "")
        for child in node:
            content += render(child) + re.sub(r"\s+", " ", child.tail or "")
        text = content.strip()
        if tag == "a":
            if "press-email" in classes:
                address = text.replace(" at ", "@")
                return f"[{address}](mailto:{address})"
            return f'[{text}]({urljoin(PAGE_URL, node.get("href", ""))})' if text else ""
        if tag in {"strong", "b"}:
            return f"**{text}**"
        if tag in {"em", "i"}:
            return f"*{text}*"
        if tag in {"h2", "h3", "h4"}:
            return f'\n\n{"#" * int(tag[1])} {text}\n\n'
        if tag == "dt":
            return f"\n- **{text}**: "
        if tag == "dd":
            return text + "\n"
        if tag == "li":
            return f"\n- {text}\n"
        if tag == "blockquote":
            return "\n\n" + "\n".join("> " + line for line in text.splitlines()) + "\n\n"
        if tag in {"p", "figcaption", "ul", "dl"} or "press-copy-head" in classes:
            return f"\n\n{text}\n\n"
        return content

    content = "# AtlasDays press sheet\n\n" + "".join(render(node) for node in selected)
    markdown = "\n".join(line.strip() for line in content.splitlines())
    return re.sub(r"\n{3,}", "\n\n", markdown).strip() + "\n"


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if the Markdown or ZIP is stale")
    args = parser.parse_args()
    files = entries()
    markdown = press_markdown().encode("utf-8")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, name in [(SHEET, "README.md"), *files]:
            info = zipfile.ZipInfo(f"{FOLDER}/{name}", STAMP)
            info.external_attr = 0o644 << 16
            # Images and video are already compressed; deflating them gains nothing.
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, markdown if path == SHEET else path.read_bytes())
    outputs = {SHEET: markdown, OUT: buffer.getvalue()}
    if args.check:
        stale = [path for path, content in outputs.items() if not path.exists() or path.read_bytes() != content]
        if stale:
            print("Press kit is stale; run python3 scripts/build_press_zip.py:")
            for path in stale:
                print(f"  {path.relative_to(ROOT)}")
            return 1
        print("Checked press kit Markdown and ZIP.")
        return 0
    for path, content in outputs.items():
        path.write_bytes(content)
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(files) + 1} files, {OUT.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
