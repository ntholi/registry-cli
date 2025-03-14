from abc import ABC, abstractmethod
from typing import Any, Dict, List

from bs4 import BeautifulSoup, Comment

from registry_cli.browser import Browser


class BaseScraper(ABC):
    """Base class for all scrapers."""

    def __init__(self, url: str):
        self.url = url
        self.browser = Browser()

    def _get_soup(self) -> BeautifulSoup:
        """Get BeautifulSoup object from URL."""
        response = self.browser.fetch(self.url)
        soup = BeautifulSoup(response.text, "lxml")
        # Remove all HTML comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        return soup

    @abstractmethod
    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape data from the URL.

        Returns:
            List of dictionaries containing scraped data.
        """
        pass
