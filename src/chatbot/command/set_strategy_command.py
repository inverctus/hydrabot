from discord import TextChannel

from chatbot.command.base_command import BaseCommand
from chatbot.utils import address_pretty_string
from database.pair_store import PairStore
from database.session_factory import SessionFactory
from models.token import Pair
from tradebot.strategies_worker import StrategyFactory


class SetStrategyCommand(BaseCommand):
    def __init__(
        self,
        *,
        session_factory: SessionFactory,
    ) -> None:
        super().__init__(
            name="strategy",
            short_hand="s",
            description="Set strategy to use for a pair",
        )

        self.session_factory = session_factory

    async def execute(self, *, channel: TextChannel, args: list[str] = []) -> None:
        if len(args) != 2:
            await channel.send("Invalid use of set strategy command")

        # first arg, pair address
        # second arg, strategy

        message_id: int | None = None
        pair_address: str | None = None

        try:
            message_id = int(args[0])
        except:
            pair_address = args[0]

        strategy = args[1]
        available_strategies = StrategyFactory().all_names()

        if strategy.lower() not in available_strategies:
            available_strategies_str = ", ".join(available_strategies)
            await channel.send(
                f"Invalid strategy \n Availables strategies: {available_strategies_str}"
            )
            return

        with self.session_factory.session() as session:
            pair_store = PairStore(session)
            pair: Pair | None = None

            if message_id:
                pair = pair_store.get_pair_by_message_id(message_id)
            elif pair_address:
                pair = pair_store.get_pair(pair_address)

            if pair:
                pair.strategy = "" if strategy.lower() == "none" else strategy
                session.commit()

                await channel.send(
                    f"Strategy for pair {address_pretty_string(pair.address)} {pair.base_token.symbol} set to {strategy}"
                )
            else:
                await channel.send(f"Pair not found")
