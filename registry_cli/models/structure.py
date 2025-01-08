from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from registry_cli.models.base import Base
from registry_cli.models.program import Program


class Structure(Base):
    __tablename__ = "structures"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(
        String(10), unique=True, index=True, nullable=False
    )
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id"), nullable=False)
    program: Mapped[Program] = relationship("Program", back_populates="structures")

    def __repr__(self) -> str:
        return f"Structure(id={self.id!r}, code={self.code!r}, program_id={self.program_id!r})"
