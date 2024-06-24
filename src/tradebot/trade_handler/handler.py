from enum import StrEnum
from typing import Any, Generic, TypeVar

from eth_account.account import LocalAccount
from sqlalchemy.orm import Session

from models.token import Pair
from web3_helper.helper import Web3Client

T = TypeVar("T")


class TradeStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"


class TradeResult:
    def __init__(
        self,
        *,
        status: TradeStatus,
        message: str = "",
        token_balance: int = 0,
        allowance_tx: str | None = None,
        swap_tx: str | None = None,
    ) -> None:
        self.status = status
        self.message = message
        self.token_balance = token_balance
        self.allowance_tx = allowance_tx
        self.swap_tx = swap_tx


class BaseTradeHandler(Generic[T]):
    def __init__(self, wallet: LocalAccount, web3_client: Web3Client) -> None:
        self.wallet = wallet
        self.web3_client = web3_client

    def execute(
        self,
        *,
        pair: Pair,
        payload: T,
        session: Session,
    ) -> TradeResult | None:
        raise NotImplementedError()
