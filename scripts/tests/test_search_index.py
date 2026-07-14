import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def normalize(value: str) -> str:
    return re.sub(r"\bdays\b", "day", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()


def score(entry: dict[str, object], raw_query: str) -> int:
    query = normalize(raw_query)
    title = normalize(str(entry["title"]))
    jurisdiction = normalize(str(entry["jurisdiction"]))
    keywords = normalize(" ".join(entry["keywords"]))
    description = normalize(str(entry["description"]))
    value = 0
    if title == query:
        value += 160
    elif title.startswith(query):
        value += 120
    elif query in title:
        value += 90
    if jurisdiction == query:
        value += 80
    elif query in jurisdiction:
        value += 45
    if query in keywords:
        value += 35
    if query in description:
        value += 20
    value += sum(8 for term in query.split() if len(term) > 1 and term in title)
    if entry["pillar"] and value > 0:
        value += 150 if " " not in query else 5
    return value


class SearchIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.entries = json.loads((ROOT / "assets/search-index.json").read_text())["entries"]

    def first(self, query: str, section: str) -> str:
        matches = [entry for entry in self.entries if entry["section"] == section and score(entry, query) > 0]
        matches.sort(key=lambda entry: (-score(entry, query), str(entry["title"])))
        self.assertTrue(matches, query)
        return str(matches[0]["url"])

    def test_expected_common_queries(self) -> None:
        expected = {
            ("CSV", "help"): "/help/csv-import",
            ("Flighty", "help"): "/help/flighty-import",
            ("iCloud", "help"): "/help/icloud-sync-and-restore",
            ("Schengen", "learn"): "/learn/schengen-90-180-rule",
            ("183 days", "learn"): "/learn/183-day-tax-residency-rule",
            ("New York", "learn"): "/learn/new-york-tax-residency",
        }
        for (query, section), url in expected.items():
            with self.subTest(query=query):
                self.assertEqual(self.first(query, section), url)

    def test_index_contains_every_generated_article(self) -> None:
        articles = json.loads((ROOT / "_site-src/data/articles.json").read_text())["articles"]
        self.assertEqual(len(self.entries), len(articles))


if __name__ == "__main__":
    unittest.main()
