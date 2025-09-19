"""
Comprehensive grade definitions system for Limkokwing University.

This module defines all grade types, their point values, descriptions, and mark ranges
in a centralized location to replace hardcoded values throughout the application.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from registry_cli.models import GradeType


@dataclass
class MarkRange:
    """Represents a mark range with minimum and maximum values."""

    min: int
    max: int


@dataclass
class GradeDefinition:
    """Represents a complete grade definition with all properties."""

    grade: GradeType
    points: Optional[float]
    description: str
    marks_range: Optional[MarkRange] = None


# Comprehensive grade definitions based on Limkokwing University grading system
GRADE_DEFINITIONS: List[GradeDefinition] = [
    GradeDefinition(
        grade="A+",
        points=4.0,
        description="Distinction",
        marks_range=MarkRange(min=90, max=100),
    ),
    GradeDefinition(
        grade="A",
        points=4.0,
        description="Distinction",
        marks_range=MarkRange(min=85, max=89),
    ),
    GradeDefinition(
        grade="A-",
        points=4.0,
        description="Distinction",
        marks_range=MarkRange(min=80, max=84),
    ),
    GradeDefinition(
        grade="B+",
        points=3.67,
        description="Merit",
        marks_range=MarkRange(min=75, max=79),
    ),
    GradeDefinition(
        grade="B",
        points=3.33,
        description="Merit",
        marks_range=MarkRange(min=70, max=74),
    ),
    GradeDefinition(
        grade="B-",
        points=3.0,
        description="Merit",
        marks_range=MarkRange(min=65, max=69),
    ),
    GradeDefinition(
        grade="C+",
        points=2.67,
        description="Pass",
        marks_range=MarkRange(min=60, max=64),
    ),
    GradeDefinition(
        grade="C",
        points=2.33,
        description="Pass",
        marks_range=MarkRange(min=55, max=59),
    ),
    GradeDefinition(
        grade="C-",
        points=2.0,
        description="Pass",
        marks_range=MarkRange(min=50, max=54),
    ),
    GradeDefinition(
        grade="PP",
        points=0.0,
        description="Pass Provisional",
        marks_range=MarkRange(min=45, max=49),
    ),
    GradeDefinition(
        grade="F",
        points=0.0,
        description="Fail",
        marks_range=MarkRange(min=0, max=49),  # Updated to match JS code
    ),
    GradeDefinition(
        grade="EXP",
        points=None,
        description="Exempted",
    ),
    GradeDefinition(
        grade="PC",
        points=1.67,
        description="Pass Conceded",
    ),
    GradeDefinition(
        grade="PX",
        points=1.67,
        description="Pass (supplementary work submitted)",
    ),
    GradeDefinition(
        grade="AP",
        points=2.0,
        description="Aegrotat Pass",
    ),
    GradeDefinition(
        grade="X",
        points=0.0,
        description="Outstanding Supplementary Assessment",
    ),
    GradeDefinition(
        grade="Def",
        points=None,
        description="Deferred",
    ),
    GradeDefinition(
        grade="DEF",
        points=None,
        description="Deferred",
    ),
    GradeDefinition(
        grade="GNS",
        points=0.0,
        description="Grade Not Submitted",
    ),
    GradeDefinition(
        grade="ANN",
        points=0.0,
        description="Result Annulled Due To Misconduct",
    ),
    GradeDefinition(
        grade="FIN",
        points=0.0,
        description="Fail Incomplete",
    ),
    GradeDefinition(
        grade="FX",
        points=0.0,
        description="Fail (supplementary work submitted)",
    ),
    GradeDefinition(
        grade="DNC",
        points=0.0,
        description="Did Not Complete",
    ),
    GradeDefinition(
        grade="DNA",
        points=0.0,
        description="Did Not Attend",
    ),
    GradeDefinition(
        grade="DNS",
        points=0.0,
        description="Did Not Submit",
    ),
    GradeDefinition(
        grade="NM",
        points=None,
        description="No Mark",
    ),
]

# Create lookup dictionaries for quick access
_GRADE_LOOKUP: Dict[GradeType, GradeDefinition] = {
    grade_def.grade: grade_def for grade_def in GRADE_DEFINITIONS
}

_MARKS_TO_GRADE_LOOKUP: List[Tuple[MarkRange, GradeType]] = [
    (grade_def.marks_range, grade_def.grade)
    for grade_def in GRADE_DEFINITIONS
    if grade_def.marks_range is not None
]

# Sort by min mark in descending order for proper lookup
_MARKS_TO_GRADE_LOOKUP.sort(key=lambda x: x[0].min, reverse=True)


def get_grade_definition(grade: GradeType) -> Optional[GradeDefinition]:
    """
    Get the complete grade definition for a given grade.

    Args:
        grade: The grade symbol to look up

    Returns:
        GradeDefinition if found, None otherwise
    """
    return _GRADE_LOOKUP.get(grade)


def get_grade_points(grade: GradeType) -> Optional[float]:
    """
    Get the point value for a given grade.

    Args:
        grade: The grade symbol to look up

    Returns:
        Point value if found, None if grade not found or has no points
    """
    grade_def = get_grade_definition(grade)
    return grade_def.points if grade_def else None


def get_grade_description(grade: GradeType) -> Optional[str]:
    """
    Get the description for a given grade.

    Args:
        grade: The grade symbol to look up

    Returns:
        Description if found, None otherwise
    """
    grade_def = get_grade_definition(grade)
    return grade_def.description if grade_def else None


def get_grade_by_marks(marks: float) -> Optional[GradeType]:
    """
    Get the appropriate grade based on numerical marks.

    Args:
        marks: The numerical mark to convert to a grade

    Returns:
        GradeType if marks fall within a defined range, None otherwise
    """
    marks_int = int(marks)  # Convert to int for range comparison

    for mark_range, grade in _MARKS_TO_GRADE_LOOKUP:
        if mark_range.min <= marks_int <= mark_range.max:
            return grade

    return None


def is_passing_grade(grade: GradeType) -> bool:
    """
    Check if a grade is considered passing.
    A grade is passing if it has points greater than 0.

    Args:
        grade: The grade to check

    Returns:
        True if the grade is passing, False otherwise
    """
    points = get_grade_points(grade)
    return points is not None and points > 0


def is_failing_grade(grade: GradeType) -> bool:
    """
    Check if a grade is considered failing.
    Matches the JavaScript isFailingGrade function.

    Args:
        grade: The grade to check

    Returns:
        True if the grade is failing, False otherwise
    """
    failing_grades = ["F", "X", "GNS", "ANN", "FIN", "FX", "DNC", "DNA", "DNS"]
    return normalize_grade_symbol(grade) in failing_grades


def is_supplementary_grade(grade: GradeType) -> bool:
    """
    Check if a grade is supplementary (PP - Pass Provisional).

    Args:
        grade: The grade to check

    Returns:
        True if the grade is PP, False otherwise
    """
    return normalize_grade_symbol(grade) == "PP"


def is_failing_or_supplementary_grade(grade: GradeType) -> bool:
    """
    Check if a grade is failing or supplementary.
    Matches the JavaScript isFailingOrSupGrade function.

    Args:
        grade: The grade to check

    Returns:
        True if the grade is failing or supplementary, False otherwise
    """
    return is_failing_grade(grade) or is_supplementary_grade(grade)


def is_no_points_grade(grade: GradeType) -> bool:
    """
    Check if a grade has no point value (None).
    These are typically administrative grades like EXP, Def, NM.

    Args:
        grade: The grade to check

    Returns:
        True if the grade has no points, False otherwise
    """
    points = get_grade_points(grade)
    return points is None


def get_passing_grades() -> List[GradeType]:
    """
    Get a list of all passing grade symbols.

    Returns:
        List of GradeType symbols that are considered passing
    """
    return [
        grade_def.grade
        for grade_def in GRADE_DEFINITIONS
        if grade_def.points is not None and grade_def.points > 0
    ]


def get_failing_grades() -> List[GradeType]:
    """
    Get a list of all failing grade symbols.

    Returns:
        List of GradeType symbols that are considered failing
    """
    return [
        grade_def.grade
        for grade_def in GRADE_DEFINITIONS
        if grade_def.points is not None and grade_def.points == 0
    ]


def get_grades_with_marks_range() -> List[GradeType]:
    """
    Get a list of all grades that have defined mark ranges.
    These are typically used for calculating grades from numerical marks.

    Returns:
        List of GradeType symbols that have mark ranges
    """
    return [
        grade_def.grade
        for grade_def in GRADE_DEFINITIONS
        if grade_def.marks_range is not None
    ]


def normalize_grade_symbol(grade: str) -> GradeType:
    """
    Normalize grade symbol by trimming and converting to uppercase.

    Args:
        grade: The grade string to normalize

    Returns:
        Normalized GradeType

    Raises:
        ValueError: If the normalized grade is not a valid GradeType
    """
    normalized = grade.strip().upper()
    if normalized in _GRADE_LOOKUP:
        return normalized  # type: ignore
    else:
        raise ValueError(f"Invalid grade symbol: {normalized}")


def normalize_module_name(name: str) -> str:
    """
    Normalize module name for comparison.
    Matches the JavaScript normalizeModuleName function.
    Handles roman numerals, ampersands, and standardizes spacing.
    """
    # Convert roman numerals to arabic numbers
    roman_to_arabic = {
        "i": "1",
        "ii": "2",
        "iii": "3",
        "iv": "4",
        "v": "5",
        "vi": "6",
        "vii": "7",
        "viii": "8",
        "ix": "9",
        "x": "10",
    }

    # Normalize the name
    normalized = name.strip().lower().replace("&", "and")

    # Replace roman numerals with arabic numbers
    for roman, arabic in roman_to_arabic.items():
        pattern = r"\b" + roman + r"\b"
        normalized = re.sub(pattern, arabic, normalized)

    # Replace multiple spaces with single space and trim
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized


@dataclass
class GradePoint:
    """Represents grade point information for a semester."""

    semester_id: int
    gpa: float
    cgpa: float
    credits_attempted: float
    credits_completed: float


@dataclass
class SemesterSummary:
    """Summary of a semester's modules and calculations."""

    points: float
    credits_attempted: float
    credits_completed: float
    gpa: float
    is_no_marks: bool


def calculate_gpa(points: float, credits_for_gpa: float) -> float:
    """
    Calculate GPA from points and credits.
    Matches the JavaScript calculateGPA function.
    """
    return points / credits_for_gpa if credits_for_gpa > 0 else 0.0


def summarize_modules(modules: List[Dict]) -> SemesterSummary:
    """
    Summarize modules for GPA calculation.
    Matches the JavaScript summarizeModules function.

    Args:
        modules: List of student module dictionaries with keys:
                - grade: Grade symbol
                - status: Module status
                - credits: Module credits (from semester_module)

    Returns:
        SemesterSummary with calculated values
    """
    # Filter out deleted/dropped modules
    relevant = [m for m in modules if m.get("status", "") not in ["Delete", "Drop"]]

    points = 0.0
    credits_attempted = 0.0
    credits_for_gpa = 0.0

    # Calculate credits completed (modules with passing grades)
    credits_completed = 0.0
    for m in relevant:
        normalized_grade = normalize_grade_symbol(m.get("grade", ""))
        if normalized_grade not in ["NM", ""] and is_passing_grade(normalized_grade):
            credits_completed += m.get("credits", 0.0)

    # Calculate points and credits
    for m in relevant:
        grade = m.get("grade", "")
        credits = m.get("credits", 0.0)

        if not grade:
            continue

        try:
            normalized_grade = normalize_grade_symbol(grade)
        except ValueError:
            continue

        credits_attempted += credits

        # Only include in GPA calculation if grade is not NM (No Mark)
        if normalized_grade not in ["NM", ""]:
            credits_for_gpa += credits
            grade_points = get_grade_points(normalized_grade)
            if grade_points is not None:
                points += grade_points * credits

    gpa = calculate_gpa(points, credits_for_gpa)

    return SemesterSummary(
        points=points,
        credits_attempted=credits_attempted,
        credits_completed=credits_completed,
        gpa=gpa,
        is_no_marks=any(m.get("grade", "") == "NM" for m in relevant),
    )


def calculate_cgpa_from_semesters(
    semesters_data: List[Dict],
) -> Tuple[List[GradePoint], float]:
    """
    Calculate CGPA from multiple semesters.
    Returns list of GradePoint objects and final CGPA.

    Args:
        semesters_data: List of semester dictionaries with keys:
                      - id: Semester ID
                      - modules: List of module dictionaries

    Returns:
        Tuple of (grade_points_list, final_cgpa)
    """
    points = []
    cumulative_points = 0.0
    cumulative_credits_for_gpa = 0.0

    for semester in semesters_data:
        semester_modules = semester.get("modules", [])
        semester_summary = summarize_modules(semester_modules)

        cumulative_points += semester_summary.points

        # Calculate semester credits for GPA (excluding NM grades)
        semester_credits_for_gpa = sum(
            m.get("credits", 0.0)
            for m in semester_modules
            if m.get("status", "") not in ["Delete", "Drop"]
            and m.get("grade", "") not in ["", "NM"]
        )

        cumulative_credits_for_gpa += semester_credits_for_gpa
        cgpa = calculate_gpa(cumulative_points, cumulative_credits_for_gpa)

        points.append(
            GradePoint(
                semester_id=semester.get("id", 0),
                gpa=semester_summary.gpa,
                cgpa=cgpa,
                credits_attempted=semester_summary.credits_attempted,
                credits_completed=semester_summary.credits_completed,
            )
        )

    final_cgpa = points[-1].cgpa if points else 0.0
    return points, final_cgpa
