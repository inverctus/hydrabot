from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.base import Base


class SessionFactory:
    def __init__(self, connection_string: str) -> None:
        self.connection_string = connection_string
        self.engine = create_engine(self.connection_string)
        self._create_all()

    def _create_all(self) -> None:
        Base.metadata.create_all(self.engine)

    def session(self) -> Session:
        return Session(self.engine, expire_on_commit=False)
