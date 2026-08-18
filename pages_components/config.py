"""Non-sensitive application configuration helpers."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse


def _secret(st: Any, key: str) -> str | None:
    try:
        value = st.secrets.get(key)
    except (FileNotFoundError, KeyError, TypeError):
        return None
    return str(value).strip() if value else None


def get_setting(st: Any, secret_key: str, environment_key: str) -> str | None:
    """Read a Streamlit secret first, then its environment fallback."""

    return _secret(st, secret_key) or os.getenv(environment_key) or None


def get_form_links(st: Any) -> dict[str, str | None]:
    return {
        "kobo": get_setting(st, "kobo_form_url", "KOBO_FORM_URL"),
        "google": get_setting(st, "google_form_url", "GOOGLE_FORM_URL"),
    }


def get_database_location(st: Any) -> str | None:
    """Return an optional SQLite path/URL configured in Streamlit secrets."""

    return _secret(st, "data_collection_db_path") or _secret(st, "database_url")


def is_public_http_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
