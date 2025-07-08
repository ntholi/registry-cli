import time
from typing import List

import click
from bs4 import BeautifulSoup, Tag
from sqlalchemy.orm import Session

from registry_cli.browser import BASE_URL, Browser, get_form_payload
from registry_cli.models import (
    Module,
    SemesterModule,
    StudentModule,
    StudentProgram,
    StudentSemester,
)


def update_student_module_refs(
    db: Session, std_nos: List[int], term: str, module_name: str, new_sem_module_id: int
) -> None:
    click.echo(
        f"Updating x_SemModuleID to {new_sem_module_id} for module '{module_name}' "
        f"for {len(std_nos)} students in term {term}"
    )

    browser = Browser()
    updated_count = 0
    skipped_count = 0
    error_count = 0
    total_modules = 0

    for i, std_no in enumerate(std_nos, 1):
        click.echo(f"Processing student {i}/{len(std_nos)}: {std_no}")

        program = (
            db.query(StudentProgram)
            .filter(StudentProgram.std_no == std_no)
            .where(StudentProgram.status == "Active")
            .first()
        )
        if not program:
            click.secho(f"No active program found for student {std_no}", fg="yellow")
            skipped_count += 1
            continue

        semester = (
            db.query(StudentSemester)
            .filter(
                StudentSemester.student_program_id == program.id,
                StudentSemester.term == term,
            )
            .first()
        )
        if not semester:
            click.secho(
                f"No semester found for student {std_no} in term {term}", fg="yellow"
            )
            skipped_count += 1
            continue

        student_modules = (
            db.query(StudentModule)
            .join(SemesterModule, StudentModule.semester_module_id == SemesterModule.id)
            .join(Module, SemesterModule.module_id == Module.id)
            .filter(
                StudentModule.student_semester_id == semester.id,
                Module.name.ilike(f"%{module_name}%"),
            )
            .all()
        )

        if not student_modules:
            click.secho(
                f"No modules matching '{module_name}' found for student {std_no} in term {term}",
                fg="yellow",
            )
            skipped_count += 1
            continue

        total_modules += len(student_modules)

        for student_module in student_modules:
            try:
                success = _update_module_ref_on_website(
                    browser, student_module.id, new_sem_module_id
                )

                if success:
                    student_module.semester_module_id = new_sem_module_id
                    updated_count += 1
                    click.secho(
                        f"✓ Updated module {student_module.id} for student {std_no}",
                        fg="green",
                    )
                else:
                    click.secho(
                        f"✗ Failed to update module {student_module.id} for student {std_no}",
                        fg="red",
                    )
                    error_count += 1

                time.sleep(1)

            except Exception as e:
                click.secho(
                    f"Error processing module {student_module.id} for student {std_no}: {str(e)}",
                    fg="red",
                )
                error_count += 1

    db.commit()

    click.echo(f"\nUpdate Summary:")
    click.echo(f"Total modules found: {total_modules}")
    click.secho(f"Successfully updated: {updated_count} modules", fg="green")
    if skipped_count > 0:
        click.secho(f"Skipped students: {skipped_count}", fg="blue")
    if error_count > 0:
        click.secho(f"Errors: {error_count} modules", fg="red")
    click.echo("------------------------------------------------\n")


def _update_module_ref_on_website(
    browser: Browser, std_module_id: int, new_sem_module_id: int
) -> bool:
    try:
        url = f"{BASE_URL}/r_stdmoduleedit.php?StdModuleID={std_module_id}"
        response = browser.fetch(url)
        soup = BeautifulSoup(response.text, "html.parser")

        form = soup.find("form", {"name": "fr_stdmoduleedit"})
        if not form or not isinstance(form, Tag):
            click.secho(f"Form not found for module {std_module_id}", fg="red")
            return False

        form_data = get_form_payload(form)

        form_data["a_edit"] = "U"
        form_data["x_SemModuleID"] = str(new_sem_module_id)

        post_url = f"{BASE_URL}/r_stdmoduleedit.php"
        post_response = browser.post(post_url, form_data)

        if post_response.status_code == 200:
            if (
                "successfully" in post_response.text.lower()
                or "updated" in post_response.text.lower()
            ):
                return True

            response_soup = BeautifulSoup(post_response.text, "html.parser")
            error_message = response_soup.find("div", class_="error")
            if error_message:
                click.secho(
                    f"Website error: {error_message.get_text(strip=True)}", fg="red"
                )
                return False

            return True
        else:
            click.secho(
                f"HTTP error {post_response.status_code} updating module {std_module_id}",
                fg="red",
            )
            return False

    except Exception as e:
        click.secho(f"Exception updating module {std_module_id}: {str(e)}", fg="red")
        return False
