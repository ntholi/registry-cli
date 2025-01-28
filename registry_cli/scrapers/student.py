from datetime import datetime
from typing import Any, Dict, List, cast

from bs4 import Tag
from bs4.element import NavigableString, ResultSet

from registry_cli.browser import BASE_URL
from registry_cli.models.student import Gender, MaritalStatus, SemesterStatus
from registry_cli.scrapers.base import BaseScraper


class StudentScraper(BaseScraper):
    """Scraper for student information."""

    def __init__(self, student_id: int):
        """Initialize the scraper with student ID."""
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
                data["gender"] = (
                    Gender.Male
                    if value == "Male"
                    else Gender.Female if value == "Female" else Gender.Other
                )
            elif header == "Marital":
                data["marital_status"] = MaritalStatus(value) if value else None
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
            elif header == "Version":
                if value:
                    data["structure_id"] = int(value)

        return data


class StudentProgramScraper(BaseScraper):
    """Scraper for student program information."""

    def __init__(self, student_id: int):
        """Initialize the scraper with student ID."""
        self.student_id = student_id
        super().__init__(
            f"{BASE_URL}/r_stdprogramlist.php?showmaster=1&StudentID={student_id}"
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
            link = cells[0].find("a")
            if link and "href" in link.attrs:
                href = link["href"]
                import re

                match = re.search(r"StdProgramID=(\d+)", href)
                if match:
                    program_id = int(match.group(1))

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
        """Initialize the scraper with program ID."""
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
                status = SemesterStatus(status_text)
            except ValueError:
                status = SemesterStatus.Active

            semester = {
                "term": cells[0].get_text(strip=True),
                "status": status,
                "credits": credits,
            }
            semesters.append(semester)

        return semesters
