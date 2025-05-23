from typing import Any, Dict, List

from bs4 import Tag

from registry_cli.browser import BASE_URL
from registry_cli.scrapers.base import BaseScraper
from registry_cli.scrapers.semester_module import SemesterModuleScraper


class StudentModuleScraper(BaseScraper):
    """Scraper for student module information."""

    def __init__(self, semester_id: int):
        if not semester_id:
            raise ValueError("semester_id must be provided")
        self.semester_id = semester_id
        super().__init__(
            f"{BASE_URL}/r_stdmodulelist.php?showmaster=1&StdSemesterID={semester_id}"
        )

    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape student module data.

        Returns:
            List of dictionaries containing module data with keys:
            - id: Module ID
            - semester_module_id: SemesterModule ID
            - code: Module code (e.g. DBBM1106)
            - name: Module name
            - type: Module type (Major/Minor/Core)
            - status: Module status (e.g. Compulsory)
            - credits: Credit hours
            - marks: Module marks
            - grade: Module grade
            - fee: Module fee
        """
        soup = self._get_soup()
        modules = []

        table = soup.find("table", {"id": "ewlistmain"})
        if not table or not isinstance(table, Tag):
            return modules

        rows = table.find_all("tr")[1:-1]
        for row in rows:
            if not isinstance(row, Tag):
                continue

            cells = row.find_all("td")
            if len(cells) < 6:
                continue

            # Extract module code and name from the first cell
            module_text = cells[0].get_text(strip=True)
            code_name = module_text.split(" ", 1)
            code = code_name[0] if len(code_name) > 0 else ""
            name = code_name[1] if len(code_name) > 1 else module_text

            # Get the student module ID from the edit link
            std_module_id = None
            edit_link = None
            for cell in cells:
                # Make sure cell is a Tag, not a NavigableString
                if not isinstance(cell, Tag):
                    continue

                links = cell.find_all("a")
                for link in links:
                    href = link.get("href", "")
                    if "r_stdmoduleedit.php" in href:
                        std_module_id = href.split("StdModuleID=")[-1]
                if std_module_id:
                    break

            # Basic module information from the list view
            module = {
                "id": std_module_id,
                "code": code,
                "name": name,
                "type": cells[1].get_text(strip=True),
                "status": cells[2].get_text(strip=True),
                "credits": float(cells[3].get_text(strip=True) or 0),
                "marks": cells[4].get_text(strip=True) or "0",
                "grade": cells[5].get_text(strip=True) or "N/A",
            }

            # If we have a student module ID, get detailed information from the edit page
            if std_module_id:
                try:
                    semester_module_scraper = SemesterModuleScraper(std_module_id)
                    semester_module_data = semester_module_scraper.scrape()

                    # Add semester module ID and fee to the module data
                    module["semester_module_id"] = semester_module_data.get(
                        "semester_module_id"
                    )
                    module["fee"] = semester_module_data.get("fee")

                    # Update other fields with more accurate data if available
                    if "credits" in semester_module_data:
                        module["credits"] = semester_module_data["credits"]
                    if "status" in semester_module_data:
                        module["status"] = semester_module_data["status"]
                    if "type" in semester_module_data:
                        module["type"] = semester_module_data["type"]
                    if (
                        "alter_mark" in semester_module_data
                        and semester_module_data["alter_mark"]
                    ):
                        module["marks"] = semester_module_data["alter_mark"]
                    if (
                        "alter_grade" in semester_module_data
                        and semester_module_data["alter_grade"]
                    ):
                        module["grade"] = semester_module_data["alter_grade"]
                except Exception as e:
                    print(
                        f"Error fetching semester module data for ID {std_module_id}: {str(e)}"
                    )

            modules.append(module)

        return modules
