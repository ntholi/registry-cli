from datetime import date
from enum import Enum

from sqlalchemy import Date, ForeignKey, String
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

    def __repr__(self) -> str:
        return f"Student(id={self.id!r}, name={self.name!r})"
