import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.strategy_state import StrategyState


class StrategyStateStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_or_update_state(self, strategy_state: StrategyState) -> None:
        stmt = (
            select(StrategyState)
            .where(
                StrategyState.pair_address == strategy_state.pair_address,
                StrategyState.strategy_name == strategy_state.strategy_name,
            )
            .order_by(StrategyState.updated_at.desc())
        )
        db_strategy_state = self.session.scalar(stmt)

        if db_strategy_state:
            db_strategy_state.data = strategy_state.data
            db_strategy_state.updated_at = int(time.time())
        else:
            self.session.add(strategy_state)

    def get_last_state(
        self, *, pair_address: str, strategy_name: str
    ) -> StrategyState | None:
        stmt = (
            select(StrategyState)
            .where(
                StrategyState.pair_address == pair_address,
                StrategyState.strategy_name == strategy_name,
            )
            .order_by(StrategyState.updated_at.desc())
        )
        return self.session.scalar(stmt)
