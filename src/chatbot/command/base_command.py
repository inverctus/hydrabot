from discord import TextChannel


class BaseCommand:
    def __init__(
        self, *, name: str, short_hand: str | None = None, description: str = ""
    ) -> None:
        self.name = name
        self.short_hand = short_hand
        self.description = description

    async def execute(self, *, channel: TextChannel, args: list[str] = []) -> None:
        raise NotImplementedError()
