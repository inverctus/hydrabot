from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.trade_setting_store import TradeSettingStore
from models.event import EventType, PersistedEventStatus
from models.trade_setting import TradeSettingName
from models.utils import get_position_metric
from tradebot.trade_strategies.trade_strategy import (
    StrategyContext,
    StrategyResult,
    TradeStrategy,
)
from tradebot.utils import push_chat_event, push_trade_event


class PrudentPumpStrategyState(BaseModel):
    highest_profit: float = 0
    retry_count: int = 0
    disabled: bool = False


class PrudentPumpStrategy(TradeStrategy[PrudentPumpStrategyState]):
    NAME = "prudent_pump"

    def __init__(self, pnl_sell: int = 50) -> None:
        super().__init__()
        self.pnl_sell = pnl_sell
        self.min_profit = 15
        self.profit_change = 0.10

    def new_state(self) -> PrudentPumpStrategyState:
        return PrudentPumpStrategyState()

    def state_from_dict(self, state_data: dict[str, Any]) -> PrudentPumpStrategyState:
        return PrudentPumpStrategyState.model_validate(state_data)

    def dump_state(self, state: PrudentPumpStrategyState) -> dict[str, Any]:
        return state.model_dump()

    def _sell_with_retry(
        self,
        *,
        session: Session,
        context: StrategyContext[PrudentPumpStrategyState],
        max_retry: int = 3,
    ) -> PrudentPumpStrategyState:

        trade_setting_store = TradeSettingStore(session)
        slippage_setting = trade_setting_store.get_setting(TradeSettingName.SLIPPAGE)

        slippage = slippage_setting.get_float() if slippage_setting else 0.1
        slippage = slippage + ((slippage / 2) * context.state.retry_count)
        retry_count = context.state.retry_count + 1

        if retry_count > 1:
            push_chat_event(
                session=session,
                message_data={
                    "message": f"Sell retry {retry_count} for {context.base_token.symbol}",
                },
            )

        event = push_trade_event(
            session=session,
            event_type=EventType.SELL,
            message_data={
                "pair": context.pair.address,
                "value": int(context.base_token.balance),
                "slippage": slippage,
            },
            wait_for_completion=True,
        )

        if event.status == PersistedEventStatus.COMPLETED:
            return PrudentPumpStrategyState(
                highest_profit=0,
                retry_count=0,
                disabled=True,
            )

        if retry_count >= max_retry:
            # max hitted
            push_chat_event(
                session=session,
                message_data={
                    "message": f"Unable to sell {context.base_token.symbol}, disabling pair {context.pair.address}..."
                },
            )

            context.pair.strategy = ""
            session.commit()

            return PrudentPumpStrategyState(
                highest_profit=context.state.highest_profit,
                retry_count=retry_count,
                disabled=True,
            )

        return PrudentPumpStrategyState(
            highest_profit=context.state.highest_profit,
            retry_count=retry_count,
            disabled=False,
        )

    def run(
        self, *, session: Session, context: StrategyContext[PrudentPumpStrategyState]
    ) -> StrategyResult[PrudentPumpStrategyState]:
        state = context.state
        if state.disabled:
            return StrategyResult(
                state=state,
            )

        if context.position and context.base_token.balance > 0:
            position_metric = get_position_metric(
                position=context.position,
                web3_client=context.web3_client,
                base_token=context.base_token,
                latest_quote=context.latest_quote,
            )

            if position_metric.profit_and_loss_percent > state.highest_profit:
                state.highest_profit = position_metric.profit_and_loss_percent

            if (
                state.highest_profit > self.min_profit
                and (state.highest_profit - (state.highest_profit * self.profit_change))
                > position_metric.profit_and_loss_percent
            ):
                push_chat_event(
                    session=session,
                    message_data={
                        "message": f"Profit decreasing rapidly for {context.base_token.symbol}, selling"
                    },
                )

                return StrategyResult(
                    state=self._sell_with_retry(
                        session=session,
                        context=context,
                    )
                )

            if position_metric.profit_and_loss_percent >= float(self.pnl_sell):
                push_chat_event(
                    session=session,
                    message_data={
                        "message": f"Profit target met for {context.base_token.symbol}, selling (retry={context.state.retry_count}/3)",
                    },
                )

                return StrategyResult(
                    state=self._sell_with_retry(
                        session=session,
                        context=context,
                    )
                )

            trade_setting_store = TradeSettingStore(session)
            stop_loss_setting = trade_setting_store.get_setting(
                TradeSettingName.STOP_LOSS
            )
            stop_loss = stop_loss_setting.get_float() if stop_loss_setting else -20
            if position_metric.profit_and_loss_percent <= stop_loss:
                push_chat_event(
                    session=session,
                    message_data={
                        "message": f"Stop loss hitted for {context.base_token.symbol}, selling"
                    },
                )

                return StrategyResult(
                    state=self._sell_with_retry(
                        session=session,
                        context=context,
                    )
                )

        return StrategyResult(
            state=state,
        )
