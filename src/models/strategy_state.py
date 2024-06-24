from enum import StrEnum
from typing import Any

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class StrategyState(Base):
    __tablename__ = "strategy_states"

    id: Mapped[int] = mapped_column(primary_key=True)

    pair_address: Mapped[str] = mapped_column()
    strategy_name: Mapped[str] = mapped_column()

    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[int] = mapped_column(nullable=False)
    updated_at: Mapped[int | None] = mapped_column(nullable=True)

    def __init__(
        self,
        *,
        pair_address: str,
        strategy_name: str,
        data: dict[str, Any],
        created_at: int,
        updated_at: int | None = None,
    ) -> None:

        self.pair_address = pair_address
        self.strategy_name = strategy_name
        self.data = data
        self.created_at = created_at
        self.updated_at = updated_at
