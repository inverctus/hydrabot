from ext_api.dexscreener import DexPair


class DexId:
    def __init__(self, name: str, version: str) -> None:
        self.name = name
        self.version = version

    def to_str(self) -> str:
        return f"{self.name}:{self.version}"

    @classmethod
    def from_str(cls, dex_str: str) -> "DexId":
        data = dex_str.split(":")
        if len(data) == 2:
            return cls(data[0].lower(), data[1].lower())
        elif len(data) == 1:
            return cls(data[0].lower(), "v2")

        raise Exception(f"invalid string")

    @classmethod
    def from_dex_pair(cls, dex_pair: DexPair) -> "DexId":
        name = dex_pair.dexId
        version = "v1"

        if name == "uniswap":
            version = "v3"

            if "v2" in dex_pair.labels:
                version = "v2"

        return cls(name, version)
