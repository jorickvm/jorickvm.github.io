#!/usr/bin/env python3
"""Remove palette-selection media queries; AtlasDays defaults to explicit dark."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSS_ROOT = ROOT / "assets" / "css"
MARKER = "@media (prefers-color-scheme:"


def strip_blocks(css: str) -> str:
    while MARKER in css:
        start = css.index(MARKER)
        open_brace = css.find("{", start)
        if open_brace < 0:
            raise ValueError("unterminated prefers-color-scheme media query")
        depth = 0
        end = None
        for index in range(open_brace, len(css)):
            if css[index] == "{":
                depth += 1
            elif css[index] == "}":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end is None:
            raise ValueError("unterminated prefers-color-scheme block")
        css = css[:start] + css[end:]
    return css


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    changed = []
    for path in sorted(CSS_ROOT.rglob("*.css")):
        current = path.read_text(encoding="utf-8")
        rendered = strip_blocks(current)
        if current == rendered:
            continue
        changed.append(path)
        if not options.check:
            path.write_text(rendered, encoding="utf-8")
    if options.check and changed:
        print("System theme still selects the palette in:")
        for path in changed:
            print(f"  {path.relative_to(ROOT)}")
        return 1
    print(("Checked" if options.check else "Updated") + f" CSS theme policy; {len(changed)} files changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
