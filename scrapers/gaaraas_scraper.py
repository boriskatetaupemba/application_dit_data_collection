"""Collecte Selenium des annonces automobiles du vendeur Dakar auto.

Le cahier des charges fixe une plage de 100 pages. Le profil public ne montre
actuellement que 13 pages; par défaut le scraper arrête donc les requêtes dès
qu'une page est vide ou répète la précédente. ``strict_pages=True`` force la
tentative de chaque numéro jusqu'à ``max_pages``.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import pandas as pd

from .base import BaseSeleniumScraper, CSS, ScraperLoadError

LOGGER = logging.getLogger(__name__)

GAARAAS_COLUMNS = [
    "brand",
    "model",
    "year",
    "price",
    "mileage",
    "transmission",
    "region",
    "url",
    "source_page",
]

_CARD_SELECTORS = (
    (CSS, "a.common-ad-card[href*='/vehicle_listings/']"),
    (CSS, "a.common-ad-card[href*='vehicle']"),
    (CSS, "a.common-ad-card"),
    (CSS, ".common-ad-card"),
)

# Les marques composées doivent être reconnues avant le repli "premier mot".
_MULTIWORD_BRANDS = tuple(
    sorted(
        {
            "Alfa Romeo",
            "Aston Martin",
            "Great Wall",
            "Land Rover",
            "Mercedes Benz",
            "Mercedes-Benz",
            "Rolls Royce",
            "Rolls-Royce",
            "Ssang Yong",
        },
        key=len,
        reverse=True,
    )
)


class GaaraasScraper(BaseSeleniumScraper):
    """Scraper Selenium des cartes d'annonces Gaaraas, pages 1 à 100."""

    page_url = "https://www.gaaraas.com/fr/users/dakar-auto?page={page}"

    def scrape(
        self,
        max_pages: int = 100,
        *,
        strict_pages: bool = False,
    ) -> list[dict[str, Any]]:
        """Collecte V1 à V7 et déduplique les annonces par URL.

        Args:
            max_pages: Dernier numéro de page à envisager, 100 par défaut.
            strict_pages: Si vrai, tente tous les numéros même après une page
                vide/répétée. Le mode par défaut évite 87 chargements inutiles
                lorsque le site ne publie que 13 pages.
        """

        if max_pages < 1:
            raise ValueError("max_pages doit être strictement positif")

        records: list[dict[str, Any]] = []
        seen_page_signatures: set[tuple[str, ...]] = set()

        for page in range(1, max_pages + 1):
            url = self.page_url.format(page=page)
            try:
                self._get_with_retry(url)
            except ScraperLoadError:
                if page == 1:
                    raise
                LOGGER.warning("Page Gaaraas %s indisponible", page)
                if strict_pages:
                    continue
                break

            cards = self._find_cards()
            if not cards:
                LOGGER.info("Page Gaaraas %s vide", page)
                if strict_pages:
                    continue
                break

            page_records = [self._extract_card(card, page) for card in cards]
            signature = tuple(
                sorted(
                    str(record.get("url") or record.get("_heading") or "")
                    for record in page_records
                )
            )
            if signature in seen_page_signatures:
                LOGGER.info(
                    "Page Gaaraas %s identique à une page déjà vue; arrêt sûr",
                    page,
                )
                if strict_pages:
                    continue
                break
            seen_page_signatures.add(signature)

            for record in page_records:
                record.pop("_heading", None)
                records.append(record)

        return self._deduplicate(
            records,
            fallback_keys=("brand", "model", "year", "price", "mileage"),
        )

    def scrape_to_dataframe(
        self,
        max_pages: int = 100,
        *,
        strict_pages: bool = False,
    ) -> pd.DataFrame:
        """Retourne les données brutes dans l'ordre stable des colonnes."""

        return pd.DataFrame(
            self.scrape(max_pages=max_pages, strict_pages=strict_pages),
            columns=GAARAAS_COLUMNS,
        )

    def _find_cards(self) -> list[Any]:
        for selector in _CARD_SELECTORS:
            cards = self._find_all(self.driver, selector)
            if cards:
                return cards
        return []

    def _extract_card(self, card: Any, source_page: int) -> dict[str, Any]:
        heading_element = self._find_first(
            card,
            ((CSS, "h4[title]"), (CSS, ".ad-specification h4"), (CSS, "h4")),
        )
        heading = None
        if heading_element is not None:
            heading = heading_element.get_attribute("title") or heading_element.text
            heading = " ".join((heading or "").split()) or None
        year, brand, model = self.parse_vehicle_heading(heading)

        href = card.get_attribute("href")
        if not href:
            href = self._attribute_first(
                card,
                ((CSS, "a[href*='/vehicle_listings/']"), (CSS, "a[href]")),
                "href",
            )

        transmission = self._text_first(
            card,
            (
                (CSS, ".ad-vehicle-engine .transmission span:last-child"),
                (CSS, ".transmission span:last-child"),
                (CSS, ".transmission span"),
                (CSS, ".transmission"),
            ),
        )

        return {
            "brand": brand,
            "model": model,
            "year": year,
            "price": self._text_first(
                card,
                (
                    (CSS, ".ad-vehicle-price .price"),
                    (CSS, ".ad-vehicle-price .value"),
                    (CSS, ".price-wrap .price"),
                ),
            ),
            "mileage": self._text_first(
                card,
                (
                    (CSS, ".ad-vehicle-mileage .value"),
                    (CSS, "[class*='mileage'] .value"),
                    (CSS, ".ad-vehicle-mileage"),
                ),
            ),
            "transmission": transmission,
            "region": self._text_first(
                card,
                (
                    (CSS, ".ad-specification .location"),
                    (CSS, ".specification-section .location"),
                    (CSS, ".location"),
                ),
            ),
            "url": href,
            "source_page": source_page,
            "_heading": heading,
        }

    @staticmethod
    def parse_vehicle_heading(
        heading: str | None,
    ) -> tuple[str | None, str | None, str | None]:
        """Sépare ``2011 Land Rover Range Rover`` en année, marque, modèle."""

        if not heading:
            return None, None, None
        normalized = " ".join(str(heading).split())
        year_match = re.search(r"\b(?:19|20)\d{2}\b", normalized)
        year = year_match.group(0) if year_match else None
        vehicle_name = normalized
        if year_match:
            vehicle_name = (
                normalized[: year_match.start()] + " " + normalized[year_match.end() :]
            )
            vehicle_name = " ".join(vehicle_name.split())
        if not vehicle_name:
            return year, None, None

        folded_name = vehicle_name.casefold()
        for known_brand in _MULTIWORD_BRANDS:
            folded_brand = known_brand.casefold()
            if folded_name == folded_brand or folded_name.startswith(folded_brand + " "):
                model = vehicle_name[len(known_brand) :].strip() or None
                return year, vehicle_name[: len(known_brand)], model

        parts = vehicle_name.split(maxsplit=1)
        brand = parts[0] if parts else None
        model = parts[1] if len(parts) == 2 else None
        return year, brand, model


def scrape_gaaraas(
    max_pages: int = 100,
    output_path: str | Path | None = None,
    driver: Any | None = None,
    *,
    headless: bool = True,
    timeout: float = 15,
    retries: int = 3,
    strict_pages: bool = False,
) -> pd.DataFrame:
    """Fonction simple pour Streamlit/scripts; renvoie le brut Selenium."""

    with GaaraasScraper(
        driver=driver,
        headless=headless,
        timeout=timeout,
        retries=retries,
    ) as scraper:
        frame = scraper.scrape_to_dataframe(
            max_pages=max_pages,
            strict_pages=strict_pages,
        )
        if output_path is not None:
            scraper.save_csv(frame, output_path)
        return frame


__all__ = ["GAARAAS_COLUMNS", "GaaraasScraper", "scrape_gaaraas"]
