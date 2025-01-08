from abc import ABC, abstractmethod
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from registry_cli.browser import Browser


class BaseScraper(ABC):
    """Base class for all scrapers."""

    def __init__(self, url: str):
        self.url = url
        self.browser = Browser()

    def _get_soup(self) -> BeautifulSoup:
        """Get BeautifulSoup object from URL."""
        response = self.browser.fetch(self.url)
        return BeautifulSoup(response.text, "lxml")

    @abstractmethod
    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape data from the URL.

        Returns:
            List of dictionaries containing scraped data.
        """
        pass
