import discord

import Variables
from Util import GearbotLogging
from commands.command import Command


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
        await GearbotLogging.logToLogChannel(f"Shutdown initiated by {user.name}")
        await client.close()


class Upgrade(OwnerCommand):
    """Perform an upgrade to the latest version"""

    def __init__(self) -> None:
        super().__init__()
        self.extraHelp["info"] = "Upgrade to the next tier"

    async def execute(self, client: discord.Client, channel: discord.Channel, user: discord.user.User, params) -> None:
        await client.send_message(channel, "<:BCWrench:344163417981976578> I'll be right back with new gears! <:woodGear:344163118089240596> <:stoneGear:344163146325295105> <:ironGear:344163170664841216> <:goldGear:344163202684289024> <:diamondGear:344163228101640192>")
        await GearbotLogging.logToLogChannel(f"Upgrade initiated by {user.name}")
        file = open("upgradeRequest", "w")
        file.write("upgrade requested")
        file.close()
        await client.logout()
        await client.close()
