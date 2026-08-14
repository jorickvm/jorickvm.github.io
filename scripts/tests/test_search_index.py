import json
import re
import unittest
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


# Mirrors normalize() in assets/js/search.js, including the CJK ranges. The
# old [^a-z0-9] class erased every Japanese character, so a Japanese query
# normalised to "" and matched everything.
CJK = "\u3040-\u309f\u30a0-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uff66-\uff9f"


def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.lower())
    latin_folded = re.sub(r"([a-z])[\u0300-\u036f]+", r"\1", decomposed)
    recomposed = unicodedata.normalize("NFC", latin_folded)
    return re.sub(r"\bdays\b", "day", re.sub(rf"[^a-z0-9{CJK}]+", " ", recomposed)).strip()


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
    # Mirrors search.js: an exact keyword beats one that merely contains the
    # query. Japanese has no word boundaries, so "リセット" is a substring of
    # "プリセット" and would otherwise win on a shorter title.
    if any(normalize(word) == query for word in entry["keywords"]):
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

    def test_dutch_georgia_names_stay_distinct(self) -> None:
        dutch = [entry for entry in self.entries if entry.get("lang") == "nl"]
        country_matches = [entry for entry in dutch if score(entry, "Georgië") > 0]
        self.assertTrue(any("Georgië" in entry["title"] for entry in country_matches))
        self.assertFalse(any("Georgia" in entry["title"] for entry in country_matches))

        state_matches = [entry for entry in dutch if score(entry, "Georgia") > 0]
        self.assertTrue(any("Georgia" in entry["title"] for entry in state_matches))

    def first(self, query: str, section: str, lang: str = "en") -> str:
        matches = [
            entry for entry in self.entries
            if entry["section"] == section
            and entry.get("lang", "en") == lang
            and score(entry, query) >= 20
        ]
        matches.sort(key=lambda entry: (-score(entry, query), len(str(entry["title"])), str(entry["title"])))
        self.assertTrue(matches, query)
        return str(matches[0]["url"])

    def test_expected_common_queries(self) -> None:
        expected = {
            ("CSV", "help"): "/help/csv-import",
            ("Flighty", "help"): "/help/flighty-import",
            ("iCloud", "help"): "/help/icloud-sync-and-restore",
            ("arrival day", "help"): "/help/day-counting",
            ("edit trip", "help"): "/help/timeline-and-calendar",
            ("restore purchase", "help"): "/help/atlasdays-pro",
            ("missing data", "help"): "/help/icloud-sync-and-restore",
            ("backup", "help"): "/help/export-and-reports",
            ("widget blank", "help"): "/help/widgets",
            ("notification", "help"): "/help/smart-alerts",
            ("ground crossing", "help"): "/help/auto-detect-trips",
            ("Schengen", "learn"): "/learn/schengen-90-180-rule",
            ("183 days", "learn"): "/learn/183-day-tax-residency-rule",
            ("New York", "learn"): "/learn/new-york-tax-residency",
        }
        for (query, section), url in expected.items():
            with self.subTest(query=query):
                self.assertEqual(self.first(query, section), url)

    def test_expected_japanese_queries(self) -> None:
        """The queries a Japanese reader would actually type.

        Substring matching, not morphological search: enough for a few dozen
        articles carrying translated synonyms, and the reason each article has
        them.
        """
        expected = {
            "ウィジェット": "/ja/help/widgets",
            "シェンゲン": "/ja/help/schengen-90-180",
            "写真": "/ja/help/photo-import",
            "書き出し": "/ja/help/export-and-reports",
            "通知": "/ja/help/smart-alerts",
            "リセット": "/ja/help/delete-and-reset",
            "機種変更": "/ja/help/icloud-sync-and-restore",
            "自動検出": "/ja/help/auto-detect-trips",
            "CSV": "/ja/help/csv-import",
            "iCloud": "/ja/help/icloud-sync-and-restore",
        }
        for query, url in expected.items():
            with self.subTest(query=query):
                self.assertEqual(self.first(query, "help", "ja"), url)

    def test_index_covers_every_article_in_every_locale(self) -> None:
        articles = json.loads((ROOT / "_site-src/data/articles.json").read_text())["articles"]
        english = [entry for entry in self.entries if entry.get("lang", "en") == "en"]
        self.assertEqual(len(english), len(articles))
        registry = json.loads((ROOT / "_site-src/data/articles.ja.json").read_text())
        japanese = [entry for entry in self.entries if entry.get("lang") == "ja"]
        self.assertEqual(len(japanese), len(registry["articles"]))

    def test_japanese_query_does_not_match_everything(self) -> None:
        """The regression that made the CJK fix necessary.

        With the old normaliser every Japanese query scored 1 against every
        entry, so the hub returned its whole article list as "results".
        """
        scores = [score(entry, normalize("ウィジェット")) for entry in self.entries]
        self.assertLess(sum(1 for value in scores if value >= 20), len(self.entries) // 2)


if __name__ == "__main__":
    unittest.main()
