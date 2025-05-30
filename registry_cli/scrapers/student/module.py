from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Union, cast

from bs4 import BeautifulSoup, NavigableString, Tag

from registry_cli.browser import BASE_URL
from registry_cli.scrapers.base import BaseScraper


class StudentModuleScraper(BaseScraper):
    def __init__(self, semester_id: int):
        if not semester_id:
            raise ValueError("semester_id must be provided")
        self.semester_id = semester_id
        super().__init__(
            f"{BASE_URL}/r_stdmodulelist.php?showmaster=1&StdSemesterID={semester_id}"
        )

    def scrape(self) -> List[Dict[str, Any]]:
        soup = self._get_soup()
        modules = []

        table = soup.find("table", {"id": "ewlistmain"})
        if not table or not isinstance(table, Tag):
            return modules

        module_tasks = []
        rows = table.find_all("tr")[1:-1]

        for row in rows:
            if not isinstance(row, Tag):
                continue

            cells = row.find_all("td")
            if len(cells) < 6:
                continue

            std_module_id = None
            module_status = None

            for cell in cells:
                if not isinstance(cell, Tag):
                    continue

                links = cell.find_all("a")
                for link in links:
                    href = link.get("href", "")
                    if "r_stdmoduleedit.php" in href:
                        std_module_id = href.split("StdModuleID=")[-1]
                if std_module_id:
                    break

            if len(cells) >= 3 and isinstance(cells[2], Tag):
                module_status = cells[2].get_text(strip=True)

            if std_module_id:
                module_tasks.append((std_module_id, module_status))

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_module = {
                executor.submit(self._scrape_module_details, module_id, status): (
                    module_id,
                    status,
                )
                for module_id, status in module_tasks
            }

            for future in as_completed(future_to_module):
                module_id, status = future_to_module[future]
                try:
                    module_data = future.result()
                    modules.append(module_data)
                except Exception as e:
                    print(f"Error fetching module data for ID {module_id}: {str(e)}")

        return modules

    def _scrape_module_details(
        self, std_module_id: str, module_status: Optional[str] = None
    ) -> Dict[str, Any]:
        url = f"{BASE_URL}/r_stdmoduleedit.php?StdModuleID={std_module_id}"
        response = self.browser.fetch(url)
        soup = BeautifulSoup(response.text, "html.parser")

        module_data = {"id": std_module_id}

        if module_status:
            module_data["status"] = module_status

        rows = soup.find_all("tr")
        for row in rows:
            if not isinstance(row, Tag):
                continue

            cells = row.find_all("td")
            if len(cells) != 2:
                continue

            if not isinstance(cells[0], Tag) or not isinstance(cells[1], Tag):
                continue

            header = cells[0].get_text(strip=True)
            value_cell = cells[1]

            if header == "Semester":
                semester_id = self._extract_hidden_value(value_cell, "x_StdSemesterID")
                module_data["semester_id"] = (
                    str(semester_id) if semester_id is not None else ""
                )
                module_data["semester_code"] = value_cell.get_text(strip=True)
            elif header == "School":
                school_id = self._extract_hidden_value(value_cell, "x_StdSchoolID")
                module_data["school_id"] = (
                    str(school_id) if school_id is not None else ""
                )
                module_data["school_code"] = value_cell.get_text(strip=True)
            elif header == "Program":
                program_id = self._extract_hidden_value(value_cell, "x_StdProgramID")
                module_data["program_id"] = (
                    str(program_id) if program_id is not None else ""
                )
                module_data["program_name"] = value_cell.get_text(strip=True)
            elif header == "Module":
                semester_module_id = self._extract_hidden_value(
                    value_cell, "x_SemModuleID"
                )
                module_data["semester_module_id"] = (
                    str(semester_module_id) if semester_module_id is not None else ""
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
                if "status" not in module_data:
                    select = value_cell.find("select")
                    if select:
                        selected_option = select.find("option", selected=True)
                        if selected_option:
                            module_data["status"] = selected_option.get_text(strip=True)
                    else:
                        module_data["status"] = value_cell.get_text(strip=True)
            elif header == "Fee":
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
                        credits_str = selected_option.get_text(strip=True)
                        try:
                            module_data["credits"] = str(float(credits_str))
                        except (ValueError, TypeError):
                            module_data["credits"] = "0.0"
                else:
                    credits_text = value_cell.get_text(strip=True)
                    try:
                        module_data["credits"] = str(float(credits_text))
                    except (ValueError, TypeError):
                        module_data["credits"] = "0.0"
            elif header == "Marks":
                input_field = value_cell.find("input", {"id": "x_StdModMark"})
                if (
                    input_field
                    and isinstance(input_field, Tag)
                    and "value" in input_field.attrs
                ):
                    value = input_field.attrs.get("value")
                    if value is not None:
                        try:
                            module_data["marks"] = str(int(value))
                        except (ValueError, TypeError):
                            module_data["marks"] = "0"
            elif header == "Grade":
                input_field = value_cell.find("input", {"id": "x_StdModGrade"})
                if (
                    input_field
                    and isinstance(input_field, Tag)
                    and "value" in input_field.attrs
                ):
                    value = input_field.attrs.get("value")
                    if value is not None:
                        module_data["grade"] = value
            elif header == "Alter Mark":
                input_field = value_cell.find("input", {"id": "x_AlterMark"})
                if (
                    input_field
                    and isinstance(input_field, Tag)
                    and "value" in input_field.attrs
                ):
                    value = input_field.attrs.get("value")
                    if value is not None and value.strip():
                        try:
                            module_data["alter_mark"] = str(int(value))
                            module_data["marks"] = module_data["alter_mark"]
                        except (ValueError, TypeError):
                            module_data["alter_mark"] = ""
            elif header == "Alter Grade":
                input_field = value_cell.find("input", {"id": "x_AlterGrade"})
                if (
                    input_field
                    and isinstance(input_field, Tag)
                    and "value" in input_field.attrs
                ):
                    value = input_field.attrs.get("value")
                    if value is not None and value.strip():
                        module_data["alter_grade"] = value
                        module_data["grade"] = value

        module_id_input = soup.find("input", {"id": "x_ModuleID"})
        if (
            module_id_input
            and isinstance(module_id_input, Tag)
            and "value" in module_id_input.attrs
        ):
            value = module_id_input.attrs.get("value")
            if value is not None:
                try:
                    module_data["module_id"] = str(int(value))
                except (ValueError, TypeError):
                    pass

        if "marks" not in module_data:
            module_data["marks"] = "0"
        if "grade" not in module_data:
            module_data["grade"] = "N/A"

        return module_data

    def _extract_hidden_value(
        self, cell: Union[Tag, NavigableString], input_id: str
    ) -> Optional[int]:
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
