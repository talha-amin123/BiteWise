import unittest
from unittest.mock import patch

from api.app import app


class CheckProductApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    @patch("api.app.match_product")
    def test_check_returns_matches(self, mock_match_product):
        mock_match_product.return_value = [
            {"recall_id": 1, "match_level": "high", "score": 92.4}
        ]

        response = self.client.post(
            "/check",
            json={
                "brand": "Rosina",
                "product_name": "Rosina Meatballs, Italian Style",
                "size": "26 oz",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["match_count"], 1)
        self.assertEqual(payload["query"]["brand"], "Rosina")
        self.assertEqual(payload["matches"][0]["match_level"], "high")
        mock_match_product.assert_called_once_with(
            "Rosina",
            "Rosina Meatballs, Italian Style",
            "26 oz",
        )

    def test_check_rejects_empty_payload(self):
        response = self.client.post("/check", json={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["error"],
            "No JSON data provided",
        )


if __name__ == "__main__":
    unittest.main()
