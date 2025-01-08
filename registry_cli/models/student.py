from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from registry_cli.models.base import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )

    def __repr__(self) -> str:
        return f"Student(id={self.id!r}, name={self.name!r})"
