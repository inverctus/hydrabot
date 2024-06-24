from discord import TextChannel

from chatbot.command.base_command import BaseCommand
from database.session_factory import SessionFactory
from database.token_store import TokenStore


class GetBalanceCommand(BaseCommand):
    def __init__(self, *, session_factory: SessionFactory) -> None:
        super().__init__(
            name="balance",
            short_hand="b",
            description="Show current balance of all tracked tokens",
        )

        self.session_factory = session_factory

    async def execute(self, *, channel: TextChannel, args: list[str] = []) -> None:
        messages: list[str] = [f"Current balance(s)"]
        with self.session_factory.session() as session:
            for token in TokenStore(session).get_tokens_by_addresses():
                messages.append(
                    f"**{'{0:.20f}'.format(float(token.balance) / 10 ** token.decimals)}** {token.symbol}"
                )

        await channel.send("\n".join(messages))
