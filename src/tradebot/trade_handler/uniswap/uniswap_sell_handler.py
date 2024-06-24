import time

from eth_account.account import LocalAccount
from sqlalchemy.orm import Session

from database.transaction_store import TransactionStore
from models.token import Pair, Transaction
from tradebot.trade_handler.handler import BaseTradeHandler, TradeResult, TradeStatus
from tradebot.trade_handler.payload import SellPayload
from tradebot.trade_handler.uniswap.constants import PERMIT2, UNISWAP_UNIVERSAL_ROUTER
from web3_helper.abi import ABIManager
from web3_helper.gas import GasHelper
from web3_helper.helper import Web3Client
from web3_helper.transaction_helper import SwapResult, UniswapTransactionHelper


class UniswapSellHandler(BaseTradeHandler[SellPayload]):
    def __init__(
        self, *, wallet: LocalAccount, web3_client: Web3Client, abi_manager: ABIManager
    ) -> None:
        super().__init__(wallet, web3_client)
        self.abi_manager = abi_manager
        self.gas_helper = GasHelper(web3_client=web3_client)

    def execute(
        self, *, pair: Pair, payload: SellPayload, session: Session
    ) -> TradeResult | None:
        transaction_helper = UniswapTransactionHelper(
            web3_client=self.web3_client,
            abi_manager=self.abi_manager,
            gas_helper=self.gas_helper,
        )

        allowance_result = transaction_helper.approve_allowance(
            allowance=payload.value,
            token_address_to_spend=pair.base_address,
            permit_address=PERMIT2,
            destination=UNISWAP_UNIVERSAL_ROUTER,
            wallet=self.wallet,
        )

        if allowance_result.tx_hash:
            TransactionStore(session).add_or_update_transaction(
                transaction=Transaction(
                    hash=allowance_result.tx_hash,
                    details=f"Allowance {payload.base_token.symbol} for {payload.value}",
                    created_at=int(time.time()),
                    data=allowance_result.sanitized_tx_params,
                )
            )
            session.commit()
        else:
            return TradeResult(
                status=TradeStatus.FAILED,
                message="Unable to create allowance transaction",
            )

        swap_result: SwapResult | None = None
        if pair.dex.version == "v2":
            swap_result = transaction_helper.v2_swap_exact_in(
                amount_in=payload.value,
                min_amount_out=payload.min_out,
                source_address=pair.base_address,
                destination_address=pair.quote_address,
                router_address=UNISWAP_UNIVERSAL_ROUTER,
                wallet=self.wallet,
                allowance_result=allowance_result,
            )
        elif pair.dex.version == "v3":
            pair_abi = self.abi_manager.get_abi(address=pair.address)
            pair_contract = self.web3_client.web3.eth.contract(
                self.web3_client.to_checksum_address(pair.address),
                abi=pair_abi,
            )

            pool_fee = pair_contract.functions.fee().call()
            swap_result = transaction_helper.v3_swap_exact_in(
                amount_in=payload.value,
                min_amount_out=payload.min_out,
                source_address=pair.base_address,
                pool_fee=pool_fee,
                destination_address=pair.quote_address,
                router_address=UNISWAP_UNIVERSAL_ROUTER,
                wallet=self.wallet,
                allowance_result=allowance_result,
            )

        if not swap_result:
            return TradeResult(status=TradeStatus.FAILED, message="Unexpected error")

        TransactionStore(session).add_or_update_transaction(
            transaction=Transaction(
                hash=swap_result.tx_hash,
                details=f"{payload.base_token.symbol} swapped for {payload.quote_token.symbol}",
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
            allowance_tx=(
                allowance_result.tx_hash.hex() if allowance_result.tx_hash else None
            ),
            swap_tx=swap_result.tx_hash.hex(),
        )
