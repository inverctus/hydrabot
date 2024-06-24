from discord import Embed, Emoji, TextChannel
from sqlalchemy.orm import Session

from chatbot.command.base_command import BaseCommand
from chatbot.constants import (
    AERODROME_THUMBNAIL_URL,
    SUSHISWAP_THUMBNAIL_URL,
    UNISWAP_THUMBNAIL_URL,
    EmojiRef,
)
from database.pair_store import PairStore
from database.position_store import PositionStore
from database.session_factory import SessionFactory
from database.token_store import TokenStore
from database.trade_setting_store import TradeSettingStore
from ext_api.dexscreener import DexPair, DexScreener
from models.token import Addresses, Pair
from models.trade_setting import TradeSettingName
from models.utils import get_position_metric
from web3_helper.helper import Web3Client


class GetPositionCommand(BaseCommand):
    def __init__(
        self, *, session_factory: SessionFactory, web3_client: Web3Client
    ) -> None:
        super().__init__(
            name="position",
            short_hand="p",
            description="Show current positions",
        )

        self.web3_client = web3_client
        self.session_factory = session_factory

    async def post_pair_information(
        self,
        pair: Pair,
        channel: TextChannel,
        session: Session,
        eth_price_usd: float | None = None,
    ) -> None:
        pair_store = PairStore(session)
        token_store = TokenStore(session)
        position = PositionStore(session).get_position(pair.address)
        latest_quote = pair_store.get_latest_quote(pair.address)
        # TODO joinedload them
        base_token = token_store.get_token(pair.base_address)
        quote_token = token_store.get_token(pair.quote_address)
        buy_trade_setting = TradeSettingStore(session).get_setting(
            TradeSettingName.BUY_AMOUNT
        )

        if (
            not base_token
            or not quote_token
            or not buy_trade_setting
            or not latest_quote
        ):
            return

        quote_price = self.web3_client.web3.from_wei(latest_quote.price, "ether") or 0

        dex_pair: DexPair | None = None
        try:
            dex_pair = DexPair.model_validate(latest_quote.data)
        except:
            pass

        dexscreener_url = DexScreener.get_pair_link(pair.chain, pair.address)

        embed = Embed(
            title=f"{base_token.symbol} ({base_token.name}) / {quote_token.symbol} - {pair.dex.to_str()}",
            url=dexscreener_url,
        )

        if pair.dex.name == "uniswap":
            embed.set_thumbnail(url=UNISWAP_THUMBNAIL_URL)
        elif pair.dex.name == "sushiswap":
            embed.set_thumbnail(url=SUSHISWAP_THUMBNAIL_URL)
        elif pair.dex.name == "aerodrome":
            embed.set_thumbnail(url=AERODROME_THUMBNAIL_URL)

        description = [
            f"Current Price **{'{0:.10f}'.format(quote_price)} {quote_token.symbol}**",
            f"Current Strategy: {pair.strategy if pair.strategy else 'None'}, reply to change",
        ]
        if dex_pair:
            description.append(
                f"Price changes: {dex_pair.priceChange.m5}% {dex_pair.priceChange.h1}% {dex_pair.priceChange.h6}% {dex_pair.priceChange.h24}%"
            )

        embed.description = "\n".join(description)

        if position and base_token.balance > 0:
            position_metric = get_position_metric(
                position=position,
                web3_client=self.web3_client,
                base_token=base_token,
                latest_quote=latest_quote,
            )

            profit_usd: float | None = None
            if eth_price_usd:
                profit_usd = float(position_metric.profit_and_loss) * eth_price_usd

            embed.add_field(
                name="Market Value",
                value=f"**{'{0:.10f}'.format(position_metric.market_value)}** {quote_token.symbol}",
            )

            embed.add_field(
                name="Price Paid",
                value=f"**{'{0:.10f}'.format(position_metric.price_paid)}** {quote_token.symbol}",
            )

            embed.add_field(
                name="PnL (%)",
                value=(
                    f"{'{0:.10f}'.format(position_metric.profit_and_loss)} {quote_token.symbol} {'{0:.2f}$'.format(profit_usd)} ({'{0:.2f}'.format(position_metric.profit_and_loss_percent)} %)"
                    if profit_usd
                    else f"{'{0:.10f}'.format(position_metric.profit_and_loss)} {quote_token.symbol} ({'{0:.2f}'.format(position_metric.profit_and_loss_percent)} %)"
                ),
            )

        double_buy_amount = buy_trade_setting.get_float() * 2

        embed.add_field(
            name="Available action(s)",
            value="\n".join(
                [
                    f":green_circle: to buy ({buy_trade_setting.value} {quote_token.symbol})",
                    f":green_square: to buy ({double_buy_amount} {quote_token.symbol})",
                    ":red_circle: to sell 50%",
                    ":red_square: to sell 100%",
                    ":put_litter_in_its_place: untrack",
                ]
            ),
            inline=False,
        )

        message = await channel.send(embed=embed)

        pair.message_id = message.id
        session.commit()

        await message.add_reaction(EmojiRef.BUY.decode())
        await message.add_reaction(EmojiRef.BUY_DOUBLE.decode())
        await message.add_reaction(EmojiRef.SELL_HALF.decode())
        await message.add_reaction(EmojiRef.SELL_ALL.decode())
        await message.add_reaction(EmojiRef.CLOSE_POSITION.decode())

    async def execute(self, *, channel: TextChannel, args: list[str] = []) -> None:

        with self.session_factory.session() as session:
            pair_store = PairStore(session)
            eth_token = TokenStore(session).get_token(str(Addresses.ETH))
            latest_eth_price = eth_token.latest_price_usd if eth_token else None
            if args:
                for symbol in args:
                    if pair := pair_store.get_pair_by_base_token_by_symbol(symbol):
                        await self.post_pair_information(
                            pair,
                            channel,
                            session,
                            latest_eth_price,
                        )
                    else:
                        await channel.send(f"Token {symbol} not found")

                return

            for pair in pair_store.get_all_pairs():
                await self.post_pair_information(
                    pair, channel, session, latest_eth_price
                )
