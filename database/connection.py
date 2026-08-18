"""Connection helpers for the local SQLite database."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Union
from urllib.parse import unquote

from .models import SCHEMA_SQL

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "data_collection.db"
PathLike = Union[str, os.PathLike[str]]


class ClosingConnection(sqlite3.Connection):
    """Commit/rollback like sqlite3, then release the file handle on context exit."""

    def __exit__(self, exc_type, exc_value, traceback):  # type: ignore[no-untyped-def]
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def _configured_database(database_path: PathLike | None = None) -> str:
    configured = (
        str(database_path)
        if database_path is not None
        else os.getenv("DATA_COLLECTION_DB_PATH")
        or os.getenv("DATABASE_URL")
        or str(DEFAULT_DB_PATH)
    )
    configured = configured.strip()
    if configured.startswith("sqlite:///"):
        configured = unquote(configured[len("sqlite:///") :])
    elif "://" in configured:
        raise ValueError("Seules les bases SQLite sont prises en charge par cette application.")
    return configured


def resolve_database_path(database_path: PathLike | None = None) -> Path:
    """Return the configured database path without creating the database."""

    return Path(_configured_database(database_path)).expanduser().resolve()


def get_connection(database_path: PathLike | None = None) -> sqlite3.Connection:
    """Open a configured SQLite connection.

    Parent directories are created for file-backed databases.  ``:memory:`` is
    accepted for small tests and interactive demonstrations.
    """

    raw_path = _configured_database(database_path)
    if raw_path != ":memory:":
        path = Path(raw_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        raw_path = str(path)

    connection = sqlite3.connect(raw_path, timeout=30.0, factory=ClosingConnection)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection


def initialize_database(database_path: PathLike | None = None) -> Path | str:
    """Create the tables and indexes, then return the resolved location."""

    with get_connection(database_path) as connection:
        connection.executescript(SCHEMA_SQL)

    if str(database_path) == ":memory:":
        return ":memory:"
    return resolve_database_path(database_path)
