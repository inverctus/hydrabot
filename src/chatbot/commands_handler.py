from discord import TextChannel

from chatbot.command.base_command import BaseCommand


class CommandsHandler:
    def __init__(
        self, *, prefix: str, commands: list[BaseCommand], separator: str = " "
    ) -> None:
        self.prefix = prefix
        self.commands = commands
        self.separator = separator

    def find_command(self, command_name: str) -> BaseCommand | None:
        for command in self.commands:
            if command.name.lower() == command_name.lower() or (
                command.short_hand
                and command_name.lower() == command.short_hand.lower()
            ):
                return command

        return None

    async def execute(self, *, message: str, channel: TextChannel) -> None:
        if message.startswith(self.prefix):
            data = message.split(self.separator)
            command_name = data[0].lstrip(self.prefix)
            args = data[1:]

            if command_name == "help":
                messages = ["Hydrabot available command(s):"]
                messages.extend(
                    [
                        f"{self.prefix}{command.name} : {command.description}"
                        for command in self.commands
                    ]
                )

                await channel.send("\n".join(messages))

            elif command := self.find_command(command_name):
                await command.execute(channel=channel, args=args)
            else:
                await channel.send(
                    "Unknown command, use !help to see available commands"
                )
