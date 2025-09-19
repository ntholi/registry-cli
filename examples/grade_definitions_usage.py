"""
Grade Definitions Usage Examples

This file demonstrates how to use the comprehensive grade definitions system
in the Limkokwing University Registry CLI.
"""

from typing import cast

from registry_cli.grade_definitions import (
    GRADE_DEFINITIONS,
    GradeDefinition,
    get_failing_grades,
    get_grade_by_marks,
    get_grade_definition,
    get_grade_description,
    get_grade_points,
    get_passing_grades,
    is_failing_grade,
    is_no_points_grade,
    is_passing_grade,
    is_supplementary_grade,
    normalize_grade_symbol,
)
from registry_cli.models import GradeType


def demo_basic_usage():
    """Demonstrate basic usage of the grade definitions system."""
    print("=== Basic Grade System Usage ===\n")

    # Get grade from marks
    marks = [95, 82, 67, 45, 30]
    print("Converting marks to grades:")
    for mark in marks:
        grade = get_grade_by_marks(mark)
        print(f"  {mark}% -> {grade}")

    print("\nGrade properties:")
    test_grades = [
        cast(GradeType, "A+"),
        cast(GradeType, "B-"),
        cast(GradeType, "PP"),
        cast(GradeType, "F"),
        cast(GradeType, "EXP"),
    ]
    for grade in test_grades:
        definition = get_grade_definition(grade)
        if definition:
            print(f"  {grade}: {definition.points} points - {definition.description}")

    print(f"\nPassing grades: {get_passing_grades()}")
    print(f"Failing grades: {get_failing_grades()}")


def demo_grade_validation():
    """Demonstrate grade validation functions."""
    print("\n=== Grade Validation ===\n")

    test_grades = [
        cast(GradeType, "A+"),
        cast(GradeType, "C-"),
        cast(GradeType, "PP"),
        cast(GradeType, "F"),
        cast(GradeType, "EXP"),
        cast(GradeType, "PC"),
        cast(GradeType, "DNS"),
    ]

    print("Grade validation results:")
    for grade in test_grades:
        passing = is_passing_grade(grade)
        failing = is_failing_grade(grade)
        supplementary = is_supplementary_grade(grade)
        no_points = is_no_points_grade(grade)

        status = []
        if passing:
            status.append("PASSING")
        if failing:
            status.append("FAILING")
        if supplementary:
            status.append("SUPPLEMENTARY")
        if no_points:
            status.append("NO_POINTS")

        print(f"  {grade}: {' | '.join(status) if status else 'NEUTRAL'}")


def demo_gpa_calculation():
    """Demonstrate how to use the system for GPA calculations."""
    print("\n=== GPA Calculation Example ===\n")

    # Sample student grades with credits
    student_grades = [
        (cast(GradeType, "A+"), 3),  # 3 credit hours
        (cast(GradeType, "B"), 4),  # 4 credit hours
        (cast(GradeType, "C+"), 2),  # 2 credit hours
        (cast(GradeType, "PP"), 3),  # 3 credit hours (0 points)
    ]

    total_points = 0
    total_credits = 0

    print("Student grades:")
    for grade, credits in student_grades:
        points = get_grade_points(grade)
        if points is not None:
            grade_points = points * credits
            total_points += grade_points
            total_credits += credits
            print(
                f"  {grade} ({credits} credits): {points} points/credit = {grade_points} total points"
            )
        else:
            print(f"  {grade} ({credits} credits): No points (excluded from GPA)")

    gpa = total_points / total_credits if total_credits > 0 else 0
    print(f"\nGPA: {total_points:.2f} points ÷ {total_credits} credits = {gpa:.2f}")


def demo_error_handling():
    """Demonstrate error handling with invalid grades."""
    print("\n=== Error Handling ===\n")

    test_inputs = [" A+ ", "b-", "invalid", "   pp   ", ""]

    print("Normalizing grade inputs:")
    for test_input in test_inputs:
        try:
            normalized = normalize_grade_symbol(test_input)
            print(f"  '{test_input}' -> '{normalized}' ✓")
        except ValueError as e:
            print(f"  '{test_input}' -> ERROR: {e}")


if __name__ == "__main__":
    demo_basic_usage()
    demo_grade_validation()
    demo_gpa_calculation()
    demo_error_handling()
