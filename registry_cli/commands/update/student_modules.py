import time
from typing import Dict, List, Optional

import click
from bs4 import BeautifulSoup, Tag
from sqlalchemy.orm import Session

from registry_cli.browser import BASE_URL, Browser, get_form_payload
from registry_cli.models import (
    ModuleGrade,
    SemesterModule,
    StudentModule,
    StudentProgram,
    StudentSemester,
)


def update_student_modules(db: Session, std_no: int, term: str) -> None:
    click.echo(f"Updating module marks and grades for student {std_no} in term {term}")

    program = (
        db.query(StudentProgram)
        .filter(StudentProgram.std_no == std_no)
        .where(StudentProgram.status == "Active")
        .first()
    )
    if not program:
        click.secho(f"No program found for student {std_no}", fg="red")
        return

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
            f"No semester found for student '{std_no}' in term '{term}'", fg="red"
        )
        return

    student_modules = (
        db.query(StudentModule)
        .filter(StudentModule.student_semester_id == semester.id)
        .all()
    )

    if not student_modules:
        click.secho(
            f"No modules found for student {std_no} in term {term}", fg="yellow"
        )
        return

    browser = Browser()
    updated_count = 0
    skipped_count = 0
    error_count = 0

    click.echo(f"Found {len(student_modules)} modules to update")

    for i, student_module in enumerate(student_modules, 1):
        try:
            click.echo(
                f"Processing module {i}/{len(student_modules)}: {student_module.id}"
            )

            semester_module = (
                db.query(SemesterModule)
                .filter(SemesterModule.id == student_module.semester_module_id)
                .first()
            )

            if not semester_module or not semester_module.module_id:
                click.secho(
                    f"Warning: SemesterModule or Module not found for StudentModule {student_module.id}",
                    fg="yellow",
                )
                skipped_count += 1
                continue

            module_grade = (
                db.query(ModuleGrade)
                .filter(
                    ModuleGrade.module_id == semester_module.module_id,
                    ModuleGrade.std_no == std_no,
                )
                .first()
            )

            if not module_grade:
                click.secho(
                    f"Warning: No module grade found for student {std_no}, module {semester_module.module_id}",
                    fg="yellow",
                )
                skipped_count += 1
                continue

            success = _update_module_on_website(
                browser,
                student_module.id,
                module_grade.weighted_total,
                module_grade.grade,
                student_module.status,
            )

            if success:
                student_module.marks = str(int(module_grade.weighted_total))
                student_module.grade = module_grade.grade
                updated_count += 1
                click.secho(
                    f"✓ Updated module {student_module.id}: mark={module_grade.weighted_total}, grade={module_grade.grade}",
                    fg="green",
                )
            else:
                click.secho(
                    f"✗ Failed to update module {student_module.id} on website",
                    fg="red",
                )
                error_count += 1

            time.sleep(1)

        except Exception as e:
            click.secho(
                f"Error processing module {student_module.id}: {str(e)}", fg="red"
            )
            error_count += 1

    db.commit()

    click.echo(f"\nUpdate Summary:")
    click.secho(f"Successfully updated: {updated_count} modules", fg="green")
    if skipped_count > 0:
        click.secho(f"Skipped: {skipped_count} modules", fg="blue")
    if error_count > 0:
        click.secho(f"Errors: {error_count} modules", fg="red")
    click.echo("------------------------------------------------\n")


def _update_module_on_website(
    browser: Browser, std_module_id: int, mark: float, grade: str, status: str
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
        form_data["x_StdModMark"] = str(int(mark))
        form_data["x_StdModGrade"] = grade
        form_data["x_StdModStatCode"] = status
        form_data["x_StdModFee"] = ""

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
