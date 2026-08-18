"""Primitives de nettoyage partagées, sans logique propre à une source."""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from numbers import Number
from typing import Any

import pandas as pd

MISSING_TOKENS = {
    "",
    "-",
    "--",
    "n/a",
    "na",
    "n.d.",
    "nd",
    "none",
    "null",
    "non renseigné",
    "non renseigne",
    "indisponible",
}


def as_dataframe(data: pd.DataFrame | Iterable[Mapping[str, Any]] | Mapping[str, Any]) -> pd.DataFrame:
    """Copie une DataFrame ou construit une DataFrame depuis des enregistrements."""

    if isinstance(data, pd.DataFrame):
        return data.copy(deep=True)
    if isinstance(data, Mapping):
        return pd.DataFrame([dict(data)])
    return pd.DataFrame(list(data))


def ensure_columns(frame: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    """Ajoute les colonnes attendues absentes avec la valeur nullable ``pd.NA``."""

    for column in columns:
        if column not in frame.columns:
            frame[column] = pd.NA
    return frame


def clean_text(series: pd.Series) -> pd.Series:
    """Supprime espaces superflus et représentations textuelles de valeurs nulles."""

    result = series.astype("string")
    result = result.str.replace(r"\s+", " ", regex=True).str.strip()
    folded = result.str.casefold()
    return result.mask(folded.isin(MISSING_TOKENS), pd.NA)


def fold_text(value: Any) -> str:
    """Produit une forme minuscule sans accent pour les comparaisons de catégories."""

    normalized = unicodedata.normalize("NFKD", str(value))
    return "".join(char for char in normalized if not unicodedata.combining(char)).casefold()


def _parse_decimal_scalar(value: Any) -> float | None:
    if value is None or value is pd.NA:
        return None
    if isinstance(value, Number) and not isinstance(value, bool):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None

    match = re.search(r"[-+]?\d[\d\s\u00a0\u202f.,]*", str(value))
    if not match:
        return None
    number = re.sub(r"[\s\u00a0\u202f]", "", match.group(0))
    comma_position = number.rfind(",")
    dot_position = number.rfind(".")

    if comma_position >= 0 and dot_position >= 0:
        decimal_separator = "," if comma_position > dot_position else "."
        thousands_separator = "." if decimal_separator == "," else ","
        number = number.replace(thousands_separator, "")
        number = number.replace(decimal_separator, ".")
    elif comma_position >= 0 or dot_position >= 0:
        separator = "," if comma_position >= 0 else "."
        integer_part, fractional_part = number.rsplit(separator, 1)
        # Deux chiffres après le séparateur correspondent aux prix du site;
        # trois chiffres correspondent le plus souvent à un groupement de milliers.
        if len(fractional_part) in {1, 2}:
            number = integer_part.replace(separator, "") + "." + fractional_part
        else:
            number = number.replace(separator, "")
    try:
        numeric = float(number)
    except ValueError:
        return None
    return numeric if math.isfinite(numeric) else None


def to_nullable_float(series: pd.Series) -> pd.Series:
    """Convertit prix/taxes localisés vers le dtype pandas ``Float64``."""

    values = [_parse_decimal_scalar(value) for value in series.tolist()]
    return pd.Series(pd.array(values, dtype="Float64"), index=series.index)


def _parse_integer_scalar(value: Any) -> int | None:
    if value is None or value is pd.NA:
        return None
    if isinstance(value, Number) and not isinstance(value, bool):
        numeric = float(value)
        if not math.isfinite(numeric):
            return None
        return int(numeric)

    text = str(value).strip()
    sign = -1 if text.startswith("-") else 1
    digits = "".join(re.findall(r"\d+", text))
    return sign * int(digits) if digits else None


def to_nullable_integer(series: pd.Series) -> pd.Series:
    """Convertit années/compteurs en entiers pandas nullables ``Int64``."""

    values = [_parse_integer_scalar(value) for value in series.tolist()]
    return pd.Series(pd.array(values, dtype="Int64"), index=series.index)


def deduplicate(
    frame: pd.DataFrame,
    *,
    fallback_columns: Sequence[str],
) -> pd.DataFrame:
    """Déduplique par URL, puis par colonnes métier quand l'URL manque."""

    if frame.empty:
        return frame

    keys: list[str] = []
    for index, row in frame.iterrows():
        url = row.get("url")
        if pd.notna(url) and str(url).strip():
            keys.append("url:" + str(url).strip().casefold())
            continue
        components = []
        for column in fallback_columns:
            value = row.get(column)
            components.append("" if pd.isna(value) else str(value).strip().casefold())
        keys.append("fallback:" + "\u241f".join(components))

    keep = ~pd.Series(keys, index=frame.index).duplicated(keep="first")
    return frame.loc[keep].copy()


__all__ = [
    "as_dataframe",
    "clean_text",
    "deduplicate",
    "ensure_columns",
    "fold_text",
    "to_nullable_float",
    "to_nullable_integer",
]
