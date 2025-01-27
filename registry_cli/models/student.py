from datetime import date
from enum import Enum
from typing import List

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from registry_cli.models.base import Base
from registry_cli.models.structure import Structure


class Gender(Enum):
    Male = "Male"
    Female = "Female"
    Other = "Other"


class MaritalStatus(Enum):
    Single = "Single"
    Married = "Married"
    Divorced = "Divorced"
    Windowed = "Windowed"


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    std_no: Mapped[int] = mapped_column(unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    national_id: Mapped[str] = mapped_column(String(20), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    phone1: Mapped[str] = mapped_column(String(20))
    phone2: Mapped[str] = mapped_column(String(20))
    gender: Mapped[Gender] = mapped_column(nullable=False)
    marital_status: Mapped[MaritalStatus] = mapped_column()
    religion: Mapped[str] = mapped_column(String(100))

    structure_id: Mapped[int] = mapped_column(ForeignKey("structures.id"))
    structure: Mapped["Structure"] = relationship(
        "Structure", back_populates="students"
    )

    programs: Mapped[List["StudentProgram"]] = relationship(
        "StudentProgram", back_populates="student"
    )

    def __repr__(self) -> str:
        return f"Student(id={self.id!r}, name={self.name!r})"


class ProgramStatus(Enum):
    Active = "Active"
    Changed = "Changed"
    Completed = "Completed"
    Deleted = "Deleted"
    Inactive = "Inactive"


class StudentProgram(Base):
    __tablename__ = "student_programs"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10))
    name: Mapped[str] = mapped_column(String(50))
    status: Mapped[ProgramStatus] = mapped_column()
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    student: Mapped["Student"] = relationship("Student", back_populates="programs")
    semesters: Mapped[List["StudentSemester"]] = relationship(
        "StudentSemester",
        back_populates="student_program",
        cascade="all, delete-orphan",
    )


class SemesterStatus(Enum):
    Active = "Active"
    Deferred = "Deferred"
    Deleted = "Deleted"
    DNR = "DNR"
    DroppedOut = "DroppedOut"
    Enrolled = "Enrolled"
    Exempted = "Exempted"
    Inactive = "Inactive"
    Repeat = "Repeat"


class StudentSemester(Base):
    __tablename__ = "student_semesters"
    id: Mapped[int] = mapped_column(primary_key=True)
    term: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[SemesterStatus] = mapped_column()
    student_program_id: Mapped[int] = mapped_column(
        ForeignKey("student_programs.id"), nullable=False
    )
    student_program: Mapped["StudentProgram"] = relationship(
        "StudentProgram", back_populates="semesters"
    )
    modules: Mapped[List["StudentModule"]] = relationship(
        back_populates="student_semester", cascade="all, delete-orphan"
    )


class ModuleType(str, Enum):
    Major = "Major"
    Minor = "Minor"
    Core = "Core"


class StudentModule(Base):
    __tablename__ = "student_modules"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[ModuleType] = mapped_column(nullable=False)
    credits: Mapped[float] = mapped_column(Numeric(3, 1), nullable=False)
    marks: Mapped[float] = mapped_column(Numeric(4, 1), nullable=False)
    grade: Mapped[str] = mapped_column(String(2), nullable=False)
    student_semester_id: Mapped[int] = mapped_column(
        ForeignKey("student_semesters.id"), nullable=False
    )
    student_semester: Mapped["StudentSemester"] = relationship(back_populates="modules")
