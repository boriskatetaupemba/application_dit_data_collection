"""Repository operations for importing and querying cleaned datasets."""

from __future__ import annotations

import hashlib
import math
import re
import sqlite3
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .connection import PathLike, get_connection
from .models import SCHEMA_SQL

BOOK_FIELDS = (
    "source_key",
    "title",
    "price",
    "availability",
    "products_on_page",
    "rating",
    "review_count",
    "description",
    "product_type",
    "category",
    "tax",
    "url",
    "source_page",
    "scraped_at",
)

CAR_FIELDS = (
    "source_key",
    "brand",
    "model",
    "year",
    "price",
    "mileage",
    "transmission",
    "region",
    "url",
    "source_page",
    "scraped_at",
)

BOOK_ALIASES = {
    "titre": "title",
    "name": "title",
    "prix": "price",
    "stock": "availability",
    "in_stock": "availability",
    "product_count": "products_on_page",
    "nombre_produits": "products_on_page",
    "note": "rating",
    "reviews": "review_count",
    "number_of_reviews": "review_count",
    "categorie": "category",
    "type": "product_type",
    "source_url": "url",
    "page": "source_page",
}

CAR_ALIASES = {
    "marque": "brand",
    "make": "brand",
    "modele": "model",
    "annee": "year",
    "prix": "price",
    "kilometrage": "mileage",
    "kilometers": "mileage",
    "gearbox": "transmission",
    "boite": "transmission",
    "region_vente": "region",
    "location": "region",
    "source_url": "url",
    "page": "source_page",
}


def _records(data: Any) -> list[dict[str, Any]]:
    """Convert a DataFrame, mapping, or iterable of mappings to dictionaries."""

    if data is None:
        return []
    if hasattr(data, "to_dict") and not isinstance(data, Mapping):
        try:
            converted = data.to_dict(orient="records")
            if isinstance(converted, list):
                return [dict(item) for item in converted]
        except TypeError:
            pass
    if isinstance(data, Mapping):
        return [dict(data)]
    if isinstance(data, Iterable) and not isinstance(data, (str, bytes)):
        output = []
        for item in data:
            if not isinstance(item, Mapping):
                raise TypeError("Chaque ligne doit être un dictionnaire ou un mapping.")
            output.append(dict(item))
        return output
    raise TypeError("Les données doivent être un DataFrame ou une collection de mappings.")


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    try:
        result = value != value
        return bool(result)
    except TypeError:
        # ``pandas.NA`` deliberately refuses boolean coercion.
        return value.__class__.__name__ in {"NAType", "NaTType"}
    except ValueError:
        return False


def _text(value: Any) -> str | None:
    if _is_missing(value):
        return None
    clean = re.sub(r"\s+", " ", str(value)).strip()
    return clean or None


def _number(value: Any, *, integer: bool = False) -> int | float | None:
    if _is_missing(value) or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        clean = str(value).strip().replace("\u00a0", " ")
        clean = re.sub(r"[^0-9,\.\-]", "", clean)
        if not clean:
            return None
        if "," in clean and "." in clean:
            if clean.rfind(",") > clean.rfind("."):
                clean = clean.replace(".", "").replace(",", ".")
            else:
                clean = clean.replace(",", "")
        elif "," in clean:
            clean = clean.replace(",", ".")
        try:
            number = float(clean)
        except ValueError:
            return None
    if not math.isfinite(number):
        return None
    return int(number) if integer else number


def _timestamp(value: Any) -> str | None:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return _text(value)


def _canonical_key(parts: Sequence[Any]) -> str:
    normalized = []
    for part in parts:
        value = _text(part) or ""
        value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
        normalized.append(value.casefold())
    return hashlib.sha256("|".join(normalized).encode("utf-8")).hexdigest()


def _apply_aliases(record: Mapping[str, Any], aliases: Mapping[str, str]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in record.items():
        clean_key = str(key).strip().casefold().replace(" ", "_")
        normalized[aliases.get(clean_key, clean_key)] = value
    return normalized


def normalize_book(record: Mapping[str, Any]) -> dict[str, Any]:
    row = _apply_aliases(record, BOOK_ALIASES)
    title = _text(row.get("title"))
    if not title:
        raise ValueError("Un livre doit avoir un titre non vide.")
    url = _text(row.get("url"))
    source_key = _text(row.get("source_key")) or _canonical_key(
        ("book-url", url)
        if url
        else ("book", title, row.get("category") or row.get("product_type"))
    )
    return {
        "source_key": source_key,
        "title": title,
        "price": _number(row.get("price")),
        "availability": _text(row.get("availability")),
        "products_on_page": _number(row.get("products_on_page"), integer=True),
        "rating": _number(row.get("rating")),
        "review_count": _number(row.get("review_count"), integer=True),
        "description": _text(row.get("description")),
        "product_type": _text(row.get("product_type")),
        "category": _text(row.get("category")),
        "tax": _number(row.get("tax")),
        "url": url,
        "source_page": _number(row.get("source_page"), integer=True),
        "scraped_at": _timestamp(row.get("scraped_at")),
    }


def normalize_car(record: Mapping[str, Any]) -> dict[str, Any]:
    row = _apply_aliases(record, CAR_ALIASES)
    brand = _text(row.get("brand"))
    if not brand:
        raise ValueError("Une annonce automobile doit avoir une marque non vide.")
    url = _text(row.get("url"))
    source_key = _text(row.get("source_key")) or _canonical_key(
        ("car-url", url)
        if url
        else (
            "car",
            brand,
            row.get("model"),
            row.get("year"),
            row.get("price"),
            row.get("mileage"),
            row.get("region"),
        )
    )
    return {
        "source_key": source_key,
        "brand": brand,
        "model": _text(row.get("model")),
        "year": _number(row.get("year"), integer=True),
        "price": _number(row.get("price")),
        "mileage": _number(row.get("mileage")),
        "transmission": _text(row.get("transmission")),
        "region": _text(row.get("region")),
        "url": url,
        "source_page": _number(row.get("source_page"), integer=True),
        "scraped_at": _timestamp(row.get("scraped_at")),
    }


class DataRepository:
    """Small, connection-per-operation repository suitable for Streamlit."""

    def __init__(self, database_path: PathLike | None = None) -> None:
        self.database_path = database_path
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        return get_connection(self.database_path)

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(SCHEMA_SQL)

    def upsert_books(self, data: Any) -> int:
        rows = [normalize_book(row) for row in _records(data)]
        if not rows:
            return 0
        placeholders = ", ".join(f":{field}" for field in BOOK_FIELDS)
        updates = ", ".join(
            f"{field} = excluded.{field}"
            for field in BOOK_FIELDS
            if field not in {"source_key"}
        )
        sql = f"""
            INSERT INTO books ({', '.join(BOOK_FIELDS)})
            VALUES ({placeholders})
            ON CONFLICT(source_key) DO UPDATE SET
                {updates},
                updated_at = CURRENT_TIMESTAMP
        """
        with self._connect() as connection:
            connection.executemany(sql, rows)
        return len(rows)

    def upsert_cars(self, data: Any) -> int:
        rows = [normalize_car(row) for row in _records(data)]
        if not rows:
            return 0
        placeholders = ", ".join(f":{field}" for field in CAR_FIELDS)
        updates = ", ".join(
            f"{field} = excluded.{field}"
            for field in CAR_FIELDS
            if field not in {"source_key"}
        )
        sql = f"""
            INSERT INTO cars ({', '.join(CAR_FIELDS)})
            VALUES ({placeholders})
            ON CONFLICT(source_key) DO UPDATE SET
                {updates},
                updated_at = CURRENT_TIMESTAMP
        """
        with self._connect() as connection:
            connection.executemany(sql, rows)
        return len(rows)

    def list_books(
        self,
        *,
        category: str | None = None,
        product_type: str | None = None,
        availability: str | None = None,
        rating: float | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        parameters: list[Any] = []
        for column, value in (
            ("category", category),
            ("product_type", product_type),
            ("availability", availability),
            ("rating", rating),
        ):
            if value is not None:
                clauses.append(f"{column} = ?")
                parameters.append(value)
        return self._select("books", clauses, parameters, limit)

    def list_cars(
        self,
        *,
        brand: str | None = None,
        year: int | None = None,
        region: str | None = None,
        transmission: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        parameters: list[Any] = []
        for column, value in (
            ("brand", brand),
            ("year", year),
            ("region", region),
            ("transmission", transmission),
        ):
            if value is not None:
                clauses.append(f"{column} = ?")
                parameters.append(value)
        return self._select("cars", clauses, parameters, limit)

    def _select(
        self,
        table: str,
        clauses: Sequence[str],
        parameters: Sequence[Any],
        limit: int | None,
    ) -> list[dict[str, Any]]:
        if table not in {"books", "cars"}:
            raise ValueError("Table non autorisée.")
        sql = f"SELECT * FROM {table}"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY id"
        params = list(parameters)
        if limit is not None:
            if int(limit) < 0:
                raise ValueError("La limite ne peut pas être négative.")
            sql += " LIMIT ?"
            params.append(int(limit))
        with self._connect() as connection:
            return [dict(row) for row in connection.execute(sql, params).fetchall()]

    def count(self, table: str) -> int:
        if table not in {"books", "cars"}:
            raise ValueError("Table non autorisée.")
        with self._connect() as connection:
            row = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            return int(row[0])

    def as_dataframe(self, table: str):
        """Load a table as a DataFrame when pandas is installed."""

        try:
            import pandas as pd
        except ImportError as error:  # pragma: no cover - depends on runtime extras
            raise RuntimeError("pandas est requis pour charger un DataFrame.") from error
        rows = self.list_books() if table == "books" else self.list_cars() if table == "cars" else None
        if rows is None:
            raise ValueError("Table non autorisée.")
        return pd.DataFrame.from_records(rows)


def upsert_books(data: Any, database_path: PathLike | None = None) -> int:
    return DataRepository(database_path).upsert_books(data)


def upsert_cars(data: Any, database_path: PathLike | None = None) -> int:
    return DataRepository(database_path).upsert_cars(data)


def load_books(database_path: PathLike | None = None, **filters: Any) -> list[dict[str, Any]]:
    return DataRepository(database_path).list_books(**filters)


def load_cars(database_path: PathLike | None = None, **filters: Any) -> list[dict[str, Any]]:
    return DataRepository(database_path).list_cars(**filters)
