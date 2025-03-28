from typing import Any, Dict, List

from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString

from registry_cli.scrapers.base import BaseScraper


class ProgramScraper(BaseScraper):
    """Scraper for program information."""

    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape program data from the URL.

        Returns:
            List of dictionaries containing program data with keys:
            - code: Program code
            - name: Program name
            - program_id: Program ID
        """
        soup = self._get_soup()
        programs = []

        table: Tag | NavigableString | None = soup.find("table", {"id": "ewlistmain"})
        if not table or isinstance(table, NavigableString):
            return programs

        for row in table.find_all("tr", {"class": ["ewTableRow", "ewTableAltRow"]}):
            cells = row.find_all("td")
            if len(cells) < 4:  # Skip rows without enough cells
                continue

            code = cells[0].get_text(strip=True)
            name = cells[1].get_text(strip=True)

            view_link = cells[3].find("a")
            if not view_link:
                continue

            program_id = view_link["href"].split("ProgramID=")[-1]
            programs.append({"code": code, "name": name, "program_id": program_id})

        return programs
