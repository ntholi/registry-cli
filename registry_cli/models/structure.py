from enum import Enum
from typing import List
from sqlalchemy import String, ForeignKey, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from registry_cli.models.base import Base
from registry_cli.models.program import Program


class ModuleType(str, Enum):
    MAJOR = "Major"
    MINOR = "Minor"
    CORE = "Core"


class ModuleStatus(str, Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[ModuleType] = mapped_column(nullable=False)
    status: Mapped[ModuleStatus] = mapped_column(nullable=False, default=ModuleStatus.ACTIVE)
    credits: Mapped[float] = mapped_column(Numeric(3, 1), nullable=False)

    def __repr__(self) -> str:
        return f"Module(code={self.code!r}, name={self.name!r}, type={self.type!r}, credits={self.credits!r})"


class Semester(Base):
    __tablename__ = "semesters"

    id: Mapped[int] = mapped_column(primary_key=True)
    structure_id: Mapped[int] = mapped_column(ForeignKey("structures.id"), nullable=False)
    year: Mapped[int] = mapped_column(nullable=False)
    semester_number: Mapped[int] = mapped_column(nullable=False)
    total_credits: Mapped[float] = mapped_column(Numeric(4, 1), nullable=False)
    
    structure: Mapped["Structure"] = relationship("Structure", back_populates="semesters")
    modules: Mapped[List["SemesterModule"]] = relationship(back_populates="semester", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"Semester(year={self.year!r}, semester_number={self.semester_number!r}, total_credits={self.total_credits!r})"


class SemesterModule(Base):
    """Association table between Semester and Module with additional attributes"""
    __tablename__ = "semester_modules"

    id: Mapped[int] = mapped_column(primary_key=True)
    semester_id: Mapped[int] = mapped_column(ForeignKey("semesters.id"), nullable=False)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"), nullable=False)
    
    semester: Mapped["Semester"] = relationship(back_populates="modules")
    module: Mapped["Module"] = relationship()

    def __repr__(self) -> str:
        return f"SemesterModule(semester_id={self.semester_id!r}, module_id={self.module_id!r})"


class Structure(Base):
    __tablename__ = "structures"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id"), nullable=False)
    
    program: Mapped[Program] = relationship("Program", back_populates="structures")
    semesters: Mapped[List[Semester]] = relationship(back_populates="structure", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"Structure(id={self.id!r}, code={self.code!r}, program_id={self.program_id!r})"