"""Scrapers Selenium des deux sources du projet."""

from .books_scraper import BooksScraper, scrape_books
from .gaaraas_scraper import GaaraasScraper, scrape_gaaraas

__all__ = [
    "BooksScraper",
    "GaaraasScraper",
    "scrape_books",
    "scrape_gaaraas",
]
