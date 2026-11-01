from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import report_source_health  # noqa: E402


REPORT = {
    "generated_at": "2026-08-09T07:23:00+00:00",
    "summary": {"ok": 86, "missing": 1, "redirected": 1, "bot-blocked-or-rate-limited": 2},
    "actionable_statuses": ["redirected", "missing"],
    "results": [
        {"url": "https://example.gov/gone", "articles": ["learn/a.html"], "status": "missing", "http_status": 404},
        {
            "url": "https://example.gov/moved",
            "articles": ["learn/b.html"],
            "status": "redirected",
            "http_status": 200,
            "final_url": "https://example.gov/new",
        },
        {"url": "https://example.gov/fine", "articles": ["learn/c.html"], "status": "ok", "http_status": 200},
        {
            "url": "https://example.gov/blocked",
            "articles": ["learn/d.html"],
            "status": "bot-blocked-or-rate-limited",
            "http_status": 403,
        },
        {"url": "https://example.gov/slow", "articles": ["learn/e.html"], "status": "network-error"},
    ],
}


class ReportSourceHealthTests(unittest.TestCase):
    def test_only_redirected_and_missing_are_actionable(self) -> None:
        grouped = report_source_health.actionable_results(REPORT)
        self.assertEqual(set(grouped), {"missing", "redirected"})
        self.assertEqual(sum(len(v) for v in grouped.values()), 2)

    def test_blocked_and_transient_never_raise_an_issue(self) -> None:
        body = report_source_health.render_body(REPORT, report_source_health.actionable_results(REPORT))
        self.assertNotIn("example.gov/blocked", body)
        self.assertNotIn("example.gov/slow", body)
        self.assertNotIn("example.gov/fine", body)

    def test_body_names_each_finding_and_its_citing_article(self) -> None:
        body = report_source_health.render_body(REPORT, report_source_health.actionable_results(REPORT))
        self.assertIn("https://example.gov/gone", body)
        self.assertIn("HTTP 404", body)
        self.assertIn("now serves: https://example.gov/new", body)
        self.assertIn("https://atlasdays.app/learn/b", body)

    def test_a_clean_report_yields_no_findings(self) -> None:
        clean = {**REPORT, "results": [r for r in REPORT["results"] if r["status"] == "ok"]}
        self.assertEqual(report_source_health.actionable_results(clean), {})

    def test_actionable_statuses_follow_the_report_not_a_hardcoded_list(self) -> None:
        narrowed = {**REPORT, "actionable_statuses": ["missing"]}
        self.assertEqual(set(report_source_health.actionable_results(narrowed)), {"missing"})


if __name__ == "__main__":
    unittest.main()
