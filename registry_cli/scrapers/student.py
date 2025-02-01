from datetime import datetime
from typing import Any, Dict, List, cast

from bs4 import ResultSet, Tag

from registry_cli.browser import BASE_URL
from registry_cli.models import Gender, MaritalStatus, SemesterStatus
from registry_cli.scrapers.base import BaseScraper


class StudentScraper(BaseScraper):
    """Scraper for student information."""

    def __init__(self, student_id: int):
        if not student_id:
            raise ValueError("student_id must be provided")
        self.student_id = student_id
        super().__init__(f"{BASE_URL}/r_stdpersonalview.php?StudentID={student_id}")

    def scrape(self) -> Dict[str, Any]:
        personal_data = self._scrape_personal_data()

        academic_url = f"{BASE_URL}/r_studentviewview.php?StudentID={self.student_id}"
        self.url = academic_url
        academic_data = self._scrape_academic_data()
        return {**personal_data, **academic_data}

    def _scrape_personal_data(self) -> Dict[str, Any]:
        """Scrape student personal data."""
        soup = self._get_soup()
        data = {}

        rows = soup.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) != 2:
                continue

            header = cells[0].get_text(strip=True)
            value = cells[1].get_text(strip=True)

            if header == "Birthdate":
                if value:
                    data["date_of_birth"] = datetime.strptime(value, "%Y-%m-%d").date()
            elif header == "Sex":
                data["gender"] = value
            elif header == "Marital":
                data["marital_status"] = value if value else None
            elif header == "Religion":
                data["religion"] = value

        return data

    def _scrape_academic_data(self) -> Dict[str, Any]:
        """Scrape student academic data."""
        soup = self._get_soup()
        data = {}

        rows = soup.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) != 2:
                continue

            header = cells[0].get_text(strip=True)
            value = cells[1].get_text(strip=True)

            if header == "ID":
                data["std_no"] = value
            elif header == "Name":
                data["name"] = value
            elif header == "IC/Passport":
                data["national_id"] = value
            elif header == "Contact No":
                data["phone1"] = value
            elif header == "Contact No 2":
                data["phone2"] = value
            elif header == "Sem":
                data["sem"] = int(value)
            elif header == "Version":
                if value:
                    data["structure_id"] = int(value)

        return data


class StudentProgramScraper(BaseScraper):
    """Scraper for student program information."""

    def __init__(self, std_no: int):
        if not std_no:
            raise ValueError("std_no must be provided")
        self.std_no = std_no
        super().__init__(
            f"{BASE_URL}/r_stdprogramlist.php?showmaster=1&StudentID={std_no}"
        )

    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape student program data."""
        soup = self._get_soup()
        programs = []

        table = soup.find("table", {"id": "ewlistmain"})
        if not table:
            return programs

        rows = table.find_all("tr")[1:]
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 6:
                continue

            code_name = cells[0].get_text(strip=True)
            code = code_name.split(" ")[0]
            name = " ".join(code_name.split(" ")[1:])

            program_id = None
            link = cells[-1].find("a")
            if link and "href" in link.attrs:
                program_id = link["href"].split("ProgramID=")[-1]

            program = {
                "id": program_id,
                "code": code,
                "name": name,
                "term": cells[1].get_text(strip=True),
                "version": cells[2].get_text(strip=True),
                "stream": cells[3].get_text(strip=True),
                "status": cells[4].get_text(strip=True),
                "assist_provider": cells[5].get_text(strip=True),
            }
            programs.append(program)

        return programs


class StudentSemesterScraper(BaseScraper):
    """Scraper for student semester information."""

    def __init__(self, program_id: int):
        if not program_id:
            raise ValueError("program_id must be provided")
        self.program_id = program_id
        super().__init__(
            f"{BASE_URL}/r_stdsemesterlist.php?showmaster=1&StdProgramID={program_id}"
        )

    def scrape(self) -> List[Dict[str, Any]]:
        """Scrape student semester data.

        Returns:
            List of dictionaries containing semester data with keys:
            - term: Term code (e.g. 2022-08)
            - status: Semester status (e.g. Active)
            - credits: Total credits for the semester
        """
        soup = self._get_soup()
        semesters = []

        table = soup.find("table", {"id": "ewlistmain"})
        if not table or not isinstance(table, Tag):
            return semesters

        table_tag = cast(Tag, table)
        rows: ResultSet[Tag] = table_tag.find_all(
            "tr", {"class": ["ewTableRow", "ewTableAltRow"]}
        )
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 8:
                continue

            credits_text = cells[6].get_text(strip=True).replace(",", "")
            try:
                credits = float(credits_text) if credits_text else 0.0
            except ValueError:
                credits = 0.0

            status_text = cells[4].get_text(strip=True)
            try:
                status: SemesterStatus = status_text
            except ValueError:
                status = "Active"

            semester_id = None
            link = cells[-1].find("a")
            if link and "href" in link.attrs:
                semester_id = link["href"].split("SemesterID=")[-1]

            semester_number = None
            try:
                semester_text = cells[1].get_text(strip=True)
                if semester_text:
                    parts = semester_text.split("-")
                    if len(parts) >= 3:
                        year_sem = parts[2].split()[0]
                        year = int(year_sem[1])
                        sem = int(year_sem[-1])
                        semester_number = (year - 1) * 2 + sem
            except ValueError:
                print(
                    f"Error! Failed to parse semester_number: {semester_text}, setting to None"
                )
                semester_number = None

            semester = {
                "id": semester_id,
                "term": cells[0].get_text(strip=True),
                "status": status,
                "credits": credits,
                "semester_number": semester_number,
            }
            semesters.append(semester)

        return semesters


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
            - code: Module code (e.g. DBBM1106)
            - name: Module name
            - type: Module type (Major/Minor/Core)
            - status: Module status (e.g. Compulsory)
            - credits: Credit hours
            - marks: Module marks
            - grade: Module grade
        """
        soup = self._get_soup()
        modules = []

        table = soup.find("table", {"id": "ewlistmain"})
        if not table:
            return modules

        rows = table.find_all("tr")[1:-1]  # Skip header and footer rows
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 6:
                continue

            # Extract module code and name from the first cell
            module_text = cells[0].get_text(strip=True)
            code_name = module_text.split(" ", 1)
            code = code_name[0] if len(code_name) > 0 else ""
            name = code_name[1] if len(code_name) > 1 else module_text

            module_id = None
            link = cells[-1].find("a")
            if link and "href" in link.attrs:
                module_id = link["href"].split("ModuleID=")[-1]

            module = {
                "id": module_id,
                "code": code,
                "name": name,
                "type": cells[1].get_text(strip=True),
                "status": cells[2].get_text(strip=True),
                "credits": float(cells[3].get_text(strip=True) or 0),
                "marks": cells[4].get_text(strip=True) or "0",
                "grade": cells[5].get_text(strip=True) or "N/A",
            }
            modules.append(module)

        return modules
