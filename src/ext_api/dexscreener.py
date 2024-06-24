from typing import List

import pydantic
import requests


class Token(pydantic.BaseModel):
    address: str
    symbol: str
    name: str


class TxnVolume(pydantic.BaseModel):
    buys: int
    sells: int


class TxnVolumeByPeriod(pydantic.BaseModel):
    m5: TxnVolume
    h1: TxnVolume
    h6: TxnVolume
    h24: TxnVolume


class FloatByPeriod(pydantic.BaseModel):
    m5: float
    h1: float
    h6: float
    h24: float


class Liquidity(pydantic.BaseModel):
    usd: float
    base: float
    quote: float


class DexPair(pydantic.BaseModel):
    chainId: str
    dexId: str
    url: str
    pairAddress: str
    labels: list[str] = []
    baseToken: Token
    quoteToken: Token
    priceNative: float
    priceUsd: float
    txns: TxnVolumeByPeriod
    volume: FloatByPeriod
    priceChange: FloatByPeriod
    liquidity: Liquidity
    fdv: int
    pairCreatedAt: int = 0


class PairsResponse(pydantic.BaseModel):
    schemaVersion: str
    pairs: List[DexPair]


class DexScreener:
    ROOT_URI = "https://api.dexscreener.com/latest/dex/"
    UI_URI = "https://dexscreener.com/"

    @staticmethod
    def get_pairs(pair_addresses: List[str], chain: str = "base") -> PairsResponse:
        resp = requests.get(
            f"{DexScreener.ROOT_URI}pairs/{chain}/{','.join(pair_addresses)}"
        )
        content = resp.content.decode()
        return PairsResponse.model_validate_json(content)

    @staticmethod
    def get_pair_link(chain_name: str, pair_address: str) -> str:
        return f"{DexScreener.UI_URI}{chain_name}/{pair_address}"
