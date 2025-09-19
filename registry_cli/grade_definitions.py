"""
Comprehensive grade definitions system for Limkokwing University.

This module defines all grade types, their point values, descriptions, and mark ranges
in a centralized location to replace hardcoded values throughout the application.
"""

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
        description="Pass with Distinction",
        marks_range=MarkRange(min=90, max=100),
    ),
    GradeDefinition(
        grade="A",
        points=4.0,
        description="Pass with Distinction",
        marks_range=MarkRange(min=85, max=89),
    ),
    GradeDefinition(
        grade="A-",
        points=4.0,
        description="Pass with Distinction",
        marks_range=MarkRange(min=80, max=84),
    ),
    GradeDefinition(
        grade="B+",
        points=3.67,
        description="Pass with Merit",
        marks_range=MarkRange(min=75, max=79),
    ),
    GradeDefinition(
        grade="B",
        points=3.33,
        description="Pass with Merit",
        marks_range=MarkRange(min=70, max=74),
    ),
    GradeDefinition(
        grade="B-",
        points=3.0,
        description="Pass with Merit",
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
        marks_range=MarkRange(
            min=0, max=44
        ),  # Note: F covers 0-44, not overlapping with PP
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
    A grade is failing if it has points equal to 0.

    Args:
        grade: The grade to check

    Returns:
        True if the grade is failing, False otherwise
    """
    points = get_grade_points(grade)
    return points is not None and points == 0


def is_supplementary_grade(grade: GradeType) -> bool:
    """
    Check if a grade is supplementary (PP - Pass Provisional).

    Args:
        grade: The grade to check

    Returns:
        True if the grade is PP, False otherwise
    """
    return grade == "PP"


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
