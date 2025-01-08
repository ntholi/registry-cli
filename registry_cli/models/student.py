from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )

    def __repr__(self) -> str:
        return f"Student(id={self.id!r}, name={self.name!r})"
