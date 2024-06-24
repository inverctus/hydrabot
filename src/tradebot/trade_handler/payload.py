from models.token import Token


class BuyPayload:
    def __init__(
        self,
        *,
        pair: str,
        value: int,
        min_out: int,
        base_token: Token,
        quote_token: Token,
        slippage: float | None = None,
    ) -> None:
        self.pair = pair
        self.value = value
        self.min_out = min_out
        self.base_token = base_token
        self.quote_token = quote_token


class SellPayload:
    def __init__(
        self,
        *,
        pair: str,
        value: int,
        min_out: int,
        base_token: Token,
        quote_token: Token,
        slippage: float | None = None,
    ) -> None:
        self.pair = pair
        self.value = value
        self.min_out = min_out
        self.base_token = base_token
        self.quote_token = quote_token
