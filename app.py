"""Streamlit entry point for the Data Collection project."""

from __future__ import annotations

from database.repository import DataRepository
from pages_components import PAGE_NAMES, render_page
from pages_components.config import get_database_location
from pages_components.theme import (
    configure_plotly_theme,
    inject_global_theme,
    render_sidebar_brand,
    render_sidebar_footer,
)


def main() -> None:
    try:
        import streamlit as st
    except ImportError as error:  # Friendly message when run with plain Python
        raise SystemExit(
            "Streamlit n'est pas installé. Installez les dépendances puis lancez "
            "`streamlit run app.py`."
        ) from error

    st.set_page_config(
        page_title="Data Collection Lab — Books & Gaaraas",
        page_icon="◈",
        layout="wide",
        initial_sidebar_state="auto",
    )

    @st.cache_resource(show_spinner=False)
    def repository() -> DataRepository:
        return DataRepository(get_database_location(st))

    inject_global_theme(st)
    configure_plotly_theme()
    render_sidebar_brand(st)
    page = st.sidebar.radio("Navigation", PAGE_NAMES, key="main_navigation")
    render_sidebar_footer(st)

    try:
        data_repository = repository()
    except Exception as error:
        st.error(f"Impossible d'initialiser la base SQLite : {error}")
        st.stop()

    render_page(st, page, data_repository)


if __name__ == "__main__":
    main()
