import requests
from pydantic import BaseModel


class QuoteData(BaseModel):
    currency: str
    rates: dict[str, str]


class CoinbaseQuoteResponse(BaseModel):
    data: QuoteData


class CoinbaseAPI:
    def __init__(self) -> None:
        self.uri = "https://api.coinbase.com/v2/"

    def get_symbol_price(self, symbol: str) -> CoinbaseQuoteResponse:
        resp = requests.get(f"{self.uri}exchange-rates?currency={symbol.upper()}")
        content = resp.content.decode()
        return CoinbaseQuoteResponse.model_validate_json(content)

    def get_symbol_usd_price(self, symbol: str) -> float:
        quote_response = self.get_symbol_price(symbol)
        return float(quote_response.data.rates.get("USD", 0.00))
