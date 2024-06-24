import logging

from eth_account.account import LocalAccount
from sqlalchemy.orm import Session

from database.token_store import TokenStore
from models.event import UpdateBalancesEvent
from models.event_handler import EventHandler
from models.token import TOKEN_ADDRESSES, TokenName
from web3_helper.abi import ABIFetcher, ABIManager
from web3_helper.helper import Web3Client

logger = logging.getLogger(__name__)


class UpdateBalancesHandler(EventHandler[UpdateBalancesEvent]):
    def __init__(
        self, *, wallet: LocalAccount, abi_fetcher: ABIFetcher, web3_client: Web3Client
    ) -> None:
        super().__init__()

        self.wallet = wallet
        self.abi_fetcher = abi_fetcher
        self.web3_client = web3_client

    def run(self, *, event: UpdateBalancesEvent, session: Session) -> None:
        abi_manager = ABIManager(session=session, abi_fetcher=self.abi_fetcher)

        for token in TokenStore(session).get_tokens_by_addresses(event.addresses):
            logger.info(f"Updating balance of {token.symbol}...")
            if token.address == TOKEN_ADDRESSES[TokenName.ETH]:
                token.balance = int(
                    self.web3_client.web3.eth.get_balance(account=self.wallet.address)
                )
            else:
                token_contract = self.web3_client.web3.eth.contract(
                    self.web3_client.to_checksum_address(token.address),
                    abi=abi_manager.get_abi(address=token.address),
                )
                token.balance = int(
                    token_contract.functions.balanceOf(self.wallet.address).call()
                )

        session.commit()
