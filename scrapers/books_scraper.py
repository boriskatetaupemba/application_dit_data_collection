"""Collecte Selenium du catalogue public Books to Scrape.

Les cartes du catalogue fournissent les URLs et un jeu minimal de valeurs. Une
visite de chaque fiche produit complète les variables V1 à V9. La pagination
s'arrête sur l'absence du lien ``next`` (50 pages au 18/08/2026).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd
from selenium.common.exceptions import WebDriverException

from .base import BaseSeleniumScraper, CSS, ScraperLoadError

LOGGER = logging.getLogger(__name__)

BOOK_COLUMNS = [
    "title",
    "price",
    "availability",
    "products_on_page",
    "rating",
    "review_count",
    "description",
    "product_type",
    "tax",
    "category",
    "url",
    "source_page",
]

_RATING_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
}


class BooksScraper(BaseSeleniumScraper):
    """Scraper réutilisable du catalogue et des fiches Books to Scrape."""

    catalogue_url = "https://books.toscrape.com/catalogue/page-{page}.html"

    def scrape(self, max_pages: int | None = None) -> list[dict[str, Any]]:
        """Collecte les livres de la première à la dernière page.

        Args:
            max_pages: Limite optionnelle utile pour un aperçu. ``None`` suit
                la pagination jusqu'à sa fin.

        Returns:
            Une liste de dictionnaires bruts, un par livre.
        """

        if max_pages is not None and max_pages < 1:
            raise ValueError("max_pages doit être positif ou None")

        records: list[dict[str, Any]] = []
        visited_urls: set[str] = set()
        page = 1

        while max_pages is None or page <= max_pages:
            page_url = self.catalogue_url.format(page=page)
            try:
                # Le DOM complet est attendu; l'absence de carte sert de signal
                # de fin sans imposer un timeout sur une page hors catalogue.
                self._get_with_retry(page_url)
            except ScraperLoadError:
                if page == 1:
                    raise
                LOGGER.warning("Arrêt du catalogue après l'échec de la page %s", page)
                break

            cards = self._find_all(self.driver, (CSS, "article.product_pod"))
            if not cards:
                LOGGER.info("Aucun livre sur la page %s; fin de pagination", page)
                break

            products_on_page = len(cards)
            has_next = bool(
                self._find_all(self.driver, (CSS, "li.next a"))
                or self._find_all(self.driver, (CSS, ".pager .next a"))
            )
            snapshots = [
                self._extract_card(card, page, products_on_page) for card in cards
            ]

            for snapshot in snapshots:
                url = str(snapshot.get("url") or "").strip()
                if url and url in visited_urls:
                    continue
                if url:
                    visited_urls.add(url)
                records.append(self._extract_product(snapshot))

            if not has_next:
                break
            page += 1

        return self._deduplicate(
            records,
            fallback_keys=("title", "price"),
        )

    def scrape_to_dataframe(self, max_pages: int | None = None) -> pd.DataFrame:
        """Retourne les données brutes dans l'ordre stable des colonnes."""

        return pd.DataFrame(self.scrape(max_pages=max_pages), columns=BOOK_COLUMNS)

    def _extract_card(
        self,
        card: Any,
        source_page: int,
        products_on_page: int,
    ) -> dict[str, Any]:
        link = self._find_first(
            card,
            ((CSS, "h3 a[title]"), (CSS, "h3 a"), (CSS, "a[href]")),
        )
        url = link.get_attribute("href") if link is not None else None
        title = None
        if link is not None:
            title = link.get_attribute("title") or " ".join((link.text or "").split())

        rating_element = self._find_first(card, ((CSS, ".star-rating"),))
        return {
            "title": title,
            "price": self._text_first(card, ((CSS, ".price_color"),)),
            "availability": self._text_first(
                card,
                ((CSS, ".availability"), (CSS, ".instock")),
            ),
            "products_on_page": products_on_page,
            "rating": self._rating_from_element(rating_element),
            "review_count": None,
            "description": None,
            "product_type": None,
            "tax": None,
            "category": None,
            "url": url,
            "source_page": source_page,
        }

    def _extract_product(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        """Complète une carte depuis sa fiche, avec repli sur la carte."""

        record = dict(snapshot)
        url = record.get("url")
        if not url:
            LOGGER.warning("Livre sans URL détail: %s", record.get("title"))
            return record

        try:
            self._get_with_retry(
                str(url),
                ready_selectors=((CSS, "article.product_page"), (CSS, ".product_main")),
            )
            record["title"] = self._text_first(
                self.driver,
                ((CSS, ".product_main h1"), (CSS, "article.product_page h1")),
                default=record.get("title"),
            )
            record["price"] = self._text_first(
                self.driver,
                ((CSS, ".product_main .price_color"), (CSS, ".price_color")),
                default=record.get("price"),
            )
            record["availability"] = self._text_first(
                self.driver,
                (
                    (CSS, ".product_main .availability"),
                    (CSS, ".product_main .instock"),
                ),
                default=record.get("availability"),
            )

            rating_element = self._find_first(
                self.driver,
                ((CSS, ".product_main .star-rating"), (CSS, ".star-rating")),
            )
            detail_rating = self._rating_from_element(rating_element)
            if detail_rating is not None:
                record["rating"] = detail_rating

            record["description"] = self._text_first(
                self.driver,
                ((CSS, "#product_description + p"), (CSS, ".product_page > p")),
            )
            if not record["description"]:
                record["description"] = self._attribute_first(
                    self.driver,
                    ((CSS, "meta[name='description']"),),
                    "content",
                )

            information = self._extract_information_table()
            record["product_type"] = information.get("product type")
            record["tax"] = information.get("tax")
            record["review_count"] = information.get("number of reviews")
            if not record.get("availability"):
                record["availability"] = information.get("availability")
            record["category"] = self._extract_category()
        except (ScraperLoadError, WebDriverException):
            LOGGER.warning(
                "Fiche produit indisponible; valeurs de la carte conservées: %s",
                url,
                exc_info=True,
            )
        return record

    def _extract_information_table(self) -> dict[str, str]:
        information: dict[str, str] = {}
        rows = self._find_all(self.driver, (CSS, "table.table-striped tr"))
        if not rows:
            rows = self._find_all(self.driver, (CSS, ".product_page table tr"))
        for row in rows:
            heading = self._text_first(row, ((CSS, "th"),))
            value = self._text_first(row, ((CSS, "td"),))
            if heading and value is not None:
                information[heading.strip().casefold()] = value
        return information

    def _extract_category(self) -> str | None:
        # Home > Books > Catégorie > Produit : le dernier lien est la catégorie.
        links = self._find_all(self.driver, (CSS, "ul.breadcrumb li a"))
        values = [" ".join((link.text or "").split()) for link in links]
        values = [value for value in values if value]
        return values[-1] if values else None

    @staticmethod
    def _rating_from_element(element: Any | None) -> int | None:
        if element is None:
            return None
        class_names = str(element.get_attribute("class") or "").split()
        for class_name in class_names:
            rating = _RATING_WORDS.get(class_name.casefold())
            if rating is not None:
                return rating
        for attribute in ("aria-label", "title"):
            value = str(element.get_attribute(attribute) or "").casefold()
            for word, rating in _RATING_WORDS.items():
                if word in value:
                    return rating
        return None


def scrape_books(
    max_pages: int | None = None,
    output_path: str | Path | None = None,
    driver: Any | None = None,
    *,
    headless: bool = True,
    timeout: float = 15,
    retries: int = 3,
) -> pd.DataFrame:
    """Fonction simple pour Streamlit/scripts; renvoie le brut Selenium."""

    with BooksScraper(
        driver=driver,
        headless=headless,
        timeout=timeout,
        retries=retries,
    ) as scraper:
        frame = scraper.scrape_to_dataframe(max_pages=max_pages)
        if output_path is not None:
            scraper.save_csv(frame, output_path)
        return frame


__all__ = ["BOOK_COLUMNS", "BooksScraper", "scrape_books"]
