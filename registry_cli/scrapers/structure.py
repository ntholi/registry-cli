from typing import Any, Dict, List

from bs4 import Comment, Tag
from bs4.element import NavigableString

from registry_cli.browser import BASE_URL
from registry_cli.models import ModuleType
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
            if len(cells) < 6:
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

            semester = cells[0].get_text(strip=True)
            credits_text = cells[1].get_text(strip=True).replace(",", "")
            try:
                credits = float(credits_text) if credits_text else 0.0
            except ValueError:
                credits = 0.0

            view_link = cells[4].find("a")
            if not view_link:
                continue
            semester_id = view_link["href"].split("SemesterID=")[-1]

            parts: List[str] = semester.split()

            if semester.startswith(("B", "F")):
                semester_number = 0
            else:
                if len(parts) >= 2 and parts[0].isdigit():
                    semester_number = int(parts[0])
                else:
                    semester_number = 0

            name = " ".join(parts[1:])

            semesters.append(
                {
                    "id": int(semester_id),
                    "semester_number": semester_number,
                    "name": name,
                    "total_credits": credits,
                }
            )

        return semesters


class SemesterModuleScraper(BaseScraper):
    """Scraper for module information within a semester."""

    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape module data from all pages of the URL.

        Returns:
            List of dictionaries containing module data with keys:
            - id: Module ID (extracted from view link)
            - code: Module code (e.g. DDC112)
            - name: Module name (e.g. Creative and Innovation Studies)
            - type: Module type (Core, Major, Minor)
            - credits: Module credits
            - prerequisite: Module prerequisite code (if any)
        """
        all_modules = []
        current_url = self.url

        while True:
            soup = self._get_soup()
            modules = self._scrape_page(soup)
            all_modules.extend(modules)

            # Check for next page link
            next_link = None
            pager_form = soup.find("form", {"name": "ewpagerform"})
            if pager_form and isinstance(pager_form, Tag):
                links = pager_form.find_all("a")
                for link in links:
                    if link.get_text(strip=True) == "Next":
                        next_link = link["href"]
                        break

            if not next_link:
                break  # Update URL for next page
            if next_link.startswith("/"):
                self.url = f"{BASE_URL}{next_link}"
            else:
                base_path = "/".join(current_url.split("/")[:-1])
                self.url = f"{base_path}/{next_link}"

        return all_modules

    def _parse_module_code_and_name(self, module_text: str) -> tuple[str, str]:
        parts = module_text.split()
        if len(parts) < 2:
            return module_text, ""

        code_parts = []
        name_parts = []

        for i, part in enumerate(parts):
            if not name_parts:
                if (
                    part.isalpha()
                    or part.isdigit()
                    or (
                        any(c.isdigit() for c in part)
                        and any(c.isalpha() for c in part)
                        and part.isalnum()
                    )
                ):
                    code_parts.append(part)
                    if i + 1 < len(parts):
                        next_part = parts[i + 1]
                        if (
                            len(next_part) >= 4 and next_part.isalpha()
                        ) or next_part.startswith("&"):
                            name_parts.extend(parts[i + 1 :])
                            break
                else:
                    name_parts.extend(parts[i:])
                    break

        if not name_parts:
            if len(parts) >= 3:
                code_parts = parts[:2]
                name_parts = parts[2:]
            else:
                code_parts = [parts[0]]
                name_parts = parts[1:]

        code = " ".join(code_parts)
        name = " ".join(name_parts)

        return code, name

    def _scrape_page(self, soup) -> List[Dict[str, Any]]:
        """Scrape module data from a single page."""
        modules = []
        table: Tag | NavigableString | None = soup.find("table", {"id": "ewlistmain"})
        if not table or isinstance(table, NavigableString):
            return modules

        for row in table.find_all("tr", {"class": ["ewTableRow", "ewTableAltRow"]}):
            cells = row.find_all("td")
            if len(cells) < 7:
                continue

            module_text = cells[0].get_text(strip=True)
            if not module_text:
                continue

            code, name = self._parse_module_code_and_name(module_text)

            # Get module type
            type_text = cells[1].get_text(strip=True)
            try:
                module_type: ModuleType = type_text
            except ValueError:
                module_type = "Core"

            if type_text == "Delete":
                continue

            # Get credits
            credits_text = cells[3].get_text(strip=True).replace(",", "")
            try:
                credits = float(credits_text) if credits_text else 0.0
            except ValueError:
                credits = 0.0

            prerequisite_text = cells[4].get_text(strip=True)
            prerequisite_code = None
            if prerequisite_text:
                parts = prerequisite_text.split()
                if len(parts) >= 2:
                    prerequisite_code = parts[1]

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
                    "prerequisite_code": prerequisite_code,
                }
            )

        return modules
