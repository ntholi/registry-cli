import re
from typing import Any, Dict, List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from registry_cli.browser import BASE_URL
from registry_cli.scrapers.base import BaseScraper


class ModuleScraper(BaseScraper):
    """Scraper for module data from the registry system."""

    def __init__(self):
        super().__init__(f"{BASE_URL}/f_modulelist.php")

    def scrape(self):
        """Scrape modules from all pages of the registry system.

        Yields:
            List of dictionaries containing module data from each page.
        """
        total_modules = 0
        current_page = 1
        total_pages = 1

        while current_page <= total_pages:
            if current_page == 1:
                url = f"{BASE_URL}/f_modulelist.php?start=1"
            else:
                start_index = (current_page - 1) * 10 + 1
                url = f"{BASE_URL}/f_modulelist.php?start={start_index}"

            self.url = url
            soup = self._get_soup()

            page_modules = self._parse_modules(soup)
            total_modules += len(page_modules)

            pager = soup.find("form", {"name": "ewpagerform"})
            if pager:
                page_links = pager.find_all("a", href=True)
                if page_links:
                    highest_page = 0
                    for link in page_links:
                        href = link.get("href", "")
                        match = re.search(r"start=(\d+)", href)
                        if match:
                            start_idx = int(match.group(1))
                            page_num = (start_idx - 1) // 10 + 1
                            highest_page = max(highest_page, page_num)

                    total_pages = max(total_pages, highest_page)

            print(
                f"Scraped page {current_page}/{total_pages}, found {len(page_modules)} modules"
            )

            # Yield modules from this page
            yield page_modules

            current_page += 1

        print(f"Total modules scraped: {total_modules}")

    def _parse_modules(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Parse modules from the HTML soup object.

        Args:
            soup: BeautifulSoup object containing module list HTML.

        Returns:
            List of dictionaries containing module data.
        """
        modules = []
        table = soup.find("table", {"id": "ewlistmain"})

        if not table:
            return modules

        rows = table.find_all("tr")
        # Skip header row
        for row in rows[1:]:
            cells = row.find_all("td")
            if len(cells) < 6:  # Ensure we have at least the minimum required cells
                continue

            # Extract module ID from the View link
            view_link = None
            for cell in cells[5:]:
                view_link = cell.find("a", href=True)
                if view_link and "moduleview" in view_link.get("href", "").lower():
                    break

            if not view_link:
                continue

            href = view_link.get("href", "")
            module_id_match = re.search(r"ModuleID=(\d+)", href)
            if not module_id_match:
                continue

            module_id = module_id_match.group(1)

            # Extract other module details
            module_code = cells[0].get_text(strip=True)
            module_name = cells[1].get_text(strip=True)
            status = cells[2].get_text(strip=True)
            total = cells[3].get_text(strip=True)
            date_stamp = cells[4].get_text(strip=True)

            # Clean up the total value to extract the number
            total_clean = re.search(r"\d+", total)
            total_value = int(total_clean.group(0)) if total_clean else 0

            module_data = {
                "id": int(module_id),
                "code": module_code,
                "name": module_name,
                "status": status,
                "total": total_value,
                "date_stamp": date_stamp,
            }

            modules.append(module_data)

        return modules
