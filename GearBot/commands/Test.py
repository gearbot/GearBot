import discord

import Variables
from commands.OwnerCommands import OwnerCommand
from commands.command import Command


class Test(Command):
    """Testing things"""

    def __init__(self) -> None:
        super().__init__()
        self.extraHelp["info"] = "Used for testing, only available in debug mode"

    def canExecute(self, user: discord.user.User) -> bool:
        return Variables.DEBUG_MODE

    async def execute(self, client, channel, user, params):
        raise Exception("just making sure this works")
