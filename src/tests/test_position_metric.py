import time
from decimal import Decimal

from models.token import PairQuote, Position, Token
from models.utils import get_position_metric
from web3_helper.helper import Web3Client


def test_position_metric_fn() -> None:
    pair_address = "0x00"
    web3_client = Web3Client()
    base_token = Token(
        address="0x01",
        name="Test",
        symbol="TST",
        decimals=18,
        balance=203275914293585192130411757,
    )

    pair_quote = PairQuote(
        pair_address=pair_address, price=11212000, data={}, timestamp=int(time.time())
    )

    position = Position(
        pair_address=pair_address,
        created_at=int(time.time()),
        token_bought=203275914293585192130411757,
        book_value=2000000000000000,
    )

    metric = get_position_metric(
        position=position,
        web3_client=web3_client,
        base_token=base_token,
        latest_quote=pair_quote,
    )

    assert metric.model_dump() == {
        "market_value": Decimal("0.002279129547768"),
        "price_paid": Decimal("0.002"),
        "profit_and_loss": Decimal("0.000279129547768"),
        "profit_and_loss_percent": 13.956477388399998,
    }

    second_pair_quote = PairQuote(
        pair_address=pair_address, price=9212000, data={}, timestamp=int(time.time())
    )

    metric = get_position_metric(
        position=position,
        web3_client=web3_client,
        base_token=base_token,
        latest_quote=second_pair_quote,
    )

    assert metric.model_dump() == {
        "market_value": Decimal("0.001872577719768"),
        "price_paid": Decimal("0.002"),
        "profit_and_loss": Decimal("-0.000127422280232"),
        "profit_and_loss_percent": -6.371114011599999,
    }
