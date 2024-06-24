import time
from typing import Any

from sqlalchemy.orm import Session

from database.event_store import EventStore
from database.pair_store import PairStore
from ext_api.dexscreener import DexScreener
from models.event import EventType
from models.event import PersistedEvent as Event
from models.event import PersistedEventStatus, Queue
from models.token import PairQuote
from web3_helper.helper import Web3Client


def push_chat_event(
    *, session: Session, message_data: dict[str, Any], auto_commit: bool = True
) -> None:
    EventStore(session).add_event(
        Event(
            queue=Queue.CHAT_BOT,
            event_type=EventType.CHAT,
            data=message_data,
            created_at=int(time.time()),
        )
    )

    if auto_commit:
        session.commit()


def push_trade_event(
    *,
    session: Session,
    event_type: EventType,
    message_data: dict[str, Any],
    wait_for_completion: bool = False,
    auto_commit: bool = True,
) -> Event:

    event_store = EventStore(session)
    new_event = Event(
        queue=Queue.TRADE_BOT,
        event_type=event_type,
        data=message_data,
        created_at=int(time.time()),
    )

    event_store.add_event(new_event)

    if auto_commit:
        session.commit()

    if wait_for_completion and auto_commit:
        # event_id = new_event.id
        while True:
            session.refresh(new_event)

            if new_event.status != PersistedEventStatus.PENDING:
                return new_event

            time.sleep(0.1)

    return new_event


def get_pair_latest_quote(
    *, session: Session, pair_address: str, web3_client: Web3Client
) -> PairQuote:
    pairs_response = DexScreener.get_pairs(pair_addresses=[pair_address])

    for dex_pair in pairs_response.pairs:
        if dex_pair.pairAddress == pair_address:
            latest_quote = PairQuote(
                pair_address=pair_address,
                price=web3_client.web3.to_wei(dex_pair.priceNative, "ether"),
                data=dex_pair.model_dump(),
                timestamp=int(time.time()),
            )

            PairStore(session).add_pair_quote(latest_quote)
            session.commit()

            return latest_quote

    raise Exception(f"Pair quote for {pair_address} not found")
