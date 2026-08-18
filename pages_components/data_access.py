"""File and database reads used by the Streamlit pages."""

from __future__ import annotations

from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
CLEANED_DIR = PROJECT_ROOT / "data" / "cleaned"

SUPPORTED_RAW_SUFFIXES = {".csv", ".json", ".xlsx", ".xls", ".parquet"}


def list_raw_files() -> list[Path]:
    """List user-provided Web Scraper exports under ``data/raw``."""

    if not RAW_DIR.exists():
        return []
    return sorted(
        path
        for path in RAW_DIR.rglob("*")
        if path.is_file() and path.suffix.casefold() in SUPPORTED_RAW_SUFFIXES
    )


def read_tabular_file(path: Path):
    """Read a supported data file as a pandas DataFrame."""

    try:
        import pandas as pd
    except ImportError as error:  # pragma: no cover - deployment concern
        raise RuntimeError("pandas est requis pour prévisualiser les fichiers.") from error

    suffix = path.suffix.casefold()
    if suffix == ".csv":
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return pd.read_csv(path, encoding=encoding)
            except UnicodeDecodeError:
                continue
        return pd.read_csv(path)
    if suffix == ".json":
        try:
            return pd.read_json(path)
        except ValueError:
            return pd.read_json(path, lines=True)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"Format non pris en charge : {suffix}")


def cleaned_file_candidates(source: str) -> list[Path]:
    if not CLEANED_DIR.exists():
        return []
    patterns = (
        ("books_cleaned*", "cleaned_books*")
        if source == "books"
        else ("gaaraas_cleaned*", "cleaned_gaaraas*", "cars_cleaned*", "cleaned_cars*")
    )
    paths: set[Path] = set()
    for pattern in patterns:
        paths.update(
            path
            for path in CLEANED_DIR.glob(pattern)
            if path.is_file() and path.suffix.casefold() in SUPPORTED_RAW_SUFFIXES
        )
    return sorted(paths, key=lambda path: path.stat().st_mtime, reverse=True)


def load_cleaned_data(repository: Any, source: str):
    """Prefer SQLite data, with a cleaned-file fallback for first use."""

    rows = repository.list_books() if source == "books" else repository.list_cars()
    if rows:
        try:
            import pandas as pd
        except ImportError as error:  # pragma: no cover - deployment concern
            raise RuntimeError("pandas est requis pour afficher les données.") from error
        return pd.DataFrame.from_records(rows), "SQLite"

    candidates = cleaned_file_candidates(source)
    if candidates:
        return read_tabular_file(candidates[0]), str(candidates[0].relative_to(PROJECT_ROOT))

    try:
        import pandas as pd
    except ImportError as error:  # pragma: no cover - deployment concern
        raise RuntimeError("pandas est requis pour afficher les données.") from error
    return pd.DataFrame(), "Aucune source"


def display_columns(frame, source: str):
    """Remove persistence metadata from the student-facing preview."""

    hidden = {"id", "source_key", "created_at", "updated_at"}
    preferred = (
        [
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
        ]
        if source == "books"
        else [
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
        ]
    )
    available = [column for column in preferred if column in frame.columns]
    extras = [column for column in frame.columns if column not in hidden and column not in available]
    return frame.loc[:, available + extras]
