from datetime import datetime
from typing import Any, Dict, List

from registry_cli.browser import BASE_URL
from registry_cli.models.student import Gender, MaritalStatus
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

        # Find all table rows
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

        # Find all table rows
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

        # Find the main table containing program data
        table = soup.find("table", {"id": "ewlistmain"})
        if not table:
            return programs

        # Get all rows except header
        rows = table.find_all("tr")[1:]  # Skip header row
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 6:  # We need at least 6 cells for the main data
                continue

            code_name = cells[0].get_text(strip=True)
            code = code_name.split(" ")[0]
            name = " ".join(code_name.split(" ")[1:])
            program = {
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
