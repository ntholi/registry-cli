from datetime import datetime
from typing import Any, Dict, List, Optional, cast

from bs4 import ResultSet, Tag
from sqlalchemy.orm import Session

from registry_cli.browser import BASE_URL
from registry_cli.models import (
    Gender,
    MaritalStatus,
    Program,
    ProgramStatus,
    SemesterStatus,
    Structure,
)
from registry_cli.scrapers.base import BaseScraper
from registry_cli.scrapers.semester_module import SemesterModuleScraper
from registry_cli.scrapers.structure import ProgramStructureScraper


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
                data["sem"] = int(value)
            elif header == "Version":
                if value:
                    data["structure_id"] = int(value)

        return data


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
            if semester_number is None and semester_id:
                semester_details = self._get_semester_details(semester_id)
                semester_number = semester_details.get("semester_number")

            semester = {
                "id": semester_id,
                "term": cells[0].get_text(strip=True),
                "status": status,
                "credits": credits,
                "semester_number": semester_number,
            }
            
            # If we have a semester ID, get detailed information
            if semester_id:
                try:
                    semester_details = self._get_semester_details(semester_id)
                    # Update the semester with detailed information
                    semester.update(semester_details)
                except Exception as e:
                    print(f"Error fetching semester details for ID {semester_id}: {str(e)}")

            semesters.append(semester)

        return semesters

    def _get_semester_details(self, semester_id: str) -> Dict[str, Any]:
        """Get all semester details directly from the semester view page.

        Args:
            semester_id: The ID of the semester

        Returns:
            Dictionary containing all semester details
        """
        view_url = f"{BASE_URL}/r_stdsemesterview.php?StdSemesterID={semester_id}"
        self.url = view_url
        soup = self._get_soup()
        
        details: Dict[str, Any] = {"id": semester_id}
        
        rows = soup.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) == 2:
                header = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                
                # Map specific fields to our data model
                if header == "Semester":
                    try:
                        value = value.strip()
                        if " " in value:
                            semester_number = int(value.split(" ")[0])
                        else:
                            semester_number = int(value)
                        details["semester_number"] = semester_number
                    except (ValueError, TypeError, IndexError):
                        print(f"Error parsing semester number from '{value}'")
                elif header == "Term":
                    details["term"] = value
                elif header == "Class":
                    details["class_id"] = value
                elif header == "Version":
                    details["structure_id"] = value
                elif header == "Campus":
                    details["campus"] = value
                elif header == "SemStatus":
                    details["status"] = value
                elif header == "CAF No":
                    details["caf_no"] = value
                elif header == "CAF Date":
                    if value:
                        try:
                            details["caf_date"] = datetime.strptime(value, "%Y-%m-%d").date()
                        except ValueError:
                            pass
                elif header == "Approval Date":
                    if value:
                        try:
                            details["approval_date"] = datetime.strptime(value, "%Y-%m-%d").date()
                        except ValueError:
                            pass
                elif header == "GPA":
                    if value:
                        try:
                            details["gpa"] = float(value)
                        except ValueError:
                            pass
                elif header == "CGPA":
                    if value:
                        try:
                            details["cgpa"] = float(value)
                        except ValueError:
                            pass
                elif header == "Credits":
                    if value:
                        try:
                            details["credits"] = float(value)
                        except ValueError:
                            pass
                elif header == "Earned":
                    if value:
                        try:
                            details["earned_credits"] = float(value)
                        except ValueError:
                            pass
                elif header == "Asst-Provider":
                    details["assist_provider"] = value
                elif header == "Asst-Scheme":
                    details["assist_scheme"] = value
                elif header == "Assist Memo":
                    details["assist_memo"] = value
                elif header == "Asst-Status":
                    details["assist_status"] = value
                elif header == "Asst-Approval Date":
                    if value:
                        try:
                            details["assist_approval_date"] = datetime.strptime(value, "%Y-%m-%d").date()
                        except ValueError:
                            pass
                elif header == "Asst-Start Date":
                    if value:
                        try:
                            details["assist_start_date"] = datetime.strptime(value, "%Y-%m-%d").date()
                        except ValueError:
                            pass
                elif header == "Asst-Expiry Date":
                    if value:
                        try:
                            details["assist_expiry_date"] = datetime.strptime(value, "%Y-%m-%d").date()
                        except ValueError:
                            pass
                elif header == "Asst-SemAmount":
                    if value:
                        try:
                            details["assist_amount"] = float(value)
                        except ValueError:
                            pass
                elif header == "Asst-Percentage":
                    if value:
                        try:
                            details["assist_percentage"] = float(value)
                        except ValueError:
                            pass
                elif header == "Asst-Bond":
                    details["assist_bond"] = value
                elif header == "Asst-Reg Remark":
                    details["assist_reg_remark"] = value
                elif header == "Asst-Bill No":
                    details["assist_bill_no"] = value
                elif header == "Asst-Bill Date":
                    if value:
                        try:
                            details["assist_bill_date"] = datetime.strptime(value, "%Y-%m-%d").date()
                        except ValueError:
                            pass
                elif header == "Asst-Bill Paid":
                    details["assist_bill_paid"] = bool("Y" in value)
                elif header == "Asst-Bill Amt":
                    if value:
                        try:
                            details["assist_bill_amount"] = float(value)
                        except ValueError:
                            pass
                elif header == "Asst-Bur Remark":
                    details["assist_bur_remark"] = value
                elif header == "Asst-Appeal Date":
                    if value:
                        try:
                            details["assist_appeal_date"] = datetime.strptime(value, "%Y-%m-%d").date()
                        except ValueError:
                            pass
                elif header == "Defer Term":
                    details["defer_term"] = value
                elif header == "Term Start":
                    details["term_start"] = value
                elif header == "Fees-Tuition":
                    if value:
                        try:
                            details["fees_tuition"] = float(value)
                        except ValueError:
                            pass
                elif header == "Fees-Resource":
                    if value:
                        try:
                            details["fees_resource"] = float(value)
                        except ValueError:
                            pass
                elif header == "Fees-Repeat":
                    if value:
                        try:
                            details["fees_repeat"] = float(value)
                        except ValueError:
                            pass
                elif header == "Fees-Total":
                    if value:
                        try:
                            details["fees_total"] = float(value)
                        except ValueError:
                            pass
                elif header == "Operator":
                    details["operator"] = value
                elif header == "Reference":
                    details["reference"] = value
                elif header == "Source":
                    details["source"] = value
                elif header == "Remark":
                    details["remark"] = value
                elif header == "Std Print Card":
                    details["std_print_card"] = bool("Y" in value)
                elif header == "TranscriptRemark Override":
                    details["transcript_remark_override"] = bool("Y" in value)
                elif header == "TranscriptRemark":
                    details["transcript_remark"] = value
                elif header == "TranscriptVisaPurposes":
                    details["transcript_visa"] = bool("Y" in value)
                elif header == "Defer Date":
                    if value:
                        try:
                            details["defer_date"] = datetime.strptime(value, "%Y-%m-%d").date()
                        except ValueError:
                            pass
                elif header == "Return Date":
                    if value:
                        try:
                            details["return_date"] = datetime.strptime(value, "%Y-%m-%d").date()
                        except ValueError:
                            pass
                elif header == "Activation Date":
                    if value:
                        try:
                            details["activation_date"] = datetime.strptime(value, "%Y-%m-%d").date()
                        except ValueError:
                            pass
        
        return details


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
            - semester_module_id: SemesterModule ID
            - code: Module code (e.g. DBBM1106)
            - name: Module name
            - type: Module type (Major/Minor/Core)
            - status: Module status (e.g. Compulsory)
            - credits: Credit hours
            - marks: Module marks
            - grade: Module grade
            - fee: Module fee
        """
        soup = self._get_soup()
        modules = []

        table = soup.find("table", {"id": "ewlistmain"})
        if not table or not isinstance(table, Tag):
            return modules

        rows = table.find_all("tr")[1:-1]
        for row in rows:
            if not isinstance(row, Tag):
                continue

            cells = row.find_all("td")
            if len(cells) < 6:
                continue

            # Extract module code and name from the first cell
            module_text = cells[0].get_text(strip=True)
            code_name = module_text.split(" ", 1)
            code = code_name[0] if len(code_name) > 0 else ""
            name = code_name[1] if len(code_name) > 1 else module_text

            # Get the student module ID from the edit link
            std_module_id = None
            edit_link = None
            for cell in cells:
                # Make sure cell is a Tag, not a NavigableString
                if not isinstance(cell, Tag):
                    continue

                links = cell.find_all("a")
                for link in links:
                    href = link.get("href", "")
                    if "r_stdmoduleedit.php" in href:
                        edit_link = href
                        std_module_id_match = href.split("StdModuleID=")
                        if len(std_module_id_match) > 1:
                            try:
                                std_module_id = int(std_module_id_match[1])
                            except (ValueError, TypeError):
                                pass
                        break
                if std_module_id:
                    break

            # Basic module information from the list view
            module = {
                "id": std_module_id,
                "code": code,
                "name": name,
                "type": cells[1].get_text(strip=True),
                "status": cells[2].get_text(strip=True),
                "credits": float(cells[3].get_text(strip=True) or 0),
                "marks": cells[4].get_text(strip=True) or "0",
                "grade": cells[5].get_text(strip=True) or "N/A",
            }

            # If we have a student module ID, get detailed information from the edit page
            if std_module_id:
                try:
                    semester_module_scraper = SemesterModuleScraper(std_module_id)
                    semester_module_data = semester_module_scraper.scrape()

                    # Add semester module ID and fee to the module data
                    module["semester_module_id"] = semester_module_data.get(
                        "semester_module_id"
                    )
                    module["fee"] = semester_module_data.get("fee")

                    # Update other fields with more accurate data if available
                    if "credits" in semester_module_data:
                        module["credits"] = semester_module_data["credits"]
                    if "status" in semester_module_data:
                        module["status"] = semester_module_data["status"]
                    if "type" in semester_module_data:
                        module["type"] = semester_module_data["type"]
                    if (
                        "alter_mark" in semester_module_data
                        and semester_module_data["alter_mark"]
                    ):
                        module["marks"] = semester_module_data["alter_mark"]
                    if (
                        "alter_grade" in semester_module_data
                        and semester_module_data["alter_grade"]
                    ):
                        module["grade"] = semester_module_data["alter_grade"]
                except Exception as e:
                    print(
                        f"Error fetching semester module data for ID {std_module_id}: {str(e)}"
                    )

            modules.append(module)

        return modules
