import logging
import time
from threading import Thread

from database.pair_store import PairStore
from database.position_store import PositionStore
from database.session_factory import SessionFactory
from database.strategy_state_store import StrategyStateStore
from database.token_store import TokenStore
from models.strategy_state import StrategyState
from tradebot.trade_strategies.prudent_pump_strategy import PrudentPumpStrategy
from tradebot.trade_strategies.stop_loss_strategy import StopLossStrategy
from tradebot.trade_strategies.trade_strategy import StrategyContext, TradeStrategy
from web3_helper.helper import Web3Client

logger = logging.getLogger(__name__)


class StrategyFactory:
    def __init__(self) -> None:
        self.mapping = {
            PrudentPumpStrategy.NAME: PrudentPumpStrategy,
            StopLossStrategy.NAME: StopLossStrategy,
        }

    def all_names(self) -> list[str]:
        return ["none"] + list(self.mapping.keys())

    def create(self, strategy_name) -> TradeStrategy | None:
        if strategy_name not in self.mapping:
            return None

        return self.mapping[strategy_name]()


class PairStrategyWorker(Thread):
    def __init__(
        self,
        session_factory: SessionFactory,
        web3_client: Web3Client,
        pair_address: str,
    ) -> None:
        super().__init__()
        self.session_factory = session_factory
        self.web3_client = web3_client
        self.pair_address = pair_address
        self.strategy_factory = StrategyFactory()
        self.ended = False

    def run(self) -> None:
        try:
            self.inner_run()
        except Exception as exp:
            logger.exception(f"PairStrategyWorker error")

        self.ended = True

    def inner_run(self) -> None:
        while True:
            tick = 0
            with self.session_factory.session() as session:

                pair_store = PairStore(session)
                token_store = TokenStore(session)
                position_store = PositionStore(session)
                strategy_state_store = StrategyStateStore(session)

                pair = pair_store.get_pair(self.pair_address)
                if not pair:
                    logger.info(f"Pair {self.pair_address} doesn't exists...")
                    break

                if pair.strategy:
                    position = position_store.get_position(pair.address)
                    base_token = token_store.get_token(pair.base_address)
                    quote_token = token_store.get_token(pair.quote_address)
                    latest_quote = pair_store.get_latest_quote(pair.address)

                    if not base_token or not quote_token or not latest_quote:
                        # TODO
                        logger.warning(f"missing some fields...")
                        continue

                    if strategy := self.strategy_factory.create(pair.strategy):
                        db_last_state = strategy_state_store.get_last_state(
                            pair_address=pair.address,
                            strategy_name=pair.strategy,
                        )

                        last_state = (
                            strategy.state_from_dict(db_last_state.data)
                            if db_last_state
                            else strategy.new_state()
                        )

                        strategy_context = StrategyContext(
                            pair=pair,
                            tick=tick,
                            state=last_state,
                            latest_quote=latest_quote,
                            base_token=base_token,
                            quote_token=quote_token,
                            position=position,
                            web3_client=self.web3_client,
                        )

                        result = strategy.run(
                            session=session,
                            context=strategy_context,
                        )
                        tick += 1
                        strategy_state_store.add_or_update_state(
                            StrategyState(
                                pair_address=pair.address,
                                strategy_name=pair.strategy,
                                data=strategy.dump_state(result.state),
                                created_at=int(time.time()),
                            )
                        )

                        session.commit()

            time.sleep(0.25)

        self.ended = True


class StrategiesWorker(Thread):
    def __init__(
        self, session_factory: SessionFactory, web3_client: Web3Client
    ) -> None:
        super().__init__()
        self.session_factory = session_factory
        self.strategy_factory = StrategyFactory()
        self.web3_client = web3_client
        self.pair_strategy_workers: dict[str, PairStrategyWorker] = {}

    def run(self) -> None:
        logger.info(f"Starting {self.__class__.__name__} thread")

        while True:
            with self.session_factory.session() as session:
                for pair in PairStore(session).get_all_pairs():
                    if pair.address not in self.pair_strategy_workers:
                        self.pair_strategy_workers[pair.address] = PairStrategyWorker(
                            self.session_factory, self.web3_client, pair.address
                        )

                        self.pair_strategy_workers[pair.address].start()

            to_removes: list[str] = []
            for pair_address, worker in self.pair_strategy_workers.items():
                if worker.ended:
                    to_removes.append(pair_address)

            for pair_address in to_removes:
                self.pair_strategy_workers.pop(pair_address)

            time.sleep(2)
