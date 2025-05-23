from typing import Any, Dict, List

from bs4 import Tag
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
        """Scrape student program data."""
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

            program_version = cells[2].get_text(strip=True)
            program_status = cells[4].get_text(strip=True)
            if program_status == "Deleted":
                continue

            structure = (
                self.db.query(Structure)
                .filter(Structure.code == program_version)
                .first()
            )
            if not structure:
                raise ValueError(
                    f"Structure with code '{program_version}' not found, did you scrape it?"
                )

            program = {
                "id": program_id,
                "start_term": cells[1].get_text(strip=True),
                "structure_id": structure.id,
                "stream": cells[3].get_text(strip=True),
                "status": program_status,
                "assist_provider": cells[5].get_text(strip=True),
            }
            programs.append(program)

        return programs
