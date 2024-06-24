import logging

from eth_account.account import LocalAccount
from sqlalchemy.orm import Session

from database.token_store import TokenStore
from models.event import WrapEvent
from models.event_handler import EventHandler
from models.token import Addresses
from tradebot.utils import push_chat_event
from web3_helper.abi import ABIFetcher, ABIManager
from web3_helper.gas import GasHelper
from web3_helper.helper import Web3Client
from web3_helper.transaction_helper import TransactionHelper

logger = logging.getLogger(__name__)


class WrapHandler(EventHandler[WrapEvent]):
    def __init__(
        self, wallet: LocalAccount, web3_client: Web3Client, abi_fetcher: ABIFetcher
    ) -> None:
        super().__init__()

        self.wallet = wallet
        self.abi_fetcher = abi_fetcher
        self.web3_client = web3_client

    def run(self, *, event: WrapEvent, session: Session) -> None:
        try:
            pair_store = TokenStore(session)
            abi_manager = ABIManager(session=session, abi_fetcher=self.abi_fetcher)
            eth_token = pair_store.get_token(str(Addresses.ETH))
            weth_token = pair_store.get_token(str(Addresses.WETH))

            if not eth_token or not weth_token:
                raise Exception("Missing token reference")

            weth_contract = self.web3_client.web3.eth.contract(
                self.web3_client.to_checksum_address(weth_token.address),
                abi=abi_manager.get_abi(address=weth_token.address),
            )

            if eth_token.balance < event.value:
                raise Exception("Not enough ETH to wrap")

            transaction_helper = TransactionHelper(
                web3_client=self.web3_client,
                abi_manager=abi_manager,
                gas_helper=GasHelper(web3_client=self.web3_client),
            )

            result = transaction_helper.wrap_eth(
                amount_in=event.value,
                weth_address=weth_token.address,
                wallet=self.wallet,
            )

            eth_token.balance = int(
                self.web3_client.web3.eth.get_balance(self.wallet.address)
            )
            weth_token.balance = int(
                weth_contract.functions.balanceOf(self.wallet.address).call()
            )

            session.commit()

        except Exception as exp:
            push_chat_event(
                session=session,
                message_data={"message": f"Error while wrapping ETH, {exp}"},
            )
            logger.exception("Error while wrapping ETH")
