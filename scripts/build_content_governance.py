#!/usr/bin/env python3
"""Build structured editorial and content-cluster manifests from Learn sources."""

from __future__ import annotations

import argparse
import calendar
import json
import re
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "_site-src"
ARTICLES = SOURCE / "data" / "articles.json"
EDITORIAL = SOURCE / "data" / "editorial.json"
CLUSTERS = SOURCE / "data" / "content-clusters.json"
QUEUE = ROOT / "EDITORIAL_REVIEW_QUEUE.md"
APP_STORE = "apps.apple.com"
MONTHS = {month: number for number, month in enumerate(calendar.month_name) if month}


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail when generated governance files are stale")
    return parser.parse_args()


def description(record: dict[str, object]) -> str:
    return next(
        (str(meta["content"]) for meta in record.get("meta", []) if meta.get("name") == "description"),
        str(record["title"]),
    )


def classify(slug: str) -> tuple[str, str, int]:
    tax_markers = ("tax-residency", "183-day", "180-day-tax", "substantial-presence", "statutory-residence")
    entry_markers = ("schengen", "visa", "visitor", "eta", "ilr", "citizenship", "overstay", "japan-90", "turkiye-90")
    if any(marker in slug for marker in tax_markers):
        return "tax-residency", "high", 365
    if any(marker in slug for marker in ("travel-history", "prove-", "rebuild-", "export-")):
        return "travel-record-evidence", "medium", 365
    if any(marker in slug for marker in entry_markers):
        return "immigration-and-entry", "high", 120
    if any(marker in slug for marker in ("atlasdays", "flighty", "icloud")):
        return "product-workflow", "medium", 180
    return "travel-day-method", "medium", 365


def cluster_for(slug: str, category: str) -> tuple[str, str]:
    if "schengen" in slug:
        return "schengen-mechanics", "learn/schengen-90-180-rule.html"
    if slug.startswith("uk-"):
        return "uk-entry-residence-and-absence", "learn/uk-standard-visitor-visa-180-day-rule.html"
    if slug.startswith("us-") and "tax-residency" not in slug and "state" not in slug:
        return "us-entry-and-presence", "learn/us-b1-b2-visa-180-day-limit.html"
    if category == "tax-residency":
        return "tax-residency", "learn/tax-residency-by-country.html"
    if category == "travel-record-evidence":
        return "travel-history-and-proof", "learn/travel-history-for-visa-applications.html"
    if category == "product-workflow":
        return "product-and-import-workflows", "learn/how-to-use-atlasdays.html"
    if any(marker in slug for marker in ("country", "layover", "track-travel", "what-counts")):
        return "day-counting-and-country-models", "learn/how-to-track-travel-days.html"
    return "country-stay-limits", "learn/day-limits.html"


def jurisdiction(slug: str, cluster: str) -> str:
    if cluster == "schengen-mechanics":
        return "Schengen Area"
    if slug.startswith("uk-"):
        return "United Kingdom"
    if slug.startswith("us-"):
        return "United States"
    names = {
        "uae": "United Arab Emirates", "turkiye": "Türkiye", "new-zealand": "New Zealand",
        "new-york": "New York", "new-jersey": "New Jersey", "north-dakota": "North Dakota",
        "rhode-island": "Rhode Island", "georgia-us": "Georgia (US state)",
    }
    for prefix, name in sorted(names.items(), key=lambda item: len(item[0]), reverse=True):
        if slug.startswith(prefix + "-"):
            return name
    match = re.match(r"([a-z]+(?:-[a-z]+)?)-(?:183|180|90|tax)", slug)
    return match.group(1).replace("-", " ").title() if match else "Multiple jurisdictions"


def verified_month(content: str) -> str | None:
    match = re.search(r"Last verified:\s*([A-Z][a-z]+)\s+(20\d{2})", content)
    if not match:
        return None
    return f"{match.group(2)}-{MONTHS[match.group(1)]:02d}"


def review_due(month: str | None, interval: int) -> str | None:
    if not month:
        return None
    year, number = map(int, month.split("-"))
    reviewed = date(year, number, calendar.monthrange(year, number)[1])
    return (reviewed + timedelta(days=interval)).isoformat()


def external_sources(content: str) -> list[str]:
    urls = re.findall(r'href="(https?://[^"#]+)', content)
    return sorted({url for url in urls if APP_STORE not in url and "atlasdays.app" not in url})


def build() -> tuple[dict[str, object], dict[str, object], str]:
    source = json.loads(ARTICLES.read_text(encoding="utf-8"))
    editorial_entries = []
    cluster_entries = []
    for record in source["articles"]:
        if record.get("section") != "learn":
            continue
        path = str(record["path"])
        slug = Path(path).stem
        content = (SOURCE / str(record["content"])).read_text(encoding="utf-8")
        category, risk, interval = classify(slug)
        cluster, pillar = cluster_for(slug, category)
        month = verified_month(content)
        sources = external_sources(content)
        editorial_entries.append(
            {
                "path": path,
                "jurisdiction": jurisdiction(slug, cluster),
                "rule_category": category,
                "risk_level": risk,
                "review_interval_days": interval,
                "last_fact_verified": month,
                "verification_precision": "month" if month else None,
                "next_review_due": review_due(month, interval),
                "source_urls": sources,
                "review_status": "exact-date-required" if month else "verification-missing",
                "review_notes": "Migrated from the visible month-level verification label; record an exact date at the next substantive source review.",
            }
        )
        cluster_entries.append(
            {
                "path": path,
                "cluster": cluster,
                "pillar": pillar,
                "primary_intent": description(record),
                "relationship": "pillar" if path == pillar else "supporting",
            }
        )

    editorial = {
        "schema_version": 1,
        "policy": {
            "fact_verification_is_separate_from_date_modified": True,
            "migration_note": "Legacy pages recorded only a verification month. Exact dates must be set only after a substantive official-source review.",
        },
        "articles": sorted(editorial_entries, key=lambda entry: entry["path"]),
    }
    clusters = {
        "schema_version": 1,
        "clusters": sorted(cluster_entries, key=lambda entry: entry["path"]),
    }
    ordered = sorted(editorial_entries, key=lambda entry: (entry["next_review_due"] or "0000", entry["path"]))
    queue_lines = [
        "# Editorial Review Queue", "", "Generated by `scripts/build_content_governance.py`.", "",
        "Legacy articles expose only a verification month. The next substantive review must record an exact date; cosmetic edits must not change it.", "",
        "| Due | Risk | Article | Status | Sources |", "|---|---|---|---|---:|",
    ]
    for entry in ordered:
        route = "/" + str(entry["path"]).removesuffix(".html")
        queue_lines.append(
            f"| {entry['next_review_due'] or 'Now'} | {entry['risk_level']} | [{entry['path']}]({route}) | {entry['review_status']} | {len(entry['source_urls'])} |"
        )
    return editorial, clusters, "\n".join(queue_lines) + "\n"


def main() -> int:
    options = args()
    editorial, clusters, queue = build()
    expected = {
        EDITORIAL: json.dumps(editorial, indent=2, ensure_ascii=False) + "\n",
        CLUSTERS: json.dumps(clusters, indent=2, ensure_ascii=False) + "\n",
        QUEUE: queue,
    }
    stale = [path for path, value in expected.items() if not path.exists() or path.read_text(encoding="utf-8") != value]
    if options.check:
        if stale:
            print("Stale governance output:")
            for path in stale:
                print(f"  {path.relative_to(ROOT)}")
            return 1
        print(f"Checked {len(editorial['articles'])} editorial records and {len(clusters['clusters'])} cluster assignments.")
        return 0
    for path, value in expected.items():
        path.write_text(value, encoding="utf-8")
    print(f"Built {len(editorial['articles'])} editorial records and {len(clusters['clusters'])} cluster assignments.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
