import logging
from typing import Optional, Union

import requests
from bs4 import BeautifulSoup, Tag
from sqlalchemy.orm import Session

from registry_cli.browser import BASE_URL, Browser, get_form_payload
from registry_cli.commands.enroll.payloads import add_semester_payload
from registry_cli.models import Module, RequestedModule, Term

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
        semester_number: int,
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
            semester_id=self.read_semester_id(form, f"0{semester_number}"),
            term=term.name,
        )
        response = self.browser.post(f"{BASE_URL}/r_stdsemesteradd.php", payload)
        std_semester_id = self.get_id_for(response, term.name)
        if std_semester_id:
            logger.info(f"Semester added successfully, semester id: {std_semester_id}")
            return int(std_semester_id.strip())
        else:
            logger.error("Failed to add semester")

    def get_existing_modules(self, std_semester_id: int) -> list[str]:
        url = f"{BASE_URL}/r_stdmodulelist.php?showmaster=1&StdSemesterID={std_semester_id}"
        response = self.browser.fetch(url)
        page = BeautifulSoup(response.text, "lxml")

        existing_modules = []
        table = page.find("table", id="ewlistmain")
        if table and isinstance(table, Tag):
            rows = table.find_all("tr", class_=["ewTableRow", "ewTableAltRow"])
            for row in rows:
                module_cell = row.find("td")
                if module_cell and module_cell.text.strip():
                    module_code = module_cell.text.strip().split()[0]
                    existing_modules.append(module_code)

        return existing_modules

    def add_modules(
        self, std_semester_id: int, requested_modules: list[RequestedModule]
    ) -> list[str]:
        existing_modules = self.get_existing_modules(
            std_semester_id
        )  # Filter out modules that are already registered
        modules_to_add = [
            rm
            for rm in requested_modules
            if rm.semester_module.module.code not in existing_modules
        ]

        if not modules_to_add:
            logger.info("No new modules to add")
            return existing_modules

        url = f"{BASE_URL}/r_stdmodulelist.php?showmaster=1&StdSemesterID={std_semester_id}"
        self.browser.fetch(url)
        add_response = self.browser.fetch(f"{BASE_URL}/r_stdmoduleadd1.php")
        page = BeautifulSoup(add_response.text, "lxml")

        modules_with_amounts = []
        for rm in modules_to_add:
            module_id = rm.semester_module.id
            module_status = rm.module_status
            module_credits = rm.semester_module.credits
            module_string = f"{module_id}-{module_status}-{module_credits}-1200"
            modules_with_amounts.append(module_string)

        payload = get_form_payload(page) | {
            "Submit": "Add+Modules",
            "take[]": modules_with_amounts,
        }

        self.browser.post(f"{BASE_URL}/r_stdmoduleadd1.php", payload)

        registered_modules = self.get_existing_modules(std_semester_id)
        logger.info(f"Successfully registered modules: {registered_modules}")

        return registered_modules

    @staticmethod
    def get_id_for(response: requests.Response, search_key: str) -> Optional[str]:
        page: BeautifulSoup = BeautifulSoup(response.text, "lxml")

        if table := page.select_one("table#ewlistmain"):
            rows = table.select("tr")
            for row in rows:
                cols = row.select("td")
                if cols and search_key in cols[0].text.strip():
                    if link := row.select_one("a"):
                        if href := link.attrs.get("href"):
                            return href.split("=")[-1]
        return None

    @staticmethod
    def read_semester_id(form: Tag, sem: str):
        sem_options = form.select("#x_SemesterID option")
        for option in sem_options:
            option_str = option.get_text(strip=True)
            if option_str.startswith(sem):
                return option.attrs["value"]

        raise ValueError(
            f"semester_id cannot be empty was expecting {sem} but not found"
        )
