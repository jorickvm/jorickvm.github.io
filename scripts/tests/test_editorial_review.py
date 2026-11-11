import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_content_governance import review_due, verification_date, build
from report_editorial_review import pending_reviews, render_body


class EditorialReviewTests(unittest.TestCase):
    def test_exact_date_overrides_legacy_label(self):
        self.assertEqual(verification_date(
            {"path": "learn/example.html", "last_fact_verified": "2026-11-11"},
            "Last verified: August 2026"), ("2026-11-11", "day"))
        self.assertEqual(review_due("2026-11-11", 182), "2027-05-12")

    def test_legacy_month_keeps_its_precision(self):
        self.assertEqual(verification_date({"path": "x"}, "Last verified: August 2026"), ("2026-08", "month"))
        self.assertEqual(review_due("2026-08", 365), "2027-08-31")

    def test_invalid_exact_date_fails(self):
        with self.assertRaises(SystemExit):
            verification_date({"path": "x", "last_fact_verified": "2026-02-30"}, "")

    def test_warning_boundary_missing_and_order(self):
        def entry(path, due, verified="2026-08"):
            return dict(path=path, next_review_due=due, last_fact_verified=verified,
                        review_tier=1, review_trigger_reason=None)
        rows = [entry("later", "2026-12-12"), entry("boundary", "2026-12-11"),
                entry("overdue", "2026-11-10"), entry("missing", None, None)]
        selected = pending_reviews(rows, date(2026, 11, 11), 30)
        self.assertEqual([r["path"] for r in selected], ["missing", "overdue", "boundary"])
        self.assertEqual(pending_reviews([rows[0]], date(2026, 11, 11), 30), [])

    def test_known_change_survives_new_verification(self):
        editorial, _, _ = build()
        for row in editorial["articles"]:
            if row["review_trigger"] == "known-change":
                self.assertLess(row["next_review_due"], row["cadence_review_due"])

    def test_report_explains_fact_verification(self):
        self.assertIn("successful link check is not fact verification", render_body([], date(2026, 11, 11), 30))


if __name__ == "__main__":
    unittest.main()
