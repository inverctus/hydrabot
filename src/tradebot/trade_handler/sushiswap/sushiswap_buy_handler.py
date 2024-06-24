import time

from eth_account.account import LocalAccount
from sqlalchemy.orm import Session

from database.transaction_store import TransactionStore
from models.token import Pair, Transaction
from tradebot.event_handlers.error import TradeException, TradeInformationBuilder
from tradebot.trade_handler.handler import BaseTradeHandler, TradeResult, TradeStatus
from tradebot.trade_handler.payload import BuyPayload
from tradebot.trade_handler.sushiswap.constants import SUSHISWAP_ROUTER
from web3_helper.abi import ABIManager
from web3_helper.gas import GasHelper
from web3_helper.helper import Web3Client
from web3_helper.transaction_helper import TransactionHelper


class SushiSwapBuyHandler(BaseTradeHandler[BuyPayload]):
    def __init__(
        self, *, wallet: LocalAccount, web3_client: Web3Client, abi_manager: ABIManager
    ) -> None:
        super().__init__(wallet, web3_client)
        self.abi_manager = abi_manager
        self.gas_helper = GasHelper(web3_client=web3_client)

    def execute(
        self, *, pair: Pair, payload: BuyPayload, session: Session
    ) -> TradeResult | None:

        transaction_helper = TransactionHelper(
            web3_client=self.web3_client,
            abi_manager=self.abi_manager,
            gas_helper=self.gas_helper,
        )

        approve_result = transaction_helper.approve(
            wallet=self.wallet,
            allowance=payload.value,
            token_address=payload.quote_token.address,
            spender_address=SUSHISWAP_ROUTER,
        )

        if approve_result.tx_hash:
            TransactionStore(session).add_or_update_transaction(
                transaction=Transaction(
                    hash=approve_result.tx_hash,
                    details=f"Approve {payload.quote_token.address} for {payload.value}",
                    created_at=int(time.time()),
                )
            )

            session.commit()

        else:
            raise TradeException(
                message=f"Unable to approve {payload.quote_token.symbol} token for sell",
                trade_information=TradeInformationBuilder(
                    trade_handler=self.__class__.__name__,
                    amount=payload.value,
                    min_amount=payload.min_out,
                    source_address=payload.quote_token.address,
                    destination_address=payload.base_token.address,
                ).build(),
            )

        if swap_result := transaction_helper.swap_exact_tokens_for_tokens(
            wallet=self.wallet,
            source_token_address=payload.quote_token.address,
            destination_token_address=payload.base_token.address,
            amount_to_sell=payload.value,
            min_amount_out=payload.min_out,
            router_address=SUSHISWAP_ROUTER,
        ):
            TransactionStore(session).add_or_update_transaction(
                transaction=Transaction(
                    hash=swap_result.tx_hash,
                    details=f"{payload.quote_token.symbol} swapped for {payload.base_token.symbol}",
                    block_number=swap_result.block_number,
                    status=swap_result.status,
                    created_at=int(time.time()),
                    data=swap_result.sanitized_tx_params,
                )
            )
            session.commit()

            return TradeResult(
                status=TradeStatus.SUCCESS,
                message="",
                swap_tx=swap_result.tx_hash.hex(),
                allowance_tx=(
                    approve_result.tx_hash.hex() if approve_result.tx_hash else None
                ),
            )
        else:
            return TradeResult(status=TradeStatus.FAILED, message="Unexpected error")
