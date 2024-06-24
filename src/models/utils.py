from decimal import Decimal

from models.token import PairQuote, Position, PositionMetric, Token
from web3_helper.helper import Web3Client


def get_position_metric(
    *,
    position: Position,
    web3_client: Web3Client,
    base_token: Token,
    latest_quote: PairQuote
) -> PositionMetric:
    web3 = web3_client.web3

    position_market_value = Decimal(
        base_token.balance_biggest() * web3.from_wei(latest_quote.price, "ether")
    )
    price_paid = Decimal(web3.from_wei(position.book_value, "ether"))

    profit_n_loss_wei = int(
        web3.to_wei(position_market_value, "ether") - position.book_value
    )
    profit_n_loss_sign = int(-1 if profit_n_loss_wei < 0 else 1)

    profit_n_loss = Decimal(
        web3.from_wei(abs(profit_n_loss_wei), "ether") * profit_n_loss_sign
    )
    profit_n_loss_percent = (
        (float(profit_n_loss) / float(price_paid)) * 100.00 if price_paid != 0 else 0
    )

    return PositionMetric(
        market_value=position_market_value,
        price_paid=price_paid,
        profit_and_loss=profit_n_loss,
        profit_and_loss_percent=profit_n_loss_percent,
    )
