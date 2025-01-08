from ctypes import Structure
from typing import List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from registry_cli.models.base import Base


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(
        String(10), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    structures: Mapped[List["Structure"]] = relationship(
        "Structure", back_populates="program", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Program(id={self.id!r}, code={self.code!r}, name={self.name!r})"
