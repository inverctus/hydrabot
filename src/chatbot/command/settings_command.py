from discord import TextChannel

from chatbot.command.base_command import BaseCommand
from database.session_factory import SessionFactory
from models.trade_setting import (
    TRADE_SETTING_CAPTION,
    TRADE_SETTING_CHAT_NAME,
    TradeSettingName,
)
from settings.trade_settings_manager import TradeSettingsManager


class SettingsCommand(BaseCommand):
    def __init__(self, session_factory: SessionFactory) -> None:
        super().__init__(
            name="settings",
            description="View and change bot settings",
        )
        self.session_factory = session_factory

    async def execute(self, *, channel: TextChannel, args: list[str] = []) -> None:
        trade_settings_manager = TradeSettingsManager(self.session_factory)

        if not args:
            all_settings = trade_settings_manager.get_all_settings()
            messages: list[str] = [
                "Current setting(s)",
            ]

            messages.extend(
                [
                    f"{TRADE_SETTING_CAPTION[setting.name]} ({TRADE_SETTING_CHAT_NAME[setting.name]}) = {setting.value}"
                    for setting in all_settings
                ]
            )

            messages.extend(
                {
                    "To change settings, use settings command with name (in parathensis) and value"
                }
            )

            await channel.send("\n".join(messages))

        if args:
            setting_chat_name = args[0]
            trade_setting_name: TradeSettingName | None = None
            setting_value = args[1]

            for setting_name, chat_name in TRADE_SETTING_CHAT_NAME.items():
                if setting_chat_name == chat_name:
                    trade_setting_name = setting_name

            if not trade_setting_name:
                await channel.send(f"{setting_chat_name} isn't a valid setting name")
                return

            try:
                value = TradeSettingsManager.SETTINGS_TYPE[trade_setting_name](
                    setting_value
                )
                trade_settings_manager.save_setting(trade_setting_name, value)
                await channel.send(
                    f"{TRADE_SETTING_CAPTION[trade_setting_name]} was changed to {value}"
                )
            except:
                await channel.send(
                    f"{setting_value} isn't a valid value for {setting_chat_name}"
                )
