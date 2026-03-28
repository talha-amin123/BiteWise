import unittest
from datetime import date, timedelta
from unittest.mock import patch

from matching.matcher import (
    brand_match,
    distinctive_tokens,
    get_recall_age_days,
    hybrid_brand_score,
    hybrid_product_score,
    match_product,
    normalize,
    product_match,
    size_compatible,
)


class MatcherUnitTests(unittest.TestCase):
    def test_recall_age_days_uses_date_string(self):
        recent_date = (date.today() - timedelta(days=10)).isoformat()
        self.assertEqual(get_recall_age_days(recent_date), 10)

    def test_normalize_lowercases_and_collapses_spaces(self):
        self.assertEqual(normalize("  Rosina   Meatballs "), "rosina meatballs")

    def test_distinctive_tokens_filters_generic_food_words(self):
        tokens = distinctive_tokens("organic pork sausage jalapeno cheddar")
        self.assertEqual(tokens, {"jalapeno", "cheddar"})

    def test_brand_score_prefers_close_matches(self):
        close_score = hybrid_brand_score("rosina", "rosina")
        far_score = hybrid_brand_score("rosina", "kirkland signature")
        self.assertGreater(close_score, far_score)

    def test_product_score_prefers_close_matches(self):
        close_score = hybrid_product_score("italian style meatballs", "italian style meatballs")
        far_score = hybrid_product_score("italian style meatballs", "organic baby food pouch")
        self.assertGreater(close_score, far_score)

    def test_brand_match_uses_brand_or_company(self):
        score = brand_match("rosina", "", "rosina food products inc")
        self.assertGreaterEqual(score, 75)

    def test_product_match_strips_brand_before_comparing(self):
        score = product_match(
            "rosina meatballs italian style",
            "rosina",
            "meatballs italian style",
            "",
            "",
        )
        self.assertGreaterEqual(score, 60)

    def test_size_compatible_requires_overlap_when_sizes_exist(self):
        self.assertTrue(size_compatible("26 oz", "Italian Style Meatballs 26 oz"))
        self.assertFalse(size_compatible("26 oz", "Italian Style Meatballs 14 oz"))

    @patch("matching.matcher.load_recalls")
    def test_match_product_returns_high_match(self, mock_load_recalls):
        recent_date = (date.today() - timedelta(days=30)).isoformat()
        mock_load_recalls.return_value = [
            {
                "recall_id": 101,
                "recall_source": "FDA",
                "recall_announcement_title": "Rosina Meatballs Recalled",
                "recall_reason": "Undeclared allergen",
                "recall_brand_name": "Rosina",
                "recall_company_name": "Rosina Food Products, Inc.",
                "recall_url": "https://example.com/recall",
                "recall_announcement_date": recent_date,
                "recall_publish_date": recent_date,
                "recall_risk_level": None,
                "product_id": 555,
                "product_description": "Meatballs, Italian Style",
                "raw_detail": "Italian Style Meatballs 26 oz",
            }
        ]

        results = match_product("Rosina", "Rosina Meatballs, Italian Style", "26 oz")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["recall_id"], 101)
        self.assertEqual(results[0]["match_level"], "high")
        self.assertGreaterEqual(results[0]["brand_score"], 75)
        self.assertGreaterEqual(results[0]["product_score"], 60)
        self.assertEqual(results[0]["recall_age_days"], 30)
        self.assertIn("italian", results[0]["shared_product_tokens"])

    @patch("matching.matcher.load_recalls")
    def test_match_product_skips_recalls_older_than_180_days(self, mock_load_recalls):
        old_date = (date.today() - timedelta(days=181)).isoformat()
        mock_load_recalls.return_value = [
            {
                "recall_id": 202,
                "recall_source": "FDA",
                "recall_announcement_title": "Old Rosina Recall",
                "recall_reason": "Undeclared allergen",
                "recall_brand_name": "Rosina",
                "recall_company_name": "Rosina Food Products, Inc.",
                "recall_url": "https://example.com/old-recall",
                "recall_announcement_date": old_date,
                "recall_publish_date": old_date,
                "recall_risk_level": None,
                "product_id": 556,
                "product_description": "Meatballs, Italian Style",
                "raw_detail": "Italian Style Meatballs 26 oz",
            }
        ]

        results = match_product("Rosina", "Rosina Meatballs, Italian Style", "26 oz")
        self.assertEqual(results, [])

    @patch("matching.matcher.load_recalls")
    def test_match_product_skips_generic_category_overlap(self, mock_load_recalls):
        recent_date = (date.today() - timedelta(days=15)).isoformat()
        mock_load_recalls.return_value = [
            {
                "recall_id": 303,
                "recall_source": "FSIS",
                "recall_announcement_title": "Bratwurst sausage recalled",
                "recall_reason": "Contamination risk",
                "recall_brand_name": "Sample Farm",
                "recall_company_name": "Sample Farm Foods, Inc.",
                "recall_url": "https://example.com/bratwurst",
                "recall_announcement_date": recent_date,
                "recall_publish_date": recent_date,
                "recall_risk_level": "High",
                "product_id": 700,
                "product_description": "Bratwurst sausage",
                "raw_detail": "Pork bratwurst sausage 14 oz",
            }
        ]

        results = match_product("Sample Farm", "Sample Farm Andouille Sausage", "14 oz")
        self.assertEqual(results, [])

    @patch("matching.matcher.load_recalls")
    def test_match_product_skips_size_mismatch(self, mock_load_recalls):
        recent_date = (date.today() - timedelta(days=15)).isoformat()
        mock_load_recalls.return_value = [
            {
                "recall_id": 404,
                "recall_source": "FDA",
                "recall_announcement_title": "Rosina Meatballs Recalled",
                "recall_reason": "Undeclared allergen",
                "recall_brand_name": "Rosina",
                "recall_company_name": "Rosina Food Products, Inc.",
                "recall_url": "https://example.com/recall",
                "recall_announcement_date": recent_date,
                "recall_publish_date": recent_date,
                "recall_risk_level": None,
                "product_id": 701,
                "product_description": "Meatballs, Italian Style 14 oz",
                "raw_detail": "Italian Style Meatballs 14 oz",
            }
        ]

        results = match_product("Rosina", "Rosina Meatballs, Italian Style", "26 oz")
        self.assertEqual(results, [])

    @patch("matching.matcher.load_recalls")
    def test_match_product_downgrades_company_only_brand_match(self, mock_load_recalls):
        recent_date = (date.today() - timedelta(days=15)).isoformat()
        mock_load_recalls.return_value = [
            {
                "recall_id": 505,
                "recall_source": "FDA",
                "recall_announcement_title": "Italian Style Meatballs Recalled",
                "recall_reason": "Undeclared allergen",
                "recall_brand_name": "",
                "recall_company_name": "Rosina Food Products, Inc.",
                "recall_url": "https://example.com/recall",
                "recall_announcement_date": recent_date,
                "recall_publish_date": recent_date,
                "recall_risk_level": None,
                "product_id": 702,
                "product_description": "Meatballs, Italian Style 26 oz",
                "raw_detail": "Italian Style Meatballs 26 oz",
            }
        ]

        results = match_product("Rosina", "Rosina Meatballs, Italian Style", "26 oz")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["match_level"], "warning")


if __name__ == "__main__":
    unittest.main()
