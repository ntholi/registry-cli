from typing import Any, Dict, List

from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString

from registry_cli.scrapers.base import BaseScraper


class SchoolScraper(BaseScraper):
    """Scraper for school information."""

    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape school data from the URL.

        Returns:
            List of dictionaries containing school data with keys:
            - code: School code
            - name: School name
            - school_id: School ID
        """
        soup = self._get_soup()
        schools = []

        table: Tag | NavigableString | None = soup.find("table", {"id": "ewlistmain"})
        if not table or isinstance(table, NavigableString):
            return schools

        for row in table.find_all("tr", {"class": ["ewTableRow", "ewTableAltRow"]}):
            cells = row.find_all("td")
            if len(cells) < 4:  # Skip rows without enough cells
                continue

            code = cells[0].get_text(strip=True)
            name = cells[1].get_text(strip=True)

            view_link = cells[3].find("a")
            if not view_link:
                continue

            school_id = view_link["href"].split("SchoolID=")[-1]
            schools.append({"code": code, "name": name, "school_id": school_id})

        return schools
