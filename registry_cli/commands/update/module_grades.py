import math
import time
from typing import Dict, List, Tuple

import click
from sqlalchemy import and_
from sqlalchemy.orm import Session

from registry_cli.grade_definitions import get_grade_by_marks
from registry_cli.models import Assessment, AssessmentMark, GradeType, ModuleGrade


def calculate_weighted_total(
    db: Session, module_id: int, std_no: int
) -> Tuple[float, List[str]]:
    assessments = db.query(Assessment).filter(Assessment.module_id == module_id).all()

    if not assessments:
        return 0.0, ["No assessments found for module"]

    total_weighted_score = 0.0
    total_weight = 0.0
    calculation_details = []

    for assessment in assessments:
        assessment_mark = (
            db.query(AssessmentMark)
            .filter(
                and_(
                    AssessmentMark.assessment_id == assessment.id,
                    AssessmentMark.std_no == std_no,
                )
            )
            .first()
        )

        if assessment_mark:
            percentage = (assessment_mark.marks / assessment.total_marks) * 100
            weighted_score = percentage * (assessment.weight / 100)
            total_weighted_score += weighted_score
            total_weight += assessment.weight

            calculation_details.append(
                f"Assessment {assessment.assessment_number}: "
                f"{assessment_mark.marks}/{assessment.total_marks} "
                f"({percentage:.1f}%) × {assessment.weight}% weight = {weighted_score:.2f}"
            )
        else:
            calculation_details.append(
                f"Assessment {assessment.assessment_number}: No marks found"
            )

    if total_weight > 0:
        calculation_details.append(f"Total weight used: {total_weight}%")
        calculation_details.append(f"Final weighted total: {total_weighted_score:.2f}")

    return total_weighted_score, calculation_details


def calculate_grade(weighted_total: float) -> GradeType:
    """
    Calculate grade based on weighted total using the comprehensive grade definitions.

    Args:
        weighted_total: The calculated weighted total marks

    Returns:
        GradeType corresponding to the marks

    Raises:
        ValueError: If no grade can be determined for the given marks
    """
    # Round up the weighted total as was done previously
    marks = math.ceil(weighted_total)

    # Use the grade definitions to get the appropriate grade
    grade = get_grade_by_marks(marks)

    if grade is None:
        # Fallback to F if no grade found (should not happen with current definitions)
        return "F"

    return grade


def create_module_grades(db: Session, verbose: bool = False) -> None:
    click.echo("Calculating module grades from assessment marks...")

    distinct_combinations = (
        db.query(AssessmentMark.std_no, Assessment.module_id)
        .join(Assessment, AssessmentMark.assessment_id == Assessment.id)
        .distinct()
        .all()
    )

    if not distinct_combinations:
        click.secho("No assessment marks found to process.", fg="yellow")
        return

    created_count = 0
    skipped_count = 0
    error_count = 0
    total_combinations = len(distinct_combinations)

    click.echo(f"Found {total_combinations} student-module combinations to process")

    for index, (std_no, module_id) in enumerate(distinct_combinations, 1):
        try:
            progress_percent = int((index / total_combinations) * 100)
            click.echo(
                f"\rProcessing {index}/{total_combinations} ({progress_percent}%) ",
                nl=False,
            )

            existing_grade = (
                db.query(ModuleGrade)
                .filter(
                    and_(
                        ModuleGrade.module_id == module_id,
                        ModuleGrade.std_no == std_no,
                    )
                )
                .first()
            )

            if existing_grade:
                skipped_count += 1
                if verbose:
                    click.echo(
                        f"\nSkipping existing grade for student {std_no}, module {module_id}"
                    )
                continue

            weighted_total, calculation_details = calculate_weighted_total(
                db, module_id, std_no
            )

            if weighted_total <= 0:
                if verbose:
                    click.echo(
                        f"\nSkipping student {std_no}, module {module_id} - no valid assessment marks"
                    )
                continue

            grade = calculate_grade(weighted_total)
            current_time = int(time.time())

            module_grade = ModuleGrade(
                module_id=module_id,
                std_no=std_no,
                grade=grade,
                weighted_total=math.ceil(weighted_total),
                created_at=current_time,
                updated_at=current_time,
            )

            db.add(module_grade)
            created_count += 1

            if verbose:
                click.echo(f"\nCreated grade for student {std_no}, module {module_id}:")
                click.echo(f"  Grade: {grade}")
                click.echo(f"  Weighted Total: {math.ceil(weighted_total)}")
                for detail in calculation_details:
                    click.echo(f"  {detail}")

            if created_count % 50 == 0:
                db.commit()
                if verbose:
                    click.echo(f"\nCommitted batch of {created_count} grades")

        except Exception as e:
            error_count += 1
            if verbose:
                click.secho(
                    f"\nError processing student {std_no}, module {module_id}: {str(e)}",
                    fg="red",
                )

    try:
        db.commit()
        click.echo("\r" + " " * 80)
        click.secho(f"Successfully created {created_count} module grades", fg="green")

        if skipped_count > 0:
            click.secho(f"Skipped {skipped_count} existing grades", fg="blue")

        if error_count > 0:
            click.secho(f"Encountered {error_count} errors", fg="red")

    except Exception as e:
        db.rollback()
        click.secho(f"Error committing final batch: {str(e)}", fg="red")
