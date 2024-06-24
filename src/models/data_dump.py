from enum import StrEnum

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class DumpType(StrEnum):
    CLOSED_POSITION = "closed-position"


class DataDump(Base):
    __tablename__ = "data_dumps"

    id: Mapped[int] = mapped_column(primary_key=True)

    _type: Mapped[str] = mapped_column("type")

    data: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[int] = mapped_column(nullable=False)

    def __init__(self, *, type: DumpType, data: dict, created_at: int) -> None:

        self.type = type
        self.data = data
        self.created_at = created_at

    @property
    def type(self) -> DumpType:
        return DumpType(self._type)

    @type.setter
    def type(self, value: DumpType) -> None:
        self._type = value.value
