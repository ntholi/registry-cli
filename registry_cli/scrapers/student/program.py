from typing import Any, Dict, List

from bs4 import BeautifulSoup, Tag
from sqlalchemy.orm import Session

from registry_cli.browser import BASE_URL
from registry_cli.models import Structure
from registry_cli.scrapers.base import BaseScraper


class StudentProgramScraper(BaseScraper):
    """Scraper for student program information."""

    def __init__(self, db: Session, std_no: int):
        if not std_no:
            raise ValueError("std_no must be provided")
        self.std_no = std_no
        self.db = db
        super().__init__(
            f"{BASE_URL}/r_stdprogramlist.php?showmaster=1&StudentID={std_no}"
        )

    def scrape(self) -> List[Dict[str, Any]]:
        soup = self._get_soup()
        programs = []

        table = soup.find("table", {"id": "ewlistmain"})
        if not table or not isinstance(table, Tag):
            return programs

        rows = table.find_all("tr")[1:]
        for row in rows:
            if not isinstance(row, Tag):
                continue

            cells = row.find_all("td")
            if len(cells) < 6:
                continue

            program_id = None
            link = cells[-1].find("a")
            if link and "href" in link.attrs:
                program_id = link["href"].split("ProgramID=")[-1]

            if not program_id:
                continue

            try:
                program = self._get_program_details(program_id)
                programs.append(program)
            except Exception as e:
                print(f"Error fetching program details for ID {program_id}: {str(e)}")

        return programs

    def _get_program_details(self, program_id: str) -> Dict[str, Any]:
        """Fetch and extract detailed program information, returning only StudentProgram fields."""
        url = f"{BASE_URL}/r_stdprogramview.php?StdProgramID={program_id}"
        response = self.browser.fetch(url)
        soup = BeautifulSoup(response.text, "lxml")

        header_to_field = {
            "ID": "id",
            "RegDate": "reg_date",
            "Intake Date": "intake_date",
            "StartTerm": "start_term",
            "Stream": "stream",
            "Graduation Date": "graduation_date",
            "Status": "status",
            "Asst-Provider": "assist_provider",
        }

        program_details = {}

        table = soup.find("table", {"class": "ewTable"})
        if not table or not isinstance(table, Tag):
            return program_details

        rows = table.find_all("tr")
        for row in rows:
            if not isinstance(row, Tag):
                continue

            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            header = cells[0].get_text(strip=True)
            value = cells[1].get_text(strip=True)

            if header == "Version":
                program_details["structure_id"] = find_structure_id(self.db, value)

            if header in header_to_field:
                field = header_to_field[header]
                if field == "id":
                    try:
                        program_details[field] = int(value)
                    except Exception:
                        program_details[field] = None
                else:
                    program_details[field] = value if value else None

        return program_details


def find_structure_id(db: Session, version_code: str) -> int:
    structure = db.query(Structure).filter(Structure.code == version_code).first()
    if not structure:
        structure = db.query(Structure).filter(Structure.desc == version_code).first()
    if not structure:
        raise ValueError(
            f"Structure with code or description '{version_code}' not found, did you scrape it?"
        )
    return structure.id
