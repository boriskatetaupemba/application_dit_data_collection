"""Defensive adapters around the Selenium scrapers and cleaning pipelines."""

from __future__ import annotations

import importlib
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .data_access import CLEANED_DIR

LOGGER = logging.getLogger(__name__)


class IntegrationUnavailable(RuntimeError):
    """Raised when an optional scraper or cleaner cannot be imported."""


@dataclass(frozen=True)
class ScrapingResult:
    source: str
    raw_data: Any
    cleaned_data: Any
    row_count: int
    persisted_rows: int
    cleaned_file: Path | None
    elapsed_seconds: float


PIPELINES = {
    "books": {
        "scraper_module": "scrapers.books_scraper",
        "scraper_names": ("scrape_books",),
        "cleaner_module": "cleaners.books_cleaner",
        "cleaner_names": ("clean_books_data", "clean_books"),
        "filename": "books_cleaned.csv",
        "maximum_pages": 50,
    },
    "cars": {
        "scraper_module": "scrapers.gaaraas_scraper",
        "scraper_names": ("scrape_gaaraas",),
        "cleaner_module": "cleaners.gaaraas_cleaner",
        "cleaner_names": ("clean_gaaraas_data", "clean_gaaraas"),
        "filename": "gaaraas_cleaned.csv",
        "maximum_pages": 100,
    },
}


def _load_callable(module_name: str, names: tuple[str, ...]) -> Callable[..., Any]:
    try:
        module = importlib.import_module(module_name)
    except (ImportError, ModuleNotFoundError) as error:
        raise IntegrationUnavailable(
            f"Le module optionnel « {module_name} » n’est pas disponible : {error}"
        ) from error
    for name in names:
        candidate = getattr(module, name, None)
        if callable(candidate):
            return candidate
    expected = " ou ".join(names)
    raise IntegrationUnavailable(
        f"Le module « {module_name} » ne fournit pas la fonction attendue : {expected}."
    )


def _length(data: Any) -> int:
    try:
        return int(len(data))
    except (TypeError, ValueError):
        return 0


def _save_cleaned(data: Any, path: Path) -> Path | None:
    if data is None or not hasattr(data, "to_csv"):
        return None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data.to_csv(path, index=False, encoding="utf-8-sig")
    except OSError:
        # SQLite remains the source used by the app on read-only deployments.
        LOGGER.warning("Copie CSV nettoyée impossible : %s", path, exc_info=True)
        return None
    return path


def run_scraping(
    source: str,
    *,
    max_pages: int,
    repository: Any,
    headless: bool = True,
) -> ScrapingResult:
    """Run one confirmed scraper API, clean its output and persist it."""

    if source not in PIPELINES:
        raise ValueError("Source de scraping inconnue.")
    if int(max_pages) < 1:
        raise ValueError("Le nombre de pages doit être supérieur ou égal à 1.")

    pipeline = PIPELINES[source]
    if int(max_pages) > int(pipeline["maximum_pages"]):
        raise ValueError(
            f"La source {source} est limitée à {pipeline['maximum_pages']} pages."
        )
    scraper = _load_callable(pipeline["scraper_module"], pipeline["scraper_names"])
    cleaner = _load_callable(pipeline["cleaner_module"], pipeline["cleaner_names"])

    started = time.monotonic()
    raw_data = scraper(max_pages=int(max_pages), output_path=None, headless=headless)
    cleaned_data = cleaner(raw_data)
    row_count = _length(cleaned_data)
    persisted_rows = (
        repository.upsert_books(cleaned_data)
        if source == "books"
        else repository.upsert_cars(cleaned_data)
    )
    cleaned_file = _save_cleaned(cleaned_data, CLEANED_DIR / pipeline["filename"])
    return ScrapingResult(
        source=source,
        raw_data=raw_data,
        cleaned_data=cleaned_data,
        row_count=row_count,
        persisted_rows=persisted_rows,
        cleaned_file=cleaned_file,
        elapsed_seconds=time.monotonic() - started,
    )
