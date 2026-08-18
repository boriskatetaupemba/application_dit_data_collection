from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from database.connection import get_connection
from database.repository import DataRepository, normalize_book, normalize_car


class DatabaseRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "test.db"
        self.repository = DataRepository(self.database_path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_schema_contains_one_table_per_source(self) -> None:
        with get_connection(self.database_path) as connection:
            names = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        self.assertTrue({"books", "cars"}.issubset(names))

    def test_book_upsert_uses_url_as_stable_deduplication_key(self) -> None:
        first = {
            "title": "  A Book  ",
            "price": "£10.50",
            "availability": "In stock",
            "review_count": 1,
            "product_type": "Fiction",
            "url": "https://example.test/book/1",
        }
        updated = {
            **first,
            "title": "A Book — corrected",
            "price": 12.5,
            "review_count": 3,
        }

        self.assertEqual(self.repository.upsert_books([first]), 1)
        self.assertEqual(self.repository.upsert_books([updated]), 1)

        rows = self.repository.list_books()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "A Book — corrected")
        self.assertEqual(rows[0]["price"], 12.5)
        self.assertEqual(rows[0]["review_count"], 3)

    def test_car_upsert_and_filters(self) -> None:
        cars = [
            {
                "marque": "Toyota",
                "modele": "Corolla",
                "annee": "2020",
                "prix": "8500000 FCFA",
                "kilometrage": "45000 km",
                "boite": "Automatique",
                "region_vente": "Dakar",
                "url": "https://example.test/car/1",
            },
            {
                "brand": "Renault",
                "model": "Clio",
                "year": 2018,
                "price": 4_000_000,
                "mileage": 80_000,
                "transmission": "Manuelle",
                "region": "Thiès",
                "url": "https://example.test/car/2",
            },
        ]

        self.assertEqual(self.repository.upsert_cars(cars), 2)
        selected = self.repository.list_cars(brand="Toyota", region="Dakar")

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["model"], "Corolla")
        self.assertEqual(selected[0]["mileage"], 45_000)

    def test_database_constraints_reject_invalid_rating(self) -> None:
        invalid = {
            "title": "Invalid rating",
            "rating": 6,
            "url": "https://example.test/book/invalid",
        }
        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.upsert_books([invalid])
        self.assertEqual(self.repository.count("books"), 0)

    def test_normalizers_accept_cleaner_columns_and_aliases(self) -> None:
        book = normalize_book(
            {
                "titre": " Exemple ",
                "products_on_page": "20",
                "reviews": "2",
                "category": "Travel",
            }
        )
        car = normalize_car({"marque": " Peugeot ", "kilometers": "12 345 km"})

        self.assertEqual(book["title"], "Exemple")
        self.assertEqual(book["products_on_page"], 20)
        self.assertEqual(book["review_count"], 2)
        self.assertEqual(book["category"], "Travel")
        self.assertEqual(car["brand"], "Peugeot")
        self.assertEqual(car["mileage"], 12_345)

    def test_empty_import_is_a_noop(self) -> None:
        self.assertEqual(self.repository.upsert_books([]), 0)
        self.assertEqual(self.repository.upsert_cars(None), 0)

    def test_optional_nan_values_are_stored_as_null(self) -> None:
        self.repository.upsert_books(
            [{"title": "Missing fields", "price": float("nan"), "description": None}]
        )
        row = self.repository.list_books()[0]
        self.assertIsNone(row["price"])
        self.assertIsNone(row["description"])

    def test_environment_can_configure_database_path(self) -> None:
        configured_path = Path(self.temporary_directory.name) / "configured.db"
        with patch.dict(
            "os.environ", {"DATA_COLLECTION_DB_PATH": str(configured_path)}, clear=False
        ):
            repository = DataRepository()
            repository.upsert_books([{"title": "Configured database"}])
        self.assertTrue(configured_path.exists())
        self.assertEqual(DataRepository(configured_path).count("books"), 1)

    def test_sqlite_database_url_is_supported(self) -> None:
        configured_path = Path(self.temporary_directory.name) / "database_url.db"
        with patch.dict(
            "os.environ",
            {
                "DATA_COLLECTION_DB_PATH": "",
                "DATABASE_URL": f"sqlite:///{configured_path.as_posix()}",
            },
            clear=False,
        ):
            repository = DataRepository()
            repository.upsert_cars([{"brand": "Toyota"}])
        self.assertTrue(configured_path.exists())
        self.assertEqual(DataRepository(configured_path).count("cars"), 1)


if __name__ == "__main__":
    unittest.main()
