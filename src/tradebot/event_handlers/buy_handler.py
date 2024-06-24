import logging
import time

from eth_account.account import LocalAccount
from sqlalchemy.orm import Session

from chatbot.utils import address_pretty_string
from database.event_store import EventStore
from database.pair_store import PairStore
from database.position_store import PositionStore
from database.token_store import TokenStore
from database.trade_setting_store import TradeSettingStore
from models.event import BuyEvent, ChatMessageType, EventType, PersistedEvent, Queue
from models.event_handler import EventHandler
from models.token import TOKEN_ADDRESSES, Position, TokenName
from models.trade_setting import TradeSettingName
from tradebot.event_handlers.error import TradeException, TradeInformationBuilder
from tradebot.trade_handler.aerodrome.aerodrome_buy_handler import AerodromeBuyHandler
from tradebot.trade_handler.handler import BaseTradeHandler, TradeStatus
from tradebot.trade_handler.payload import BuyPayload
from tradebot.trade_handler.sushiswap.sushiswap_buy_handler import SushiSwapBuyHandler
from tradebot.trade_handler.uniswap.uniswap_buy_handler import UniswapBuyHandler
from tradebot.utils import get_pair_latest_quote, push_chat_event
from web3_helper.abi import ABIFetcher, ABIManager
from web3_helper.helper import Web3Client

logger = logging.getLogger(__name__)


class BuyHandler(EventHandler[BuyEvent]):
    def __init__(
        self,
        *,
        wallet: LocalAccount,
        web3_client: Web3Client,
        abi_fetcher: ABIFetcher,
    ) -> None:
        super().__init__()

        self.wallet = wallet
        self.abi_fetcher = abi_fetcher
        self.web3_client = web3_client

    def run(self, *, event: BuyEvent, session: Session) -> None:
        try:
            pair_store = PairStore(session)
            token_store = TokenStore(session)
            if pair := pair_store.get_pair(event.pair):
                position_store = PositionStore(session)
                abi_manager = ABIManager(session=session, abi_fetcher=self.abi_fetcher)

                base_token = token_store.get_token(pair.base_address)
                quote_token = token_store.get_token(pair.quote_address)
                eth_token = token_store.get_token(TOKEN_ADDRESSES[TokenName.ETH])
                position = position_store.get_position(pair.address)

                if not position:
                    # Position doesn't exists yet
                    position = Position(
                        pair_address=pair.address, created_at=int(time.time())
                    )

                    position_store.add_position(position)
                    session.commit()

                slippage: float = 0.0
                trade_setting_store = TradeSettingStore(session)
                if not event.slippage:
                    slippage_setting = trade_setting_store.get_setting(
                        TradeSettingName.SLIPPAGE
                    )
                    if not slippage_setting:
                        raise TradeException(message=f"Slippage settings not defined")

                    slippage = slippage_setting.get_float()
                else:
                    slippage = event.slippage

                minimum_eth_setting = trade_setting_store.get_setting(
                    TradeSettingName.MIN_ETH_REQUIRED
                )
                minimum_weth_setting = trade_setting_store.get_setting(
                    TradeSettingName.MIN_WETH_REQUIRED
                )
                w3 = self.web3_client.web3

                if not minimum_eth_setting or not minimum_weth_setting:
                    raise TradeException(message=f"Trade settings not defined")

                if (
                    not pair
                    or not base_token
                    or not quote_token
                    or not eth_token
                    or not position
                ):

                    raise TradeException(message=f"Pair {event.pair} doesn't exists")

                if not pair.chain == "base":
                    raise TradeException(message=f"Chain {pair.chain} isn't supported")

                base_abi = abi_manager.get_abi(address=pair.base_address)
                quote_abi = abi_manager.get_abi(address=pair.quote_address)

                base_contract = w3.eth.contract(
                    self.web3_client.to_checksum_address(pair.base_address),
                    abi=base_abi,
                )

                base_balance_before = base_contract.functions.balanceOf(
                    self.wallet.address
                ).call()
                eth_balance = w3.eth.get_balance(self.wallet.address)

                quote_contract = w3.eth.contract(
                    self.web3_client.to_checksum_address(pair.quote_address),
                    abi=quote_abi,
                )
                previous_quote_balance = quote_contract.functions.balanceOf(
                    self.wallet.address
                ).call()

                if previous_quote_balance < event.value:
                    raise TradeException(
                        message=f"Balance too low for {quote_token.symbol}, balance={previous_quote_balance}"
                    )

                if previous_quote_balance < w3.to_wei(
                    minimum_weth_setting.get_float(), "ether"
                ):
                    raise TradeException(
                        message=f"Balance of WETH under minimum requirement"
                    )

                if eth_balance < w3.to_wei(minimum_eth_setting.get_float(), "ether"):
                    raise TradeException(
                        message=f"Balance of ETH under minimum requirement"
                    )

                latest_quote = get_pair_latest_quote(
                    session=session,
                    pair_address=pair.address,
                    web3_client=self.web3_client,
                )

                amount_out = float(event.value / latest_quote.price)
                min_amount_out = int(
                    (amount_out - (amount_out * slippage)) * 10**base_token.decimals
                )

                buy_payload = BuyPayload(
                    pair=event.pair,
                    value=event.value,
                    min_out=min_amount_out,
                    base_token=base_token,
                    quote_token=quote_token,
                )

                trade_handler: BaseTradeHandler[BuyPayload] | None = None

                if pair.dex.name == "uniswap":
                    trade_handler = UniswapBuyHandler(
                        wallet=self.wallet,
                        web3_client=self.web3_client,
                        abi_manager=abi_manager,
                    )
                elif pair.dex.name == "sushiswap":
                    trade_handler = SushiSwapBuyHandler(
                        wallet=self.wallet,
                        web3_client=self.web3_client,
                        abi_manager=abi_manager,
                    )
                # elif pair.dex.name == "aerodrome":
                #    trade_handler = AerodromeBuyHandler(
                #        wallet=self.wallet,
                #        web3_client=self.web3_client,
                #        abi_manager=abi_manager,
                #    )

                if not trade_handler:
                    raise TradeException(message=f"Dex {pair.dex.name} isn't supported")

                if result := trade_handler.execute(
                    pair=pair,
                    payload=buy_payload,
                    session=session,
                ):
                    if result.status == TradeStatus.FAILED:
                        raise TradeException(
                            message=f"Buy order has failed! {result.message}",
                            trade_information=TradeInformationBuilder(
                                trade_handler=type(trade_handler).__name__,
                                amount=event.value,
                                min_amount=min_amount_out,
                                slippage=slippage,
                                source_address=quote_token.address,
                                destination_address=base_token.address,
                            ).build(),
                            transation_hashes={
                                "approve": result.allowance_tx,
                                "swap": result.swap_tx,
                            },
                        )

                    # update quote, base and quote balance
                    quote_balance = quote_contract.functions.balanceOf(
                        self.wallet.address
                    ).call()
                    quote_token.balance = quote_balance

                    base_balance = base_contract.functions.balanceOf(
                        self.wallet.address
                    ).call()
                    base_token.balance = base_balance

                    token_bought = base_balance - base_balance_before
                    if token_bought == 0:
                        raise TradeException(
                            message="Trade has failed",
                            trade_information=TradeInformationBuilder(
                                trade_handler=type(trade_handler).__name__,
                                amount=event.value,
                                min_amount=min_amount_out,
                                slippage=slippage,
                                source_address=quote_token.address,
                                destination_address=base_token.address,
                            ).build(),
                            transation_hashes={
                                "approve": result.allowance_tx,
                                "swap": result.swap_tx,
                            },
                        )

                    position.book_value += event.value  # use balance instead
                    position.token_bought += token_bought  # use base
                    position.last_action_at = int(time.time())

                    tx_link = f"https://basescan.org/tx/{result.swap_tx}"

                    EventStore(session).add_event(
                        PersistedEvent(
                            queue=Queue.CHAT_BOT,
                            event_type=EventType.CHAT,
                            data={
                                "message_type": ChatMessageType.EMBED,
                                "title": f"Buy {base_token.symbol} transaction",
                                "url": tx_link,
                                "message": f"Bought {token_bought / 10**base_token.decimals} {base_token.symbol}",
                                "fields": [
                                    {"name": "Swap Tx id", "value": result.swap_tx},
                                    {
                                        "name": "Approve Tx id",
                                        "value": result.allowance_tx,
                                    },
                                    {"name": "Event Id", "value": event.id},
                                ],
                            },
                            created_at=int(time.time()),
                        )
                    )

                    session.commit()

        except Exception as exp:
            push_chat_event(
                session=session,
                message_data={
                    "message": f"Trade error (swap pair {address_pretty_string(event.pair)}): {exp}",
                    "source_event_id": event.id,
                    "message_type": ChatMessageType.ERROR.value,
                },
            )
            logger.exception("Exception while running buy order")
            raise exp
