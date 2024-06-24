import logging
import time
from decimal import Decimal

from discord import TextChannel
from sqlalchemy.orm import Session

from chatbot.command.base_command import BaseCommand
from database.pair_price_alert_store import PairPriceAlertStore
from database.pair_store import PairStore
from database.position_store import PositionStore
from database.session_factory import SessionFactory
from database.token_store import TokenStore
from ext_api.dexscreener import DexScreener
from models.token import Pair, PairPriceAlert, PairQuote
from models.utils import get_position_metric
from web3_helper.helper import Web3Client

logger = logging.getLogger(__name__)


class UpdatePairQuotesCommand(BaseCommand):
    ALERT_THRESHOLD = 10

    def __init__(
        self, *, session_factory: SessionFactory, web3_client: Web3Client
    ) -> None:
        super().__init__(
            name="pair_quotes", description="Update all tracked pair quotes"
        )

        self.session_factory = session_factory
        self.web3_client = web3_client

    async def analyze_pair_price_change(
        self,
        *,
        pair: Pair,
        latest_quote: PairQuote,
        session: Session,
        channel: TextChannel,
    ) -> None:

        pair_store = PairStore(session)
        token_store = TokenStore(session)
        pair_price_alert_store = PairPriceAlertStore(session)
        if position := PositionStore(session).get_position(pair.address):
            quote_token = token_store.get_token(pair.quote_address)
            base_token = token_store.get_token(pair.base_address)
            if base_token and quote_token:
                position_metric = get_position_metric(
                    position=position,
                    web3_client=self.web3_client,
                    base_token=base_token,
                    latest_quote=latest_quote,
                )

                latest_price_alert = pair_price_alert_store.get_latest_price_alert(
                    pair.address
                )

                latest_alert_pnl_percent = (
                    latest_price_alert.pnl_percent if latest_price_alert else Decimal(0)
                )

                current_diff = (
                    Decimal(position_metric.profit_and_loss_percent)
                    - latest_alert_pnl_percent
                )
                abs_current_diff = abs(current_diff)

                if abs_current_diff > self.ALERT_THRESHOLD:
                    # new alert here
                    new_alert = PairPriceAlert(
                        pair_address=pair.address,
                        price=latest_quote.price,
                        pnl_percent=Decimal(position_metric.profit_and_loss_percent),
                        pnl=position_metric.profit_and_loss,
                        created_at=int(time.time()),
                    )

                    pair_price_alert_store.add_price_alert(new_alert)
                    session.commit()

                    sign = "+" if current_diff > 0 else "-"

                    messages = [
                        f"Price Alert for {base_token.symbol} {sign}10%",
                        f"PnL WETH (%): {sign}{abs(position_metric.profit_and_loss)} ({'{0:.2f}'.format(position_metric.profit_and_loss_percent)} %)",
                    ]

                    await channel.send("\n".join(messages))

    async def execute(self, *, channel: TextChannel, args: list[str] = []) -> None:
        with self.session_factory.session() as session:
            pair_store = PairStore(session)
            pairs = {pair.address: pair for pair in pair_store.get_all_pairs()}
            pair_addresses = list(pairs.keys())
            pairs_response = (
                DexScreener.get_pairs(pair_addresses) if pair_addresses else None
            )

            pairs_tuples: list[tuple[Pair, PairQuote]] = []

            if pairs_response:
                for dex_pair in pairs_response.pairs:
                    if pair := pairs.get(dex_pair.pairAddress):
                        latest_quote = PairQuote(
                            pair_address=pair.address,
                            price=self.web3_client.web3.to_wei(
                                dex_pair.priceNative, "ether"
                            ),
                            data=dex_pair.model_dump(),
                            timestamp=int(time.time()),
                        )

                        if pair_store.get_quote_by_data_hash(
                            pair.address, latest_quote.data_hash
                        ):
                            logging.info(
                                f"Quote with same hash for {pair.address} already exists, hash={latest_quote.data_hash}"
                            )
                            continue

                        pair_store.add_pair_quote(latest_quote)
                        session.commit()
                        pairs_tuples.append((pair, latest_quote))

            for pair, pair_quote in pairs_tuples:
                await self.analyze_pair_price_change(
                    pair=pair,
                    latest_quote=pair_quote,
                    session=session,
                    channel=channel,
                )
