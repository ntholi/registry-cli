import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup, Tag
from sqlalchemy.orm import Session

from registry_cli.browser import BASE_URL, Browser, get_form_payload
from registry_cli.commands.enroll.payloads import add_semester_payload
from registry_cli.models import Module, Term

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

    def get_existing_modules(self, std_semester_id: int) -> list[str]:
        url = f"{BASE_URL}/r_stdmodulelist.php?showmaster=1&StdSemesterID={std_semester_id}"
        response = self.browser.fetch(url)
        page = BeautifulSoup(response.text, "lxml")
        
        existing_modules = []
        table = page.find("table", id="ewlistmain")
        if table:
            rows = table.find_all("tr", class_=["ewTableRow", "ewTableAltRow"])
            for row in rows:
                module_cell = row.find("td")
                if module_cell and module_cell.text.strip():
                    module_code = module_cell.text.strip().split()[0]
                    existing_modules.append(module_code)
        
        return existing_modules

    def add_modules(self, std_semester_id: int, requested_modules: list[Module]):
        existing_modules = self.get_existing_modules(std_semester_id)
        
        modules_to_add = [
            module for module in requested_modules 
            if module.code not in existing_modules
        ]
        
        if not modules_to_add:
            logger.info("No new modules to add")
            return

        url = f"{BASE_URL}/r_stdmodulelist.php?showmaster=1&StdSemesterID={std_semester_id}"
        self.browser.fetch(url)
        add_response = self.browser.fetch(f"{BASE_URL}/r_stdmoduleadd1.php")
        page = BeautifulSoup(add_response.text, "lxml")
        checkboxes = page.find_all("input", type="checkbox")

        modules = []
        for _, checkbox in enumerate(checkboxes):
            row = checkbox.find_parent("tr")
            if row:
                module_name = row.find("td").text.strip()
                is_requested_module = any(
                    module.name == module_name for module in modules_to_add
                )
                if is_requested_module:
                    modules.append(checkbox.attrs["value"])

        modules_with_amounts = []
        for module in modules:
            parts = module.split("-")
            parts[-1] = "1200"
            modules_with_amounts.append("-".join(parts))

        payload = get_form_payload(page) | {
            "Submit": "Add+Modules",
            "take[]": modules_with_amounts,
        }
        hidden_inputs = page.find_all("input", type="hidden")
        for hidden in hidden_inputs:
            payload.update({hidden["name"]: hidden["value"]})

        self.browser.post(f"{BASE_URL}/r_stdmoduleadd1.php", payload)

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
    def read_semester_id(form: Tag, target: str):
        sem_options = form.select("#x_SemesterID option")
        for option in sem_options:
            option_str = option.get_text(strip=True)
            if target in option_str:
                return option.attrs["value"]

        raise ValueError(
            f"semester_id cannot be empty was expecting 'Year 1 Sem 1' but not found"
        )