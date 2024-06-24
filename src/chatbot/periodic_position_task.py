from discord import TextChannel
from discord.ext import commands, tasks

from chatbot.command.position_command import GetPositionCommand
from database.session_factory import SessionFactory
from web3_helper.helper import Web3Client


class PeriodicPositionTask(commands.Cog):
    def __init__(
        self,
        session_factory: SessionFactory,
        web3_client: Web3Client,
        channel: TextChannel,
    ):
        self.session_factory = session_factory
        self.web3_client = web3_client
        self.channel = channel
        self.positions_message.start()

    @tasks.loop(minutes=60)
    async def positions_message(self):
        await GetPositionCommand(
            session_factory=self.session_factory, web3_client=self.web3_client
        ).execute(channel=self.channel)
