import time

from sqlalchemy import null, select
from sqlalchemy.orm import Session

from models.event import PersistedEvent as Event
from models.event import Queue
from models.token import Transaction


class TransactionStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_or_update_transaction(self, transaction: Transaction) -> None:
        if db_transaction := self.get_transaction(transaction.hash):
            if transaction.block_number:
                db_transaction.block_number = transaction.block_number

            if transaction.data:
                db_transaction.data = transaction.data

            if transaction.details:
                db_transaction.details = transaction.details

            if transaction.status:
                db_transaction.status = transaction.status
        else:
            self.add_transaction(transaction)

    def add_transaction(self, transaction: Transaction) -> None:
        self.session.add(transaction)

    def get_transaction(self, tx_hash: str) -> Transaction | None:
        stmt = select(Transaction).where(Transaction.hash == tx_hash)
        return self.session.scalar(stmt)
