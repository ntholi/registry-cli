from typing import Any, Dict, List

from bs4 import Tag
from bs4.element import NavigableString

from registry_cli.scrapers.base import BaseScraper


class ProgramStructureScraper(BaseScraper):
    """Scraper for program structure information."""

    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape program structure data from the URL.

        Returns:
            List of dictionaries containing program structure data with keys:
            - id: Structure ID
            - code: Structure code
        """
        soup = self._get_soup()
        structures = []

        table: Tag | NavigableString | None = soup.find("table", {"id": "ewlistmain"})
        if not table or isinstance(table, NavigableString):
            return structures

        for row in table.find_all("tr", {"class": ["ewTableRow", "ewTableAltRow"]}):
            cells = row.find_all("td")
            if len(cells) < 6:  # Skip rows without enough cells
                continue

            code = cells[0].get_text(strip=True)

            view_link = cells[5].find("a")
            if not view_link:
                continue

            structure_id = view_link["href"].split("StructureID=")[-1]
            structures.append({"id": structure_id, "code": code})

        return structures
