from datetime import datetime
from typing import Any, Dict

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
        """Scrape student data from both personal and academic pages.

        Returns:
            Dictionary containing student data with keys:
            - std_no: Student number
            - name: Student name
            - national_id: National ID/Passport number
            - date_of_birth: Date of birth
            - phone1: Primary phone number
            - phone2: Secondary phone number
            - gender: Gender (MALE/FEMALE/OTHER)
            - marital_status: Marital status
            - religion: Religion
            - structure_id: Program structure ID
        """
        # First get personal data
        personal_data = self._scrape_personal_data()

        # Then get academic data
        academic_url = f"{BASE_URL}/r_studentviewview.php?StudentID={self.student_id}"
        self.url = academic_url
        academic_data = self._scrape_academic_data()

        # Merge the data
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
