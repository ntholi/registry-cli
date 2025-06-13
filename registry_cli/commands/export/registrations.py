import csv
import os
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

import click
from sqlalchemy import func
from sqlalchemy.orm import Session

from registry_cli.models import (
    Program,
    RegistrationRequest,
    RequestedModule,
    Structure,
    Student,
    StudentProgram,
)


def export_program_registrations(db: Session) -> None:
    """Export registration statistics by program and semester to CSV files."""

    # Query to get all registered students grouped by program and semester
    query = (
        db.query(
            Program.name.label("program_name"),
            RegistrationRequest.semester_number,
            func.count(RegistrationRequest.std_no.distinct()).label("student_count"),
        )
        .join(Student, RegistrationRequest.std_no == Student.std_no)
        .join(StudentProgram, Student.std_no == StudentProgram.std_no)
        .join(Structure, StudentProgram.structure_id == Structure.id)
        .join(Program, Structure.program_id == Program.id)
        .filter(RegistrationRequest.status == "registered")
        .filter(StudentProgram.status == "Active")
        .group_by(Program.name, RegistrationRequest.semester_number)
        .order_by(Program.name, RegistrationRequest.semester_number)
    )

    results = query.all()

    if not results:
        click.secho("No registered students found.", fg="yellow")
        return

    # Group results by program
    program_data: Dict[str, Dict[int, int]] = defaultdict(dict)
    all_semesters = set()

    for program_name, semester_number, student_count in results:
        program_data[program_name][semester_number] = student_count
        all_semesters.add(semester_number)

    # Sort semesters for consistent output
    sorted_semesters = sorted(all_semesters)

    # Create output directory
    output_dir = "exports"
    os.makedirs(output_dir, exist_ok=True)

    # Generate timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Export to CSV
    csv_filename = f"program_registrations_{timestamp}.csv"
    csv_path = os.path.join(output_dir, csv_filename)

    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)

        # Write header
        header = ["program_name"] + [f"semester_{sem}" for sem in sorted_semesters]
        writer.writerow(header)
        # Write data for each program
        for program_name in sorted(program_data.keys()):
            row = [program_name]
            for semester in sorted_semesters:
                student_count = program_data[program_name].get(semester, 0)
                row.append(str(student_count))
            writer.writerow(row)

    click.secho(
        f"Successfully exported program registration statistics to: {csv_path}",
        fg="green",
    )

    # Print summary
    click.echo(f"\nSummary:")
    click.echo(f"- Total programs: {len(program_data)}")
    click.echo(f"- Semester range: {min(sorted_semesters)} to {max(sorted_semesters)}")
    click.echo(
        f"- Total registrations: {sum(sum(semester_data.values()) for semester_data in program_data.values())}"
    )

    # Show program breakdown
    click.echo(f"\nProgram breakdown:")
    for program_name in sorted(program_data.keys()):
        total_students = sum(program_data[program_name].values())
        click.echo(f"- {program_name}: {total_students} registrations")
