import time
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.event import PersistedEvent, PersistedEventStatus, Queue


class EventStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_event(self, event: PersistedEvent) -> None:
        self.session.add(event)

    def get_latest_event(
        self,
        *,
        queue: Queue,
        target_status: PersistedEventStatus = PersistedEventStatus.PENDING,
    ) -> PersistedEvent | None:
        stmt = (
            select(PersistedEvent)
            .where(
                PersistedEvent.queue == queue.value,
                PersistedEvent._status == target_status.value,
            )
            .order_by(PersistedEvent.created_at.asc())
            .limit(1)
        )

        return self.session.scalar(stmt)

    def get_event_by_id(self, event_id: int) -> PersistedEvent | None:
        stmt = select(PersistedEvent).where(PersistedEvent.id == event_id)

        return self.session.scalar(stmt)

    def ack_event(self, event: PersistedEvent) -> None:
        event.acked_at = int(time.time())

    def complete_event(self, event: PersistedEvent, execution_data: dict = {}) -> None:
        event.completed_at = int(time.time())
        event.status = PersistedEventStatus.COMPLETED
        event.execution_data = execution_data

    def fail_event(self, event: PersistedEvent, execution_data: dict = {}) -> None:
        event.completed_at = int(time.time())
        event.status = PersistedEventStatus.FAILED
        event.execution_data = execution_data

    def expire_event(self, event: PersistedEvent) -> None:
        event.status = PersistedEventStatus.EXPIRED

    def get_events(
        self,
        *,
        status: PersistedEventStatus | None = None,
        queue: Queue | None = None,
        limit: int | None = None,
        skip: int | None = None,
        order_by: str = "-created_at",
    ) -> Iterable[PersistedEvent]:

        stmt = select(PersistedEvent)

        if status:
            stmt = stmt.where(PersistedEvent._status == status.value)

        if queue:
            stmt = stmt.where(PersistedEvent.queue == queue.value)

        if order_by.endswith("created_at"):
            if order_by.startswith("-"):
                stmt = stmt.order_by(PersistedEvent.created_at.desc())
            else:
                stmt = stmt.order_by(PersistedEvent.created_at.asc())

        if limit:
            stmt = stmt.limit(limit)

        if skip:
            stmt = stmt.offset(skip)

        return self.session.scalars(stmt)
