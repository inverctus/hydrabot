from discord import TextChannel

from chatbot.command.base_command import BaseCommand
from database.pair_store import PairStore
from database.session_factory import SessionFactory
from database.token_store import TokenStore
from web3_helper.gas import GasHelper
from web3_helper.helper import Web3Client


class GasCommand(BaseCommand):
    def __init__(
        self, *, session_factory: SessionFactory, web3_client: Web3Client
    ) -> None:
        super().__init__(
            name="gas",
            short_hand="g",
            description="Show current gas fee",
        )

        self.session_factory = session_factory
        self.web3_client = web3_client
        self.gas_helper = GasHelper(web3_client=self.web3_client)

    async def execute(self, *, channel: TextChannel, args: list[str] = []) -> None:
        with self.session_factory.session() as session:
            if eth_token := TokenStore(session).get_token_by_symbol("ETH"):
                estimated_gas_fee = self.gas_helper.estimated_gas_price()
                fee = estimated_gas_fee.base_fee + estimated_gas_fee.priority_fee

                swap_price = float(
                    self.web3_client.web3.from_wei(fee, "ether") * 250_000
                )

                messages: list[str] = [
                    f"Current gas fee",
                    f"Average gas price: {float(self.web3_client.web3.from_wei(fee, 'ether')):0.10f} ETH",
                    f"Gas fee for a swap: ~{swap_price:0.6f} ETH",
                    f"Price in USD: ~{(eth_token.latest_price_usd*swap_price):0.4f} $",
                ]

                await channel.send("\n".join(messages))
