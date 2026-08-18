"""Nettoyage documenté des annonces automobiles Gaaraas."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date
from typing import Any

import pandas as pd

from scrapers.gaaraas_scraper import GAARAAS_COLUMNS

from .common import (
    as_dataframe,
    clean_text,
    deduplicate,
    ensure_columns,
    fold_text,
    to_nullable_integer,
)

_BRAND_CASE = {
    "bmw": "BMW",
    "byd": "BYD",
    "gmc": "GMC",
    "mg": "MG",
    "mini": "MINI",
}


def _normalize_brand(value: Any) -> str | Any:
    if pd.isna(value):
        return pd.NA
    cleaned = " ".join(str(value).split())
    return _BRAND_CASE.get(fold_text(cleaned), cleaned.title())


def _normalize_transmission(value: Any) -> str | Any:
    if pd.isna(value):
        return pd.NA
    folded = fold_text(value)
    if "auto" in folded:
        return "Automatique"
    if "manual" in folded or "manuell" in folded:
        return "Manuelle"
    if folded in {"n/a", "na", "nd", "non renseigne"}:
        return pd.NA
    return " ".join(str(value).split()).capitalize()


def clean_gaaraas_data(
    data: pd.DataFrame | Iterable[Mapping[str, Any]] | Mapping[str, Any],
) -> pd.DataFrame:
    """Nettoie et type les variables V1 à V7 de Gaaraas.

    Transformations appliquées: espaces/valeurs manquantes normalisés, prix
    CFA et kilométrage en ``Int64``, année en ``Int64`` avec plage cohérente
    1886..année courante+1, boîtes ramenées à Automatique/Manuelle et
    doublons supprimés par URL (sinon clé métier). Aucun prix n'est converti
    dans une autre devise.
    """

    frame = ensure_columns(as_dataframe(data), GAARAAS_COLUMNS)
    for column in ("brand", "model", "transmission", "region", "url"):
        frame[column] = clean_text(frame[column])

    frame["brand"] = frame["brand"].map(_normalize_brand).astype("string")
    frame["transmission"] = frame["transmission"].map(_normalize_transmission).astype("string")
    frame["region"] = frame["region"].str.title()

    for column in ("year", "price", "mileage", "source_page"):
        frame[column] = to_nullable_integer(frame[column])

    maximum_year = date.today().year + 1
    invalid_year = (frame["year"] < 1886) | (frame["year"] > maximum_year)
    frame.loc[invalid_year.fillna(False), "year"] = pd.NA
    frame.loc[(frame["price"] < 0).fillna(False), "price"] = pd.NA
    frame.loc[(frame["mileage"] < 0).fillna(False), "mileage"] = pd.NA
    frame.loc[(frame["source_page"] < 1).fillna(False), "source_page"] = pd.NA

    frame = deduplicate(
        frame,
        fallback_columns=("brand", "model", "year", "price", "mileage"),
    )
    return frame.loc[:, GAARAAS_COLUMNS].reset_index(drop=True)


clean_gaaraas = clean_gaaraas_data

__all__ = ["clean_gaaraas", "clean_gaaraas_data"]
