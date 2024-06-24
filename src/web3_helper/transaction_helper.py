import time
from typing import Any, cast

from eth_account.account import LocalAccount, SignedMessage
from hexbytes import HexBytes
from uniswap_universal_router_decoder import FunctionRecipient, RouterCodec
from web3.exceptions import TimeExhausted
from web3.types import TxParams

from tradebot.constants import BASE_CHAIN_ID
from web3_helper.abi import ABIManager
from web3_helper.gas import GasHelper
from web3_helper.helper import Web3Client


class ApproveResult:
    def __init__(
        self,
        *,
        amount: int,
        expiration: int,
        tx_hash: HexBytes | None = None,
        tx_params: TxParams = {},
    ) -> None:

        self.tx_hash = tx_hash
        self.amount = amount
        self.expiration = expiration
        self.tx_params = tx_params

    @property
    def sanitized_tx_params(self) -> dict[str, Any]:
        tx_params = dict(self.tx_params)

        if "data" in tx_params:
            tx_params.pop("data")

        if "to" in tx_params:
            tx_params["to"] = str(tx_params["to"])

        if "from" in tx_params:
            tx_params["from"] = str(tx_params["from"])

        return tx_params


class AllowanceResult:
    def __init__(
        self,
        *,
        amount: int,
        expiration: int,
        signed_message: SignedMessage,
        permit_data: dict[str, Any],
        tx_hash: HexBytes | None = None,
        tx_params: TxParams = {},
    ) -> None:

        self.tx_hash = tx_hash
        self.amount = amount
        self.expiration = expiration
        self.signed_message = signed_message
        self.permit_data = permit_data
        self.tx_params = tx_params

    @property
    def sanitized_tx_params(self) -> dict[str, Any]:
        tx_params = dict(self.tx_params)

        if "data" in tx_params:
            tx_params.pop("data")

        if "to" in tx_params:
            tx_params["to"] = str(tx_params["to"])

        if "from" in tx_params:
            tx_params["from"] = str(tx_params["from"])

        return tx_params


class SwapResult:
    def __init__(
        self,
        *,
        tx_hash: HexBytes,
        block_number: int,
        status: int,
        tx_params: TxParams = {},
    ) -> None:
        self.tx_hash = tx_hash
        self.block_number = block_number
        self.status = status
        self.tx_params = tx_params

    @property
    def sanitized_tx_params(self) -> dict[str, Any]:
        tx_params = dict(self.tx_params)

        if "data" in tx_params:
            tx_params.pop("data")

        if "to" in tx_params:
            tx_params["to"] = str(tx_params["to"])

        if "from" in tx_params:
            tx_params["from"] = str(tx_params["from"])

        return tx_params


class TransactionHelper:
    def __init__(
        self, *, web3_client: Web3Client, abi_manager: ABIManager, gas_helper: GasHelper
    ) -> None:
        self.web3_client = web3_client
        self.abi_manager = abi_manager
        self.gas_helper = gas_helper

    def wrap_eth(
        self,
        *,
        amount_in: int,
        weth_address: str,
        wallet: LocalAccount,
        chain_id: int = BASE_CHAIN_ID,
    ) -> bool:
        w3 = self.web3_client.web3
        gas_estimate = self.gas_helper.estimated_gas_price()

        weth_contract = self.web3_client.web3.eth.contract(
            self.web3_client.to_checksum_address(weth_address),
            abi=self.abi_manager.get_abi(address=weth_address),
        )

        tx = weth_contract.functions.deposit().build_transaction(
            cast(
                TxParams,
                {
                    "gas": 75_000,
                    "maxPriorityFeePerGas": w3.eth.max_priority_fee,
                    "maxFeePerGas": gas_estimate.priority_fee + gas_estimate.base_fee,
                    "chainId": chain_id,
                    "value": amount_in,
                    "nonce": w3.eth.get_transaction_count(wallet.address),
                },
            )
        )

        raw_transaction = w3.eth.account.sign_transaction(tx, wallet.key).rawTransaction
        tx_hash = w3.eth.send_raw_transaction(raw_transaction)
        try:
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            return True

        except TimeExhausted:
            raise Exception(f"Transaction timed out")  # TODO

    def approve(
        self,
        *,
        wallet: LocalAccount,
        allowance: int,
        token_address: str,
        spender_address: str,
        chain_id: int = BASE_CHAIN_ID,
    ) -> ApproveResult:

        w3 = self.web3_client.web3
        source_abi = self.abi_manager.get_abi(address=token_address)

        token_contract = w3.eth.contract(
            self.web3_client.to_checksum_address(token_address),
            abi=source_abi,
        )

        approve_function = token_contract.functions.approve(
            spender_address,
            allowance,
        )

        nonce = w3.eth.get_transaction_count(wallet.address)

        gas_estimate = self.gas_helper.estimated_gas_price()

        tx_params = cast(
            TxParams,
            {
                "from": wallet.address,
                "maxPriorityFeePerGas": w3.eth.max_priority_fee,
                "maxFeePerGas": w3.eth.max_priority_fee + gas_estimate.base_fee,
                "type": "0x2",
                "chainId": chain_id,
                "value": 0,
                "nonce": nonce,
            },
        )

        gas_price = w3.eth.estimate_gas(tx_params)

        tx_params["gas"] = gas_price + 10_000

        builded_tx_params = approve_function.build_transaction(tx_params)

        raw_transaction = w3.eth.account.sign_transaction(
            builded_tx_params, wallet.key
        ).rawTransaction

        approve_tx_hash = w3.eth.send_raw_transaction(raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(approve_tx_hash)
        # TODO store receipt
        return ApproveResult(
            amount=allowance,
            expiration=0,
            tx_hash=approve_tx_hash,
            tx_params=builded_tx_params,
        )

    def swap_exact_tokens_for_tokens(
        self,
        *,
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
                [source_token_address, destination_token_address],
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


class UniswapTransactionHelper:
    def __init__(
        self, *, web3_client: Web3Client, abi_manager: ABIManager, gas_helper: GasHelper
    ) -> None:
        self.web3_client = web3_client
        self.abi_manager = abi_manager
        self.gas_helper = gas_helper

        self.codec = RouterCodec()

    def allowance(
        self, *, wallet: LocalAccount, token_address: str, spender: str
    ) -> int:
        w3 = self.web3_client.web3
        token_contract = w3.eth.contract(
            self.web3_client.to_checksum_address(token_address),
            abi=self.abi_manager.get_abi(address=token_address),
        )
        current_allowance = token_contract.functions.allowance(
            wallet.address, spender
        ).call()
        return current_allowance

    def v2_swap_exact_in(
        self,
        *,
        amount_in: int,
        min_amount_out: int,
        source_address: str,
        destination_address: str,
        router_address: str,
        wallet: LocalAccount,
        allowance_result: AllowanceResult | None = None,
        chain_id: int = BASE_CHAIN_ID,
    ) -> SwapResult:
        w3 = self.web3_client.web3

        chain_input_builder = self.codec.encode.chain()

        if allowance_result:
            chain_input_builder = chain_input_builder.permit2_permit(
                allowance_result.permit_data, allowance_result.signed_message
            )

        encoded_input = chain_input_builder.v2_swap_exact_in(
            FunctionRecipient.SENDER,
            amount_in,
            min_amount_out,
            [source_address, destination_address],
            payer_is_sender=True,
        ).build(self.codec.get_default_deadline())

        gas_estimate = self.gas_helper.estimated_gas_price()

        tx_params = cast(
            TxParams,
            {
                "from": wallet.address,
                "to": router_address,
                "gas": 250_000,
                "maxPriorityFeePerGas": w3.eth.max_priority_fee,
                "maxFeePerGas": w3.eth.max_priority_fee + gas_estimate.base_fee,
                "type": "0x2",
                "chainId": chain_id,
                "value": 0,
                "nonce": w3.eth.get_transaction_count(wallet.address),
                "data": encoded_input,
            },
        )

        raw_transaction = w3.eth.account.sign_transaction(
            tx_params, wallet.key
        ).rawTransaction
        tx_hash = w3.eth.send_raw_transaction(raw_transaction)
        try:
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

            return SwapResult(
                tx_hash=tx_hash,
                block_number=receipt["blockNumber"],
                status=receipt["status"],
                tx_params=tx_params,
            )

        except TimeExhausted:
            raise Exception(f"Transaction timed out")  # TODO

    def v3_swap_exact_in(
        self,
        *,
        amount_in: int,
        min_amount_out: int,
        source_address: str,
        destination_address: str,
        pool_fee: int,
        router_address: str,
        wallet: LocalAccount,
        allowance_result: AllowanceResult | None = None,
        chain_id: int = BASE_CHAIN_ID,
    ) -> SwapResult:
        w3 = self.web3_client.web3

        chain_input_builder = self.codec.encode.chain()

        if allowance_result:
            chain_input_builder = chain_input_builder.permit2_permit(
                allowance_result.permit_data, allowance_result.signed_message
            )

        encoded_input = chain_input_builder.v3_swap_exact_in(
            FunctionRecipient.SENDER,
            amount_in,
            min_amount_out,
            [source_address, pool_fee, destination_address],
            payer_is_sender=True,
        ).build(self.codec.get_default_deadline())

        gas_estimate = self.gas_helper.estimated_gas_price()

        tx_params = cast(
            TxParams,
            {
                "from": wallet.address,
                "to": router_address,
                "gas": 250_000,
                "maxPriorityFeePerGas": w3.eth.max_priority_fee,
                "maxFeePerGas": w3.eth.max_priority_fee + gas_estimate.base_fee,
                "type": "0x2",
                "chainId": chain_id,
                "value": 0,
                "nonce": w3.eth.get_transaction_count(wallet.address),
                "data": encoded_input,
            },
        )

        raw_transaction = w3.eth.account.sign_transaction(
            tx_params, wallet.key
        ).rawTransaction
        tx_hash = w3.eth.send_raw_transaction(raw_transaction)
        try:
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

            return SwapResult(
                tx_hash=tx_hash,
                block_number=receipt["blockNumber"],
                status=receipt["status"],
                tx_params=tx_params,
            )

        except TimeExhausted:
            raise Exception(f"Transaction timed out")  # TODO

    def permit_signed_message(
        self,
        *,
        allowance: int,
        wallet: LocalAccount,
        token_address_to_spend: str,
        destination: str,
        permit_address: str,
        chain_id: int = BASE_CHAIN_ID,
    ) -> AllowanceResult:

        w3 = self.web3_client.web3

        permit_abi = self.abi_manager.get_abi(address=permit_address)
        permit_contract = w3.eth.contract(
            self.web3_client.to_checksum_address(permit_address),
            abi=permit_abi,
        )
        _, permit_expiration, permit_nonce = permit_contract.functions.allowance(
            wallet.address,
            token_address_to_spend,
            destination,
        ).call()

        # permit message
        permit_data, signable_message = self.codec.create_permit2_signable_message(
            token_address_to_spend,
            allowance,
            permit_expiration,
            permit_nonce,
            destination,
            self.codec.get_default_deadline(),  # 180 seconds
            chain_id,
        )

        # Signing the message
        signed_message = wallet.sign_message(signable_message)

        return AllowanceResult(
            amount=allowance,
            expiration=permit_expiration,
            signed_message=signed_message,
            permit_data=permit_data,
        )

    def approve_allowance(
        self,
        *,
        allowance: int,
        token_address_to_spend: str,
        destination: str,
        wallet: LocalAccount,
        chain_id: int = BASE_CHAIN_ID,
        permit_address: str | None = None,
    ) -> AllowanceResult:

        w3 = self.web3_client.web3

        token_abi = self.abi_manager.get_abi(address=token_address_to_spend)
        token_contract = w3.eth.contract(
            self.web3_client.to_checksum_address(token_address_to_spend),
            abi=token_abi,
        )

        contract_function = token_contract.functions.approve(
            wallet.address if not permit_address else permit_address,
            allowance,
        )

        permit_nonce = w3.eth.get_transaction_count(wallet.address)

        gas_estimate = self.gas_helper.estimated_gas_price()

        tx_params = cast(
            TxParams,
            {
                "from": wallet.address,
                "maxPriorityFeePerGas": w3.eth.max_priority_fee,
                "maxFeePerGas": w3.eth.max_priority_fee + gas_estimate.base_fee,
                "type": "0x2",
                "chainId": chain_id,
                "value": 0,
                "nonce": permit_nonce,
            },
        )

        gas_price = w3.eth.estimate_gas(tx_params)

        tx_params["gas"] = gas_price + 10_000

        builded_tx_params = contract_function.build_transaction(tx_params)

        raw_transaction = w3.eth.account.sign_transaction(
            builded_tx_params, wallet.key
        ).rawTransaction

        tx_hash = w3.eth.send_raw_transaction(raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        permit_expiration = 0

        if permit_address:
            allowance_result = self.permit_signed_message(
                allowance=allowance,
                wallet=wallet,
                token_address_to_spend=token_address_to_spend,
                destination=destination,
                permit_address=permit_address,
                chain_id=chain_id,
            )

            return AllowanceResult(
                tx_hash=tx_hash,
                amount=allowance_result.amount,
                expiration=allowance_result.expiration,
                signed_message=allowance_result.signed_message,
                permit_data=allowance_result.permit_data,
                tx_params=tx_params,
            )

        else:
            # permit message
            permit_data, signable_message = self.codec.create_permit2_signable_message(
                token_address_to_spend,
                allowance,
                self.codec.get_default_expiration(),  # 30 days
                permit_nonce,
                destination,
                self.codec.get_default_deadline(),  # 180 seconds
                chain_id,
            )

            # Signing the message
            signed_message = wallet.sign_message(signable_message)

            return AllowanceResult(
                tx_hash=tx_hash,
                amount=allowance,
                expiration=self.codec.get_default_expiration(),
                signed_message=signed_message,
                permit_data=permit_data,
                tx_params=tx_params,
            )
