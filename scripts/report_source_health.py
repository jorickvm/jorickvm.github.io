#!/usr/bin/env python3
"""Turn an external-source report into a GitHub issue body.

check_external_sources.py writes a JSON report that used to end up in a CI
artifact nobody opened, which is a smoke detector with no battery for a site
whose credibility rests on official sources still saying what we claim.

This renders the actionable part of that report as markdown so the weekly
workflow can open one issue (and close it again when every source is clean).
Only `redirected` and `missing` are actionable: a government site that answers
401/403/429 is almost always refusing the CI runner rather than reporting a
dead page, and 5xx or network errors are transient. Those stay in the report
for reference and never raise an issue, because a monitor that cries wolf is
one you learn to ignore.

Exit status is 0 whether or not findings exist; the caller reads the
`actionable` count from stdout or $GITHUB_OUTPUT and decides what to do.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "external-source-report.json"

HEADINGS = {
    "missing": (
        "Dead sources (404 or 410)",
        "The page the article cites is gone. Find the current official page, verify it still states the rule, "
        "and update the link. If the rule itself changed, the article needs a fact review, not just a new URL.",
    ),
    "redirected": (
        "Moved sources (redirect)",
        "The source still resolves but the publisher moved it. Confirm the destination states the same rule, "
        "then update the link to the final URL so the citation stays precise.",
    ),
}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--body", type=Path, help="Write the issue body here when there are findings")
    return parser.parse_args()


def actionable_results(report: dict[str, object]) -> dict[str, list[dict[str, object]]]:
    statuses = [str(value) for value in report.get("actionable_statuses", [])]
    grouped: dict[str, list[dict[str, object]]] = {}
    for result in report.get("results", []):
        status = str(result.get("status", ""))
        if status in statuses:
            grouped.setdefault(status, []).append(result)
    return grouped


def render_body(report: dict[str, object], grouped: dict[str, list[dict[str, object]]]) -> str:
    lines = [
        "The weekly source monitor found official sources that no longer resolve the way the articles cite them.",
        "",
        f"Checked {len(report.get('results', []))} unique sources at {report.get('generated_at', 'unknown time')}.",
        "",
    ]
    for status in ("missing", "redirected"):
        results = grouped.get(status)
        if not results:
            continue
        heading, guidance = HEADINGS[status]
        lines += [f"## {heading}", "", guidance, ""]
        for result in sorted(results, key=lambda item: str(item.get("url", ""))):
            lines.append(f"- {result.get('url')}")
            final = result.get("final_url")
            if status == "redirected" and final:
                lines.append(f"  - now serves: {final}")
            code = result.get("http_status")
            if status == "missing" and code:
                lines.append(f"  - HTTP {code}")
            for path in result.get("articles", []):
                route = "/" + str(path).removesuffix(".html")
                lines.append(f"  - cited by [{path}](https://atlasdays.app{route})")
        lines.append("")

    summary = report.get("summary", {})
    if isinstance(summary, dict) and summary:
        counts = ", ".join(f"{key}: {value}" for key, value in sorted(summary.items()))
        lines += [
            "## Full run",
            "",
            f"`{counts}`",
            "",
            "Blocked (401/403/429), server errors, and network failures are not listed above. Government sites "
            "routinely refuse CI runners, so those are recorded but never raise an issue.",
            "",
        ]
    lines += [
        "---",
        "",
        "Follow `EDITORIAL_CHECKLIST.md` in the private repo when fixing these: read the new source before "
        "recording a verification date, and never advance `last_fact_verified` for a link swap alone.",
        "",
        "This issue is maintained by the Site audit workflow. It closes itself when every source resolves cleanly.",
    ]
    return "\n".join(lines)


def main() -> int:
    options = arguments()
    try:
        report = json.loads(options.report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"Could not read {options.report}: {error}")
        print("actionable=0")
        return 0

    grouped = actionable_results(report)
    count = sum(len(items) for items in grouped.values())
    if count and options.body:
        options.body.write_text(render_body(report, grouped) + "\n", encoding="utf-8")

    print(f"actionable={count}")
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as handle:
            handle.write(f"actionable={count}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
