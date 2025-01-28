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

    std_no: Mapped[int] = mapped_column(primary_key=True)
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
        "StudentProgram", back_populates="student", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Student(std_no={self.std_no!r}, name={self.name!r}, national_id={self.national_id!r}, date_of_birth={self.date_of_birth!r}, gender={self.gender!r}, marital_status={self.marital_status!r})"


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
    std_no: Mapped[int] = mapped_column(ForeignKey("students.std_no"), nullable=False)
    student: Mapped["Student"] = relationship("Student", back_populates="programs")
    semesters: Mapped[List["StudentSemester"]] = relationship(
        "StudentSemester",
        back_populates="student_program",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"StudentProgram(id={self.id!r}, code={self.code!r}, name={self.name!r}, status={self.status!r}, std_no={self.std_no!r})"


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

    def __repr__(self) -> str:
        return f"StudentSemester(id={self.id!r}, term={self.term!r}, status={self.status!r}, student_program_id={self.student_program_id!r})"


class ModuleType(str, Enum):
    Major = "Major"
    Minor = "Minor"
    Core = "Core"


class ModuleStatus(str, Enum):
    Add = "Add"
    Compulsory = "Compulsory"
    Delete = "Delete"
    Drop = "Drop"
    Exempted = "Exempted"
    Ineligible = "Ineligible"
    Repeat1 = "Repeat1"
    Repeat2 = "Repeat2"
    Repeat3 = "Repeat3"
    Repeat4 = "Repeat4"
    Repeat5 = "Repeat5"
    Repeat6 = "Repeat6"
    Repeat7 = "Repeat7"
    Resit1 = "Resit1"
    Resit2 = "Resit2"
    Resit3 = "Resit3"
    Resit4 = "Resit4"
    Supplementary = "Supplementary"


class StudentModule(Base):
    __tablename__ = "student_modules"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[ModuleType] = mapped_column(nullable=False)
    status: Mapped[ModuleStatus] = mapped_column(nullable=False)
    credits: Mapped[float] = mapped_column(Numeric(3, 1), nullable=False)
    marks: Mapped[float] = mapped_column(String(10), nullable=False)
    grade: Mapped[str] = mapped_column(String(2), nullable=False)
    student_semester_id: Mapped[int] = mapped_column(
        ForeignKey("student_semesters.id"), nullable=False
    )
    student_semester: Mapped["StudentSemester"] = relationship(
        "StudentSemester", back_populates="modules"
    )

    def __repr__(self) -> str:
        return f"StudentModule(id={self.id!r}, code={self.code!r}, name={self.name!r}, type={self.type!r}, status={self.status!r}, credits={self.credits!r}, marks={self.marks!r}, grade={self.grade!r}, student_semester_id={self.student_semester_id!r})"
