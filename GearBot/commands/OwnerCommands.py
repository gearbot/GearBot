import discord

import Variables
from commands.command import Command
from Util import GearbotLogging


class OwnerCommand(Command):
    def canExecute(self, user):
        return user.id == Variables.APP_INFO.owner.id


class Stop(OwnerCommand):
    """Stops the bot"""

    def __init__(self) -> None:
        super().__init__()
        self.extraHelp["info"] = "Stop turning the gears"

    async def execute(self, client, channel, user, params):
        await client.send_message(channel, 'Shutting down')
        await client.close()


class Upgrade(OwnerCommand):
    """Perform an upgrade to the latest version"""

    def __init__(self) -> None:
        super().__init__()
        self.extraHelp["info"] = "Upgrade to the next tier"

    async def execute(self, client: discord.Client, channel: discord.Channel, user: discord.user.User, params) -> None:
        await client.send_message(channel, "I'll be right back with new gears!")
        await GearbotLogging.logToLogChannel(f"Upgrade initiated by {user.name}")
        file = open("upgradeRequest", "w")
        file.write("upgrade requested")
        file.close()
        await client.logout()
        await client.close()
