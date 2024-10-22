import logging

from discord.ext import commands, tasks

from database.token_store import TokenStore
from database.session_factory import SessionFactory
from ext_api.coinbase import CoinbaseAPI
from web3_helper.helper import Web3Client

logger = logging.getLogger(__name__)


class UpdateEtherPriceTask(commands.Cog):
    def __init__(self, session_factory: SessionFactory, web3_client: Web3Client):
        self.session_factory = session_factory
        self.web3_client = web3_client
        self.update.start()

    @tasks.loop(seconds=60)
    async def update(self):
        with self.session_factory.session() as session:
            if eth_token := TokenStore(session).get_token_by_symbol(token_symbol="ETH"):
                try:
                    price_usd = CoinbaseAPI().get_symbol_usd_price("ETH")
                    eth_token.latest_price_usd = price_usd
                    # also update WETH if it's there
                    if weth_token := TokenStore(session).get_token_by_symbol(
                        token_symbol="WETH"
                    ):
                        weth_token.latest_price_usd = price_usd

                    session.commit()
                except Exception:
                    logger.exception(
                        "Unable to get latest ETH/USD price via CoinbaseAPI"
                    )
