import discord

import Variables
from commands.command import Command


class Ping(Command):
    """Basic ping"""

    def __init__(self) -> None:
        super().__init__()
        self.extraHelp["info"] = "Just pongs"

    async def execute(self, client: discord.Client, channel: discord.Channel, user: discord.user.User, params) -> None:
        print(f"ping trigger, {Variables.MINECRAFT_RUNNING}, {Variables.MINECRAFT_TERMINATED}")
        await (client.send_message(channel, "Pong"))