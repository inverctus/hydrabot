import logging
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.trade_setting_store import TradeSettingStore
from models.event import EventType
from models.trade_setting import TradeSettingName
from models.utils import get_position_metric
from tradebot.trade_strategies.trade_strategy import (
    StrategyContext,
    StrategyResult,
    TradeStrategy,
)
from tradebot.utils import push_trade_event

logger = logging.getLogger(__name__)


class StopLossStrategyState(BaseModel):
    pass


class StopLossStrategy(TradeStrategy[StopLossStrategyState]):
    NAME = "stop_loss"

    def __init__(self) -> None:
        super().__init__()

    def new_state(self) -> StopLossStrategyState:
        return StopLossStrategyState()

    def state_from_dict(self, state_data: dict[str, Any]) -> StopLossStrategyState:
        return StopLossStrategyState.model_validate(state_data)

    def dump_state(self, state: StopLossStrategyState) -> dict[str, Any]:
        return state.model_dump()

    def run(
        self, *, session: Session, context: StrategyContext[StopLossStrategyState]
    ) -> StrategyResult[StopLossStrategyState]:
        state = context.state
        if context.position and context.base_token.balance > 0:
            stop_loss_setting = TradeSettingStore(session).get_setting(
                TradeSettingName.STOP_LOSS
            )
            stop_loss = stop_loss_setting.get_float() if stop_loss_setting else -20

            position_metric = get_position_metric(
                position=context.position,
                web3_client=context.web3_client,
                base_token=context.base_token,
                latest_quote=context.latest_quote,
            )

            if position_metric.profit_and_loss_percent <= stop_loss:
                logger.info("Stop loss hit, selling")
                push_trade_event(
                    session=session,
                    event_type=EventType.SELL,
                    message_data={
                        "pair": context.pair.address,
                        "value": int(context.base_token.balance),
                    },
                    wait_for_completion=True,
                )

        return StrategyResult(
            state=state,
        )
