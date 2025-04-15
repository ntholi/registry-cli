from typing import Any, Dict, Optional, Union, cast

from bs4 import BeautifulSoup, NavigableString, Tag

from registry_cli.browser import BASE_URL
from registry_cli.scrapers.base import BaseScraper


class SemesterModuleScraper(BaseScraper):
    """Scraper for semester module information by navigating to the module edit page."""

    def __init__(self, std_module_id: int):
        """Initialize the scraper with the student module ID.

        Args:
            std_module_id: The ID of the student module to fetch details for
        """
        if not std_module_id:
            raise ValueError("std_module_id must be provided")
        self.std_module_id = std_module_id
        super().__init__(f"{BASE_URL}/r_stdmoduleedit.php?StdModuleID={std_module_id}")

    def scrape(self) -> Dict[str, Any]:
        """Scrape semester module data from the module edit page.

        Returns:
            Dictionary containing semester module data with keys:
            - id: SemesterModule ID
            - code: Module code (e.g. COMM101)
            - name: Module name
            - type: Module type (Major/Minor/Core)
            - status: Module status (e.g. Compulsory)
            - credits: Credit hours
            - fee: Module fee
            - semester_id: ID of the semester
            - program_id: ID of the program
            - school_id: ID of the school
            - alter_mark: Alter Mark value (if available)
            - alter_grade: Alter Grade value (if available)
        """
        soup = self._get_soup()
        module_data = {}

        # Extract data from the form fields
        rows = soup.find_all("tr")
        for row in rows:
            # Skip if row is not a Tag
            if not isinstance(row, Tag):
                continue

            cells = row.find_all("td")
            if len(cells) != 2:
                continue

            # Skip if either cell is not a Tag
            if not isinstance(cells[0], Tag) or not isinstance(cells[1], Tag):
                continue

            header = cells[0].get_text(strip=True)
            value_cell = cells[1]

            if header == "ID":
                module_data["id"] = self._extract_hidden_value(
                    value_cell, "x_StdModuleID"
                )
            elif header == "Semester":
                module_data["semester_id"] = self._extract_hidden_value(
                    value_cell, "x_StdSemesterID"
                )
                module_data["semester_code"] = value_cell.get_text(strip=True)
            elif header == "School":
                module_data["school_id"] = self._extract_hidden_value(
                    value_cell, "x_StdSchoolID"
                )
                module_data["school_code"] = value_cell.get_text(strip=True)
            elif header == "Program":
                module_data["program_id"] = self._extract_hidden_value(
                    value_cell, "x_StdProgramID"
                )
                module_data["program_name"] = value_cell.get_text(strip=True)
            elif header == "Module":
                # Extract SemesterModule ID and name
                module_data["semester_module_id"] = self._extract_hidden_value(
                    value_cell, "x_SemModuleID"
                )
                module_text = value_cell.get_text(strip=True)
                if " " in module_text:
                    code, name = module_text.split(" ", 1)
                    module_data["code"] = code
                    module_data["name"] = name
                else:
                    module_data["code"] = module_text
                    module_data["name"] = ""
            elif header == "Type":
                module_data["type"] = value_cell.get_text(strip=True)
            elif header == "ModuleStatus":
                # Extract from select field
                select = value_cell.find("select")
                if select:
                    selected_option = select.find("option", selected=True)
                    if selected_option:
                        module_data["status"] = selected_option.get_text(strip=True)
                else:
                    module_data["status"] = value_cell.get_text(strip=True)
            elif header == "Fee":
                # Extract from select field
                select = value_cell.find("select")
                if select:
                    selected_option = select.find("option", selected=True)
                    if selected_option:
                        module_data["fee"] = selected_option.get_text(strip=True)
                else:
                    module_data["fee"] = value_cell.get_text(strip=True)
            elif header == "Credits":
                select = value_cell.find("select")
                if select:
                    selected_option = select.find("option", selected=True)
                    if selected_option:
                        module_data["credits"] = float(
                            selected_option.get_text(strip=True)
                        )
                else:
                    credits_text = value_cell.get_text(strip=True)
                    try:
                        module_data["credits"] = float(credits_text)
                    except (ValueError, TypeError):
                        module_data["credits"] = 0.0
            elif header == "Alter Mark":
                input_field = value_cell.find("input", {"id": "x_AlterMark"})
                if (
                    input_field
                    and isinstance(input_field, Tag)
                    and "value" in input_field.attrs
                ):
                    value = input_field.attrs.get("value")
                    if value is not None:
                        try:
                            module_data["alter_mark"] = int(value)
                        except (ValueError, TypeError):
                            module_data["alter_mark"] = None
            elif header == "Alter Grade":
                input_field = value_cell.find("input", {"id": "x_AlterGrade"})
                if (
                    input_field
                    and isinstance(input_field, Tag)
                    and "value" in input_field.attrs
                ):
                    value = input_field.attrs.get("value")
                    if value is not None:
                        module_data["alter_grade"] = value

        module_id_input = soup.find("input", {"id": "x_ModuleID"})
        if (
            module_id_input
            and isinstance(module_id_input, Tag)
            and "value" in module_id_input.attrs
        ):
            value = module_id_input.attrs.get("value")
            if value is not None:
                try:
                    module_data["module_id"] = int(value)
                except (ValueError, TypeError):
                    pass

        return module_data

    def _extract_hidden_value(
        self, cell: Union[Tag, NavigableString], input_id: str
    ) -> Optional[int]:
        """Extract a hidden input value from a table cell.

        Args:
            cell: The BeautifulSoup Tag containing the hidden input
            input_id: The ID of the hidden input to extract

        Returns:
            The value as an integer, or None if not found
        """
        if isinstance(cell, NavigableString):
            return None

        cell_tag = cast(Tag, cell)
        hidden_input = cell_tag.find("input", {"id": input_id})

        if (
            hidden_input
            and isinstance(hidden_input, Tag)
            and "value" in hidden_input.attrs
        ):
            try:
                value = hidden_input.attrs.get("value")
                if value is not None:
                    return int(value)
            except (ValueError, TypeError):
                return None
        return None
