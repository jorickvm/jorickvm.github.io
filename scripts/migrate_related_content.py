#!/usr/bin/env python3
"""Remove legacy hand-picked Learn related blocks after cluster migration."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "_site-src" / "content" / "learn"
PATTERN = re.compile(r"\n\s*<div class=\"related\">.*?</div>\s*\n", re.DOTALL)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    changed = []
    for path in sorted(CONTENT.glob("*.html")):
        current = path.read_text(encoding="utf-8")
        rendered, count = PATTERN.subn("\n\n", current)
        if not count:
            continue
        changed.append(path)
        if not options.check:
            path.write_text(rendered, encoding="utf-8")
    if options.check and changed:
        print("Hand-authored related blocks remain:")
        for path in changed:
            print(f"  {path.relative_to(ROOT)}")
        return 1
    print(("Checked" if options.check else "Migrated") + f" related content; {len(changed)} files changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
