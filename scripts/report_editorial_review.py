#!/usr/bin/env python3
"""Report missing, overdue, and upcoming Learn fact reviews."""

from __future__ import annotations

import argparse
import os
from datetime import date, timedelta
from pathlib import Path

from build_content_governance import build


def pending_reviews(entries: list[dict], today: date, lead_days: int) -> list[dict]:
    cutoff = (today + timedelta(days=lead_days)).isoformat()
    return sorted(
        (entry for entry in entries if not entry["last_fact_verified"]
         or not entry["next_review_due"] or entry["next_review_due"] <= cutoff),
        key=lambda entry: (entry["next_review_due"] or "0000", entry["last_fact_verified"] or "0000", entry["path"]),
    )


def render_body(entries: list[dict], today: date, lead_days: int) -> str:
    lines = [
        f"Learn articles needing an official-source review as of {today.isoformat()}, including the next {lead_days} days.",
        "", "| Due | Last verified | Article | Review trigger |", "|---|---|---|---|",
    ]
    for entry in entries:
        path = entry["path"]
        route = "https://atlasdays.app/" + path.removesuffix(".html")
        trigger = entry.get("review_trigger_reason") or f"Tier {entry['review_tier']} cadence"
        trigger = str(trigger).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {entry['next_review_due'] or 'Now'} | {entry['last_fact_verified'] or 'Missing'} | [{path}]({route}) | {trigger} |")
    lines += [
        "", "Work in due-date order, oldest verification first within a due date. Known changes can bring a review forward.",
        "Read each article and its official sources, check scope, exceptions and worked examples, and correct unsupported claims.",
        "Record an exact `last_fact_verified` date in `articles.json` only after completing that review. A successful link check is not fact verification.",
        "Update or remove a resolved `review_by` trigger; keep a future trigger when the change is still pending.",
        "", "This issue is maintained by the Site audit workflow and closes when no reviews are due within the warning window.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body", type=Path, required=True)
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    parser.add_argument("--lead-days", type=int, default=30)
    options = parser.parse_args()
    if options.lead_days < 0:
        parser.error("--lead-days must be nonnegative")
    editorial, _, _ = build()
    pending = pending_reviews(editorial["articles"], options.today, options.lead_days)
    options.body.write_text(render_body(pending, options.today, options.lead_days), encoding="utf-8")
    output = f"actionable={len(pending)}\n"
    print(output, end="")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as handle:
            handle.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
