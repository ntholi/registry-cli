from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from registry_cli.models.base import Base


class ProgramStructure(Base):
    __tablename__ = "structures"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(
        String(10), unique=True, index=True, nullable=False
    )
