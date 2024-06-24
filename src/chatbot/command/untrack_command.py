from discord import TextChannel

from chatbot.command.base_command import BaseCommand
from database.pair_price_alert_store import PairPriceAlertStore
from database.pair_store import PairStore
from database.position_store import PositionStore
from database.session_factory import SessionFactory
from database.token_store import TokenStore


class UntrackCommand(BaseCommand):
    def __init__(self, *, session_factory: SessionFactory) -> None:
        super().__init__(
            name="untrack",
            description="Untrack a pair",
        )

        self.session_factory = session_factory

    async def execute(self, *, channel: TextChannel, args: list[str] = []) -> None:
        pair_address = args[0]
        with self.session_factory.session() as session:
            pair_store = PairStore(session)
            pair = pair_store.get_pair(pair_address)
            if pair:
                PositionStore(session).delete_position(pair.address)
                PairPriceAlertStore(session).delete_price_alert_for_pair(pair.address)
                pair_store.delete_pair(pair.address)
                session.commit()
                TokenStore(session).delete_token(pair.base_address)
                session.commit()
                await channel.send(f"Pair {pair.address} deleted")
