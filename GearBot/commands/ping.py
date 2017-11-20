import discord

from commands.command import Command


class Ping(Command):
    """Basic ping"""

    def __init__(self) -> None:
        super().__init__()
        self.extraHelp["info"] = "Just pongs"

    async def execute(self, client: discord.Client, channel: discord.Channel, user: discord.user.User, params) -> None:
        await (client.send_message(channel, "Pong"))