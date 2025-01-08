from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from registry_cli.models.student import Base


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[str] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(
        String(10), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    program_id: Mapped[str] = mapped_column(String(10), nullable=False)

    def __repr__(self) -> str:
        return f"Program(id={self.id!r}, code={self.code!r}, name={self.name!r}, program_id={self.program_id!r})"
