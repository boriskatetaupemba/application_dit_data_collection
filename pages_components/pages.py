"""All page renderers for the single-entrypoint Streamlit application."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from dashboard.books_dashboard import render_books_dashboard
from dashboard.cars_dashboard import render_cars_dashboard

from .config import get_form_links, is_public_http_url
from .data_access import (
    PROJECT_ROOT,
    display_columns,
    list_raw_files,
    load_cleaned_data,
    read_tabular_file,
)
from .integrations import IntegrationUnavailable, run_scraping
from .theme import (
    render_callout,
    render_empty_state,
    render_file_summary,
    render_page_header,
    render_raw_badge,
    render_step_cards,
)

LOGGER = logging.getLogger(__name__)

PAGE_NAMES = (
    "Accueil",
    "Scraping",
    "Données brutes",
    "Données nettoyées",
    "Dashboard",
    "Évaluation",
    "Documentation",
)


def render_home(st: Any, repository: Any) -> None:
    render_page_header(
        st,
        kicker="Atelier de collecte · Vue d'ensemble",
        title="Data Collection Lab",
        intro=(
            "Un espace de travail unique pour collecter Books et Gaaraas, préparer les "
            "données, les conserver dans SQLite et transformer les résultats en décisions."
        ),
    )

    first, second = st.columns(2)
    first.metric("Livres en base", repository.count("books"))
    second.metric("Annonces automobiles en base", repository.count("cars"))

    st.subheader("Parcours conseillé")
    st.markdown(
        """
1. Lancez une collecte limitée depuis **Scraping** pour valider l'environnement Selenium.
2. Consultez ou téléchargez les exports de l'extension Web Scraper dans **Données brutes**.
3. Vérifiez les lignes normalisées dans **Données nettoyées**.
4. Explorez les indicateurs dans **Dashboard**, puis utilisez **Évaluation**.
"""
    )
    st.info(
        "Les exports no-code de l’extension Web Scraper restent distincts des données "
        "nettoyées produites par le pipeline Selenium."
    )


def render_scraping_page(st: Any, repository: Any) -> None:
    render_page_header(
        st,
        kicker="Module 01 · Collecte automatisée",
        title="Scraping Selenium",
        intro=(
            "Paramétrez une collecte multi-page. À la fin du parcours, les lignes sont "
            "nettoyées, dédupliquées puis enregistrées dans SQLite."
        ),
    )

    labels = {
        "Books to Scrape": ("books", 50),
        "Gaaraas — Dakar Auto": ("cars", 100),
    }
    label = st.selectbox("Source", list(labels), key="scrape_source")
    source, required_pages = labels[label]
    default_pages = min(3, required_pages)
    max_pages = int(
        st.number_input(
            "Nombre de pages",
            min_value=1,
            max_value=required_pages,
            value=default_pages,
            step=1,
            help=(
                f"Le périmètre complet demandé est de {required_pages} pages. "
                "Commencez par quelques pages pour tester le navigateur."
            ),
        )
    )
    headless = st.checkbox(
        "Exécuter le navigateur en mode headless",
        value=True,
        help="Recommandé sur un serveur ou lors du déploiement.",
    )

    if max_pages == required_pages:
        st.warning(
            "Collecte complète sélectionnée : l'opération peut prendre plusieurs minutes "
            "et l'interface attendra la fin du navigateur."
        )
    else:
        st.info(
            "Pendant la collecte, cette page attend le navigateur. Ne la fermez pas et "
            "commencez avec peu de pages si vous testez la configuration."
        )

    acknowledged = st.checkbox(
        "J’ai compris que Selenium peut prendre du temps.", key="scrape_acknowledged"
    )
    launch = st.button(
        "Lancer le scraping",
        type="primary",
        disabled=not acknowledged,
        width="stretch",
    )
    if not launch:
        return

    try:
        with st.spinner(f"Collecte de {max_pages} page(s), nettoyage et sauvegarde en cours…"):
            result = run_scraping(
                source,
                max_pages=max_pages,
                repository=repository,
                headless=headless,
            )
    except IntegrationUnavailable as error:
        st.error(str(error))
        st.caption("Vérifiez que les modules scrapers et cleaners sont présents et importables.")
        return
    except Exception as error:  # Streamlit must stay usable after Selenium failures
        LOGGER.exception("Échec du pipeline de scraping %s", source)
        st.error(f"Le scraping a échoué : {error}")
        st.caption(
            "Consultez les logs du serveur pour le détail, puis vérifiez le pilote du navigateur, "
            "la connexion réseau et les sélecteurs Selenium."
        )
        return

    st.success(
        f"{result.row_count} ligne(s) nettoyée(s) et {result.persisted_rows} ligne(s) "
        f"traitée(s) en {result.elapsed_seconds:.1f} s."
    )
    if result.cleaned_file:
        st.caption(f"Copie nettoyée : {result.cleaned_file.relative_to(PROJECT_ROOT)}")
    if result.row_count:
        st.subheader("Aperçu nettoyé")
        st.dataframe(result.cleaned_data.head(100), width="stretch", hide_index=True)


def _raw_file_label(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT / "data" / "raw"))


def _format_file_size(size: int) -> str:
    if size < 1024:
        return f"{size} o"
    if size < 1024**2:
        return f"{size / 1024:,.1f} Kio"
    return f"{size / 1024**2:,.1f} Mio"


def render_raw_data_page(st: Any, repository: Any) -> None:
    del repository
    render_page_header(
        st,
        kicker="Module 03 · Web Scraper no-code",
        title="Données brutes",
        intro=(
            "Consultez et téléchargez les exports produits par l'extension Web Scraper, "
            "dans leur état d'origine avant toute correction ou normalisation."
        ),
    )
    render_raw_badge(st)
    render_callout(
        st,
        title="Pourquoi garder la version brute ?",
        text=(
            "Elle constitue la trace fidèle de la collecte no-code. Elle permet de comparer "
            "la source avec les données Selenium nettoyées et de reprendre une transformation."
        ),
        mark="≠",
    )

    st.subheader("Alimenter cette page en quatre étapes")
    render_step_cards(
        st,
        (
            (
                "Importer un sitemap",
                "Dans l'extension Web Scraper, importez le sitemap Books ou Gaaraas fourni dans web_scraper/.",
            ),
            (
                "Lancer la collecte",
                "Démarrez le scraping dans l'extension et attendez la fin du parcours des pages.",
            ),
            (
                "Exporter le résultat",
                "Exportez les lignes sans les modifier, de préférence en CSV, JSON ou XLSX.",
            ),
            (
                "Déposer puis actualiser",
                "Copiez l'export dans data/raw, puis revenez ici pour le sélectionner et le télécharger.",
            ),
        ),
    )

    files = list_raw_files()
    if not files:
        render_empty_state(
            st,
            title="Le dépôt de données brutes est vide",
            text=(
                "Aucun export Web Scraper n'est encore disponible. Copiez un fichier CSV, "
                "JSON ou XLSX dans le dossier data/raw du projet."
            ),
        )
        st.caption("Exemple PowerShell depuis la racine du projet :")
        st.code(
            'Copy-Item -LiteralPath "C:\\chemin\\export.csv" -Destination "data\\raw\\"',
            language="powershell",
        )
        _, refresh_column, _ = st.columns((1, 1.4, 1))
        refresh_column.button(
            "Vérifier à nouveau",
            key="refresh_empty_raw_files",
            width="stretch",
        )
        st.caption(
            "Le dépôt se fait dans le système de fichiers du projet ; aucun upload temporaire "
            "n'est présenté comme persistant."
        )
        return

    total_size = sum(path.stat().st_size for path in files)
    latest_update = max(path.stat().st_mtime for path in files)
    first, second, third = st.columns(3)
    first.metric("Exports disponibles", len(files))
    second.metric("Poids du dépôt", _format_file_size(total_size))
    third.metric(
        "Dernière mise à jour",
        datetime.fromtimestamp(latest_update).strftime("%d/%m/%Y · %H:%M"),
    )

    st.subheader("Sélectionner un export")
    selected = st.selectbox(
        "Fichier brut",
        files,
        format_func=_raw_file_label,
        label_visibility="collapsed",
    )
    selected_stat = selected.stat()
    render_file_summary(
        st,
        (
            f"Format {selected.suffix.lstrip('.').upper()}",
            _format_file_size(selected_stat.st_size),
            f"Modifié le {datetime.fromtimestamp(selected_stat.st_mtime):%d/%m/%Y à %H:%M}",
            "Aucune transformation appliquée",
        ),
    )
    download_column, refresh_column = st.columns((3, 1))
    download_column.download_button(
        "Télécharger le fichier brut",
        data=selected.read_bytes(),
        file_name=selected.name,
        mime="application/octet-stream",
        key=f"download_raw_{selected.as_posix()}",
        width="stretch",
    )
    refresh_column.button(
        "Actualiser",
        key="refresh_raw_files",
        width="stretch",
    )

    try:
        preview = read_tabular_file(selected)
    except Exception as error:
        st.warning(f"Le téléchargement reste disponible, mais l'aperçu a échoué : {error}")
        return
    st.subheader("Aperçu sans transformation")
    st.dataframe(preview.head(100), width="stretch", hide_index=True)
    st.caption(
        f"{len(preview):,} ligne(s) dans le fichier · les 100 premières sont affichées."
    )


def render_cleaned_data_page(st: Any, repository: Any) -> None:
    render_page_header(
        st,
        kicker="Module 04 · Préparation",
        title="Données nettoyées",
        intro=(
            "Contrôlez les lignes issues du pipeline Selenium après typage, normalisation "
            "des valeurs, contrôle de cohérence et dédoublonnage."
        ),
    )
    source_label = st.radio(
        "Source",
        ("Books to Scrape", "Gaaraas"),
        horizontal=True,
        key="cleaned_source",
    )
    source = "books" if source_label == "Books to Scrape" else "cars"
    try:
        frame, origin = load_cleaned_data(repository, source)
    except Exception as error:
        st.error(f"Impossible de charger les données nettoyées : {error}")
        return

    if frame.empty:
        st.info("Aucune donnée nettoyée disponible. Lancez d'abord un scraping Selenium.")
        return
    visible = display_columns(frame, source)
    st.caption(f"Source de l'aperçu : {origin} — {len(visible):,} ligne(s)")
    st.dataframe(visible, width="stretch", hide_index=True)
    st.download_button(
        "Télécharger les données nettoyées (CSV)",
        data=visible.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{source}_cleaned.csv",
        mime="text/csv",
        key=f"download_cleaned_{source}",
        width="stretch",
    )


def render_dashboard_page(st: Any, repository: Any) -> None:
    render_page_header(
        st,
        kicker="Module 05 · Exploration",
        title="Dashboard",
        intro=(
            "Filtrez les données nettoyées et comparez les indicateurs essentiels des livres "
            "et des annonces automobiles."
        ),
    )
    books_tab, cars_tab = st.tabs(("Books to Scrape", "Gaaraas"))
    try:
        books, _ = load_cleaned_data(repository, "books")
        cars, _ = load_cleaned_data(repository, "cars")
    except Exception as error:
        st.error(f"Impossible de charger les données du dashboard : {error}")
        return

    with books_tab:
        try:
            render_books_dashboard(st, books)
        except RuntimeError as error:
            st.error(str(error))
    with cars_tab:
        try:
            render_cars_dashboard(st, cars)
        except RuntimeError as error:
            st.error(str(error))


def render_evaluation_page(st: Any, repository: Any) -> None:
    del repository
    render_page_header(
        st,
        kicker="Module 06 · Retour utilisateur",
        title="Évaluer l'application",
        intro=(
            "Partagez votre expérience dans KoboToolbox ou Google Forms. Les deux versions "
            "reposent sur la même spécification d'évaluation."
        ),
    )
    links = get_form_links(st)
    first, second = st.columns(2)

    with first:
        st.subheader("KoboToolbox")
        if is_public_http_url(links["kobo"]):
            st.link_button("Ouvrir le formulaire Kobo", links["kobo"], width="stretch")
        else:
            st.info("Configurez `kobo_form_url` dans les secrets ou `KOBO_FORM_URL` dans l'environnement.")

    with second:
        st.subheader("Google Forms")
        if is_public_http_url(links["google"]):
            st.link_button(
                "Ouvrir le formulaire Google",
                links["google"],
                width="stretch",
            )
        else:
            st.info(
                "Configurez `google_form_url` dans les secrets ou `GOOGLE_FORM_URL` dans l'environnement."
            )


def render_documentation_page(st: Any, repository: Any) -> None:
    del repository
    render_page_header(
        st,
        kicker="Repères techniques",
        title="Documentation",
        intro=(
            "Retrouvez le flux de données, le périmètre des collectes et les paramètres "
            "nécessaires à l'exécution locale ou au déploiement."
        ),
    )
    st.subheader("Flux des données")
    st.code(
        "Selenium → données brutes en mémoire → nettoyeur → SQLite → dashboard\n"
        "Web Scraper (extension) → data/raw → aperçu et téléchargement",
        language="text",
    )
    st.subheader("Sources et périmètre")
    st.markdown(
        """
- **Books to Scrape** : catalogue complet, jusqu'à 50 pages.
- **Gaaraas — Dakar Auto** : pages 1 à 100.
- Le scraping codé repose exclusivement sur **Selenium**.
- Les imports SQLite utilisent une clé stable et un UPSERT afin de gérer les doublons.
"""
    )
    st.subheader("Configuration")
    st.code(
        "KOBO_FORM_URL=https://…\n"
        "GOOGLE_FORM_URL=https://…\n"
        "DATA_COLLECTION_DB_PATH=/chemin/optionnel/data_collection.db",
        language="bash",
    )
    st.caption(
        "Sur Streamlit Community Cloud, utilisez les secrets `kobo_form_url` et "
        "`google_form_url` plutôt que de versionner des liens sensibles."
    )


PAGE_RENDERERS = {
    "Accueil": render_home,
    "Scraping": render_scraping_page,
    "Données brutes": render_raw_data_page,
    "Données nettoyées": render_cleaned_data_page,
    "Dashboard": render_dashboard_page,
    "Évaluation": render_evaluation_page,
    "Documentation": render_documentation_page,
}


def render_page(st: Any, page: str, repository: Any) -> None:
    try:
        renderer = PAGE_RENDERERS[page]
    except KeyError as error:
        raise ValueError(f"Page inconnue : {page}") from error
    renderer(st, repository)
