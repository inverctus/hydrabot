import time

from discord import TextChannel

from chatbot.command.base_command import BaseCommand
from database.event_store import EventStore
from database.session_factory import SessionFactory
from models.event import EventType
from models.event import PersistedEvent as Event
from models.event import Queue
from web3_helper.helper import Web3Client


class WrapCommand(BaseCommand):
    def __init__(
        self,
        *,
        session_factory: SessionFactory,
        web3_client: Web3Client,
    ) -> None:
        super().__init__(name="wrap", description="Wrap ETH")
        self.session_factory = session_factory
        self.web3_client = web3_client

    async def execute(self, *, channel: TextChannel, args: list[str] = []) -> None:
        if len(args) == 0:
            await channel.send("Missing amount to wrap")

        value = float(args[0])

        with self.session_factory.session() as session:
            EventStore(session).add_event(
                Event(
                    queue=Queue.TRADE_BOT,
                    event_type=EventType.WRAP,
                    data={
                        "value": int(self.web3_client.web3.to_wei(value, "ether")),
                    },
                    created_at=int(time.time()),
                )
            )
            session.commit()
            await channel.send(f"Trying to wrap {value} ETH to WETH")
