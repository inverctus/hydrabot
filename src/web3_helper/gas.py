import time

from pydantic import BaseModel

from web3_helper.helper import Web3Client


class GasEstimate(BaseModel):
    base_fee: int
    priority_fee: int


class BlockFee(BaseModel):
    number: int
    baseFeePerGas: int
    gasUsedRatio: float
    priorityFeePerGas: list[int]


class GasHelper:
    def __init__(
        self,
        *,
        web3_client: Web3Client,
        estimate_duration: int = 60,
        overhead: float = 0.1
    ) -> None:
        self.web3_client = web3_client
        self.last_estimate_time = 0
        self.gas = GasEstimate(base_fee=0, priority_fee=0)
        self.estimate_duration = estimate_duration
        self.overhead = overhead

    def _get_latest_block_fees(self, blocks_count: int = 4) -> list[BlockFee]:
        fee_history = self.web3_client.web3.eth.fee_history(
            blocks_count,
            "pending",
            [25, 50, 75],
        )

        block_fees: list[BlockFee] = []

        blocks_count = len(fee_history["reward"])
        oldest_block = fee_history["oldestBlock"]
        block_id = int(oldest_block)
        index = 0

        while block_id < oldest_block + blocks_count:
            index = block_id - oldest_block
            block_fees.append(
                BlockFee(
                    number=block_id,
                    baseFeePerGas=int(fee_history["baseFeePerGas"][index]),
                    gasUsedRatio=float(fee_history["gasUsedRatio"][index]),
                    priorityFeePerGas=[int(x) for x in fee_history["reward"][index]],
                )
            )

            block_id += 1

        return block_fees

    def get_average_from_block_fees(self, block_fees: list[BlockFee]) -> int:
        total = 0
        for block_fee in block_fees:
            total += block_fee.baseFeePerGas

        return int(total / len(block_fees))

    def get_average_priority_from_block_fees(self, block_fees: list[BlockFee]) -> int:
        total = 0
        for block_fee in block_fees:
            total += block_fee.priorityFeePerGas[1]

        return int(total / len(block_fees))

    def _generate_estimate(self) -> GasEstimate:
        block_fees = self._get_latest_block_fees()
        average_gas_price = self.get_average_from_block_fees(block_fees)
        average_priority_fee = self.get_average_priority_from_block_fees(block_fees)

        return GasEstimate(
            base_fee=int(
                float(average_gas_price) + (self.overhead * float(average_gas_price))
            ),
            priority_fee=average_priority_fee,
        )

    def estimated_gas_price(self) -> GasEstimate:
        now = int(time.time())
        if (now - self.last_estimate_time) > self.estimate_duration:
            self.gas = self._generate_estimate()
            self.last_estimate_time = now

        return self.gas
