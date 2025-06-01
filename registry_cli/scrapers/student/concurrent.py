from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Tuple

import click

from registry_cli.scrapers.student.module import StudentModuleScraper
from registry_cli.scrapers.student.semester import StudentSemesterScraper


class ConcurrentStudentDataCollector:
    """Concurrent data collector for student semester and module information."""

    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers

    def collect_program_data(self, program_id: int) -> Dict[str, Any]:
        """Collect all semester and module data for a program concurrently."""
        semester_scraper = StudentSemesterScraper(program_id)
        semesters_data = semester_scraper.scrape()

        if not semesters_data:
            return {"semesters": [], "modules_by_semester": {}}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            semester_module_futures = {
                semester["id"]: executor.submit(
                    self._fetch_semester_modules, semester["id"]
                )
                for semester in semesters_data
            }

            modules_by_semester = {}
            for semester_id, future in semester_module_futures.items():
                try:
                    modules_by_semester[semester_id] = future.result()
                except Exception as e:
                    click.secho(
                        f"Error fetching modules for semester {semester_id}: {str(e)}",
                        fg="red",
                    )
                    modules_by_semester[semester_id] = []

        return {
            "semesters": semesters_data,
            "modules_by_semester": modules_by_semester,
        }

    def _fetch_semester_modules(self, semester_id: int) -> List[Dict[str, Any]]:
        """Fetch module data for a semester."""
        try:
            module_scraper = StudentModuleScraper(semester_id)
            return module_scraper.scrape()
        except Exception as e:
            click.secho(
                f"Error scraping modules for semester {semester_id}: {str(e)}", fg="red"
            )
            return []
