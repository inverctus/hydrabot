from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from models.token import Position


class PositionStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_positions(self) -> Iterable[Position]:
        stmt = select(Position).options(joinedload(Position.pair))
        return self.session.scalars(stmt)

    def get_position(self, pair_address: str) -> Position | None:
        stmt = (
            select(Position)
            .where(Position.pair_address == pair_address)
            .options(joinedload(Position.pair))
        )
        return self.session.scalar(stmt)

    def add_position(self, position: Position) -> None:
        self.session.add(position)

    def delete_position(self, pair_address: str) -> None:
        stmt = delete(Position).where(Position.pair_address == pair_address)
        self.session.execute(stmt)
