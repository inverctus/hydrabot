from flask import Blueprint
from flask_pydantic import validate
from pydantic import BaseModel

from api.auth import Authorization
from database.event_store import EventStore
from database.session_factory import SessionFactory
from models.event import PersistedEventStatus, Queue
from settings import SettingsFactory

api_settings = SettingsFactory.get_api_settings()

events_blueprint = Blueprint("events", __name__, url_prefix="/events")
auth = Authorization(api_settings["api_key"])
session_factory = SessionFactory(api_settings["database_uri"])


class EventsQuery(BaseModel):
    limit: int = 100
    skip: int = 0
    queue: Queue | None = None
    status: PersistedEventStatus | None = None


@events_blueprint.route("/", methods=["GET"])
@auth.should_be_authenticated
@validate()
def get_events(query: EventsQuery):
    with session_factory.session() as session:
        events = EventStore(session=session).get_events(
            queue=query.queue,
            status=query.status,
            limit=query.limit,
            skip=query.skip,
        )

        return {
            "events": [event.asdict() for event in events],
        }, 200


@events_blueprint.route("/<event_id>", methods=["GET"])
@auth.should_be_authenticated
@validate()
def get_event(event_id: int):
    with session_factory.session() as session:
        event = EventStore(session=session).get_event_by_id(event_id=event_id)

        if not event:
            return "Not Found", 404

        return event.asdict(), 200
