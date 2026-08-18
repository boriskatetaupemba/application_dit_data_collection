from __future__ import annotations

import unittest

from dashboard.analytics import book_metrics, car_metrics, filter_books, filter_cars


class DashboardAnalyticsTests(unittest.TestCase):
    def test_book_metrics_ignore_missing_numeric_values(self) -> None:
        metrics = book_metrics(
            [
                {"price": 10, "review_count": 2},
                {"price": 20, "review_count": None},
                {"price": None, "review_count": 4},
            ]
        )

        self.assertEqual(metrics["total_books"], 3)
        self.assertEqual(metrics["average_price"], 15)
        self.assertEqual(metrics["minimum_price"], 10)
        self.assertEqual(metrics["maximum_price"], 20)
        self.assertEqual(metrics["average_reviews"], 3)

    def test_car_metrics_include_price_and_mileage(self) -> None:
        metrics = car_metrics(
            [
                {"price": 4_000_000, "mileage": 100_000},
                {"price": 6_000_000, "mileage": 50_000},
            ]
        )

        self.assertEqual(metrics["total_ads"], 2)
        self.assertEqual(metrics["average_price"], 5_000_000)
        self.assertEqual(metrics["average_mileage"], 75_000)

    def test_book_filters_can_be_combined(self) -> None:
        rows = [
            {"title": "A", "category": "Travel", "product_type": "Books", "availability": "In stock", "rating": 5},
            {"title": "B", "category": "Fiction", "product_type": "Books", "availability": "In stock", "rating": 4},
            {"title": "C", "category": "Travel", "product_type": "Books", "availability": "Out of stock", "rating": 5},
        ]

        selected = filter_books(
            rows,
            categories=["Travel"],
            availabilities=["In stock"],
            ratings=[5],
        )
        self.assertEqual([row["title"] for row in selected], ["A"])

    def test_car_filters_can_be_combined(self) -> None:
        rows = [
            {"brand": "Toyota", "year": 2020, "region": "Dakar", "transmission": "Auto"},
            {"brand": "Toyota", "year": 2019, "region": "Dakar", "transmission": "Manuelle"},
            {"brand": "Renault", "year": 2020, "region": "Thiès", "transmission": "Auto"},
        ]

        selected = filter_cars(
            rows,
            brands=["Toyota"],
            years=[2020],
            regions=["Dakar"],
            transmissions=["Auto"],
        )
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["year"], 2020)

    def test_empty_filter_selection_keeps_all_rows(self) -> None:
        rows = [{"brand": "Toyota"}, {"brand": "Renault"}]
        self.assertEqual(filter_cars(rows, brands=[]), rows)


if __name__ == "__main__":
    unittest.main()
