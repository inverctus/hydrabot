import time
from typing import Any, cast

from discord import Client, Intents, Message, Reaction, TextChannel, User
from sqlalchemy.orm import Session

from chatbot.chat_queue_listener import ChatQueueListener
from chatbot.command.balance_command import GetBalanceCommand
from chatbot.command.gas_command import GasCommand
from chatbot.command.position_command import GetPositionCommand
from chatbot.command.set_strategy_command import SetStrategyCommand
from chatbot.command.settings_command import SettingsCommand
from chatbot.command.track_pair_command import TrackPairCommand
from chatbot.command.untrack_command import UntrackCommand
from chatbot.command.update_pair_quotes_command import UpdatePairQuotesCommand
from chatbot.command.wrap_command import WrapCommand
from chatbot.commands_handler import CommandsHandler
from chatbot.constants import EmojiRef
from chatbot.periodic_position_task import PeriodicPositionTask
from chatbot.update_ether_price_task import UpdateEtherPriceTask
from chatbot.update_quotes_task import UpdateQuotesTask
from database.event_store import EventStore
from database.pair_store import PairStore
from database.session_factory import SessionFactory
from database.token_store import TokenStore
from database.trade_setting_store import TradeSettingStore
from models.event import EventType
from models.event import PersistedEvent as Event
from models.event import Queue
from models.token import TOKEN_ADDRESSES, Token, TokenName
from models.trade_setting import TradeSettingName
from settings.trade_settings_manager import TradeSettingsManager
from web3_helper.abi import ABIFetcher
from web3_helper.helper import Web3Client


def look_likes_token_addr(message: str) -> tuple[bool, str]:
    trimmed_message = message.strip()
    return (message.startswith("0x") and len(trimmed_message) == 42, trimmed_message)


def push_event_to_trade_bot(
    session: Session, event_type: EventType, event_data: dict[str, Any]
) -> None:
    EventStore(session).add_event(
        Event(
            queue=Queue.TRADE_BOT,
            event_type=event_type,
            data=event_data,
            created_at=int(time.time()),
        )
    )

    session.commit()


class DiscordChatBot(Client):
    def __init__(
        self,
        *,
        db_session_factory: SessionFactory,
        listen_channel_id: str,
        web3_client: Web3Client,
        base_scan_api_key: str,
        allowed_user_ids: list[int],
        web_api_key: str | None,
        web_api_uri: str | None,
    ) -> None:
        intents = Intents.default()
        intents.message_content = True

        super().__init__(intents=intents)
        self.command_prefix = "!"
        self.db_session_factory = db_session_factory
        self.listen_channel_id = int(listen_channel_id)
        self.web3_client = web3_client
        self.abi_fetcher = ABIFetcher(base_scan_api_key=base_scan_api_key)
        self.allowed_user_ids = allowed_user_ids
        self.web_api_key = web_api_key
        self.web_api_uri = web_api_uri

        self.bot_user_id: int | None = None

        self.commands_handler = CommandsHandler(
            prefix=self.command_prefix,
            commands=[
                GetPositionCommand(
                    session_factory=self.db_session_factory,
                    web3_client=self.web3_client,
                ),
                GetBalanceCommand(
                    session_factory=self.db_session_factory,
                ),
                SettingsCommand(
                    session_factory=self.db_session_factory,
                ),
                UpdatePairQuotesCommand(
                    session_factory=self.db_session_factory,
                    web3_client=self.web3_client,
                ),
                TrackPairCommand(
                    session_factory=self.db_session_factory,
                    web3_client=self.web3_client,
                    abi_fetcher=self.abi_fetcher,
                ),
                GasCommand(
                    session_factory=self.db_session_factory,
                    web3_client=self.web3_client,
                ),
                UntrackCommand(
                    session_factory=self.db_session_factory,
                ),
                WrapCommand(
                    session_factory=self.db_session_factory,
                    web3_client=self.web3_client,
                ),
            ],
        )

        self.update_quotes_task: UpdateQuotesTask | None = None
        self.chat_queue_listener: ChatQueueListener | None = None
        self.update_ether_price: UpdateEtherPriceTask | None = None
        self.periodic_position: PeriodicPositionTask | None = None

    def _init_bot(self):
        self.bot_user_id = self.user.id if self.user else None

        trade_settings_manager = TradeSettingsManager(self.db_session_factory)
        trade_settings_manager.get_all_settings()

        with self.db_session_factory.session() as session:
            token_store = TokenStore(session)
            eth_token = token_store.get_token(TOKEN_ADDRESSES[TokenName.ETH])
            if not eth_token:
                eth_token = Token(
                    address=TOKEN_ADDRESSES[TokenName.ETH],
                    symbol="ETH",
                    name="Ether",
                    decimals=18,
                )

                token_store.add_token(eth_token)
                session.commit()

            weth_token = token_store.get_token(TOKEN_ADDRESSES[TokenName.WETH])
            if not weth_token:
                weth_token = Token(
                    address=TOKEN_ADDRESSES[TokenName.WETH],
                    symbol="WETH",
                    name="Wrapped Ether",
                    decimals=18,
                )

                token_store.add_token(weth_token)
                session.commit()

        push_event_to_trade_bot(session, EventType.UPDATE_BALANCES, {})

    async def on_ready(self) -> None:
        self._init_bot()

        channel = self.get_channel(self.listen_channel_id)

        self.update_ether_price = UpdateEtherPriceTask(
            session_factory=self.db_session_factory,
            web3_client=self.web3_client,
        )

        if isinstance(channel, TextChannel):
            self.update_quotes_task = UpdateQuotesTask(
                session_factory=self.db_session_factory,
                web3_client=self.web3_client,
                channel=channel,
            )

            self.chat_queue_listener = ChatQueueListener(
                session_factory=self.db_session_factory,
                web3_client=self.web3_client,
                channel=channel,
                web_api_uri=self.web_api_uri,
                web_api_key=self.web_api_key,
            )

            self.periodic_position = PeriodicPositionTask(
                session_factory=self.db_session_factory,
                web3_client=self.web3_client,
                channel=channel,
            )

    async def on_reaction_add(self, reaction: Reaction, user: User) -> None:
        if self.user and user.id != self.user.id:
            if user.id not in self.allowed_user_ids:
                return

            encoded_emoji = (
                reaction.emoji.encode() if isinstance(reaction.emoji, str) else ""
            )

            with self.db_session_factory.session() as session:
                trade_setting_store = TradeSettingStore(session)
                if pair := PairStore(session).get_pair_by_message_id(
                    reaction.message.id
                ):
                    if encoded_emoji == EmojiRef.BUY:
                        if buy_amount_setting := trade_setting_store.get_setting(
                            TradeSettingName.BUY_AMOUNT
                        ):
                            push_event_to_trade_bot(
                                session,
                                EventType.BUY,
                                {
                                    "pair": pair.address,
                                    "value": self.web3_client.web3.to_wei(
                                        buy_amount_setting.get_float(), "ether"
                                    ),
                                    "slippage": None,
                                },
                            )

                    elif encoded_emoji == EmojiRef.BUY_DOUBLE:
                        if buy_amount_setting := trade_setting_store.get_setting(
                            TradeSettingName.BUY_AMOUNT
                        ):
                            push_event_to_trade_bot(
                                session,
                                EventType.BUY,
                                {
                                    "pair": pair.address,
                                    "value": self.web3_client.web3.to_wei(
                                        buy_amount_setting.get_float() * 2.000000,
                                        "ether",
                                    ),
                                    "slippage": None,
                                },
                            )

                    elif encoded_emoji == EmojiRef.SELL_ALL:
                        if token := TokenStore(session).get_token(pair.base_address):
                            push_event_to_trade_bot(
                                session,
                                EventType.SELL,
                                {
                                    "pair": pair.address,
                                    "value": int(token.balance),
                                    "slippage": None,
                                },
                            )

                            session.commit()

                    elif encoded_emoji == EmojiRef.SELL_HALF:
                        if token := TokenStore(session).get_token(pair.base_address):
                            push_event_to_trade_bot(
                                session,
                                EventType.SELL,
                                {
                                    "pair": pair.address,
                                    "value": int(token.balance / 2),
                                    "slippage": None,
                                },
                            )

                    elif encoded_emoji == EmojiRef.CLOSE_POSITION:
                        await UntrackCommand(
                            session_factory=self.db_session_factory
                        ).execute(
                            channel=cast(TextChannel, reaction.message.channel),
                            args=[pair.address],
                        )

    async def on_message(self, message: Message) -> None:
        channel = cast(TextChannel, message.channel)
        if message.channel.id == self.listen_channel_id:
            if message.author.id in self.allowed_user_ids:
                if (
                    message.mentions
                    and message.reference
                    and message.reference.message_id
                ):
                    parent_message_id = message.reference.message_id
                    for mention in message.mentions:
                        if mention.id == self.bot_user_id:
                            await SetStrategyCommand(
                                session_factory=self.db_session_factory,
                            ).execute(
                                channel=channel,
                                args=[
                                    str(parent_message_id),
                                    message.content,
                                ],
                            )
                    return

                if message.content.startswith(self.command_prefix):
                    await self.commands_handler.execute(
                        message=message.content, channel=channel
                    )
                    return

                is_pair_addr, pair_addr = look_likes_token_addr(message.content)

                if is_pair_addr:
                    # track this token
                    await TrackPairCommand(
                        session_factory=self.db_session_factory,
                        web3_client=self.web3_client,
                        abi_fetcher=self.abi_fetcher,
                    ).execute(channel=channel, args=[pair_addr])
