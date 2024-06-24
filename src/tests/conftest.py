from typing import Any, Callable, Generator, Generic, TypeVar
from unittest import mock

from eth_account.account import Account, LocalAccount
from eth_typing import ChecksumAddress
from pytest import fixture
from sqlalchemy.orm import Session
from web3 import Web3

from database.session_factory import SessionFactory
from settings import SettingsFactory, SettingsKey, TradeBotSettings, must_get
from web3_helper.abi import ABIFetcher
from web3_helper.helper import Web3Client


@fixture
def trade_bot_settings() -> TradeBotSettings:
    return SettingsFactory.get_trade_bot_setings()


@fixture
def connection_string() -> str:
    return must_get(SettingsKey.DATABASE_URI)


@fixture
def session(connection_string: str) -> Generator[Session, Any, Any]:
    session_factory = SessionFactory(connection_string)
    session = session_factory.session()

    yield session

    session.rollback()


@fixture
def mock_wallet() -> LocalAccount:
    return Account.from_key(must_get(SettingsKey.WALLET_PRIVATE_KEY))


class MockABIFetcher(ABIFetcher):
    def __init__(self) -> None:
        super().__init__(base_scan_api_key="")

    def get_contracts_from_api(self, address: str) -> dict[str, Any]:
        return {
            "abi": [],
        }


@fixture
def abi_fetcher() -> ABIFetcher:
    return MockABIFetcher()


T = TypeVar("T")


class MockTokenContract:

    class ContractFunction(Generic[T]):
        def __init__(self, fn: Callable[[], T]) -> None:
            self.fn = fn

        def call(self) -> T:
            return self.fn()

    class IntFunction(ContractFunction[int]):
        def __init__(self, fn: Callable[[], int]) -> None:
            super().__init__(fn)

        def call(self) -> int:
            return self.fn()

    class FunctionDef:
        def __init__(self, token_contract: "MockTokenContract") -> None:
            self.token_contract = token_contract

        def balanceOf(
            self, wallet_address: ChecksumAddress
        ) -> "MockTokenContract.IntFunction":
            def balance() -> int:
                return self.token_contract.token_balance

            return MockTokenContract.IntFunction(fn=balance)

    def __init__(self, *, address: ChecksumAddress, token_balance: int = 0) -> None:
        self.address = address
        self.token_balance = token_balance
        self.functions = MockTokenContract.FunctionDef(self)


class MockWeb3Client(Web3Client):
    class Eth:
        def __init__(
            self, registries: dict[ChecksumAddress, MockTokenContract] = {}
        ) -> None:
            self.registries = registries
            self.eth_balance = 0

        def contract(
            self, address: ChecksumAddress, *, abi: list[dict[str, Any]]
        ) -> MockTokenContract:
            if address in self.registries:
                return self.registries[address]

            return MockTokenContract(address=address)

        def get_balance(self, *, account: ChecksumAddress) -> int:
            return self.eth_balance

    class Web3:
        def __init__(self) -> None:
            self.eth = MockWeb3Client.Eth()
            self.real_web3 = Web3()

        def to_checksum_address(self, address: str) -> ChecksumAddress:
            return self.real_web3.to_checksum_address(address)

    def __init__(self) -> None:
        self._web3 = MockWeb3Client.Web3()  # type: ignore


@fixture
def web3_client() -> Web3Client:
    web3_client = MockWeb3Client()
    return web3_client
