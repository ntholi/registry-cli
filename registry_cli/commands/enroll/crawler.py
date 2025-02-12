import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup, Tag
from sqlalchemy.orm import Session

from registry_cli.browser import BASE_URL, Browser, get_form_payload
from registry_cli.commands.enroll.payloads import add_semester_payload
from registry_cli.models import Term

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Crawler:
    def __init__(self, db: Session):
        self.browser = Browser()
        self.db = db

    def add_semester(
        self,
        school_id: int,
        program_id: int,
        structure_id: int,
        std_program_id: int,
        semester: str,
    ) -> int | None:
        logger.info(f"Adding semester for student '{std_program_id}'")
        url = f"{BASE_URL}/r_stdsemesterlist.php?showmaster=1&StdProgramID={std_program_id}"
        term = self.db.query(Term).filter(Term.is_active == True).first()
        if not term:
            raise ValueError("No active Term found in database")

        std_semester_id = self.get_id_for(self.browser.fetch(url), term.name)
        if std_semester_id:
            logger.info(f"Semester already added, semester id: {std_semester_id}")
            return int(std_semester_id.strip())
        response = self.browser.fetch(f"{BASE_URL}/r_stdsemesteradd.php")
        page = BeautifulSoup(response.text, "lxml")
        form = page.select_one("form")
        if not form:
            raise ValueError("form element not found in", response.text)
        payload = get_form_payload(form) | add_semester_payload(
            school_id=school_id,
            program_id=program_id,
            structure_id=structure_id,
            std_program_id=std_program_id,
            semester_id=self.read_semester_id(form, semester),
            term=term.name,
        )
        response = self.browser.post(f"{BASE_URL}/r_stdsemesteradd.php", payload)
        std_semester_id = self.get_id_for(response, term.name)
        if std_semester_id:
            logger.info(f"Semester added successfully, semester id: {std_semester_id}")
            return int(std_semester_id.strip())
        else:
            logger.error("Failed to add semester")

    @staticmethod
    def get_id_for(response: requests.Response, search_key: str) -> Optional[str]:
        page: BeautifulSoup = BeautifulSoup(response.text, "lxml")

        if table := page.select_one("table#ewlistmain"):
            rows = table.select("tr.ewTableRow")
            for row in rows:
                cols = row.select("td")
                if cols and search_key in cols[0].text.strip():
                    if link := row.select_one("a"):
                        if href := link.attrs.get("href"):
                            return href.split("=")[-1]
        return None

    @staticmethod
    def read_semester_id(form: Tag, target: str):
        sem_options = form.select("#x_SemesterID option")
        for option in sem_options:
            option_str = option.get_text(strip=True)
            if target in option_str:
                return option.attrs["value"]

        raise ValueError(
            f"semester_id cannot be empty was expecting 'Year 1 Sem 1' but not found"
        )
