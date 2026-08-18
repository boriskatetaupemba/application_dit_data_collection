"""Interactive dashboard for cleaned Books to Scrape data."""

from __future__ import annotations

from typing import Any


def _dependencies():
    try:
        import pandas as pd
        import plotly.express as px
    except ImportError as error:  # pragma: no cover - runtime packaging concern
        raise RuntimeError("pandas et plotly sont requis pour afficher le dashboard.") from error
    return pd, px


def _frame(data: Any):
    pd, _ = _dependencies()
    if isinstance(data, pd.DataFrame):
        return data.copy()
    return pd.DataFrame.from_records(data or [])


def _money(value: float | None, currency: str = "£") -> str:
    return "—" if value is None else f"{value:,.2f} {currency}"


def render_books_dashboard(st, data: Any) -> None:
    """Render filters, KPIs and charts into the provided Streamlit module."""

    from .analytics import book_metrics

    pd, px = _dependencies()
    frame = _frame(data)
    if frame.empty:
        st.info("Aucune donnée Books nettoyée n’est encore disponible.")
        return

    for column in ("price", "rating", "review_count"):
        if column in frame:
            frame[column] = frame[column].apply(lambda value: None if value == "" else value)
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    for column in ("category", "product_type", "availability"):
        if column not in frame:
            frame[column] = None

    frame["analysis_category"] = frame["category"].fillna(frame["product_type"])
    categories = sorted(frame["analysis_category"].dropna().astype(str).unique().tolist())
    availabilities = sorted(frame["availability"].dropna().astype(str).unique().tolist())
    ratings = sorted(frame["rating"].dropna().unique().tolist()) if "rating" in frame else []

    with st.expander("Filtres Books", expanded=True):
        left, middle, right = st.columns(3)
        selected_categories = left.multiselect(
            "Catégorie", categories, default=categories, key="books_filter_category"
        )
        selected_availabilities = middle.multiselect(
            "Disponibilité",
            availabilities,
            default=availabilities,
            key="books_filter_availability",
        )
        selected_ratings = right.multiselect(
            "Note", ratings, default=ratings, key="books_filter_rating"
        )

    filtered = frame
    if selected_categories:
        filtered = filtered[filtered["analysis_category"].astype(str).isin(selected_categories)]
    if selected_availabilities:
        filtered = filtered[filtered["availability"].astype(str).isin(selected_availabilities)]
    if selected_ratings:
        filtered = filtered[filtered["rating"].isin(selected_ratings)]

    metrics = book_metrics(filtered.to_dict(orient="records"))
    columns = st.columns(5)
    columns[0].metric("Livres", metrics["total_books"])
    columns[1].metric("Prix moyen", _money(metrics["average_price"]))
    columns[2].metric("Prix minimum", _money(metrics["minimum_price"]))
    columns[3].metric("Prix maximum", _money(metrics["maximum_price"]))
    average_reviews = metrics["average_reviews"]
    columns[4].metric("Reviews moyennes", "—" if average_reviews is None else f"{average_reviews:.1f}")

    if filtered.empty:
        st.warning("Aucune ligne ne correspond aux filtres sélectionnés.")
        return

    first, second = st.columns(2)
    category_counts = (
        filtered["analysis_category"]
        .fillna("Non renseigné")
        .value_counts()
        .rename_axis("Catégorie")
        .reset_index(name="Livres")
    )
    first.plotly_chart(
        px.bar(category_counts, x="Catégorie", y="Livres", title="Livres par catégorie"),
        width="stretch",
    )

    rating_frame = filtered.dropna(subset=["rating"])
    if not rating_frame.empty:
        second.plotly_chart(
            px.histogram(
                rating_frame,
                x="rating",
                nbins=5,
                title="Distribution des notes",
                labels={"rating": "Note", "count": "Livres"},
            ),
            width="stretch",
        )
    else:
        second.info("Les notes ne sont pas disponibles pour cette sélection.")

    third, fourth = st.columns(2)
    availability_counts = (
        filtered["availability"]
        .fillna("Non renseigné")
        .value_counts()
        .rename_axis("Disponibilité")
        .reset_index(name="Livres")
    )
    third.plotly_chart(
        px.pie(
            availability_counts,
            names="Disponibilité",
            values="Livres",
            title="Disponibilité des produits",
        ),
        width="stretch",
    )

    price_frame = filtered.dropna(subset=["price"])
    if not price_frame.empty:
        fourth.plotly_chart(
            px.box(
                price_frame,
                x="analysis_category",
                y="price",
                title="Prix par catégorie",
                labels={"analysis_category": "Catégorie", "price": "Prix (£)"},
            ),
            width="stretch",
        )
    else:
        fourth.info("Les prix ne sont pas disponibles pour cette sélection.")
