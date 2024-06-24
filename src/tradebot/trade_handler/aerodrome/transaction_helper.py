import time
from typing import cast

from eth_account.account import LocalAccount
from web3.exceptions import TimeExhausted
from web3.types import TxParams

from tradebot.constants import BASE_CHAIN_ID
from tradebot.trade_handler.aerodrome.constants import AERODROME_POOL_FACTORY
from web3_helper.abi import ABIManager
from web3_helper.gas import GasHelper
from web3_helper.helper import Web3Client
from web3_helper.transaction_helper import SwapResult


class TransactionHelper:
    def __init__(
        self, *, web3_client: Web3Client, abi_manager: ABIManager, gas_helper: GasHelper
    ) -> None:
        self.web3_client = web3_client
        self.abi_manager = abi_manager
        self.gas_helper = gas_helper

    def swap_exact_tokens_for_tokens(
        self,
        *,
        pair_address: str,
        wallet: LocalAccount,
        source_token_address: str,
        destination_token_address: str,
        amount_to_sell: int,
        min_amount_out: int,
        router_address: str,
        chain_id: int = BASE_CHAIN_ID,
        expiration: int = 30,
    ) -> SwapResult | None:

        w3 = self.web3_client.web3
        router_abi = self.abi_manager.get_abi(address=router_address)
        router_contract = w3.eth.contract(
            self.web3_client.to_checksum_address(router_address),
            abi=router_abi,
        )

        swap_tokens_for_tokens_function = (
            router_contract.functions.swapExactTokensForTokens(
                amount_to_sell,
                min_amount_out,
                [
                    (
                        source_token_address,
                        destination_token_address,
                        False,
                        AERODROME_POOL_FACTORY,
                    )
                ],
                wallet.address,
                int(time.time()) + expiration,
            )
        )

        gas_estimate = self.gas_helper.estimated_gas_price()

        tx_params = cast(
            TxParams,
            {
                "from": wallet.address,
                "gas": 250_000,
                "maxPriorityFeePerGas": w3.eth.max_priority_fee,
                "maxFeePerGas": w3.eth.max_priority_fee + gas_estimate.base_fee,
                "type": "0x2",
                "chainId": chain_id,
                "value": 0,
                "nonce": w3.eth.get_transaction_count(wallet.address),
            },
        )

        builded_tx_params = swap_tokens_for_tokens_function.build_transaction(tx_params)

        raw_transaction = w3.eth.account.sign_transaction(
            builded_tx_params, wallet.key
        ).rawTransaction
        tx_hash = w3.eth.send_raw_transaction(raw_transaction)
        try:
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

            return SwapResult(
                tx_hash=tx_hash,
                block_number=receipt["blockNumber"],
                status=receipt["status"],
                tx_params=builded_tx_params,
            )

        except TimeExhausted:
            raise Exception(f"Transaction timed out")  # TODO

        except Exception as exp:
            raise exp
