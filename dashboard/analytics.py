"""Dependency-light calculations shared by dashboards and tests."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping
from statistics import fmean
from typing import Any


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        clean = re.sub(r"[^0-9,\.\-]", "", str(value).strip())
        if not clean:
            return None
        if "," in clean and "." in clean:
            clean = clean.replace(".", "").replace(",", ".")
        elif "," in clean:
            clean = clean.replace(",", ".")
        try:
            number = float(clean)
        except ValueError:
            return None
    return number if math.isfinite(number) else None


def _values(records: Iterable[Mapping[str, Any]], field: str) -> list[float]:
    output: list[float] = []
    for record in records:
        value = _number(record.get(field))
        if value is not None:
            output.append(value)
    return output


def _summary(values: list[float]) -> tuple[float | None, float | None, float | None]:
    if not values:
        return None, None, None
    return fmean(values), min(values), max(values)


def book_metrics(records: Iterable[Mapping[str, Any]]) -> dict[str, int | float | None]:
    """Return meaningful Book to Scrape indicators, ignoring missing numbers."""

    rows = list(records)
    prices = _values(rows, "price")
    reviews = _values(rows, "review_count")
    average_price, minimum_price, maximum_price = _summary(prices)
    return {
        "total_books": len(rows),
        "average_price": average_price,
        "minimum_price": minimum_price,
        "maximum_price": maximum_price,
        "average_reviews": fmean(reviews) if reviews else None,
    }


def car_metrics(records: Iterable[Mapping[str, Any]]) -> dict[str, int | float | None]:
    """Return meaningful Gaaraas indicators, ignoring missing numbers."""

    rows = list(records)
    prices = _values(rows, "price")
    mileage = _values(rows, "mileage")
    average_price, minimum_price, maximum_price = _summary(prices)
    return {
        "total_ads": len(rows),
        "average_price": average_price,
        "minimum_price": minimum_price,
        "maximum_price": maximum_price,
        "average_mileage": fmean(mileage) if mileage else None,
    }


def _selected(value: Any, selected: Iterable[Any] | None) -> bool:
    if selected is None:
        return True
    choices = set(selected)
    return not choices or value in choices


def filter_books(
    records: Iterable[Mapping[str, Any]],
    *,
    categories: Iterable[str] | None = None,
    product_types: Iterable[str] | None = None,
    availabilities: Iterable[str] | None = None,
    ratings: Iterable[float] | None = None,
) -> list[dict[str, Any]]:
    """Filter books without requiring pandas (empty selections mean all)."""

    return [
        dict(row)
        for row in records
        if _selected(row.get("category") or row.get("product_type"), categories)
        and _selected(row.get("product_type"), product_types)
        and _selected(row.get("availability"), availabilities)
        and _selected(row.get("rating"), ratings)
    ]


def filter_cars(
    records: Iterable[Mapping[str, Any]],
    *,
    brands: Iterable[str] | None = None,
    years: Iterable[int] | None = None,
    regions: Iterable[str] | None = None,
    transmissions: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Filter car listings without requiring pandas."""

    return [
        dict(row)
        for row in records
        if _selected(row.get("brand"), brands)
        and _selected(row.get("year"), years)
        and _selected(row.get("region"), regions)
        and _selected(row.get("transmission"), transmissions)
    ]
