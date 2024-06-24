from enum import StrEnum

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class TradeSettingName(StrEnum):
    BUY_AMOUNT = "BUY_AMOUNT"
    SLIPPAGE = "SLIPPAGE"
    MIN_WETH_REQUIRED = "MIN_WETH_REQUIRED"
    MIN_ETH_REQUIRED = "MIN_ETH_REQUIRED"
    STOP_LOSS = "STOP_LOSS"


TRADE_SETTING_CAPTION: dict[TradeSettingName, str] = {
    TradeSettingName.BUY_AMOUNT: "Buy amount",
    TradeSettingName.SLIPPAGE: "Slippage",
    TradeSettingName.MIN_WETH_REQUIRED: "Minimum WETH required",
    TradeSettingName.MIN_ETH_REQUIRED: "Minimum ETH required",
    TradeSettingName.STOP_LOSS: "Stop loss",
}


TRADE_SETTING_CHAT_NAME: dict[TradeSettingName, str] = {
    TradeSettingName.BUY_AMOUNT: "buy",
    TradeSettingName.SLIPPAGE: "slippage",
    TradeSettingName.MIN_WETH_REQUIRED: "weth",
    TradeSettingName.MIN_ETH_REQUIRED: "eth",
    TradeSettingName.STOP_LOSS: "stoploss",
}


class TradeSetting(Base):
    __tablename__ = "trade_settings"

    _name: Mapped[str] = mapped_column("name", primary_key=True)
    value: Mapped[str] = mapped_column(nullable=False)

    def __init__(self, *, name: str, value: str | int | float) -> None:
        self._name = name
        self.value = str(value)

    @property
    def name(self) -> TradeSettingName:
        return TradeSettingName(self._name)

    def get_float(self) -> float:
        return float(self.value)

    def get_int(self) -> int:
        return int(self.value)
