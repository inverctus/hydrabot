from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from models.token import Pair, PairQuote, Token


class PairStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_all_pairs(self) -> Iterable[Pair]:
        stmt = select(Pair)
        return self.session.scalars(stmt)

    def get_pairs(
        self,
        *,
        chain: str | None = None,
        dex: str | None = None,
        skip: int | None = None,
        limit: int | None = None,
    ) -> Iterable[Pair]:
        stmt = select(Pair)

        if chain:
            stmt = stmt.where(Pair.chain == chain)

        if dex:
            stmt = stmt.where(Pair._dex == dex)

        if skip:
            stmt = stmt.offset(skip)

        if limit:
            stmt = stmt.limit(limit)

        return self.session.scalars(stmt)

    def get_pair(self, pair_address: str) -> Pair | None:
        stmt = select(Pair).where(Pair.address == pair_address)
        return self.session.scalar(stmt)

    def get_pair_by_message_id(self, message_id: int) -> Pair | None:
        stmt = select(Pair).where(Pair.message_id == message_id)
        return self.session.scalar(stmt)

    def get_pair_by_token(self, token_address: str) -> Pair | None:
        stmt = select(Pair).where(Pair.base_address == token_address)
        return self.session.scalar(stmt)

    def add_pair(self, pair: Pair) -> None:
        self.session.add(pair)

    def add_pair_quote(self, pair_quote: PairQuote) -> None:
        self.session.add(pair_quote)

    def get_pair_by_base_token_by_symbol(self, token_symbol: str) -> Pair | None:
        token_stmt = select(Token).where(Token.symbol.ilike(token_symbol))
        if token := self.session.scalar(token_stmt):
            stmt = select(Pair).where(Pair.base_address == token.address)
            return self.session.scalar(stmt)

        return None

    def get_latest_quote(self, pair_address: str) -> PairQuote | None:
        stmt = (
            select(PairQuote)
            .where(PairQuote.pair_address == pair_address)
            .order_by(PairQuote.timestamp.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def get_quote_by_data_hash(
        self, pair_address: str, data_hash: str
    ) -> PairQuote | None:
        stmt = (
            select(PairQuote)
            .where(
                PairQuote.pair_address == pair_address, PairQuote.data_hash == data_hash
            )
            .limit(1)
        )
        return self.session.scalar(stmt)

    def clean_quotes_before_timestamp(self, before: int) -> None:
        stmt = delete(PairQuote).where(PairQuote.timestamp <= before)
        self.session.execute(stmt)

    def delete_pair(self, pair_address: str) -> None:
        stmt = delete(PairQuote).where(PairQuote.pair_address == pair_address)
        self.session.execute(stmt)

        stmt = delete(Pair).where(Pair.address == pair_address)
        self.session.execute(stmt)
