"""Nettoyage documenté des variables Books to Scrape."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

from scrapers.books_scraper import BOOK_COLUMNS

from .common import (
    as_dataframe,
    clean_text,
    deduplicate,
    ensure_columns,
    fold_text,
    to_nullable_float,
    to_nullable_integer,
)

_RATINGS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}


def _normalize_availability(value: Any) -> str | Any:
    if pd.isna(value):
        return pd.NA
    folded = fold_text(value)
    if any(token in folded for token in ("out of stock", "rupture", "epuise")):
        return "out_of_stock"
    if any(token in folded for token in ("in stock", "en stock", "available", "disponible")):
        return "in_stock"
    return "_".join(folded.split()) or pd.NA


def _normalize_rating(value: Any) -> int | None:
    if value is None or value is pd.NA or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        rating = int(value)
        return rating if 1 <= rating <= 5 else None
    folded = fold_text(value)
    for word, rating in _RATINGS.items():
        if re.search(rf"\b{word}\b", folded):
            return rating
    match = re.search(r"\b([1-5])\b", folded)
    return int(match.group(1)) if match else None


def clean_books_data(
    data: pd.DataFrame | Iterable[Mapping[str, Any]] | Mapping[str, Any],
) -> pd.DataFrame:
    """Nettoie et type les données Books collectées par Selenium.

    Transformations appliquées: espaces et valeurs manquantes normalisés,
    prix/taxe en ``Float64``, compteurs/note en ``Int64``, disponibilité en
    ``in_stock``/``out_of_stock``, valeurs incohérentes mises à ``NA`` et
    doublons supprimés par URL (sinon titre + prix). Les textes ne sont ni
    traduits ni tronqués.
    """

    frame = ensure_columns(as_dataframe(data), BOOK_COLUMNS)

    for column in (
        "title",
        "availability",
        "description",
        "product_type",
        "category",
        "url",
    ):
        frame[column] = clean_text(frame[column])

    frame["availability"] = frame["availability"].map(_normalize_availability).astype("string")
    frame["price"] = to_nullable_float(frame["price"])
    frame["tax"] = to_nullable_float(frame["tax"])
    frame.loc[frame["price"] < 0, "price"] = pd.NA
    frame.loc[frame["tax"] < 0, "tax"] = pd.NA

    ratings = [_normalize_rating(value) for value in frame["rating"].tolist()]
    frame["rating"] = pd.array(ratings, dtype="Int64")
    for column in ("products_on_page", "review_count", "source_page"):
        frame[column] = to_nullable_integer(frame[column])
        frame.loc[frame[column] < 0, column] = pd.NA

    frame = deduplicate(frame, fallback_columns=("title", "price"))
    return frame.loc[:, BOOK_COLUMNS].reset_index(drop=True)


# Alias court conservé pour l'usage interactif dans Streamlit/notebooks.
clean_books = clean_books_data

__all__ = ["clean_books", "clean_books_data"]
