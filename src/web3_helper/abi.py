import logging
import time
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.token import ContractCache
from web3_helper.helper import Web3Helper

ABI = dict[str, Any]

logger = logging.getLogger(__name__)


class ABIFetcher:
    def __init__(self, *, base_scan_api_key: str) -> None:
        self.base_scan_api_key = base_scan_api_key

    def get_contracts_from_api(self, address: str) -> ABI:
        logger.info(f"ABI for {address} not found, fetching it from basescan.org...")
        return Web3Helper.fetch_abi(address, self.base_scan_api_key)


class ABIManager:
    def __init__(self, *, session: Session, abi_fetcher: ABIFetcher) -> None:
        self.session = session
        self.abi_fetcher = abi_fetcher

    def fetch_from_database(self, *, address: str) -> ContractCache | None:
        stmt = select(ContractCache).where(ContractCache.address == address)
        return self.session.scalar(stmt)

    def get_abi(self, *, address: str) -> list[dict[str, Any]]:
        contract_cache = self.fetch_from_database(address=address)
        if not contract_cache:
            contract = self.abi_fetcher.get_contracts_from_api(address)

            contract_cache = ContractCache(
                address=address, contract=contract, created_at=int(time.time())
            )

            self.session.add(contract_cache)
            self.session.commit()

        return cast(list[dict[str, Any]], contract_cache.contract["abi"])
