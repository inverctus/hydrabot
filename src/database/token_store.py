from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from models.token import Token


class TokenStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_token_by_symbol(self, token_symbol: str) -> Token | None:
        stmt = select(Token).where(Token.symbol == token_symbol)
        return self.session.scalar(stmt)

    def get_token(self, token_address: str) -> Token | None:
        stmt = select(Token).where(Token.address == token_address)
        return self.session.scalar(stmt)

    def delete_token(self, token_address: str) -> None:
        stmt = delete(Token).where(Token.address == token_address)
        self.session.execute(stmt)

    def get_tokens(
        self, *, skip: int | None = None, limit: int | None = None
    ) -> Iterable[Token]:
        stmt = select(Token)

        if skip:
            stmt = stmt.offset(skip)

        if limit:
            stmt = stmt.limit(limit)

        return self.session.scalars(stmt)

    def get_tokens_by_addresses(
        self, addresses: list[str] | None = None
    ) -> Iterable[Token]:
        stmt = select(Token)

        if addresses:
            stmt = stmt.where(Token.address.in_(addresses))

        return self.session.scalars(stmt)

    def add_token(self, token: Token) -> None:
        self.session.add(token)
