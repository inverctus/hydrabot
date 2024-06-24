import os
from typing import Final, TypedDict

from dotenv import load_dotenv


class SettingsKey:
    DATABASE_URI = "DATABASE_URI"
    WALLET_PRIVATE_KEY = "WALLET_PRIVATE_KEY"
    BOT_TOKEN = "BOT_TOKEN"
    WEB3_PROVIDER_URL = "WEB3_PROVIDER_URL"
    LISTEN_CHANNEL_ID = "LISTEN_CHANNEL_ID"
    BASESCAN_API_KEY = "BASESCAN_API_KEY"
    USER_IDS = "USER_IDS"

    WEB_API_HOST = "WEB_API_HOST"
    WEB_API_KEY = "WEB_API_KEY"
    WEB_API_URI = "WEB_API_URI"


class Settings(TypedDict):
    database_uri: str
    wallet_private_key: str
    bot_token: str
    web3_provider_url: str
    listen_channel_id: str
    basescan_api_key: str
    user_ids: str


class ChatBotSettings(TypedDict):
    database_uri: str
    bot_token: str
    web3_provider_url: str
    listen_channel_id: str
    basescan_api_key: str
    user_ids: str
    web_api_key: str | None
    web_api_uri: str | None


class TradeBotSettings(TypedDict):
    database_uri: str
    wallet_private_key: str
    web3_provider_url: str
    basescan_api_key: str


class APISettings(TypedDict):
    api_host: str
    database_uri: str
    api_key: str


def try_get(setting_key: str) -> str | None:
    value = os.getenv(setting_key)
    return value


def must_get(setting_key: str) -> str:
    value = os.getenv(setting_key)

    if not value:
        raise Exception(f"Environment variable {setting_key} not defined")

    return value


DEFAULT_WEB_API_HOST: Final[str] = "0.0.0.0"
DEFAULT_WEB_API_URI: Final[str] = "http://localhost:5000/"


class SettingsFactory:

    @staticmethod
    def get_api_settings() -> APISettings:
        load_dotenv()

        return APISettings(
            database_uri=must_get(SettingsKey.DATABASE_URI),
            api_host=try_get(SettingsKey.WEB_API_HOST) or DEFAULT_WEB_API_HOST,
            api_key=must_get(SettingsKey.WEB_API_KEY),
        )

    @staticmethod
    def get_chat_bot_settings() -> ChatBotSettings:
        load_dotenv()

        return ChatBotSettings(
            database_uri=must_get(SettingsKey.DATABASE_URI),
            bot_token=must_get(SettingsKey.BOT_TOKEN),
            web3_provider_url=must_get(SettingsKey.WEB3_PROVIDER_URL),
            listen_channel_id=must_get(SettingsKey.LISTEN_CHANNEL_ID),
            basescan_api_key=must_get(SettingsKey.BASESCAN_API_KEY),
            user_ids=must_get(SettingsKey.USER_IDS),
            web_api_key=try_get(SettingsKey.WEB_API_KEY),
            web_api_uri=try_get(SettingsKey.WEB_API_URI) or DEFAULT_WEB_API_URI,
        )

    @staticmethod
    def get_trade_bot_setings() -> TradeBotSettings:
        load_dotenv()

        return TradeBotSettings(
            database_uri=must_get(SettingsKey.DATABASE_URI),
            wallet_private_key=must_get(SettingsKey.WALLET_PRIVATE_KEY),
            web3_provider_url=must_get(SettingsKey.WEB3_PROVIDER_URL),
            basescan_api_key=must_get(SettingsKey.BASESCAN_API_KEY),
        )
