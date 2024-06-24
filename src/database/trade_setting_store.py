from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.trade_setting import TradeSetting, TradeSettingName


class TradeSettingStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_settings(self) -> Iterable[TradeSetting]:
        stmt = select(TradeSetting)
        return self.session.scalars(stmt)

    def get_setting(self, setting_name: TradeSettingName) -> TradeSetting | None:
        stmt = select(TradeSetting).where(TradeSetting._name == setting_name.value)
        return self.session.scalar(stmt)

    def add_setting(self, trade_setting: TradeSetting) -> None:
        self.session.add(trade_setting)
