import time

from discord import TextChannel

from chatbot.command.base_command import BaseCommand
from chatbot.command.position_command import GetPositionCommand
from database.event_store import EventStore
from database.pair_store import PairStore
from database.session_factory import SessionFactory
from database.token_store import TokenStore
from ext_api.dexscreener import DexPair, DexScreener
from models.dex_id import DexId
from models.event import EventType
from models.event import PersistedEvent as Event
from models.event import Queue
from models.token import Pair, PairQuote, Token
from web3_helper.abi import ABIFetcher, ABIManager
from web3_helper.helper import Web3Client


class TrackPairCommand(BaseCommand):
    def __init__(
        self,
        *,
        session_factory: SessionFactory,
        web3_client: Web3Client,
        abi_fetcher: ABIFetcher,
    ) -> None:
        super().__init__(name="track", description="Track a new token")
        self.session_factory = session_factory
        self.web3_client = web3_client
        self.abi_fetcher = abi_fetcher

    async def track_pair(self, dex_pair: DexPair, channel: TextChannel) -> bool:
        # check if pair already exists
        with self.session_factory.session() as session:
            pair_store = PairStore(session)
            token_store = TokenStore(session)
            abi_manager = ABIManager(session=session, abi_fetcher=self.abi_fetcher)
            base_token = dex_pair.baseToken
            quote_token = dex_pair.quoteToken

            pair = pair_store.get_pair(dex_pair.pairAddress)
            if pair:
                await channel.send(
                    f"Token {base_token.symbol}/{base_token.name} is already tracked"
                )
                return False

            db_base_token = token_store.get_token(base_token.address)
            if not db_base_token:
                base_contract = self.web3_client.web3.eth.contract(
                    self.web3_client.to_checksum_address(base_token.address),
                    abi=abi_manager.get_abi(address=base_token.address),
                )

                token_decimals = base_contract.functions.decimals().call()

                db_base_token = Token(
                    address=base_token.address,
                    symbol=base_token.symbol,
                    name=base_token.name,
                    decimals=token_decimals,
                )

                token_store.add_token(db_base_token)
                session.commit()

            db_quote_token = token_store.get_token(quote_token.address)
            if not db_quote_token:
                quote_contract = self.web3_client.web3.eth.contract(
                    self.web3_client.to_checksum_address(quote_token.address),
                    abi=abi_manager.get_abi(address=quote_token.address),
                )

                token_decimals = quote_contract.functions.decimals().call()

                db_quote_token = Token(
                    address=quote_token.address,
                    symbol=quote_token.symbol,
                    name=quote_token.name,
                    decimals=token_decimals,
                )

                token_store.add_token(db_quote_token)
                session.commit()

            pair = Pair(
                address=dex_pair.pairAddress,
                base_address=base_token.address,
                quote_address=quote_token.address,
                dex=DexId.from_dex_pair(dex_pair),
                chain=dex_pair.chainId,
            )

            pair_store.add_pair(pair)
            session.commit()

            pair_store.add_pair_quote(
                PairQuote(
                    pair_address=pair.address,
                    price=self.web3_client.web3.to_wei(dex_pair.priceNative, "ether"),
                    data=dex_pair.model_dump(),
                    timestamp=int(time.time()),
                )
            )

            EventStore(session).add_event(
                Event(
                    queue=Queue.TRADE_BOT,
                    event_type=EventType.UPDATE_BALANCES,
                    data={"addresses": [pair.base_address]},
                    created_at=int(time.time()),
                )
            )
            session.commit()

            await channel.send(f"Token {base_token.symbol}/{base_token.name} added")
            await GetPositionCommand(
                session_factory=self.session_factory, web3_client=self.web3_client
            ).post_pair_information(pair, channel, session)

            return True

    async def execute(self, *, channel: TextChannel, args: list[str] = []) -> None:
        if args:
            pair_addr = args[0]
            pairs_response = DexScreener.get_pairs([pair_addr])

            def filter_pair(dex_pair: DexPair) -> bool:
                return dex_pair.chainId == "base"  # and dex_pair.dexId == "uniswap"

            base_pairs = list(filter(filter_pair, pairs_response.pairs))

            if base_pairs:
                is_added = await self.track_pair(base_pairs[0], channel)
            else:
                await channel.send(f"Pair unsupported")
