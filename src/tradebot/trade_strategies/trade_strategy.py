from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import Session

from models.token import Pair, PairQuote, Position, Token
from web3_helper.helper import Web3Client


class StrategyState(BaseModel):
    pass


T = TypeVar("T", bound="BaseModel")


class StrategyContext(Generic[T]):
    def __init__(
        self,
        *,
        pair: Pair,
        tick: int,
        state: T,
        latest_quote: PairQuote,
        base_token: Token,
        quote_token: Token,
        web3_client: Web3Client,
        position: Position | None = None,
    ) -> None:

        self.pair = pair
        self.tick = tick
        self.state = state
        self.latest_quote = latest_quote
        self.position = position
        self.base_token = base_token
        self.quote_token = quote_token
        self.web3_client = web3_client


class StrategyResult(Generic[T]):
    def __init__(self, state: T) -> None:
        self.state = state


class TradeStrategy(Generic[T]):
    def __init__(self) -> None:
        pass

    def dump_state(self, state: T) -> dict[str, Any]:
        raise NotImplementedError()

    def new_state(self) -> T:
        raise NotImplementedError()

    def state_from_dict(self, state_data: dict[str, Any]) -> T:
        raise NotImplementedError()

    def run(
        self, *, session: Session, context: StrategyContext[T]
    ) -> StrategyResult[T]:
        raise NotImplementedError()
