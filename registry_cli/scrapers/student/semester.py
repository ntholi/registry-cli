from datetime import datetime
from typing import Any, Dict, List, cast

from bs4 import ResultSet, Tag

from registry_cli.browser import BASE_URL
from registry_cli.models import SemesterStatus
from registry_cli.scrapers.base import BaseScraper


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
                    print(
                        f"Error fetching semester details for ID {semester_id}: {str(e)}"
                    )

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
                            details["caf_date"] = datetime.strptime(
                                value, "%Y-%m-%d"
                            ).date()
                        except ValueError:
                            pass
                elif header == "Approval Date":
                    if value:
                        try:
                            details["approval_date"] = datetime.strptime(
                                value, "%Y-%m-%d"
                            ).date()
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
                            details["assist_approval_date"] = datetime.strptime(
                                value, "%Y-%m-%d"
                            ).date()
                        except ValueError:
                            pass
                elif header == "Asst-Start Date":
                    if value:
                        try:
                            details["assist_start_date"] = datetime.strptime(
                                value, "%Y-%m-%d"
                            ).date()
                        except ValueError:
                            pass
                elif header == "Asst-Expiry Date":
                    if value:
                        try:
                            details["assist_expiry_date"] = datetime.strptime(
                                value, "%Y-%m-%d"
                            ).date()
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
                            details["assist_bill_date"] = datetime.strptime(
                                value, "%Y-%m-%d"
                            ).date()
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
                            details["assist_appeal_date"] = datetime.strptime(
                                value, "%Y-%m-%d"
                            ).date()
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
                            details["defer_date"] = datetime.strptime(
                                value, "%Y-%m-%d"
                            ).date()
                        except ValueError:
                            pass
                elif header == "Return Date":
                    if value:
                        try:
                            details["return_date"] = datetime.strptime(
                                value, "%Y-%m-%d"
                            ).date()
                        except ValueError:
                            pass
                elif header == "Activation Date":
                    if value:
                        try:
                            details["activation_date"] = datetime.strptime(
                                value, "%Y-%m-%d"
                            ).date()
                        except ValueError:
                            pass

        return details
