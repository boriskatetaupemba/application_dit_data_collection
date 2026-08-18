"""Outils communs aux scrapers Selenium.

Ce module ne fait aucune analyse HTML hors du DOM exposé par Selenium. Le
driver peut être fourni par l'appelant, ce qui permet d'utiliser un navigateur
déjà configuré et de tester les scrapers sans lancer Chrome.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

LOGGER = logging.getLogger(__name__)

Selector = tuple[str, str]


class ScraperLoadError(RuntimeError):
    """Signale qu'une page n'a pas pu être chargée après les retries."""


class BaseSeleniumScraper:
    """Base légère fournissant driver, attentes, retries et export CSV."""

    def __init__(
        self,
        driver: WebDriver | Any | None = None,
        *,
        headless: bool = True,
        timeout: float = 15,
        retries: int = 3,
        retry_backoff: float = 0.75,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout doit être strictement positif")
        if retries < 1:
            raise ValueError("retries doit être supérieur ou égal à 1")
        if retry_backoff < 0:
            raise ValueError("retry_backoff ne peut pas être négatif")

        self.timeout = timeout
        self.retries = retries
        self.retry_backoff = retry_backoff
        self._owns_driver = driver is None
        self.driver = driver if driver is not None else self._create_driver(headless)

        if hasattr(self.driver, "set_page_load_timeout"):
            try:
                self.driver.set_page_load_timeout(timeout)
            except WebDriverException:
                LOGGER.debug("Le driver n'accepte pas set_page_load_timeout", exc_info=True)

    @staticmethod
    def _create_driver(headless: bool) -> WebDriver:
        """Crée Chrome via Selenium Manager, sans dépendance à chromedriver local."""

        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--lang=fr-FR")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
        )
        # Le DOM utile est rendu côté serveur sur les deux sources. Attendre
        # ``interactive`` évite que publicités/images tierces bloquent inutilement
        # le chargement, puis ``_get_with_retry`` vérifie explicitement le DOM.
        options.page_load_strategy = "eager"
        return webdriver.Chrome(options=options)

    def __enter__(self) -> "BaseSeleniumScraper":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        """Ferme uniquement le driver créé par cette instance.

        Un driver injecté reste sous la responsabilité de l'appelant.
        """

        if self._owns_driver and self.driver is not None:
            try:
                self.driver.quit()
            except WebDriverException:
                LOGGER.debug("Erreur ignorée pendant la fermeture du driver", exc_info=True)
            finally:
                self.driver = None

    def _get_with_retry(
        self,
        url: str,
        *,
        ready_selectors: Sequence[Selector] | None = None,
    ) -> None:
        """Charge ``url`` et attend le DOM, avec retry exponentiel borné."""

        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                self.driver.get(url)
                WebDriverWait(self.driver, self.timeout).until(
                    lambda current_driver: current_driver.execute_script(
                        "return document.readyState"
                    )
                    in {"interactive", "complete"}
                )
                if ready_selectors:
                    WebDriverWait(self.driver, self.timeout).until(
                        lambda current_driver: any(
                            self._find_all(current_driver, selector)
                            for selector in ready_selectors
                        )
                    )
                return
            except (TimeoutException, WebDriverException) as error:
                last_error = error
                LOGGER.warning(
                    "Chargement %s impossible (tentative %s/%s): %s",
                    url,
                    attempt,
                    self.retries,
                    error,
                )
                if attempt < self.retries and self.retry_backoff:
                    time.sleep(self.retry_backoff * (2 ** (attempt - 1)))

        raise ScraperLoadError(
            f"Impossible de charger {url!r} après {self.retries} tentative(s)"
        ) from last_error

    @staticmethod
    def _find_all(root: Any, selector: Selector) -> list[Any]:
        try:
            return list(root.find_elements(*selector))
        except (NoSuchElementException, StaleElementReferenceException):
            return []

    @classmethod
    def _find_first(
        cls,
        root: Any,
        selectors: Sequence[Selector],
    ) -> Any | None:
        for selector in selectors:
            elements = cls._find_all(root, selector)
            if elements:
                return elements[0]
        return None

    @classmethod
    def _text_first(
        cls,
        root: Any,
        selectors: Sequence[Selector],
        *,
        default: str | None = None,
    ) -> str | None:
        for selector in selectors:
            for element in cls._find_all(root, selector):
                text = " ".join((element.text or "").split())
                if text:
                    return text
        return default

    @classmethod
    def _attribute_first(
        cls,
        root: Any,
        selectors: Sequence[Selector],
        attribute: str,
        *,
        default: str | None = None,
    ) -> str | None:
        for selector in selectors:
            for element in cls._find_all(root, selector):
                value = element.get_attribute(attribute)
                if value is not None and str(value).strip():
                    return str(value).strip()
        return default

    @staticmethod
    def _deduplicate(
        records: Iterable[Mapping[str, Any]],
        *,
        preferred_key: str = "url",
        fallback_keys: Sequence[str] = (),
    ) -> list[dict[str, Any]]:
        """Déduplique en conservant l'ordre et la première occurrence."""

        unique: list[dict[str, Any]] = []
        seen: set[tuple[Any, ...]] = set()
        for record in records:
            copied = dict(record)
            preferred_value = copied.get(preferred_key)
            if preferred_value:
                key = (preferred_key, str(preferred_value).strip())
            else:
                key = tuple(copied.get(field) for field in fallback_keys)
            if key in seen:
                continue
            seen.add(key)
            unique.append(copied)
        return unique

    @staticmethod
    def save_csv(
        rows: pd.DataFrame | Iterable[Mapping[str, Any]],
        path: str | Path,
    ) -> Path:
        """Enregistre les lignes en CSV UTF-8 avec BOM, compatible avec Excel."""

        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        frame = rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
        frame.to_csv(destination, index=False, encoding="utf-8-sig")
        return destination


CSS = By.CSS_SELECTOR

__all__ = ["BaseSeleniumScraper", "CSS", "ScraperLoadError", "Selector"]
