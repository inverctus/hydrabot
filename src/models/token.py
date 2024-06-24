import hashlib
import json
import time
from decimal import Decimal
from enum import StrEnum
from typing import Any

from hexbytes import HexBytes
from pydantic import BaseModel
from sqlalchemy import NUMERIC, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.dex_id import DexId


class TokenName(StrEnum):
    WETH = "weth"
    ETH = "eth"


TOKEN_ADDRESSES: dict[TokenName, str] = {
    TokenName.ETH: "0x0000000000000000000000000000000000000000",
    TokenName.WETH: "0x4200000000000000000000000000000000000006",
}


class Addresses(StrEnum):
    # UNISWAP_UNIVERSAL_ROUTER = "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD"
    # PERMIT2 = "0x000000000022D473030F116dDEE9F6B43aC78BA3"
    WETH = "0x4200000000000000000000000000000000000006"
    ETH = "0x0000000000000000000000000000000000000000"


CONTRACT_TTL = 60 * 60 * 24  # 1 days


class ContractCache(Base):
    __tablename__ = "contracts"

    address: Mapped[str] = mapped_column(primary_key=True)
    contract: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[int] = mapped_column(nullable=False)
    updated_at: Mapped[int | None] = mapped_column(nullable=True)

    def __init__(
        self,
        *,
        address: str,
        contract: dict[str, Any],
        created_at: int,
        updated_at: int | None = None,
    ) -> None:
        self.address = address
        self.contract = contract
        self.created_at = created_at
        self.updated_at = updated_at


class Transaction(Base):
    __tablename__ = "transactions"

    hash: Mapped[str] = mapped_column(primary_key=True)
    details: Mapped[str] = mapped_column(nullable=False)
    block_number: Mapped[int | None] = mapped_column(NUMERIC, nullable=True)
    status: Mapped[int | None] = mapped_column(nullable=True)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[int] = mapped_column(nullable=False)

    def __init__(
        self,
        *,
        hash: str | HexBytes,
        details: str,
        created_at: int,
        block_number: int | None = None,
        status: int | None = None,
        data: dict[str, Any] = {},
    ) -> None:

        self.hash = hash if isinstance(hash, str) else hash.hex()
        self.details = details
        self.created_at = created_at
        self.block_number = block_number
        self.status = status
        self.data = data


class Token(Base):
    __tablename__ = "tokens"

    address: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    symbol: Mapped[str] = mapped_column(nullable=False)
    balance: Mapped[int] = mapped_column(NUMERIC, nullable=False)
    decimals: Mapped[int] = mapped_column(nullable=False)
    latest_price_usd: Mapped[float] = mapped_column(nullable=True)

    def __init__(
        self,
        *,
        address: str,
        name: str,
        symbol: str,
        decimals: int,
        balance: int = 0,
        latest_price_usd: float = 0,
    ) -> None:

        self.address = address
        self.name = name
        self.symbol = symbol
        self.balance = balance
        self.decimals = decimals
        self.latest_price_usd = latest_price_usd

    def balance_biggest(self) -> int:
        return int(Decimal(self.balance) / Decimal(10**self.decimals))

    def asdict(self) -> dict:
        return {
            "address": self.address,
            "name": self.name,
            "symbol": self.symbol,
            "decimals": self.decimals,
            "balance": int(self.balance),
            "latest_price_usd": float(self.latest_price_usd),
        }


class Pair(Base):
    __tablename__ = "pairs"

    address: Mapped[str] = mapped_column(primary_key=True)
    base_address: Mapped[str] = mapped_column(
        ForeignKey("tokens.address"), nullable=False
    )

    base_token: Mapped[Token] = relationship(Token, foreign_keys=[base_address])

    quote_address: Mapped[str] = mapped_column(
        ForeignKey("tokens.address"), nullable=False
    )

    _dex: Mapped[str] = mapped_column("dex", nullable=False)
    chain: Mapped[str] = mapped_column(nullable=False)

    message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    strategy: Mapped[str | None] = mapped_column(nullable=True)

    def __init__(
        self,
        address: str,
        base_address: str,
        quote_address: str,
        dex: DexId,
        chain: str,
        message_id: int | None = None,
        strategy: str | None = None,
    ) -> None:
        self.address = address
        self.base_address = base_address
        self.quote_address = quote_address
        self.dex = dex
        self.chain = chain
        self.message_id = message_id
        self.strategy = strategy

    @property
    def dex(self) -> DexId:
        return DexId.from_str(self._dex)

    @dex.setter
    def dex(self, value: DexId) -> None:
        self._dex = value.to_str()

    def asdict(self) -> dict:
        return {
            "address": self.address,
            "base_address": self.base_address,
            "quote_address": self.quote_address,
            "dex": self._dex,
            "chain": self.chain,
            "messsage_id": self.message_id,
            "strategy": self.strategy,
        }


class PairPriceAlert(Base):
    __tablename__ = "pair_price_alerts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    pair_address: Mapped[str] = mapped_column(ForeignKey("pairs.address"))
    created_at: Mapped[int] = mapped_column(nullable=False)
    price: Mapped[int] = mapped_column(NUMERIC, nullable=False)
    pnl_percent: Mapped[Decimal] = mapped_column(NUMERIC, nullable=False)
    pnl: Mapped[Decimal] = mapped_column(NUMERIC, nullable=False)

    def __init__(
        self,
        *,
        pair_address: str,
        price: int,
        pnl_percent: Decimal,
        pnl: Decimal,
        created_at: int,
    ) -> None:

        self.pair_address = pair_address
        self.price = price
        self.pnl_percent = pnl_percent
        self.pnl = pnl
        self.created_at = created_at


class PairQuote(Base):
    __tablename__ = "pair_quotes"

    pair_quote_id: Mapped[int] = mapped_column(primary_key=True)
    pair_address: Mapped[str] = mapped_column(ForeignKey("pairs.address"))
    price: Mapped[int] = mapped_column(NUMERIC, nullable=False)

    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    data_hash: Mapped[str] = mapped_column(nullable=False)

    timestamp: Mapped[int] = mapped_column(nullable=False)

    def _hash_data(self) -> str:
        return hashlib.sha256(json.dumps(self.data).encode()).hexdigest()

    def __init__(
        self,
        *,
        pair_address: str,
        price: int,
        data: dict,
        timestamp: int,
    ) -> None:

        self.pair_address = pair_address
        self.price = price
        self.data = data
        self.data_hash = self._hash_data()
        self.timestamp = timestamp


class PositionMetric(BaseModel):
    market_value: Decimal
    price_paid: Decimal
    profit_and_loss: Decimal
    profit_and_loss_percent: float


class Position(Base):
    __tablename__ = "positions"

    pair_address: Mapped[str] = mapped_column(
        ForeignKey("pairs.address"), primary_key=True
    )
    pair: Mapped[Pair] = relationship()

    token_sold: Mapped[int] = mapped_column(NUMERIC, nullable=False)
    token_bought: Mapped[int] = mapped_column(NUMERIC, nullable=False)

    book_value: Mapped[int] = mapped_column(NUMERIC, nullable=False)

    created_at: Mapped[int] = mapped_column(nullable=False)
    last_action_at: Mapped[int | None] = mapped_column(nullable=True)

    realized_pnl: Mapped[int] = mapped_column(NUMERIC, nullable=False)

    def __init__(
        self,
        *,
        pair_address: str,
        created_at: int,
        token_sold: int = 0,
        token_bought: int = 0,
        book_value: int = 0,
        last_action_at: int | None = None,
        realized_pnl: int = 0,
    ) -> None:

        self.pair_address = pair_address
        self.created_at = created_at
        self.token_sold = token_sold
        self.token_bought = token_bought
        self.book_value = book_value
        self.last_action_at = last_action_at
        self.realized_pnl = realized_pnl

    def as_dict(self) -> dict:
        return {
            "pair_address": self.pair_address,
            "token_sold": int(self.token_sold),
            "token_bought": int(self.token_bought),
            "book_value": int(self.book_value),
            "created_at": self.created_at,
            "last_action_at": self.last_action_at,
            "realized_pnl": int(self.realized_pnl),
        }
