import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import click
from PyPDF2 import PdfReader, PdfWriter
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from registry_cli.models import (
    Clearance,
    GraduationClearance,
    GraduationRequest,
    Program,
    School,
    Structure,
    Student,
    StudentProgram,
)
from registry_cli.utils.certificate_generator import (
    TEMPLATE_PATH,
    OUTPUT_DIR,
    _build_overlay,
    expand_program_name,
)


def _get_cleared_students(db: Session) -> List[int]:
    """
    Get all students who have approved clearances from academic, finance, and library departments.
    
    Returns:
        List of student numbers (std_no) who have all required clearances approved.
    """
    # Define the three required departments for graduation
    required_departments = ["academic", "finance", "library"]
    required_dept_count = len(required_departments)

    # Query to find students with approved clearances from all required departments
    query = (
        db.query(StudentProgram.std_no)
        .select_from(GraduationRequest)
        .join(StudentProgram, GraduationRequest.student_program_id == StudentProgram.id)
        .join(
            GraduationClearance,
            GraduationRequest.id == GraduationClearance.graduation_request_id,
        )
        .join(Clearance, GraduationClearance.clearance_id == Clearance.id)
        .filter(
            and_(
                Clearance.status == "approved",
                Clearance.department.in_(required_departments),
            )
        )
        .group_by(StudentProgram.std_no)
        .having(func.count(func.distinct(Clearance.department)) == required_dept_count)
        .order_by(StudentProgram.std_no)
    )

    results = query.all()
    return [row.std_no for row in results]


def _get_student_details(db: Session, std_no: int) -> Optional[dict]:
    """
    Get student details including name, program, and school information.
    
    Args:
        db: Database session
        std_no: Student number
        
    Returns:
        Dictionary with student details or None if not found
    """
    query = (
        db.query(
            Student.std_no,
            Student.name.label("student_name"),
            Program.code.label("program_code"),
            Program.name.label("program_name"),
            School.name.label("school_name"),
        )
        .select_from(Student)
        .join(StudentProgram, Student.std_no == StudentProgram.std_no)
        .join(Structure, StudentProgram.structure_id == Structure.id)
        .join(Program, Structure.program_id == Program.id)
        .join(School, Program.school_id == School.id)
        .filter(Student.std_no == std_no)
        .first()
    )
    
    if query:
        return {
            "std_no": query.std_no,
            "student_name": query.student_name,
            "program_code": query.program_code,
            "program_name": query.program_name,
            "school_name": query.school_name,
        }
    return None


def _generate_single_certificate_overlay(
    name: str, program_name: str, program_code: str, std_no: int, temp_dir: Path
) -> Optional[Path]:
    """
    Generate a single certificate overlay for a student.
    
    Args:
        name: Student's name
        program_name: Program name
        program_code: Program code
        std_no: Student number
        temp_dir: Temporary directory to store the overlay
        
    Returns:
        Path to the generated overlay PDF or None if failed
    """
    try:
        # Expand abbreviated program name to full form
        expanded_program_name = expand_program_name(program_name)
        
        issue_date = datetime.now().strftime("%d %B %Y")
        reference = f"LSO{program_code}{std_no}"
        
        # Create temporary overlay file
        overlay_path = temp_dir / f"overlay_{name.replace(' ', '_')}.pdf"
        
        _build_overlay(name, expanded_program_name, reference, issue_date, overlay_path)
        
        return overlay_path if overlay_path.exists() else None
        
    except Exception as e:
        click.secho(f"    ❌ Error creating overlay for {name}: {str(e)}", fg="red")
        return None


def _combine_certificates_to_multi_page_pdf(
    students_data: List[dict], temp_dir: Path
) -> Optional[str]:
    """
    Generate a single multi-page PDF containing all certificates.
    
    Args:
        students_data: List of student data dictionaries
        temp_dir: Temporary directory for overlay files
        
    Returns:
        Path to the generated multi-page PDF or None if failed
    """
    try:
        if not TEMPLATE_PATH.exists():
            click.secho("❌ Template PDF not found", fg="red")
            return None
        
        # Create output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = OUTPUT_DIR / f"bulk_certificates_{timestamp}.pdf"
        
        # Ensure output directory exists
        OUTPUT_DIR.mkdir(exist_ok=True)
        
        writer = PdfWriter()
        
        successful_count = 0
        failed_count = 0
        
        for i, student in enumerate(students_data, 1):
            name = student['student_name']
            program_name = student['program_name']
            program_code = student['program_code']
            std_no = student['std_no']
            
            click.echo(f"  [{i:3d}/{len(students_data)}] Adding {std_no} - {name}...")
            
            # Generate overlay for this student
            overlay_path = _generate_single_certificate_overlay(name, program_name, program_code, std_no, temp_dir)
            
            if overlay_path and overlay_path.exists():
                try:
                    # Read template and overlay fresh for each student to avoid accumulation
                    base_reader = PdfReader(str(TEMPLATE_PATH))
                    overlay_reader = PdfReader(str(overlay_path))
                    
                    # Create a fresh copy of the template page for this student
                    base_page = base_reader.pages[0]
                    overlay_page = overlay_reader.pages[0]
                    
                    # Merge the overlay onto the fresh template copy
                    base_page.merge_page(overlay_page)
                    
                    # Add the merged page to the output PDF
                    writer.add_page(base_page)
                    
                    successful_count += 1
                    click.secho(f"    ✅ Added to PDF", fg="green")
                    
                except Exception as e:
                    click.secho(f"    ❌ Error merging certificate: {str(e)}", fg="red")
                    failed_count += 1
            else:
                click.secho(f"    ❌ Failed to create overlay", fg="red")
                failed_count += 1
        
        if successful_count > 0:
            # Write the combined PDF
            with open(output_file, "wb") as f_out:
                writer.write(f_out)
            
            click.echo(f"\n📊 Multi-page PDF Generation Summary:")
            click.secho(f"Successfully added: {successful_count} certificates", fg="green")
            if failed_count > 0:
                click.secho(f"Failed: {failed_count} certificates", fg="red")
            
            return str(output_file)
        else:
            click.secho("❌ No certificates were successfully generated", fg="red")
            return None
            
    except Exception as e:
        click.secho(f"❌ Error creating multi-page PDF: {str(e)}", fg="red")
        return None
    
def generate_certificates_for_cleared_students(
    db: Session, 
    limit: Optional[int] = None,
    dry_run: bool = False
) -> None:
    """
    Generate graduation certificates for all students who have been cleared by 
    academic, finance, and library departments. Creates a single multi-page PDF.
    
    Args:
        db: Database session
        limit: Optional limit on number of certificates to generate
        dry_run: If True, only show which students would get certificates without generating them
    """
    click.echo("Finding students with approved graduation clearances...")
    
    # Get all cleared students
    cleared_students = _get_cleared_students(db)
    
    if not cleared_students:
        click.secho(
            "No students found with approved clearances from all required departments (academic, finance, library).",
            fg="yellow",
        )
        return
    
    total_students = len(cleared_students)
    click.echo(f"Found {total_students} students with all required clearances approved")
    
    # Apply limit if specified
    if limit and limit < total_students:
        cleared_students = cleared_students[:limit]
        click.echo(f"Processing first {limit} students due to limit")
    
    if dry_run:
        click.echo("\n🔍 DRY RUN MODE - No certificates will be generated")
        click.echo("Students who would receive certificates:")
        
        for i, std_no in enumerate(cleared_students, 1):
            student_details = _get_student_details(db, std_no)
            if student_details:
                click.echo(
                    f"{i:3d}. {std_no} - {student_details['student_name']} "
                    f"({student_details['program_name']}, {student_details['school_name']})"
                )
            else:
                click.echo(f"{i:3d}. {std_no} - [Details not found]")
        
        click.echo(f"\nTotal certificates that would be generated: {len(cleared_students)}")
        return
    
    # Collect student data for multi-page PDF generation
    students_data = []
    missing_details = []
    
    click.echo(f"\n� Collecting student details for {len(cleared_students)} students...")
    
    for i, std_no in enumerate(cleared_students, 1):
        student_details = _get_student_details(db, std_no)
        
        if student_details:
            students_data.append(student_details)
            click.echo(f"[{i:3d}/{len(cleared_students)}] ✅ {std_no} - {student_details['student_name']}")
        else:
            missing_details.append(std_no)
            click.echo(f"[{i:3d}/{len(cleared_students)}] ❌ {std_no} - Details not found")
    
    if not students_data:
        click.secho("❌ No student details found. Cannot generate certificates.", fg="red")
        return
    
    if missing_details:
        click.echo(f"\n⚠️  Warning: {len(missing_details)} students skipped due to missing details:")
        for std_no in missing_details:
            click.echo(f"  - {std_no}")
    
    # Generate multi-page PDF
    click.echo(f"\n📜 Generating multi-page PDF with {len(students_data)} certificates...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        try:
            final_pdf_path = _combine_certificates_to_multi_page_pdf(students_data, temp_path)
            
            if final_pdf_path:
                click.echo(f"\n🎉 Success!")
                click.secho(f"Multi-page certificate PDF generated: {final_pdf_path}", fg="green")
                click.echo(f"Total certificates in PDF: {len(students_data)}")
                
                # Display summary by school/program
                from collections import Counter
                
                school_counts = Counter(student["school_name"] for student in students_data)
                program_counts = Counter(student["program_name"] for student in students_data)
                
                click.echo(f"\n📊 Summary by School:")
                for school, count in school_counts.most_common():
                    click.echo(f"  - {school}: {count} certificates")
                
                click.echo(f"\n📊 Summary by Program:")
                for program, count in program_counts.most_common():
                    click.echo(f"  - {program}: {count} certificates")
            else:
                click.secho("❌ Failed to generate multi-page PDF", fg="red")
                
        except Exception as e:
            click.secho(f"❌ Error during PDF generation: {str(e)}", fg="red")


@click.command(name="certificates-bulk")
@click.option(
    "--limit",
    type=int,
    help="Limit the number of certificates to generate (useful for testing)"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show which students would get certificates without actually generating them"
)
def certificates_bulk_cmd(limit: Optional[int], dry_run: bool) -> None:
    """
    Generate a single multi-page PDF containing graduation certificates for all 
    students who have been cleared by academic, finance, and library departments.
    
    This command will:
    1. Find all students with approved graduation requests that have clearances 
       from academic, finance, and library departments
    2. Generate a single PDF file with multiple pages, one certificate per page
    3. Provide a summary of the generated certificates and organize by school/program
    
    Use --dry-run to see which students would receive certificates without 
    actually generating them.
    
    Use --limit to restrict the number of certificates generated (useful for testing).
    
    Examples:
      registry-cli create certificates-bulk --dry-run
      registry-cli create certificates-bulk --limit 10
      registry-cli create certificates-bulk
    """
    from registry_cli.main import get_db

    db = get_db()
    generate_certificates_for_cleared_students(db, limit=limit, dry_run=dry_run)