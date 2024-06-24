import json
from typing import Any

import requests
from eth_account import Account
from eth_account.account import LocalAccount
from eth_typing import ChecksumAddress
from web3 import Web3
from web3.middleware import geth_poa_middleware


class Web3Client:
    def __init__(
        self, *, web3_provider_url: str | None = None, inject_middleware: bool = True
    ) -> None:
        self.web3_provider_url = web3_provider_url
        self._web3 = (
            Web3(Web3.HTTPProvider(web3_provider_url))
            if self.web3_provider_url
            else Web3()
        )

        if inject_middleware:
            self._web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    @property
    def web3(self) -> Web3:
        return self._web3

    def to_checksum_address(self, str) -> ChecksumAddress:
        return self._web3.to_checksum_address(str)


class Web3Helper:
    @staticmethod
    def get_web3(provider_url: str) -> Web3Client:
        return Web3Client(web3_provider_url=provider_url)

    @staticmethod
    def get_wallet(wallet_private_key: str) -> LocalAccount:
        return Account.from_key(private_key=wallet_private_key)

    @staticmethod
    def fetch_abi(address: str, base_scan_api_key: str) -> dict[str, Any]:
        url = f"https://api.basescan.org/api?module=contract&action=getabi&address={address}&apikey={base_scan_api_key}"

        resp = requests.get(url)

        abi_dict = {"abi": json.loads(resp.content.decode())["result"]}

        return abi_dict
