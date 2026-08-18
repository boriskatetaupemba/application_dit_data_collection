"""Interactive dashboard for cleaned Gaaraas car-listing data."""

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


def _money(value: float | None) -> str:
    return "—" if value is None else f"{value:,.0f} FCFA"


def render_cars_dashboard(st, data: Any) -> None:
    """Render filters, KPIs and charts into the provided Streamlit module."""

    from .analytics import car_metrics

    pd, px = _dependencies()
    frame = _frame(data)
    if frame.empty:
        st.info("Aucune donnée Gaaraas nettoyée n’est encore disponible.")
        return

    for column in ("year", "price", "mileage"):
        if column not in frame:
            frame[column] = None
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    for column in ("brand", "region", "transmission"):
        if column not in frame:
            frame[column] = None

    brands = sorted(frame["brand"].dropna().astype(str).unique().tolist())
    years = sorted(frame["year"].dropna().astype(int).unique().tolist())
    regions = sorted(frame["region"].dropna().astype(str).unique().tolist())
    transmissions = sorted(frame["transmission"].dropna().astype(str).unique().tolist())

    with st.expander("Filtres Gaaraas", expanded=True):
        first, second = st.columns(2)
        selected_brands = first.multiselect(
            "Marque", brands, default=brands, key="cars_filter_brand"
        )
        selected_years = second.multiselect(
            "Année", years, default=years, key="cars_filter_year"
        )
        third, fourth = st.columns(2)
        selected_regions = third.multiselect(
            "Région", regions, default=regions, key="cars_filter_region"
        )
        selected_transmissions = fourth.multiselect(
            "Boîte de vitesses",
            transmissions,
            default=transmissions,
            key="cars_filter_transmission",
        )

    filtered = frame
    if selected_brands:
        filtered = filtered[filtered["brand"].astype(str).isin(selected_brands)]
    if selected_years:
        filtered = filtered[filtered["year"].isin(selected_years)]
    if selected_regions:
        filtered = filtered[filtered["region"].astype(str).isin(selected_regions)]
    if selected_transmissions:
        filtered = filtered[filtered["transmission"].astype(str).isin(selected_transmissions)]

    metrics = car_metrics(filtered.to_dict(orient="records"))
    columns = st.columns(5)
    columns[0].metric("Annonces", metrics["total_ads"])
    columns[1].metric("Prix moyen", _money(metrics["average_price"]))
    columns[2].metric("Prix minimum", _money(metrics["minimum_price"]))
    columns[3].metric("Prix maximum", _money(metrics["maximum_price"]))
    average_mileage = metrics["average_mileage"]
    columns[4].metric(
        "Kilométrage moyen", "—" if average_mileage is None else f"{average_mileage:,.0f} km"
    )

    if filtered.empty:
        st.warning("Aucune annonce ne correspond aux filtres sélectionnés.")
        return

    first, second = st.columns(2)
    brand_counts = (
        filtered["brand"]
        .fillna("Non renseigné")
        .value_counts()
        .head(20)
        .rename_axis("Marque")
        .reset_index(name="Annonces")
    )
    first.plotly_chart(
        px.bar(brand_counts, x="Marque", y="Annonces", title="Annonces par marque"),
        width="stretch",
    )

    year_counts = (
        filtered.dropna(subset=["year"])["year"]
        .astype(int)
        .value_counts()
        .sort_index()
        .rename_axis("Année")
        .reset_index(name="Annonces")
    )
    if not year_counts.empty:
        second.plotly_chart(
            px.bar(year_counts, x="Année", y="Annonces", title="Annonces par année"),
            width="stretch",
        )
    else:
        second.info("Les années ne sont pas disponibles pour cette sélection.")

    third, fourth = st.columns(2)
    mileage_frame = filtered.dropna(subset=["mileage"])
    if not mileage_frame.empty:
        third.plotly_chart(
            px.histogram(
                mileage_frame,
                x="mileage",
                nbins=25,
                title="Distribution du kilométrage",
                labels={"mileage": "Kilométrage (km)"},
            ),
            width="stretch",
        )
    else:
        third.info("Le kilométrage n’est pas disponible pour cette sélection.")

    scatter_frame = filtered.dropna(subset=["price", "mileage"])
    if not scatter_frame.empty:
        fourth.plotly_chart(
            px.scatter(
                scatter_frame,
                x="mileage",
                y="price",
                color="brand",
                hover_data=[column for column in ("model", "year", "region") if column in scatter_frame],
                title="Prix et kilométrage",
                labels={"mileage": "Kilométrage (km)", "price": "Prix (FCFA)", "brand": "Marque"},
            ),
            width="stretch",
        )
    else:
        fourth.info("Prix et kilométrage sont nécessaires pour cette comparaison.")

    transmission_counts = (
        filtered["transmission"]
        .fillna("Non renseigné")
        .value_counts()
        .rename_axis("Boîte")
        .reset_index(name="Annonces")
    )
    st.plotly_chart(
        px.pie(
            transmission_counts,
            names="Boîte",
            values="Annonces",
            title="Répartition par type de boîte",
        ),
        width="stretch",
    )
