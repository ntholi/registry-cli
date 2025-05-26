from datetime import datetime
from typing import Any, Dict

from bs4 import Tag

from registry_cli.browser import BASE_URL
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
            if not isinstance(row, Tag):
                continue

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
            if not isinstance(row, Tag):
                continue

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
                data["sem"] = int(value) if value else 1

        return data
