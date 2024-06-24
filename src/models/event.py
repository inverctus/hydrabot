from enum import StrEnum
from typing import Any, Type, TypedDict, cast

from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Queue(StrEnum):
    CHAT_BOT = "chat-bot"
    TRADE_BOT = "trade-bot"


class EventType(StrEnum):
    UPDATE_BALANCES = "update-balances"
    BUY = "buy"
    CHAT = "chat"
    SELL = "sell"
    WRAP = "wrap"


class Event:
    def __init__(self, *, id: int, event_type: EventType, created_at: int) -> None:
        self.id = id
        self.event_type = event_type
        self.created_at = created_at


class UpdateBalancesEvent(Event):
    def __init__(
        self,
        *,
        id: int,
        created_at: int,
        data: dict[str, Any] = {},
    ) -> None:
        super().__init__(
            id=id, event_type=EventType.UPDATE_BALANCES, created_at=created_at
        )
        self.addresses: list[str] = cast(list[str], data.get("addresses", []))


class TradeEvent(Event):
    def __init__(
        self,
        *,
        id: int,
        event_type: EventType,
        created_at: int,
        data: dict[str, Any] = {},
    ) -> None:
        super().__init__(id=id, event_type=event_type, created_at=created_at)
        self.pair = str(data["pair"])
        self.value = int(data["value"])
        self.slippage: float | None = None

        if slippage := data.get("slippage"):
            try:
                self.slippage = float(slippage)
            except:
                self.slippage = None
        else:
            self.slippage = None


class BuyEvent(TradeEvent):
    def __init__(
        self,
        *,
        id: int,
        created_at: int,
        data: dict[str, Any] = {},
    ) -> None:
        super().__init__(
            id=id, event_type=EventType.BUY, created_at=created_at, data=data
        )


class SellEvent(TradeEvent):
    def __init__(
        self,
        *,
        id: int,
        created_at: int,
        data: dict[str, Any] = {},
    ) -> None:
        super().__init__(
            id=id, event_type=EventType.SELL, created_at=created_at, data=data
        )


class ChatMessageType(StrEnum):
    TEXT = "text"
    EMBED = "embed"
    ERROR = "error"


class EmbedField(TypedDict):
    name: str
    value: str
    inline: bool


class ChatEvent(Event):
    def __init__(
        self,
        *,
        id: int,
        created_at: int,
        data: dict[str, Any] = {},
    ) -> None:
        super().__init__(id=id, event_type=EventType.CHAT, created_at=created_at)
        self.message = ""
        self.source_event_id: int | None = None
        self.title: str | None = None
        self.url: str | None = None
        self.fields: list[EmbedField] = []

        if "source_event_id" in data:
            self.source_event_id = int(data["source_event_id"])

        self.message_type = ChatMessageType(
            data.get("message_type", ChatMessageType.TEXT)
        )
        self.message = str(data["message"])

        if self.message_type == ChatMessageType.EMBED:
            if title := data.get("title"):
                self.title = str(title)

            if url := data.get("url"):
                self.url = str(url)

            if fields := data.get("fields"):
                if isinstance(fields, list):
                    self.fields = [
                        EmbedField(
                            name=str(field.get("name", "")),
                            value=str(field.get("value", "")),
                            inline=bool(field.get("inline", False)),
                        )
                        for field in fields
                    ]


class WrapEvent(Event):
    def __init__(
        self,
        *,
        id: int,
        created_at: int,
        data: dict[str, Any] = {},
    ) -> None:
        super().__init__(id=id, event_type=EventType.WRAP, created_at=created_at)
        self.value = int(data["value"])


EVENT_CONSTRUCT: dict[EventType, Type] = {
    EventType.UPDATE_BALANCES: UpdateBalancesEvent,
    EventType.BUY: BuyEvent,
    EventType.CHAT: ChatEvent,
    EventType.SELL: SellEvent,
    EventType.WRAP: WrapEvent,
}


class PersistedEventStatus(StrEnum):
    PENDING = "pending"
    EXPIRED = "expired"
    COMPLETED = "completed"
    FAILED = "failed"


class PersistedEvent(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    queue: Mapped[str] = mapped_column(nullable=False)

    event_type: Mapped[str] = mapped_column(nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[int] = mapped_column(nullable=False)
    expire_at: Mapped[int | None] = mapped_column(nullable=True)
    acked_at: Mapped[int | None] = mapped_column(nullable=True)
    completed_at: Mapped[int | None] = mapped_column(nullable=True)

    _status: Mapped[str] = mapped_column("status", nullable=False)

    execution_data: Mapped[dict] = mapped_column(JSONB, nullable=False)

    def __init__(
        self,
        *,
        queue: str,
        event_type: str,
        data: dict,
        created_at: int,
        status: PersistedEventStatus = PersistedEventStatus.PENDING,
        execution_data: dict = {},
        acked_at: int | None = None,
        expire_at: int | None = None,
        completed_at: int | None = None,
    ) -> None:
        self.queue = queue
        self.event_type = event_type
        self.data = data
        self.execution_data = execution_data
        self.status = status
        self.created_at = created_at
        self.acked_at = acked_at
        self.expire_at = expire_at
        self.completed_at = completed_at

    @property
    def status(self) -> PersistedEventStatus:
        return PersistedEventStatus(self._status)

    @status.setter
    def status(self, value: PersistedEventStatus) -> None:
        self._status = value.value

    def asdict(self) -> dict:
        return {
            "id": self.id,
            "queue": self.queue,
            "event_type": self.event_type,
            "data": self.data,
            "execution_data": self.execution_data,
            "status": self._status,
            "created_at": self.created_at,
            "acked_at": self.acked_at,
            "expire_at": self.expire_at,
            "completed_at": self.completed_at,
        }


class EventBuilder:
    def __init__(self, event_construct: dict[EventType, Type]) -> None:
        self.event_construct = event_construct

    def build_from_persisted_event(self, persisted_event: PersistedEvent) -> Event:
        event_type = EventType(persisted_event.event_type)
        if not event_type in self.event_construct:
            raise Exception(f"Invalid Event Type {persisted_event.event_type}")

        return self.event_construct[event_type](
            id=persisted_event.id,
            created_at=persisted_event.created_at,
            data=persisted_event.data,
        )


def get_event_builder() -> EventBuilder:
    return EventBuilder(EVENT_CONSTRUCT)
