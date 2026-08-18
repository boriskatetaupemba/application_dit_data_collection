"""Tests unitaires des transformations, sans accès réseau."""

from __future__ import annotations

import pandas as pd
import pytest

from cleaners.books_cleaner import clean_books_data
from cleaners.gaaraas_cleaner import clean_gaaraas_data


def test_clean_books_types_normalization_and_deduplication() -> None:
    raw = [
        {
            "title": "  A   Book  ",
            "price": "£1,234.56",
            "availability": " In stock (22 available) ",
            "products_on_page": "20",
            "rating": "star-rating Three",
            "review_count": "0 reviews",
            "description": " Une   description\ncomplète ",
            "product_type": " Books ",
            "tax": "£0.00",
            "category": " Poetry ",
            "url": "https://books.test/a",
            "source_page": "1",
        },
        {
            "title": "Doublon",
            "price": "£99.00",
            "url": "https://books.test/a",
        },
        {
            "title": "Unavailable",
            "price": "-4.20",
            "availability": "Rupture de stock",
            "rating": "Six",
            "url": "https://books.test/b",
        },
    ]

    cleaned = clean_books_data(raw)

    assert len(cleaned) == 2
    assert cleaned.loc[0, "title"] == "A Book"
    assert cleaned.loc[0, "description"] == "Une description complète"
    assert cleaned.loc[0, "price"] == pytest.approx(1234.56)
    assert cleaned.loc[0, "tax"] == pytest.approx(0.0)
    assert cleaned.loc[0, "availability"] == "in_stock"
    assert cleaned.loc[0, "rating"] == 3
    assert cleaned.loc[1, "availability"] == "out_of_stock"
    assert pd.isna(cleaned.loc[1, "price"])
    assert pd.isna(cleaned.loc[1, "rating"])
    assert str(cleaned["price"].dtype) == "Float64"
    assert str(cleaned["rating"].dtype) == "Int64"
    assert str(cleaned["products_on_page"].dtype) == "Int64"
    assert str(cleaned["title"].dtype) == "string"


def test_clean_books_accepts_empty_input_with_stable_schema() -> None:
    cleaned = clean_books_data([])

    assert cleaned.empty
    assert list(cleaned.columns) == [
        "title",
        "price",
        "availability",
        "products_on_page",
        "rating",
        "review_count",
        "description",
        "product_type",
        "tax",
        "category",
        "url",
        "source_page",
    ]
    assert str(cleaned["price"].dtype) == "Float64"
    assert str(cleaned["rating"].dtype) == "Int64"


def test_clean_gaaraas_types_coherence_and_categories() -> None:
    raw = [
        {
            "brand": " bmw ",
            "model": " X5 ",
            "year": "2019",
            "price": "CFA 3 800 000",
            "mileage": "107.000 km",
            "transmission": "automatic",
            "region": " dakar ",
            "url": "https://gaaraas.test/1",
            "source_page": "2",
        },
        {
            "brand": "BMW",
            "model": "X5 duplicate",
            "url": "https://gaaraas.test/1",
        },
        {
            "brand": " toyota ",
            "model": "Yaris",
            "year": "1500",
            "price": "2 700 000 CFA",
            "mileage": "-5 km",
            "transmission": "Boîte manuelle",
            "region": "thiès",
            "url": "https://gaaraas.test/2",
            "source_page": 3,
        },
    ]

    cleaned = clean_gaaraas_data(raw)

    assert len(cleaned) == 2
    assert cleaned.loc[0, "brand"] == "BMW"
    assert cleaned.loc[0, "price"] == 3_800_000
    assert cleaned.loc[0, "mileage"] == 107_000
    assert cleaned.loc[0, "transmission"] == "Automatique"
    assert cleaned.loc[0, "region"] == "Dakar"
    assert pd.isna(cleaned.loc[1, "year"])
    assert pd.isna(cleaned.loc[1, "mileage"])
    assert cleaned.loc[1, "transmission"] == "Manuelle"
    assert str(cleaned["year"].dtype) == "Int64"
    assert str(cleaned["price"].dtype) == "Int64"
    assert str(cleaned["brand"].dtype) == "string"
