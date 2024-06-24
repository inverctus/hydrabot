from discord import Embed, TextChannel
from discord.ext import commands, tasks

from chatbot.command.update_pair_quotes_command import UpdatePairQuotesCommand
from database.event_store import EventStore
from database.session_factory import SessionFactory
from models.event import ChatEvent, ChatMessageType, EventType, Queue
from web3_helper.helper import Web3Client


class ChatQueueListener(commands.Cog):
    def __init__(
        self,
        *,
        session_factory: SessionFactory,
        web3_client: Web3Client,
        channel: TextChannel,
        web_api_uri: str | None = None,
        web_api_key: str | None = None,
    ):
        self.session_factory = session_factory
        self.web3_client = web3_client
        self.channel = channel
        self.web_api_uri = web_api_uri
        self.web_api_key = web_api_key
        self.post_pending_message.start()

    def _get_embed_from_chat_event(self, chat_event: ChatEvent) -> Embed:
        embed = Embed(
            title=chat_event.title,
            url=chat_event.url,
            description=chat_event.message,
        )

        for field in chat_event.fields:
            embed.add_field(
                name=field["name"],
                value=field["value"],
                inline=field["inline"],
            )

        return embed

    def _get_error_embed_from_chat_event(self, chat_event: ChatEvent) -> Embed:
        api_event_url = ""
        if chat_event.source_event_id and self.web_api_key:
            api_event_url = f"{self.web_api_uri}events/{chat_event.source_event_id}?apikey={self.web_api_key}"

        embed = Embed(
            title="Error",
            description=chat_event.message,
            url=api_event_url,
        )

        embed.add_field(
            name="Event Id", value=str(chat_event.source_event_id), inline=False
        )

        return embed

    @tasks.loop(seconds=2)
    async def post_pending_message(self):
        with self.session_factory.session() as session:
            event_store = EventStore(session)
            if last_event := EventStore(session).get_latest_event(queue=Queue.CHAT_BOT):
                event_store.ack_event(last_event)
                if last_event.event_type == EventType.CHAT:
                    chat_event = ChatEvent(
                        id=last_event.id,
                        created_at=last_event.created_at,
                        data=last_event.data,
                    )

                    if chat_event.message_type == ChatMessageType.TEXT:
                        await self.channel.send(last_event.data["message"])
                    elif chat_event.message_type == ChatMessageType.EMBED:
                        embed = self._get_embed_from_chat_event(chat_event)
                        await self.channel.send(embed=embed)
                    elif chat_event.message_type == ChatMessageType.ERROR:
                        embed = self._get_error_embed_from_chat_event(chat_event)
                        await self.channel.send(embed=embed)

                event_store.complete_event(last_event)
                session.commit()
