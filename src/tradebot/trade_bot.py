import logging
import time
from typing import Any, Type

from sqlalchemy.orm import Session

from database.event_store import EventStore
from database.session_factory import SessionFactory
from models.event import (
    BuyEvent,
    Event,
    Queue,
    SellEvent,
    UpdateBalancesEvent,
    WrapEvent,
    get_event_builder,
)
from models.event_handler import EventHandler
from tradebot.event_handlers.buy_handler import BuyHandler
from tradebot.event_handlers.error import TradeException
from tradebot.event_handlers.sell_handler import SellHandler
from tradebot.event_handlers.update_balances_handler import UpdateBalancesHandler
from tradebot.event_handlers.wrap_handler import WrapHandler
from web3_helper.abi import ABIFetcher
from web3_helper.helper import Web3Helper

logger = logging.getLogger(__name__)


class TradeBot:
    def __init__(
        self,
        *,
        wallet_private_key: str,
        db_session_factory: SessionFactory,
        web3_provider_url: str,
        base_scan_api_key: str,
    ) -> None:
        self._wallet = Web3Helper.get_wallet(wallet_private_key)
        self._abi_fetcher = ABIFetcher(base_scan_api_key=base_scan_api_key)
        self._web3_client = Web3Helper.get_web3(web3_provider_url)

        self.db_session_factory = db_session_factory
        self.handlers: dict[Type, EventHandler] = {
            UpdateBalancesEvent: UpdateBalancesHandler(
                wallet=self._wallet,
                abi_fetcher=self._abi_fetcher,
                web3_client=self._web3_client,
            ),
            BuyEvent: BuyHandler(
                wallet=self._wallet,
                web3_client=self._web3_client,
                abi_fetcher=self._abi_fetcher,
            ),
            SellEvent: SellHandler(
                wallet=self._wallet,
                web3_client=self._web3_client,
                abi_fetcher=self._abi_fetcher,
            ),
            WrapEvent: WrapHandler(
                wallet=self._wallet,
                web3_client=self._web3_client,
                abi_fetcher=self._abi_fetcher,
            ),
        }

    def _handle_event(self, event: Event, session: Session) -> None:
        if event_handler := self.handlers.get(type(event)):
            event_handler.run(event=event, session=session)
        else:
            logger.warning(f"No handler for this type {type(event)}")

    def run(self) -> None:
        while True:
            with self.db_session_factory.session() as session:
                event_store = EventStore(session)

                if persisted_event := event_store.get_latest_event(
                    queue=Queue.TRADE_BOT
                ):
                    try:
                        if (
                            persisted_event.expire_at
                            and persisted_event.expire_at > int(time.time())
                        ):
                            # expire event
                            event_store.expire_event(persisted_event)
                        else:
                            event = get_event_builder().build_from_persisted_event(
                                persisted_event
                            )
                            event_store.ack_event(persisted_event)

                            self._handle_event(event, session)
                            event_store.complete_event(
                                persisted_event,
                                {},
                            )
                            session.commit()
                    except Exception as exp:
                        execution_data: dict = {
                            "exception": str(exp),
                        }

                        if isinstance(exp, TradeException):
                            execution_data["trade_information"] = exp.trade_information
                            execution_data["transaction_hashes"] = exp.transation_hashes

                        event_store.fail_event(
                            event=persisted_event, execution_data=execution_data
                        )
                        session.commit()
                        logger.exception(
                            f"Error while executing event id={persisted_event.id}"
                        )

            time.sleep(0.2)
