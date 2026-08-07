#!/usr/bin/env python3
"""Preview the built site locally, the way GitHub Pages serves it.

The site links to extensionless URLs (``/help/create-a-tracker``, ``/about``).
GitHub Pages resolves those to the matching ``.html`` file; a plain
``python3 -m http.server`` returns 404 for every one of them, so clicking
through the site locally does not work without this.

    python3 scripts/serve_site.py            # http://localhost:8899
    python3 scripts/serve_site.py --port 9000

Dev tooling only. Never deployed.
"""

from __future__ import annotations

import argparse
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parents[1]


class PagesHandler(SimpleHTTPRequestHandler):
    """Adds GitHub Pages' extensionless-URL resolution and a WebP MIME type."""

    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".json": "application/json",
    }

    def translate_path(self, path: str) -> str:
        resolved = Path(super().translate_path(path))
        if resolved.is_dir() or resolved.exists() or resolved.suffix:
            return str(resolved)
        # `/help/day-counting` -> `help/day-counting.html`
        with_html = resolved.with_suffix(".html")
        if with_html.is_file():
            return str(with_html)
        return str(resolved)

    def log_message(self, fmt: str, *args) -> None:
        # Only surface failures; a full request log buries them.
        status = str(args[1]) if len(args) > 1 else ""
        if status.startswith(("4", "5")):
            super().log_message(fmt, *args)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8899)
    args = parser.parse_args()

    handler = partial(PagesHandler, directory=str(SITE_ROOT))
    server = HTTPServer(("127.0.0.1", args.port), handler)
    print(f"Serving {SITE_ROOT}")
    print(f"  http://localhost:{args.port}/")
    print(f"  http://localhost:{args.port}/help/")
    print("Ctrl+C to stop. Only 4xx/5xx requests are logged.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
