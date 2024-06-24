from eth_account.account import LocalAccount
from sqlalchemy.orm import Session

from database.token_store import TokenStore
from models.event import UpdateBalancesEvent
from models.token import TOKEN_ADDRESSES, Token, TokenName
from tests.conftest import MockTokenContract
from tradebot.event_handlers.update_balances_handler import UpdateBalancesHandler
from web3_helper.abi import ABIFetcher
from web3_helper.helper import Web3Client


def test_update_token_balance_handler(
    session: Session,
    mock_wallet: LocalAccount,
    abi_fetcher: ABIFetcher,
    web3_client: Web3Client,
) -> None:

    token_store = TokenStore(session)

    test_token = Token(
        address="0xfdc944fb59201fB163596EE5e209EBC8fA4DcdC5",
        name="Test",
        symbol="TST",
        decimals=18,
        balance=2000000,
    )

    token_store.add_token(test_token)

    session.commit()

    update_balances_handler = UpdateBalancesHandler(
        wallet=mock_wallet,
        abi_fetcher=abi_fetcher,
        web3_client=web3_client,
    )

    web3_client.web3.eth.registries[test_token.address] = MockTokenContract(  # type: ignore
        address=web3_client.to_checksum_address(test_token.address),
        token_balance=1337,
    )

    update_balances_handler.run(
        event=UpdateBalancesEvent(
            id=1, created_at=1, data={"addresses": [test_token.address]}
        ),
        session=session,
    )

    token_from_db = token_store.get_token(test_token.address)

    assert token_from_db
    assert token_from_db.balance == 1337


def test_update_multiples_token_balance_handler(
    session: Session,
    mock_wallet: LocalAccount,
    abi_fetcher: ABIFetcher,
    web3_client: Web3Client,
) -> None:

    token_store = TokenStore(session)

    test_token = Token(
        address="0xF6e932Ca12afa26665dC4dDE7e27be02A7c02e50",
        name="Test",
        symbol="TST",
        decimals=18,
        balance=2000000,
    )

    token_store.add_token(test_token)

    test_token2 = Token(
        address="0xdb6e0e5094A25a052aB6845a9f1e486B9A9B3DdE",
        name="Test2",
        symbol="TST2",
        decimals=18,
        balance=1000000,
    )

    token_store.add_token(test_token2)

    session.commit()

    update_balances_handler = UpdateBalancesHandler(
        wallet=mock_wallet,
        abi_fetcher=abi_fetcher,
        web3_client=web3_client,
    )

    web3_client.web3.eth.registries[test_token.address] = MockTokenContract(  # type: ignore
        address=web3_client.to_checksum_address(test_token.address),
        token_balance=2500,
    )

    web3_client.web3.eth.registries[test_token2.address] = MockTokenContract(  # type: ignore
        address=web3_client.to_checksum_address(test_token2.address),
        token_balance=5700,
    )

    update_balances_handler.run(
        event=UpdateBalancesEvent(id=1, created_at=1, data={}),
        session=session,
    )

    token_from_db = token_store.get_token(test_token.address)
    token2_from_db = token_store.get_token(test_token2.address)

    assert token_from_db
    assert token_from_db.balance == 2500

    assert token2_from_db
    assert token2_from_db.balance == 5700


def test_update_eth_balance(
    session: Session,
    mock_wallet: LocalAccount,
    abi_fetcher: ABIFetcher,
    web3_client: Web3Client,
) -> None:

    token_store = TokenStore(session)

    eth_token = Token(
        address=TOKEN_ADDRESSES[TokenName.ETH],
        name="Ether",
        symbol="ETH",
        decimals=18,
        balance=0,
    )

    token_store.add_token(eth_token)

    session.commit()

    update_balances_handler = UpdateBalancesHandler(
        wallet=mock_wallet,
        abi_fetcher=abi_fetcher,
        web3_client=web3_client,
    )

    web3_client.web3.eth.eth_balance = 6000  # type: ignore

    update_balances_handler.run(
        event=UpdateBalancesEvent(id=1, created_at=1, data={}),
        session=session,
    )

    eth_token_from_db = token_store.get_token(eth_token.address)

    assert eth_token_from_db
    assert eth_token_from_db.balance == 6000
