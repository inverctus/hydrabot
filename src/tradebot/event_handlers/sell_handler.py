import logging
import time

from eth_account.account import LocalAccount
from sqlalchemy.orm import Session

from chatbot.utils import address_pretty_string
from database.data_dump_store import DataDumpStore
from database.event_store import EventStore
from database.pair_store import PairStore
from database.position_store import PositionStore
from database.token_store import TokenStore
from database.trade_setting_store import TradeSettingStore
from models.data_dump import DumpType
from models.event import ChatMessageType, EventType, PersistedEvent, Queue, SellEvent
from models.event_handler import EventHandler
from models.token import TOKEN_ADDRESSES, TokenName
from models.trade_setting import TradeSettingName
from models.utils import get_position_metric
from tradebot.event_handlers.error import TradeException, TradeInformationBuilder
from tradebot.trade_handler.aerodrome.aerodrome_sell_handler import AerodromeSellHandler
from tradebot.trade_handler.handler import BaseTradeHandler, TradeStatus
from tradebot.trade_handler.payload import SellPayload
from tradebot.trade_handler.sushiswap.sushiswap_sell_handler import SushiSwapSellHandler
from tradebot.trade_handler.uniswap.uniswap_sell_handler import UniswapSellHandler
from tradebot.utils import get_pair_latest_quote, push_chat_event
from web3_helper.abi import ABIFetcher, ABIManager
from web3_helper.helper import Web3Client

logger = logging.getLogger(__name__)


class SellHandler(EventHandler[SellEvent]):
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

    def run(self, *, event: SellEvent, session: Session) -> None:
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

                trade_setting_store = TradeSettingStore(session)
                slippage: float = 0.0

                if not event.slippage:
                    slippage_setting = trade_setting_store.get_setting(
                        TradeSettingName.SLIPPAGE
                    )

                    if not slippage_setting:
                        raise TradeException(
                            message=f"Trade settings not defined",
                            trade_information=TradeInformationBuilder(
                                trade_handler=self.__class__.__name__,
                                event_id=event.id,
                            ).build(),
                        )

                    slippage = slippage_setting.get_float()
                else:
                    slippage = event.slippage

                minimum_eth_setting = trade_setting_store.get_setting(
                    TradeSettingName.MIN_ETH_REQUIRED
                )
                w3 = self.web3_client.web3

                if not minimum_eth_setting:
                    raise TradeException(
                        message=f"Trade settings not defined",
                        trade_information=TradeInformationBuilder(
                            trade_handler=self.__class__.__name__,
                            event_id=event.id,
                        ).build(),
                    )

                if (
                    not pair
                    or not base_token
                    or not quote_token
                    or not eth_token
                    or not position
                ):
                    raise TradeException(
                        message=f"Pair {pair.address} doesn't exists",
                        trade_information=TradeInformationBuilder(
                            trade_handler=self.__class__.__name__,
                            event_id=event.id,
                        ).build(),
                    )

                if not pair.chain == "base":
                    raise TradeException(
                        message=f"Chain {pair.chain} isn't supported",
                        trade_information=TradeInformationBuilder(
                            trade_handler=self.__class__.__name__,
                            event_id=event.id,
                        ).build(),
                    )

                base_abi = abi_manager.get_abi(address=pair.base_address)
                quote_abi = abi_manager.get_abi(address=pair.quote_address)

                latest_quote = get_pair_latest_quote(
                    session=session,
                    pair_address=pair.address,
                    web3_client=self.web3_client,
                )

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
                quote_balance_before = quote_contract.functions.balanceOf(
                    self.wallet.address
                ).call()

                if base_balance_before < event.value:
                    raise TradeException(
                        message=f"Balance too low for {base_token.symbol}, balance={base_balance_before}",
                        trade_information=TradeInformationBuilder(
                            trade_handler=self.__class__.__name__,
                            event_id=event.id,
                        ).build(),
                    )

                if eth_balance < w3.to_wei(minimum_eth_setting.get_float(), "ether"):
                    raise TradeException(
                        message=f"Balance of ETH under minimum requirement",
                        trade_information=TradeInformationBuilder(
                            trade_handler=self.__class__.__name__,
                            event_id=event.id,
                        ).build(),
                    )

                amount_out = float(
                    event.value * w3.from_wei(latest_quote.price, "ether")
                )
                min_amount_out = int(
                    (amount_out - (amount_out * slippage))
                    * 10 ** (quote_token.decimals - base_token.decimals)
                )

                sell_payload = SellPayload(
                    pair=event.pair,
                    value=event.value,
                    min_out=min_amount_out,
                    base_token=base_token,
                    quote_token=quote_token,
                )

                trade_handler: BaseTradeHandler[SellPayload] | None = None

                if pair.dex.name == "uniswap":
                    trade_handler = UniswapSellHandler(
                        wallet=self.wallet,
                        web3_client=self.web3_client,
                        abi_manager=abi_manager,
                    )
                elif pair.dex.name == "sushiswap":
                    trade_handler = SushiSwapSellHandler(
                        wallet=self.wallet,
                        web3_client=self.web3_client,
                        abi_manager=abi_manager,
                    )
                # elif pair.dex.name == "aerodrome":
                #    trade_handler = AerodromeSellHandler(
                #        wallet=self.wallet,
                #        web3_client=self.web3_client,
                #        abi_manager=abi_manager,
                #    )

                if not trade_handler:
                    raise TradeException(
                        message=f"Dex {pair.dex.name} isn't supported",
                        trade_information=TradeInformationBuilder(
                            trade_handler=self.__class__.__name__,
                            event_id=event.id,
                        ).build(),
                    )

                if result := trade_handler.execute(
                    pair=pair,
                    payload=sell_payload,
                    session=session,
                ):

                    if result.status == TradeStatus.FAILED:
                        raise TradeException(
                            message=f"Sell order has failed! {result.message}",
                            trade_information=TradeInformationBuilder(
                                trade_handler=type(trade_handler).__name__,
                                event_id=event.id,
                                amount=event.value,
                                min_amount=min_amount_out,
                                slippage=slippage,
                                source_address=base_token.address,
                                destination_address=quote_token.address,
                            ).build(),
                            transation_hashes={
                                "approve": result.allowance_tx,
                                "swap": result.swap_tx,
                            },
                        )

                    position_metric = get_position_metric(
                        position=position,
                        web3_client=self.web3_client,
                        base_token=base_token,
                        latest_quote=latest_quote,
                    )

                    quote_balance = quote_contract.functions.balanceOf(
                        self.wallet.address
                    ).call()
                    quote_token.balance = quote_balance

                    base_balance = base_contract.functions.balanceOf(
                        self.wallet.address
                    ).call()
                    base_token.balance = base_balance

                    token_ratio = (
                        float(event.value / position.token_bought)
                        if position.token_bought > 0
                        else 0
                    )

                    token_sold = base_balance_before - base_balance
                    quote_received = quote_balance - quote_balance_before

                    if token_sold == 0:
                        raise TradeException(
                            message="Trade has failed",
                            trade_information=TradeInformationBuilder(
                                trade_handler=type(trade_handler).__name__,
                                event_id=event.id,
                                amount=event.value,
                                min_amount=min_amount_out,
                                slippage=slippage,
                                source_address=base_token.address,
                                destination_address=quote_token.address,
                            ).build(),
                            transation_hashes={
                                "approve": result.allowance_tx,
                                "swap": result.swap_tx,
                            },
                        )

                    realized_pnl = token_ratio * float(position_metric.profit_and_loss)

                    position.book_value = int(
                        (1.00000000000 - float(token_ratio))
                        * float(position.book_value)
                    )
                    position.token_sold += int(token_sold)

                    position.realized_pnl += int(realized_pnl)
                    position.last_action_at = int(time.time())
                    tx_link = f"https://basescan.org/tx/{result.swap_tx}"

                    EventStore(session).add_event(
                        PersistedEvent(
                            queue=Queue.CHAT_BOT,
                            event_type=EventType.CHAT,
                            data={
                                "message_type": ChatMessageType.EMBED,
                                "title": f"Sell {base_token.symbol} transaction",
                                "url": tx_link,
                                "message": f"Sold {token_sold / 10**base_token.decimals} {base_token.symbol} for {self.web3_client.web3.from_wei(quote_received, 'ether')} WETH",
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

                    if result.status == TradeStatus.SUCCESS and base_balance == 0:
                        position_store = PositionStore(session)
                        if position := position_store.get_position(pair.address):
                            DataDumpStore(session).add_data_dump(
                                dump_type=DumpType.CLOSED_POSITION,
                                data=position.as_dict(),
                            )

                            position_store.delete_position(pair.address)
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
            logging.exception("Transaction Error")

            raise exp
