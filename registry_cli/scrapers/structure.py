from typing import Any, Dict, List

from bs4 import Tag
from bs4.element import NavigableString

from registry_cli.models.structure import ModuleType
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


class SemesterScraper(BaseScraper):
    """Scraper for semester information within a program structure."""

    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape semester data from the URL.

        Returns:
            List of dictionaries containing semester data with keys:
            - id: Semester ID
            - year: Year number (extracted from semester code)
            - semester_number: Semester number within the year
            - total_credits: Total credits for the semester
        """
        soup = self._get_soup()
        semesters = []

        table: Tag | NavigableString | None = soup.find("table", {"id": "ewlistmain"})
        if not table or isinstance(table, NavigableString):
            return semesters

        for row in table.find_all("tr", {"class": ["ewTableRow", "ewTableAltRow"]}):
            cells = row.find_all("td")
            if len(cells) < 7:  # Skip rows without enough cells
                continue

            semester_code = cells[0].get_text(strip=True)
            credits_text = cells[1].get_text(strip=True).replace(",", "")
            try:
                credits = float(credits_text) if credits_text else 0.0
            except ValueError:
                credits = 0.0

            # Extract semester ID from the view link
            view_link = cells[4].find("a")
            if not view_link:
                continue
            semester_id = view_link["href"].split("SemesterID=")[-1]

            # Parse semester code to extract year and semester number
            # Example: "01 Year 1 Sem 1" -> year=1, semester_number=1
            # Example: "B1 Bridging Semester 1" -> year=0, semester_number=1
            # Example: "F1 Foundation Semester 1" -> year=0, semester_number=1
            parts = semester_code.split()

            if semester_code.startswith(("B", "F")):
                year = 0  # Special case for Bridging and Foundation
            else:
                # Find the year number in the parts
                for part in parts:
                    if part.isdigit():
                        year = int(part)
                        break
                else:
                    year = 0

            # Get the last number in the code as semester number
            for part in reversed(parts):
                if part.isdigit():
                    semester_number = int(part)
                    break
            else:
                semester_number = 0

            semesters.append(
                {
                    "id": int(semester_id),
                    "year": year,
                    "semester_number": semester_number,
                    "total_credits": credits,
                }
            )

        return semesters


class SemesterModuleScraper(BaseScraper):
    """Scraper for module information within a semester."""

    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape module data from the URL.

        Returns:
            List of dictionaries containing module data with keys:
            - id: Module ID (extracted from view link)
            - code: Module code (e.g. DDC112)
            - name: Module name (e.g. Creative and Innovation Studies)
            - type: Module type (Core, Major, Minor)
            - credits: Module credits
        """
        soup = self._get_soup()
        modules = []

        table: Tag | NavigableString | None = soup.find("table", {"id": "ewlistmain"})
        if not table or isinstance(table, NavigableString):
            return modules

        for row in table.find_all("tr", {"class": ["ewTableRow", "ewTableAltRow"]}):
            cells = row.find_all("td")
            if len(cells) < 7:  # Skip rows without enough cells
                continue

            # Parse module code and name
            # Format: "DDC112 Creative and Innovation Studies"
            module_text = cells[0].get_text(strip=True)
            code_end = module_text.find(" ")
            if code_end == -1:
                continue

            code = module_text[:code_end]
            name = module_text[code_end + 1 :]

            # Get module type
            type_text = cells[1].get_text(strip=True)
            try:
                module_type = ModuleType(type_text)
            except ValueError:
                module_type = ModuleType.Core

            # Get credits
            credits_text = cells[3].get_text(strip=True).replace(",", "")
            try:
                credits = float(credits_text) if credits_text else 0.0
            except ValueError:
                credits = 0.0

            # Get module ID from view link
            view_link = cells[5].find("a")
            if not view_link:
                continue
            module_id = view_link["href"].split("SemModuleID=")[-1]

            modules.append(
                {
                    "id": int(module_id),
                    "code": code,
                    "name": name,
                    "type": module_type,
                    "credits": credits,
                }
            )

        return modules
