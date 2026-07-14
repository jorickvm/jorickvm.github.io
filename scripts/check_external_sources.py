#!/usr/bin/env python3
"""Check structured official sources and classify actionable link changes."""

from __future__ import annotations

import argparse
import json
import socket
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EDITORIAL = ROOT / "_site-src" / "data" / "editorial.json"
DEFAULT_REPORT = ROOT / "external-source-report.json"


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-config", action="store_true", help="Validate source coverage without network requests")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--timeout", type=float, default=15)
    return parser.parse_args()


def sources() -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    payload = json.loads(EDITORIAL.read_text(encoding="utf-8"))
    articles = payload["articles"]
    unique: dict[str, set[str]] = {}
    for article in articles:
        for url in article["source_urls"]:
            unique.setdefault(url, set()).add(article["path"])
    return articles, [{"url": url, "articles": sorted(paths)} for url, paths in sorted(unique.items())]


def classify(code: int) -> str:
    if 200 <= code < 300:
        return "ok"
    if code in {401, 403, 429}:
        return "bot-blocked-or-rate-limited"
    if code in {404, 410}:
        return "missing"
    if 500 <= code < 600:
        return "temporary-server-error"
    return "http-error"


def request_source(item: dict[str, object], timeout: float) -> dict[str, object]:
    url = str(item["url"])
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "AtlasDaysSourceMonitor/1.0 (+https://atlasdays.app/about)", "Range": "bytes=0-32767"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            final = response.geturl()
            code = response.status
            status = "redirected" if final.rstrip("/") != url.rstrip("/") else classify(code)
            return {**item, "status": status, "http_status": code, "final_url": final}
    except urllib.error.HTTPError as error:
        return {**item, "status": classify(error.code), "http_status": error.code, "final_url": error.geturl()}
    except (urllib.error.URLError, TimeoutError, socket.timeout) as error:
        return {**item, "status": "network-error", "error": str(error.reason if hasattr(error, "reason") else error)}


def main() -> int:
    options = arguments()
    articles, unique = sources()
    missing = [article["path"] for article in articles if article["risk_level"] == "high" and not article["source_urls"]]
    if missing:
        print("High-risk articles missing an external source:")
        for path in missing:
            print(f"  {path}")
        return 1
    if options.check_config:
        print(f"Checked {len(articles)} editorial records and {len(unique)} unique external sources.")
        return 0
    results = [request_source(item, options.timeout) for item in unique]
    counts = Counter(result["status"] for result in results)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": dict(sorted(counts.items())),
        "actionable_statuses": ["redirected", "missing"],
        "results": results,
    }
    options.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Checked {len(results)} sources: " + ", ".join(f"{key}={value}" for key, value in sorted(counts.items())))
    print("Redirected and missing sources require editorial review; blocking and transient failures are classified separately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
