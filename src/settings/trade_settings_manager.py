from database.session_factory import SessionFactory
from database.trade_setting_store import TradeSettingStore
from models.trade_setting import TradeSetting, TradeSettingName


class TradeSettingsManager:
    DEFAULT_SETTINGS = {
        TradeSettingName.BUY_AMOUNT: 0.001,
        TradeSettingName.SLIPPAGE: 0.10,
        TradeSettingName.MIN_ETH_REQUIRED: 0.0005,
        TradeSettingName.MIN_WETH_REQUIRED: 0.0003,
        TradeSettingName.STOP_LOSS: -20,
    }

    SETTINGS_TYPE = {
        TradeSettingName.BUY_AMOUNT: float,
        TradeSettingName.SLIPPAGE: float,
        TradeSettingName.MIN_ETH_REQUIRED: float,
        TradeSettingName.MIN_WETH_REQUIRED: float,
        TradeSettingName.STOP_LOSS: float,
    }

    def __init__(self, session_factory: SessionFactory) -> None:
        self.session_factory = session_factory
        self._settings: dict[TradeSettingName, TradeSetting] = {}

    def get_setting(self, setting_name: TradeSettingName) -> TradeSetting:
        if setting_name in self._settings:
            return self._settings[setting_name]

        with self.session_factory.session() as session:
            trade_setting_store = TradeSettingStore(session)
            trade_setting = trade_setting_store.get_setting(setting_name)

            if not trade_setting:
                trade_setting = TradeSetting(
                    name=setting_name.value, value=self.DEFAULT_SETTINGS[setting_name]
                )
                TradeSettingStore(session).add_setting(trade_setting)
                session.commit()

            self._settings[setting_name] = trade_setting
            session.expunge_all()

            return trade_setting

    def save_setting(
        self, setting_name: TradeSettingName, value: str | float | int
    ) -> None:
        with self.session_factory.session() as session:
            trade_setting_store = TradeSettingStore(session)
            trade_setting = trade_setting_store.get_setting(setting_name)
            if trade_setting:
                trade_setting.value = str(value)
            else:
                trade_setting = TradeSetting(
                    name=setting_name.value,
                    value=value,
                )

                trade_setting_store.add_setting(trade_setting)

            session.commit()

            self._settings[setting_name] = trade_setting

    def get_all_settings(self) -> list[TradeSetting]:
        trade_settings: list[TradeSetting] = []
        for trade_setting_name in TradeSettingName:
            trade_settings.append(self.get_setting(trade_setting_name))

        return trade_settings
