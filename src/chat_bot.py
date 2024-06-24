from chatbot.discord_chat_bot import DiscordChatBot
from database.session_factory import SessionFactory
from settings import SettingsFactory
from web3_helper.helper import Web3Helper

if __name__ == "__main__":
    chat_bot_settings = SettingsFactory.get_chat_bot_settings()

    db_session_factory = SessionFactory(chat_bot_settings["database_uri"])

    uni_chat_bot = DiscordChatBot(
        db_session_factory=db_session_factory,
        listen_channel_id=chat_bot_settings["listen_channel_id"],
        web3_client=Web3Helper.get_web3(chat_bot_settings["web3_provider_url"]),
        base_scan_api_key=chat_bot_settings["basescan_api_key"],
        allowed_user_ids=[
            int(user_id) for user_id in chat_bot_settings["user_ids"].split(",")
        ],
        web_api_key=chat_bot_settings["web_api_key"],
        web_api_uri=chat_bot_settings["web_api_uri"],
    )

    uni_chat_bot.run(chat_bot_settings["bot_token"])
