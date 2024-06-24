from database.session_factory import SessionFactory
from settings import SettingsFactory
from tradebot.strategies_worker import StrategiesWorker
from tradebot.trade_bot import TradeBot
from web3_helper.helper import Web3Helper

if __name__ == "__main__":
    bot_settings = SettingsFactory.get_trade_bot_setings()

    db_session_factory = SessionFactory(bot_settings["database_uri"])

    strategies_worker = StrategiesWorker(
        session_factory=db_session_factory,
        web3_client=Web3Helper.get_web3(bot_settings["web3_provider_url"]),
    )

    strategies_worker.start()

    trade_bot = TradeBot(
        wallet_private_key=bot_settings["wallet_private_key"],
        db_session_factory=db_session_factory,
        web3_provider_url=bot_settings["web3_provider_url"],
        base_scan_api_key=bot_settings["basescan_api_key"],
    )

    trade_bot.run()
