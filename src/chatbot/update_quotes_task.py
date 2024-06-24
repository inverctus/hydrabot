import time

from discord.abc import GuildChannel
from discord.ext import commands, tasks

from chatbot.command.update_pair_quotes_command import UpdatePairQuotesCommand
from database.pair_store import PairStore
from database.session_factory import SessionFactory
from web3_helper.helper import Web3Client


class UpdateQuotesTask(commands.Cog):
    QUOTE_EXPIRATION = 3600 * 24 * 31

    def __init__(
        self,
        session_factory: SessionFactory,
        web3_client: Web3Client,
        channel: GuildChannel,
    ):
        self.session_factory = session_factory
        self.web3_client = web3_client
        self.channel = channel
        self.update.start()

    @tasks.loop(seconds=10)
    async def update(self):
        with self.session_factory.session() as session:
            await UpdatePairQuotesCommand(
                session_factory=self.session_factory,
                web3_client=self.web3_client,
            ).execute(
                channel=self.channel,
            )

            PairStore(session).clean_quotes_before_timestamp(
                int(time.time()) - self.QUOTE_EXPIRATION
            )
            session.commit()
