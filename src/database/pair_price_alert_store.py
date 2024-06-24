from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from models.token import PairPriceAlert


class PairPriceAlertStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_latest_price_alert(self, pair_address: str) -> PairPriceAlert | None:
        stmt = (
            select(PairPriceAlert)
            .where(PairPriceAlert.pair_address == pair_address)
            .order_by(PairPriceAlert.created_at.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def add_price_alert(self, pair_price_alert: PairPriceAlert) -> None:
        self.session.add(pair_price_alert)

    def delete_price_alert_for_pair(self, pair_address: str) -> None:
        stmt = delete(PairPriceAlert).where(PairPriceAlert.pair_address == pair_address)
        self.session.execute(stmt)
