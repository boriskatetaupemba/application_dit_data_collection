"""Tests unitaires Selenium via driver injecté; aucun navigateur ni réseau."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd
from selenium.common.exceptions import WebDriverException

from scrapers.books_scraper import BooksScraper
from scrapers.gaaraas_scraper import GaaraasScraper


class FakeElement:
    def __init__(
        self,
        text: str = "",
        *,
        attributes: Mapping[str, Any] | None = None,
        children: Mapping[str, list["FakeElement"]] | None = None,
    ) -> None:
        self.text = text
        self.attributes = dict(attributes or {})
        self.children = dict(children or {})

    def find_elements(self, _by: str, selector: str) -> list["FakeElement"]:
        return list(self.children.get(selector, []))

    def get_attribute(self, name: str) -> Any:
        return self.attributes.get(name)


class FakeDriver:
    def __init__(
        self,
        pages: Mapping[str, FakeElement],
        *,
        failures: Mapping[str, int] | None = None,
    ) -> None:
        self.pages = dict(pages)
        self.failures = dict(failures or {})
        self.root = FakeElement()
        self.calls: list[str] = []
        self.quit_called = False
        self.page_load_timeout: float | None = None

    def set_page_load_timeout(self, timeout: float) -> None:
        self.page_load_timeout = timeout

    def get(self, url: str) -> None:
        self.calls.append(url)
        if self.failures.get(url, 0) > 0:
            self.failures[url] -= 1
            raise WebDriverException("temporary failure")
        self.root = self.pages[url]

    def execute_script(self, _script: str) -> str:
        return "complete"

    def find_elements(self, by: str, selector: str) -> list[FakeElement]:
        return self.root.find_elements(by, selector)

    def quit(self) -> None:
        self.quit_called = True


def _table_row(key: str, value: str) -> FakeElement:
    return FakeElement(
        children={
            "th": [FakeElement(key)],
            "td": [FakeElement(value)],
        }
    )


def test_books_scraper_follows_detail_retries_and_deduplicates(tmp_path: Path) -> None:
    catalogue_url = BooksScraper.catalogue_url.format(page=1)
    detail_url = "https://books.toscrape.test/catalogue/book_1/index.html"
    link = FakeElement("Book", attributes={"href": detail_url, "title": "Card title"})
    card = FakeElement(
        children={
            "h3 a[title]": [link],
            ".price_color": [FakeElement("£12.34")],
            ".availability": [FakeElement("In stock")],
            ".star-rating": [FakeElement(attributes={"class": "star-rating Two"})],
        }
    )
    catalogue = FakeElement(children={"article.product_pod": [card, card]})
    details = FakeElement(
        children={
            "article.product_page": [FakeElement()],
            ".product_main h1": [FakeElement("Complete title")],
            ".product_main .price_color": [FakeElement("£12.34")],
            ".product_main .availability": [FakeElement("In stock (4 available)")],
            ".product_main .star-rating": [
                FakeElement(attributes={"class": "star-rating Four"})
            ],
            "#product_description + p": [FakeElement("Full description")],
            "table.table-striped tr": [
                _table_row("Product Type", "Books"),
                _table_row("Tax", "£0.00"),
                _table_row("Number of reviews", "7"),
            ],
            "ul.breadcrumb li a": [
                FakeElement("Home"),
                FakeElement("Books"),
                FakeElement("Poetry"),
            ],
        }
    )
    driver = FakeDriver(
        {catalogue_url: catalogue, detail_url: details},
        failures={detail_url: 1},
    )

    with BooksScraper(driver=driver, timeout=0.1, retries=2, retry_backoff=0) as scraper:
        rows = scraper.scrape(max_pages=1)
        destination = scraper.save_csv(rows, tmp_path / "books.csv")

    assert not driver.quit_called  # un driver injecté appartient à l'appelant
    assert driver.calls == [catalogue_url, detail_url, detail_url]
    assert len(rows) == 1
    assert rows[0]["title"] == "Complete title"
    assert rows[0]["products_on_page"] == 2
    assert rows[0]["rating"] == 4
    assert rows[0]["review_count"] == "7"
    assert rows[0]["product_type"] == "Books"
    assert rows[0]["category"] == "Poetry"
    assert destination.exists()
    assert pd.read_csv(destination).loc[0, "title"] == "Complete title"


def _gaaraas_card(url: str) -> FakeElement:
    return FakeElement(
        attributes={"href": url},
        children={
            "h4[title]": [
                FakeElement(
                    "2018 Land Rover Range Rover Sport",
                    attributes={"title": "2018 Land Rover Range Rover Sport"},
                )
            ],
            ".ad-vehicle-price .price": [FakeElement("18 500 000")],
            ".ad-vehicle-mileage .value": [FakeElement("95 000 km")],
            ".ad-vehicle-engine .transmission span:last-child": [
                FakeElement("Automatique")
            ],
            ".ad-specification .location": [FakeElement("Dakar")],
        },
    )


def test_gaaraas_scraper_stops_on_repeated_page_and_parses_multiword_brand() -> None:
    page_1 = GaaraasScraper.page_url.format(page=1)
    page_2 = GaaraasScraper.page_url.format(page=2)
    listing_url = "https://www.gaaraas.com/fr/vehicle_listings/car-42"
    repeated_card = _gaaraas_card(listing_url)
    pages = {
        page_1: FakeElement(
            children={"a.common-ad-card[href*='/vehicle_listings/']": [repeated_card]}
        ),
        page_2: FakeElement(
            children={"a.common-ad-card[href*='/vehicle_listings/']": [repeated_card]}
        ),
    }
    driver = FakeDriver(pages)

    scraper = GaaraasScraper(driver=driver, timeout=0.1, retry_backoff=0)
    rows = scraper.scrape(max_pages=100)

    assert driver.calls == [page_1, page_2]
    assert len(rows) == 1
    assert rows[0] == {
        "brand": "Land Rover",
        "model": "Range Rover Sport",
        "year": "2018",
        "price": "18 500 000",
        "mileage": "95 000 km",
        "transmission": "Automatique",
        "region": "Dakar",
        "url": listing_url,
        "source_page": 1,
    }


def test_gaaraas_strict_mode_attempts_pages_after_an_empty_page() -> None:
    page_1 = GaaraasScraper.page_url.format(page=1)
    page_2 = GaaraasScraper.page_url.format(page=2)
    page_3 = GaaraasScraper.page_url.format(page=3)
    card = _gaaraas_card("https://www.gaaraas.com/fr/vehicle_listings/car-1")
    driver = FakeDriver(
        {
            page_1: FakeElement(
                children={"a.common-ad-card[href*='/vehicle_listings/']": [card]}
            ),
            page_2: FakeElement(),
            page_3: FakeElement(),
        }
    )

    scraper = GaaraasScraper(driver=driver, timeout=0.1, retry_backoff=0)
    rows = scraper.scrape(max_pages=3, strict_pages=True)

    assert len(rows) == 1
    assert driver.calls == [page_1, page_2, page_3]
