from typing import Type, TypedDict


class TradeInformation(TypedDict):
    event_id: int | None
    trade_handler: str | None
    amount: int | None
    min_amount: int | None
    slippage: float | None
    source_address: str | None
    destination_address: str | None
    chain_id: int | None


class TradeInformationBuilder:
    def __init__(
        self,
        *,
        event_id: int | None = None,
        trade_handler: str | None = None,
        amount: int | None = None,
        min_amount: int | None = None,
        slippage: float | None = None,
        source_address: str | None = None,
        destination_address: str | None = None,
        chain_id: int | None = None,
    ) -> None:

        self.event_id = event_id
        self.trade_handler = trade_handler
        self.amount = amount
        self.min_amount = min_amount
        self.slippage = slippage
        self.source_address = source_address
        self.destination_address = destination_address
        self.chain_id = chain_id

    def build(self) -> TradeInformation:
        return TradeInformation(
            event_id=self.event_id,
            trade_handler=self.trade_handler,
            amount=self.amount,
            min_amount=self.min_amount,
            slippage=self.slippage,
            source_address=self.source_address,
            destination_address=self.destination_address,
            chain_id=self.chain_id,
        )


class TradeException(Exception):
    def __init__(
        self,
        *,
        message: str,
        transation_hashes: dict[str, str | None] = {},
        trade_information: TradeInformation | None = None,
    ) -> None:
        super().__init__(message)

        self.transation_hashes = transation_hashes
        self.trade_information = trade_information
