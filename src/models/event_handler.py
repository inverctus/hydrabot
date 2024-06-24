from typing import Generic, TypeVar

from sqlalchemy.orm import Session

from models.event import Event

T = TypeVar("T", bound="Event")


class EventHandler(Generic[T]):
    def __init__(self) -> None:
        pass

    def run(self, *, event: T, session: Session) -> None:
        raise NotImplementedError()
